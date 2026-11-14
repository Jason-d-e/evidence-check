# v4 script-only check

28 claims from `eval/v4/cases.json`, written before the script change. A correct claim should pass; a wrong claim (a changed number) must be flagged; a limit claim is true but states a number the document does not, or rounds it too coarsely, and is flagged on purpose.

| Rule | Correct claims passed (0.3.0 → current) | Wrong claims flagged (0.3.0 → current) | Limit claims flagged |
|---|---|---|---|
| rounding | 0/5 → 5/5 | 4/4 → 4/4 | 2/2 |
| Chinese ordinals | 0/2 → 2/2 | 2/2 → 2/2 | — |
| a third without of | 0/1 → 1/1 | 2/2 → 2/2 | — |
| time with seconds | 0/1 → 1/1 | 2/2 → 2/2 | — |
| name with a spaced number | 0/1 → 1/1 | 1/1 → 1/1 | — |
| quoted names | 0/1 → 1/1 | 2/2 → 2/2 | — |
| not handled | — | — | 2/2 |
| **Total** | **0/11 → 11/11** | **13/13 → 13/13** | **4/4** |

## Every claim

| ID | Kind | Claim | 0.3.0 | Current | Missing numbers (current) | Rounded (current) |
|---|---|---|---|---|---|---|
| A01 | correct | In round 4, agreement on the hard set was 0.31. | numbers_not_in_quote | supported | — | 0.31 ← 0.314 |
| A02 | correct | 第四轮简单题的一致率是 0.36。 | numbers_not_in_quote | supported | — | 0.36 ← 0.3649 |
| A03 | correct | The refusal rate was 17%. | numbers_not_in_quote | supported | — | 17 ← 16.5 |
| A04 | correct | 平均每个回答用时 156 秒。 | numbers_not_in_quote | supported | — | 156 ← 155.9 |
| A05 | wrong | In round 4, agreement on the hard set was 0.32. | numbers_not_in_quote | numbers_not_in_quote | 0.32 | — |
| A06 | wrong | The refusal rate was 18%. | numbers_not_in_quote | numbers_not_in_quote | 18 | — |
| A07 | limit | In round 4, agreement on the hard set was 0.3. | numbers_not_in_quote | numbers_not_in_quote | 0.3 | — |
| A08 | wrong | The sample held 120 answers. | numbers_not_in_quote | numbers_not_in_quote | 120 | — |
| A09 | correct | 会员约 8.5 万人。 | numbers_not_in_quote | supported | — | 85000 ← 85252 |
| A10 | wrong | 会员约 8.6 万人。 | numbers_not_in_quote | numbers_not_in_quote | 86000 | — |
| A11 | limit | 会员约 9 万人。 | numbers_not_in_quote | numbers_not_in_quote | 90000 | — |
| B01 | correct | 第 6 条规定作品要在周日下午 2 点前提交。 | numbers_not_in_quote | supported | — | — |
| B02 | wrong | 第 7 条规定作品要在周日下午 2 点前提交。 | numbers_not_in_quote | numbers_not_in_quote | 7 | — |
| B03 | correct | 第二轮复核时，48 条结果一次都没变。 | numbers_not_in_quote | supported | — | — |
| B04 | wrong | 第三轮复核时，48 条结果一次都没变。 | numbers_not_in_quote | numbers_not_in_quote | 3 | — |
| C01 | correct | 刚好不到三分之一的被标出的回答被拒绝。 | numbers_not_in_quote | supported | — | — |
| C02 | wrong | 刚好不到四分之一的被标出的回答被拒绝。 | numbers_not_in_quote | numbers_not_in_quote | 1/4 | — |
| C03 | wrong | 四分之一的结果已经公布。 | numbers_not_in_quote | numbers_not_in_quote | 1/4 | — |
| D01 | correct | 评分在 22:18 开始。 | numbers_not_in_quote | supported | — | — |
| D02 | wrong | 评分在 22:19 开始。 | numbers_not_in_quote | numbers_not_in_quote | 22:19 | — |
| D03 | wrong | 评分在 22:18:45 开始。 | numbers_not_in_quote | numbers_not_in_quote | 22:18:45 | — |
| E01 | correct | SigLIP 2 找到 5 处违规。 | numbers_not_in_quote | supported | — | — |
| E02 | wrong | SigLIP 3 找到 5 处违规。 | numbers_not_in_quote | numbers_not_in_quote | 3 | — |
| F01 | correct | “一次提示词”组拦下了 30 条。 | numbers_not_in_quote | supported | — | — |
| F02 | wrong | “两次提示词”组拦下了 30 条。 | numbers_not_in_quote | numbers_not_in_quote | 2 | — |
| F03 | wrong | “一次提示词”组拦下了 31 条。 | numbers_not_in_quote | numbers_not_in_quote | 31 | — |
| L01 | limit | “strict-v2”组通过了 85% 的检查。 | numbers_not_in_quote | numbers_not_in_quote | 85 | — |
| L02 | limit | 两个模型一共找到 8 处违规。 | numbers_not_in_quote | numbers_not_in_quote | 2, 8 | — |
