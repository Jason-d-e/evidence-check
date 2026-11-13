# evidence-check（有据可查）

一个 [Agent Skill](https://agentskills.io)：让 AI 写的每一句事实都附上你自己资料里的逐字原文，再用一个脚本核对这些原文。

[English](README.md)

根据资料写的回答和草稿，常常错在不起眼又要命的地方：截止日期差了一天，时长是自己算的而不是照抄的，多出一个哪份资料都没写的细节。evidence-check 让 Agent 给每个事实注明出处，然后由脚本确认：

1. **引文确实在所引的文件里**（大小写、空格、弯引号、标点的差别不算）；
2. **说法里的每个日期、时间、金额、数量都出现在引文里**，中英文可以互相对照：`下午2点` 对得上 `14:00`，`五位` 对得上 `Five`，`4.3万` 对得上 `43,000`，引文写的是 `13:00` 时，`13:30` 过不了。

脚本看不懂意思：一句真实存在的原文，可能被拿来支持相反的说法。所以 Skill 还要求 Agent 把每条通过脚本的说法和引文对照着读一遍。

## 两种用法

- **只依据资料回答。** “只根据 handbook.md 和 faq.md 回答，每句给出处。”过不了脚本的说法会先被改正或删掉，你看到的回答里每句都有原文。
- **核对一份草稿。** “用规章文件夹核对这份通知。”Agent 把草稿拆成一条条说法，给每条找原文，跑脚本，再逐条报告问题：资料原话是什么，建议怎么改。它不会替你改草稿。

## 安装

Claude Code，作为插件安装：

```
/plugin marketplace add Jason-d-e/evidence-check
/plugin install evidence-check@evidence-check
```

其他支持 Agent Skills 的工具：把 `skills/evidence-check/` 复制到它的 Skill 文件夹（不用插件的 Claude Code 是 `~/.claude/skills/evidence-check/`）。

脚本只需要 Python 3.9 或以上，不用装别的包。

## 自己跑脚本

claims 文件列出每条说法和支持它的原文：

```json
{"claims": [
  {"id": "2", "text": "Projects must be submitted by 13:30 on Sunday.",
   "evidence": [{"source": "B02-update-notice-1.md",
                 "quote": "Project submission now closes on Sunday 17 January 2027 at 14:00 MYT instead of 13:00."}]}
]}
```

```bash
python skills/evidence-check/scripts/check_evidence.py claims.json --sources eval/v2/sources --format markdown --lang zh
```

用 `eval/v2/sources` 里的示例资料核对四条说法，结果是：第 1 条（报名 2027 年 1 月 3 日 23:59 截止）有依据；第 2 条（13:30 前提交）数字在引文里找不到，缺 `13:30`；第 3 条（押金是50令吉）对上了英文原文 “refundable deposit of RM 50”；第 4 条（每人送一件 T 恤）没有给出依据。完整表格见 [英文说明](README.md#run-the-script-yourself)。

退出码 0 表示全部通过，1 表示至少一条没通过，2 表示输入读不了。`--format json` 输出完整报告。字段和匹配规则见 [`references/claims-format.md`](skills/evidence-check/references/claims-format.md)。

## 能抓到什么

| | 脚本 | Agent 读意思 | 处理不了 |
|---|---|---|---|
| 引文被改过、拼接过或编造 | ✓ | | |
| 日期、时间、金额、数量被改 | ✓ | | |
| 数字是自己算出来的（把 19:00 到 20:30 说成“两小时”） | ✓ | | |
| 说法没有出处 | ✓ | | |
| 用真实原文支持相反的意思、漏掉条件、说大了范围 | | ✓ | |
| 旧值已被新文件替换，但旧文件还在资料里 | | v2 题目里都抓到了 | |
| 四舍五入、加总和换算（`约 4 万` 对 `43,000`）、罗马数字：会标出来，由你核对 | | | ✓ |

## 相关工具

- **Claude API 的 [Citations](https://platform.claude.com/docs/en/build-with-claude/citations)（引用功能）** 直接从你的文档里截取引文，引文一定在原文里。在这个 API 上做产品，就用它。它是在 Messages API 里给 Claude 正在写的回答附出处：不检查说法里的数字是否在引文里；用工具读文件的 Agent 和其他模型用不到它；也不会把别人写好的草稿拆成一条条说法来核对。evidence-check 管的是这几块。
- **云平台的依据检查**（Vertex AI check grounding、Azure AI Content Safety groundedness detection、Amazon Bedrock Guardrails contextual grounding check）和**开源检测模型**（LettuceDetect、MiniCheck、HHEM）用模型判断一段话有没有依据。evidence-check 给每条说法附上原文和行号，比对数字不用模型、不用云账号，也不用装别的包。
- **评测框架**（RAGAS、DeepEval、TruLens、promptfoo）事后给一批测试题打分。这个项目的评测用的是 promptfoo。

## 评测

在虚构资料上做了两轮，同一个模型（Claude Haiku 5.5）装和不装 Skill，每道题跑两遍：

- **v1，84 句已拆好的句子。** 普通提示词 168 个判断已经对了 167 个；漏掉的那一句是算错的时长（把 19:00 到 20:30 说成“两小时”），脚本抓住了。
- **v2，留出题：16 道自由作答、8 篇没拆好的草稿。** 三种做法都抓到了全部 30 处埋好的错误。唯一编出来的数字是自己算的“32 小时”（普通提示词 32 个回答里有 4 个，SKILL.md v0.2 一个也没有），脚本每次都能标出来。如果事后才对普通提示词的输出跑脚本，它会把 150 处正确事实里的 12 处也判成不通过，因为引文不完整；装了 Skill，Agent 会自己补齐引文，只剩 2 到 3 处误报。代价是每个任务的费用约为普通提示词的 3 倍。
- **脚本 0.3.0，来自真实使用。** 针对在真实文件上出现的误报加了 9 条比对规则（`December 2025`、`三分之一`、`4.3万`、`99.6%` 对 `0.996`、带版本号的模型名）。在改动之前定好的 36 道新题上，正确说法的通过数从 16 条里 3 条变成 16 条全过，17 处改过的数字仍然全部标出；v1、v2 的结果一处没变。

完整报告（英文）：[`eval/EVALUATION.md`](eval/EVALUATION.md)。测试用的资料和草稿是虚构的，和 Skill 出自同一作者。

## 开发

```bash
python -m unittest discover -s tests -v     # 离线测试，不调用模型
python eval/script_only.py                  # 只用脚本核对 v1 题目
python eval/v2/score.py --check             # 检查 v2 题目本身
python eval/v3/run.py                       # 比对规则：脚本 0.2.0 和当前版本对照
```

模型对比评测用 [promptfoo](https://www.promptfoo.dev)，需要 Node.js，并在 `eval/.env` 里放 Anthropic API 密钥（`ANTHROPIC_API_KEY=...`）；运行命令写在每个 `promptfooconfig.yaml` 的开头。

## 许可证

MIT，见 [LICENSE](LICENSE)。
