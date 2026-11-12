// promptfoo provider for the v2 held-out evaluation of evidence-check.
//
// Three arms, same model, effort, documents and JSON output; only the instructions differ:
//   plain       one-sentence instruction, no tools;
//   skill-v0.1  the body of SKILL.md v0.1 (frozen copy) and a check_evidence tool;
//   skill-v0.2  the body of SKILL.md v0.2 (frozen copy) and the same tool.
// The tool runs the real checking script (frozen copy) on the claims the model passes, the way an
// agent with a shell would run `python scripts/check_evidence.py`. Two kinds of task:
//   answer  answer a question from the documents (Mode A);
//   draft   check an unsplit draft (Mode B).
// Labels and markers in cases.json never reach the model.
//
// The API key is read from an .env file (EVAL_ENV_FILE, relative to the eval folder; default eval/.env),
// never from process.env, so this cannot pick up credentials that belong to other tools. It is never logged.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import { parseEnv } from "node:util";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";

const here = path.dirname(fileURLToPath(import.meta.url));
const EVAL_DIR = path.resolve(here, "..");
const MODEL = "claude-haiku-5-5"; // cheapest current model, chosen by the user
const EFFORT = "medium";
const PRICE = { input: 0.1 / 1e6, output: 0.5 / 1e6 }; // Claude Haiku 5.5 list price, prompts up to 100K tokens
const MAX_TOOL_ROUNDS = 4;
// Resolve the real interpreter once: a launcher such as the Windows Python install manager needs the
// full environment, while the script itself is then run with a minimal one.
const PYTHON = (() => {
  const launcher = process.env.EVAL_PYTHON ?? "python";
  const r = spawnSync(launcher, ["-c", "import sys; print(sys.executable)"], { encoding: "utf8" });
  return r.status === 0 && r.stdout.trim() ? r.stdout.trim() : launcher;
})();

const envFile = path.resolve(EVAL_DIR, process.env.EVAL_ENV_FILE ?? ".env");
const apiKey = fs.existsSync(envFile) ? (parseEnv(fs.readFileSync(envFile, "utf8")).ANTHROPIC_API_KEY ?? "").trim() : "";

const sha12 = (text) => crypto.createHash("sha256").update(text).digest("hex").slice(0, 12);
const readJson = (f) => JSON.parse(fs.readFileSync(path.join(here, f), "utf8"));
const cases = readJson("cases.json");
const smoke = fs.existsSync(path.join(here, "smoke-cases.json")) ? readJson("smoke-cases.json") : { questions: [], drafts: [] };

const SOURCE_DIR = path.join(here, "sources");
const sourcesText = cases.sources
  .map((f) => `=== ${f} ===\n${fs.readFileSync(path.join(SOURCE_DIR, f), "utf8").trim()}`)
  .join("\n\n");
const SCRIPT = path.join(here, "frozen", "check_evidence.py");
const SCRIPT_SHA = sha12(fs.readFileSync(SCRIPT));

function loadSkill(version) {
  const file = fs.readFileSync(path.join(here, "skill-versions", `SKILL-${version}.md`), "utf8");
  return { body: file.replace(/^---[\s\S]*?\n---\n/, "").trim(), sha: sha12(file) };
}
const SKILLS = { "v0.1": loadSkill("v0.1"), "v0.2": loadSkill("v0.2") };

const PLAIN = {
  answer:
    "Answer the user's question using the source documents. For each fact in your answer, give the source file name and the supporting text.",
  draft:
    "You check whether a draft is supported by the source documents. Split the draft into separate claims. For each claim, decide whether the documents support it, and for a supported claim give the source file name and the supporting text.",
};

function skillSystem(version, kind) {
  return [
    "You have the following skill loaded. Follow it.",
    "",
    '<skill name="evidence-check">',
    SKILLS[version].body,
    "</skill>",
    "",
    "In this run there is no shell. Run the script through the check_evidence tool instead: it runs scripts/check_evidence.py with --format markdown on the claims you pass, against the source documents in the user's message, and returns the exit code and the report.",
    kind === "answer"
      ? "Work in Mode A."
      : 'Work in Mode B. In your final JSON, give verdict "supported" only to claims that passed the script and your own reading; give every other claim "unsupported".',
    "When you are done, reply with the final result in the required JSON format.",
  ].join("\n");
}

