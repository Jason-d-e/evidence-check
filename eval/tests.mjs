// One promptfoo test per draft. Only the draft id is passed; the provider reads the
// sentences from cases.json. Labels and gold quotes never reach the model.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const { drafts } = JSON.parse(fs.readFileSync(path.join(here, "cases.json"), "utf8"));

export default drafts.map((d) => ({
  description: `${d.id} (${d.lang}, ${d.kind})`,
  vars: { draft_id: d.id },
}));
