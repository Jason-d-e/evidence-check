// One promptfoo test per case. Only the case id is passed; the provider reads the question or draft
// from the cases file. Set V2_CASES=smoke-cases.json for the harness check (not part of the evaluation).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const { questions, drafts } = JSON.parse(fs.readFileSync(path.join(here, process.env.V2_CASES ?? "cases.json"), "utf8"));

export default [
  ...questions.map((q) => ({ description: `${q.id} (${q.lang}, answer)`, vars: { case_id: q.id } })),
  ...drafts.map((d) => ({ description: `${d.id} (${d.lang}, draft: ${d.kind})`, vars: { case_id: d.id } })),
];