function userMessage(c) {
  if (c.kind === "answer") {
    return `Source documents:\n\n${sourcesText}\n\nQuestion: ${c.question}\n\nReply in JSON. status: "answered", or "not_in_documents" if the documents do not answer the question. claims: the sentences of your answer to the user, in order, one fact each, each with its evidence (source file name and supporting text). With not_in_documents, the claims may say so and point to the closest passage.`;
  }
  return `Source documents:\n\n${sourcesText}\n\nDraft to check (${c.draftKind}):\n\n${c.text}\n\nReply in JSON. claims: every checkable claim in the draft, in order. For each: draft_text (the words of the draft it comes from, copied exactly), text (the claim, one fact), verdict (supported or unsupported) and evidence (source file name and supporting text; empty if none).`;
}

const EVIDENCE = {
  type: "array",
  items: {
    type: "object",
    additionalProperties: false,
    required: ["source", "quote"],
    properties: { source: { type: "string" }, quote: { type: "string" } },
  },
};
const SCHEMA = {
  answer: {
    type: "object",
    additionalProperties: false,
    required: ["status", "claims"],
    properties: {
      status: { type: "string", enum: ["answered", "not_in_documents"] },
      claims: {
        type: "array",
        items: {
          type: "object",
          additionalProperties: false,
          required: ["text", "evidence"],
          properties: { text: { type: "string" }, evidence: EVIDENCE },
        },
      },
    },
  },
  draft: {
    type: "object",
    additionalProperties: false,
    required: ["claims"],
    properties: {
      claims: {
        type: "array",
        items: {
          type: "object",
          additionalProperties: false,
          required: ["draft_text", "text", "verdict", "evidence"],
          properties: {
            draft_text: { type: "string" },
            text: { type: "string" },
            verdict: { type: "string", enum: ["supported", "unsupported"] },
            evidence: EVIDENCE,
          },
        },
      },
    },
  },
};

const TOOL = {
  name: "check_evidence",
  description:
    "Runs scripts/check_evidence.py on a claims file built from your input, against the source documents in the user's message (use their file names as source). Returns the exit code (0: every claim supported, 1: at least one not, 2: bad input) and the script's report.",
  strict: true,
  input_schema: {
    type: "object",
    additionalProperties: false,
    required: ["lang", "claims"],
    properties: {
      lang: { type: "string", enum: ["en", "zh"] },
      claims: {
        type: "array",
        items: {
          type: "object",
          additionalProperties: false,
          required: ["id", "text", "evidence"],
          properties: { id: { type: "string" }, text: { type: "string" }, evidence: EVIDENCE },
        },
      },
    },
  },
};

function findCase(id) {
  for (const set of [cases, smoke]) {
    const q = set.questions.find((x) => x.id === id);
    if (q) return { kind: "answer", question: q.question };
    const d = set.drafts.find((x) => x.id === id);
    if (d) return { kind: "draft", text: d.text, draftKind: d.kind };
  }
  return null;
}

