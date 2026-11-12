// promptfoo custom provider: asks Claude Haiku 5.5 to check one draft against the source
// documents, with either a plain instruction or the evidence-check skill as the system prompt.
// Both arms use the same model, effort, documents and JSON output format; only the
// instructions differ. The labels in cases.json are never sent to the model.
//
// The API key is read from an .env file (EVAL_ENV_FILE, relative to this folder; default eval/.env),
// never from process.env, so this cannot pick up credentials that belong to other tools. It is never logged.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { parseEnv } from "node:util";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";

const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, "..");
const MODEL = "claude-haiku-5-5"; // cheapest current model, chosen by the user
const EFFORT = "medium";
// Claude Haiku 5.5 list price per token (prompts up to 100K tokens).
const PRICE = { input: 0.1 / 1e6, output: 0.5 / 1e6 };

const envFile = path.resolve(here, process.env.EVAL_ENV_FILE ?? ".env");
const apiKey = fs.existsSync(envFile) ? (parseEnv(fs.readFileSync(envFile, "utf8")).ANTHROPIC_API_KEY ?? "").trim() : "";

const cases = JSON.parse(fs.readFileSync(path.join(here, "cases.json"), "utf8"));
const sourceFiles = Object.values(cases.sources);
const sourcesText = sourceFiles
  .map((f) => `=== ${f} ===\n${fs.readFileSync(path.join(here, "sources", f), "utf8").trim()}`)
  .join("\n\n");

const skillFile = fs.readFileSync(path.join(ROOT, "skills/evidence-check/SKILL.md"), "utf8");
const skillBody = skillFile.replace(/^---[\s\S]*?\n---\n/, "").trim();
export const SKILL_SHA = crypto.createHash("sha256").update(skillFile).digest("hex").slice(0, 12);

const SYSTEM = {
  plain:
    "You check whether a draft is supported by the source documents. For each numbered line, decide whether the documents support it. For a supported line, give the source file name and the supporting text.",
  skill: [
    "You have the following skill loaded. Follow it.",
    "",
    "<skill name=\"evidence-check\">",
    skillBody,
    "</skill>",
    "",
    "In this run you cannot execute the script yourself. Work in Mode B and return one entry per numbered line in the required JSON format: verdict \"supported\" only when you found a quote that states the claim; otherwise \"unsupported\" with an empty evidence list or the closest quote. The script will be run on your output.",
  ].join("\n"),
};

const SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["claims"],
  properties: {
    claims: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["id", "verdict", "evidence"],
        properties: {
          id: { type: "string" },
          verdict: { type: "string", enum: ["supported", "unsupported"] },
          evidence: {
            type: "array",
            items: {
              type: "object",
              additionalProperties: false,
              required: ["source", "quote"],
              properties: { source: { type: "string" }, quote: { type: "string" } },
            },
          },
        },
      },
    },
  },
};

function userMessage(draft) {
  const lines = draft.sentences.map((s, i) => `${i + 1}. ${s.text}`).join("\n");
  return `Source documents:\n\n${sourcesText}\n\nDraft to check (${draft.kind}; one claim per numbered line):\n${lines}`;
}

let client = null;
function getClient() {
  client ??= new Anthropic({ apiKey, baseURL: "https://api.anthropic.com", timeout: 120_000, maxRetries: 2 });
  return client;
}

export default class EvidenceCheckProvider {
  constructor(options = {}) {
    this.arm = options.config?.arm;
    this.label = options.label ?? this.arm;
  }

  id() {
    return `evidence-check:${this.arm}`;
  }

  async callApi(_prompt, context) {
    if (!apiKey) return { error: `NOT RUN: no ANTHROPIC_API_KEY in ${envFile}` };
    const draft = cases.drafts.find((d) => d.id === context?.vars?.draft_id);
    if (!draft) return { error: `unknown draft ${context?.vars?.draft_id}` };
    const started = Date.now();
    try {
      const response = await getClient().messages.create({
        model: MODEL,
        max_tokens: 16000,
        output_config: { effort: EFFORT, format: { type: "json_schema", schema: SCHEMA } },
        system: SYSTEM[this.arm],
        messages: [{ role: "user", content: userMessage(draft) }],
      });
      const latency_ms = Date.now() - started;
      if (response.stop_reason === "refusal") return { error: "refused" };
      if (response.stop_reason === "max_tokens") return { error: "cut off at max_tokens" };
      const text = response.content.filter((b) => b.type === "text").map((b) => b.text).join("");
      const { input_tokens = 0, output_tokens = 0 } = response.usage ?? {};
      return {
        output: text,
        tokenUsage: { prompt: input_tokens, completion: output_tokens, total: input_tokens + output_tokens },
        cost: input_tokens * PRICE.input + output_tokens * PRICE.output,
        metadata: { latency_ms, model_served: response.model, arm: this.arm, skill_sha: SKILL_SHA, effort: EFFORT },
      };
    } catch (err) {
      if (err instanceof Anthropic.AuthenticationError) return { error: "API key rejected" };
      if (err instanceof Anthropic.RateLimitError) return { error: "rate limited" };
      if (err instanceof Anthropic.APIError) return { error: `API error ${err.status ?? ""}: ${err.message}` };
      return { error: `failed: ${err.message}` };
    }
  }
}
