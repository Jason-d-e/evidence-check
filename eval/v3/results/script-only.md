# v3 script-only check

36 claims from `eval/v3/cases.json`, written before the script change. A correct claim should pass; a wrong claim (a changed number) must be flagged; a limit claim is true but states a number the document does not, and is flagged on purpose.

| Rule | Correct claims passed (0.2.0 → current) | Wrong claims flagged (0.2.0 → current) | Limit claims flagged |
|---|---|---|---|
| month and year | 1/2 → 2/2 | 1/2 → 2/2 | — |
| fractions | 1/2 → 2/2 | 2/2 → 2/2 | — |
| negated 一 | 0/2 → 2/2 | 2/2 → 2/2 | — |
| none is 0 | 0/1 → 1/1 | 1/1 → 1/1 | — |
| 百 in 每百万 | 0/1 → 1/1 | 1/1 → 1/1 | — |
| 万 and million | 0/2 → 2/2 | 3/3 → 3/3 | — |
| percent and decimal | 0/2 → 2/2 | 1/1 → 1/1 | — |
| names with numbers | 1/3 → 3/3 | 3/3 → 3/3 | — |
| document title | 0/1 → 1/1 | 2/2 → 2/2 | — |
| not handled | — | — | 3/3 |
| **Total** | **3/16 → 16/16** | **16/17 → 17/17** | **3/3** |

## Every claim

| ID | Kind | Claim | 0.2.0 | Current | Missing numbers (current) |
|---|---|---|---|---|---|
| A01 | correct | 报告于 2025 年 12 月发布。 | numbers_not_in_quote | supported | — |
| A02 | correct | The report came out in December 2025. | supported | supported | — |
| A03 | wrong | 报告于 2025 年 11 月发布。 | numbers_not_in_quote | numbers_not_in_quote | 11 |
| A04 | wrong | The autumn meetup was held in November 2025. | supported | numbers_not_in_quote | 11 |
| B01 | correct | 约三分之一的会员是 2025 年加入的。 | numbers_not_in_quote | supported | — |
| B02 | correct | About one third of members joined in 2025. | supported | supported | — |
| B03 | wrong | 约四分之一的会员是 2025 年加入的。 | numbers_not_in_quote | numbers_not_in_quote | 1/4 |
| B04 | wrong | About two-thirds of members joined during 2025. | numbers_not_in_quote | numbers_not_in_quote | 2/3 |
| C01 | correct | 48 次评分运行，一次都没有失败。 | numbers_not_in_quote | supported | — |
| C02 | correct | 48 次评分运行里没有一次失败。 | numbers_not_in_quote | supported | — |
| C03 | wrong | 48 次评分运行里有 1 次失败。 | numbers_not_in_quote | numbers_not_in_quote | 1 |
| C04 | wrong | 48 次评分运行里有一次失败。 | numbers_not_in_quote | numbers_not_in_quote | 1 |
| D01 | correct | 0 of the 48 scoring runs failed. | numbers_not_in_quote | supported | — |
| D02 | wrong | 2 of the 48 scoring runs failed. | numbers_not_in_quote | numbers_not_in_quote | 2 |
| E01 | correct | 语音转写每百万 token 收费 0.10 美元。 | numbers_not_in_quote | supported | — |
| E02 | wrong | 语音转写每百万 token 收费 0.20 美元。 | numbers_not_in_quote | numbers_not_in_quote | 0.2 |
| F01 | correct | 会员达到 4.3万人。 | numbers_not_in_quote | supported | — |
| F02 | correct | Membership reached 43,000 people. | numbers_not_in_quote | supported | — |
| F03 | wrong | 会员达到 4.8万人。 | numbers_not_in_quote | numbers_not_in_quote | 48000 |
| F04 | wrong | 会员达到 43万人。 | numbers_not_in_quote | numbers_not_in_quote | 430000 |
| F05 | wrong | Membership reached 4.3 million people. | numbers_not_in_quote | numbers_not_in_quote | 4300000 |
| G01 | correct | Agreement between the two passes was 99.6%. | numbers_not_in_quote | supported | — |
| G02 | correct | 两遍的一致率是 0.996。 | numbers_not_in_quote | supported | — |
| G03 | wrong | Agreement between the two passes was 96.6%. | numbers_not_in_quote | numbers_not_in_quote | 96.6 |
| H01 | correct | echo-asr-2025-08-28 costs US$0.10 per million tokens. | numbers_not_in_quote | supported | — |
| H02 | correct | With ranker-v3.2, every result was checked twice. | numbers_not_in_quote | supported | — |
| H03 | wrong | Answers were scored with ranker-v4.1. | numbers_not_in_quote | numbers_not_in_quote | 4.1 |
| H04 | wrong | The p90 latency was 2.1 seconds. | numbers_not_in_quote | numbers_not_in_quote | 2.1 |
| H05 | correct | Venue hire cost RM4,350. | supported | supported | — |
| H06 | wrong | Venue hire cost RM4,530. | numbers_not_in_quote | numbers_not_in_quote | 4530 |
| I01 | correct | Update notice 2 moves the autumn meetup to Room 6. | numbers_not_in_quote | supported | — |
| I02 | wrong | Update notice 2 moves the autumn meetup to Room 5. | numbers_not_in_quote | numbers_not_in_quote | 5 |
| I03 | wrong | Update notice 3 moves the autumn meetup to Room 6. | numbers_not_in_quote | numbers_not_in_quote | 3 |
| L01 | limit | The spring meetup was a two-day event. | numbers_not_in_quote | numbers_not_in_quote | 2 |
| L02 | limit | Venue hire and catering together cost RM 6,530. | numbers_not_in_quote | numbers_not_in_quote | 6530 |
| L03 | limit | 会员约 4 万人。 | numbers_not_in_quote | numbers_not_in_quote | 40000 |