function runScript(input) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "evcheck-"));
  try {
    const file = path.join(dir, "claims.json");
    fs.writeFileSync(file, JSON.stringify({ claims: Array.isArray(input?.claims) ? input.claims : [] }), "utf8");
    // A minimal environment: the script needs nothing else, and no credentials are passed on.
    const env = Object.fromEntries(
      Object.entries({ PATH: process.env.PATH, SYSTEMROOT: process.env.SYSTEMROOT, PYTHONIOENCODING: "utf-8" }).filter(([, v]) => v),
    );
    const lang = input?.lang === "zh" ? "zh" : "en";
    const r = spawnSync(PYTHON, [SCRIPT, file, "--sources", SOURCE_DIR, "--format", "markdown", "--lang", lang], {
      encoding: "utf8",
      timeout: 60_000,
      env,
    });
    const code = r.status ?? 2;
    const report = `${r.stdout ?? ""}${r.stderr ? `\n${r.stderr}` : ""}`.trim();
    // No report on stdout means the script itself did not run (as opposed to a claim failing).
    return { code, text: `exit code ${code}\n\n${report}`, broken: !(r.stdout ?? "").trim() };
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

let client = null;
function getClient() {
  client ??= new Anthropic({ apiKey, baseURL: "https://api.anthropic.com", timeout: 180_000, maxRetries: 3 });
  return client;
}

export default class EvidenceCheckV2Provider {
  constructor(options = {}) {
    this.arm = options.config?.arm;
    this.version = options.config?.version;
    this.label = options.label ?? this.arm;
  }

  id() {
    return `evidence-check-v2:${this.arm}${this.version ? `-${this.version}` : ""}`;
  }

  async callApi(_prompt, context) {
    if (!apiKey) return { error: `NOT RUN: no ANTHROPIC_API_KEY in ${envFile}` };
    const c = findCase(context?.vars?.case_id);
    if (!c) return { error: `unknown case ${context?.vars?.case_id}` };
    const skill = this.arm === "skill";
    const system = skill ? skillSystem(this.version, c.kind) : PLAIN[c.kind];
    const messages = [{ role: "user", content: userMessage(c) }];
    const usage = { input: 0, output: 0 };
    const toolLog = [];
    let apiCalls = 0;
    const started = Date.now();
    try {
      for (let round = 0; round <= MAX_TOOL_ROUNDS + 2; round++) {
        const params = {
          model: MODEL,
          max_tokens: 16000,
          output_config: { effort: EFFORT, format: { type: "json_schema", schema: SCHEMA[c.kind] } },
          system,
          messages,
        };
        if (skill) {
          params.tools = [TOOL];
          if (round > MAX_TOOL_ROUNDS) params.tool_choice = { type: "none" };
        }
        const response = await getClient().messages.create(params);
        apiCalls += 1;
        usage.input += response.usage?.input_tokens ?? 0;
        usage.output += response.usage?.output_tokens ?? 0;
        if (response.stop_reason === "refusal") return { error: "refused" };
        if (response.stop_reason === "max_tokens") return { error: "cut off at max_tokens" };
        if (response.stop_reason === "tool_use") {
          messages.push({ role: "assistant", content: response.content });
          const results = [];
          for (const block of response.content.filter((b) => b.type === "tool_use")) {
            if (round >= MAX_TOOL_ROUNDS) {
              results.push({ type: "tool_result", tool_use_id: block.id, is_error: true, content: "Tool limit reached. Reply with the final JSON now." });
              continue;
            }
            const r = runScript(block.input);
            toolLog.push({ exit: r.code, broken: r.broken, claims: Array.isArray(block.input?.claims) ? block.input.claims.length : 0 });
            results.push({ type: "tool_result", tool_use_id: block.id, content: r.text });
          }
          messages.push({ role: "user", content: results });
          continue;
        }
        const text = response.content.filter((b) => b.type === "text").map((b) => b.text).join("");
        if (!text) return { error: `empty output (stop_reason ${response.stop_reason})` };
        return {
          output: text,
          tokenUsage: { prompt: usage.input, completion: usage.output, total: usage.input + usage.output },
          cost: usage.input * PRICE.input + usage.output * PRICE.output,
          metadata: {
            latency_ms: Date.now() - started,
            model_served: response.model,
            arm: this.id(),
            skill_sha: skill ? SKILLS[this.version].sha : null,
            script_sha: SCRIPT_SHA,
            effort: EFFORT,
            api_calls: apiCalls,
            tool_calls: toolLog.length,
            tool_log: toolLog,
          },
        };
      }
      return { error: "no final answer after the tool limit" };
    } catch (err) {
      if (err instanceof Anthropic.AuthenticationError) return { error: "API key rejected" };
      if (err instanceof Anthropic.RateLimitError) return { error: "rate limited" };
      if (err instanceof Anthropic.APIError) return { error: `API error ${err.status ?? ""}: ${err.message}` };
      return { error: `failed: ${err.message}` };
    }
  }
}
