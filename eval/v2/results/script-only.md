# v2 script-only check (gold quotes, no model)

Each draft item's marked detail is checked against its gold quotes: the supporting quotes for a
correct fact, the sentence a careless checker would most likely cite for an error.

| Item type | Items | Flagged by the script |
|---|---|---|
| supported | 75 | 0 |
| number | 9 | 7 |
| outdated | 4 | 0 |
| invented | 5 | 5 |
| contradiction | 11 | 1 |
| computed | 1 | 1 |

| Item | Type | Script result | Marked detail |
|---|---|---|---|
| DE1-1 | outdated | supported | hall b |
| DE1-2 | contradiction | supported | lend you one |
| DE1-3 | invented | no_evidence | build weekend t-shirt |
| DE1-4 | number | supported | midnight |
| DE1-5 | supported | supported | 16 january at 09:00 |
| DE1-6 | supported | supported | 17 january at 17:00 |
| DE1-7 | supported | supported | 08:15 |
| DE1-8 | supported | supported | laptop and charger |
| DE1-9 | supported | supported | student id card |
| DE1-10 | supported | supported | breakfast and lunch on sunday |
| DE1-11 | supported | supported | vegetarian and halal |
| DE1-12 | supported | supported | cannot stay overnight |
| DE1-13 | supported | supported | 14:00 on sunday |
| DE1-14 | supported | supported | demos start at 14:30 |
| DE2-1 | contradiction | supported | no age limit |
| DE2-2 | number | numbers_not_in_quote | 2 to 5 |
| DE2-3 | computed | numbers_not_in_quote | 32 hours |
| DE2-4 | invented | numbers_not_in_quote | rm 800 |
| DE2-5 | supported | supported | 16–17 january 2027 |
| DE2-6 | supported | supported | kuala lumpur |
| DE2-7 | supported | supported | match you with a team |
| DE2-8 | supported | supported | deposit of rm 50 |
| DE2-9 | supported | supported | both days |
| DE2-10 | supported | supported | rm 3,000 |
| DE2-11 | supported | supported | rm 1,500 |
| DE2-12 | supported | supported | 3 january 2027 at 23:59 |
| DE2-13 | supported | supported | 120 participants |
| DE3-1 | outdated | supported | rm 300 |
| DE3-2 | contradiction | supported | flights are covered |
| DE3-3 | contradiction | supported | in cash |
| DE3-4 | number | numbers_not_in_quote | 7 days |
| DE3-5 | supported | supported | more than 100 km |
| DE3-6 | supported | supported | bus or train fares |
| DE3-7 | supported | supported | up to 20 grants |
| DE3-8 | supported | supported | 20 december 2026 |
| DE3-9 | supported | supported | 28 december 2026 |
| DE3-10 | supported | supported | 9 january 2027 at 23:59 |
| DE3-11 | supported | supported | rm 50 back in full |
| DE3-12 | supported | supported | medical certificate |
| DE4-1 | number | numbers_not_in_quote | presentation (25%) |
| DE4-2 | contradiction | supported | broken by the presentation |
| DE4-3 | number | numbers_not_in_quote | up to 5 minutes |
| DE4-4 | contradiction | supported | started before the event |
| DE4-5 | supported | supported | five judges |
| DE4-6 | supported | supported | usefulness (30%) |
| DE4-7 | supported | supported | technical execution (30%) |
| DE4-8 | supported | supported | design (20%) |
| DE4-9 | supported | supported | 4-minute demo |
| DE4-10 | supported | supported | 2 minutes of questions |
| DE4-11 | supported | supported | public code repository |
| DE4-12 | supported | supported | ai tools |
| DE4-13 | supported | supported | at most one prize |
| DE4-14 | supported | supported | no third-place prize |
| DZ1-1 | number | numbers_not_in_quote | 一个月内退回 |
| DZ1-2 | contradiction | supported | 通宵 |
| DZ1-3 | invented | no_evidence | 代金券 |
| DZ1-4 | supported | supported | 上午9点开始 |
| DZ1-5 | supported | supported | 下午5点结束 |
| DZ1-6 | supported | supported | hall c |
| DZ1-7 | supported | supported | 8点15分开门 |
| DZ1-8 | supported | supported | 自己填写报名表 |
| DZ1-9 | supported | supported | 50令吉押金 |
| DZ1-10 | supported | supported | 2027年1月3日23:59 |
| DZ1-11 | supported | supported | 提前截止 |
| DZ1-12 | supported | supported | 只在线下举行 |
| DZ1-13 | supported | supported | 学生证 |
| DZ2-1 | contradiction | supported | 去年毕业 |
| DZ2-2 | invented | no_evidence | 奶茶 |
| DZ2-3 | outdated | supported | 最多300令吉 |
| DZ2-4 | number | numbers_not_in_quote | 名额只有100个 |
| DZ2-5 | supported | supported | 1月16日到17日 |
| DZ2-6 | supported | supported | 吉隆坡 |
| DZ2-7 | supported | supported | 年满18岁的在读大学生 |
| DZ2-8 | supported | supported | 2到4人 |
| DZ2-9 | supported | supported | 周六上午现场帮你组队 |
| DZ2-10 | supported | supported | 3000令吉 |
| DZ2-11 | supported | supported | 1500令吉 |
| DZ2-12 | supported | supported | 500令吉的最佳无障碍 |
| DZ2-13 | supported | supported | 队员平分 |
| DZ2-14 | supported | supported | 报名1月3日截止 |
| DZ3-1 | outdated | supported | 下午1点 |
| DZ3-2 | contradiction | numbers_not_in_quote | 两个项目 |
| DZ3-3 | number | supported | 设计占30% |
| DZ3-4 | contradiction | supported | 按技术实现得分 |
| DZ3-5 | supported | supported | 逾期提交的作品不参加评审 |
| DZ3-6 | supported | supported | 公开的代码仓库链接 |
| DZ3-7 | supported | supported | 不超过3分钟 |
| DZ3-8 | supported | supported | ai工具 |
| DZ3-9 | supported | supported | 评委一共5位 |
| DZ3-10 | supported | supported | 四项打分 |
| DZ3-11 | supported | supported | 30天内 |
| DZ3-12 | supported | supported | 银行转账 |
| DZ4-1 | contradiction | supported | 访客停车场 |
| DZ4-2 | invented | no_evidence | 共享单车 |
| DZ4-3 | number | numbers_not_in_quote | 提前3天 |
| DZ4-4 | supported | supported | 12 jalan contoh |
| DZ4-5 | supported | supported | 大约400米 |
| DZ4-6 | supported | supported | 无台阶入口 |
| DZ4-7 | supported | supported | 电梯 |
| DZ4-8 | supported | supported | 无障碍卫生间 |
| DZ4-9 | supported | supported | 2.04号房间 |
| DZ4-10 | supported | supported | 40个储物柜 |
| DZ4-11 | supported | supported | 自带挂锁 |
| DZ4-12 | supported | supported | 扫二维码 |
| DZ4-13 | supported | supported | 保管30天 |
