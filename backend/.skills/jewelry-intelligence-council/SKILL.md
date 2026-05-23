---
name: jewelry-intelligence-council
description: 当用户要求"运行智囊团"、"生成战略决策报告"、"多专家分析情报"、"产出行行动建议"、"运行 council"，或提到"智囊团"、"战略决策"、"行动建议"、"部门行动"、"上中下三策"时应使用此技能。当需要对一批市场情报进行多维度专家分析并产出可执行战略报告时同样适用。
version: 2.0
---

# 珠宝海外市场战略情报智囊团

在情报清洗结果之后，引入五位领域专家对同一批市场情报**并行分析**，
再由总参谋汇总为**管理层可直接执行**的战略决策报告。

## 解决什么问题

主流水线阶段 7「行动」原先用单个 LLM + 部门模板产出建议，存在三个问题：

1. **视角单一**：一个 prompt 同时看品类、竞品、消费者、风险、战略，每个维度都浅。
2. **判断不可追溯**：结论与证据脱钩，"金价涨=利好"这类粗判断难以拦截。
3. **不可直接执行**：输出常停在"需关注 XX"，没有落到部门、品类、渠道、动作。

智囊团用**专家分工 + 强制证据绑定 + 总参谋综合**解决这三点。

## 执行模式

`parallel_then_synthesis`：五位专家对同一批情报并行独立分析，互不看对方输出；
随后总参谋综合五份输出。

```
intelligence_batch（清洗结果）
        │
        ├──▶ 产品营销战略专家 ─┐
        ├──▶ 竞品战略专家     ─┤
        ├──▶ 消费者洞察专家   ─┼──▶ 总参谋 ──▶ 决策报告
        ├──▶ 风险合规专家     ─┤
        └──▶ 兵法谋士         ─┘
```

## 阶段一：五专家并行分析

为五位专家各启动一次独立调用，互不看对方输出。每位专家遵循各自的
Skill 定义文件，只在自己 Scope 内深挖，每个判断必须绑定 `evidence_ids`。

### 产品营销战略专家

- **聚焦**：珠宝品类机会 / 金钻珍珠彩宝趋势 / 价格带 / 节日营销 / 社媒内容打法 / 新品方向
- **核心能力**：从情报中识别品类机会与新品/营销打法，判断哪些值得立即投入
- **分析框架**：分品类拆解 → 机会窗口判断 → 价格带定位 → 营销节点对齐 → 打法建议
- **特别注意**：金价相关情报必须区分投资金条 / 饰品金 / 婚庆金 / 悦己金饰，它们对金价上涨的反应方向相反
- **详细定义**：`references/experts/product_marketing_strategist.md`

### 竞品战略专家

- **聚焦**：国际与本地品牌动作 / 门店扩张 / 定价策略 / 联名代言广告投放 / 渠道变化
- **核心能力**：还原竞争对手正在做什么，推断为什么这样做，判断对我方意味着威胁还是机会
- **分析框架**：动作归类 → 意图推断 → 威胁/机会定性 → 应对方向
- **特别注意**：区分事实与意图推断（意图必须标注 `inference`）
- **详细定义**：`references/experts/competitor_strategy_analyst.md`

### 消费者洞察专家

- **聚焦**：婚庆消费 / 悦己消费 / 年轻客群 / 高净值客群 / 宗教文化偏好 / 社媒情绪
- **核心能力**：还原是谁在买、为什么买、购买意愿在如何变化
- **分析框架**：客群归属 → 意愿vs情绪辨别 → 文化校准 → 客群变化方向
- **特别注意**：社媒讨论热度上升 ≠ 购买意愿上升，只有社媒证据时置信度不得高于 medium
- **详细定义**：`references/experts/consumer_insight_analyst.md`

### 风险合规专家

- **聚焦**：金价波动 / 汇率 / 关税 / 广告合规 / 文化禁忌 / 地缘政治与监管变化
- **核心能力**：识别会侵蚀利润、阻断渠道、引发处罚或舆情反噬的风险
- **分析框架**：风险归类 → 金价双向分析 → 传导路径 → 严重度评级 → 对冲方向
- **特别注意**：金价上涨不是单向利好也不是单向利空，必须按投资金/饰品金/婚庆金/悦己金分别判断
- **详细定义**：`references/experts/risk_compliance_analyst.md`

### 兵法谋士

- **聚焦**：用孙子兵法 + 毛选框架判局 / 主要矛盾 / 匹配 12 条策略库计策 / 上中下三策思路
- **核心能力**：用战略框架判读市场局势，匹配策略库计策，给出三策思路
- **分析框架**：判局（定战场/敌我/虚实/势 + 主要矛盾/一分为二） → 计策匹配（策略库） → 三策思路
- **特别注意**：不做角色扮演、不用第一人称；计策匹配必须用 `strategy_library.json` 真实存在的 `strategy_id`，不得编造
- **谋略知识源**：孙子兵法（`references/knowledge/sunzi-strategy/`）、毛选（`references/knowledge/maoxuan/`）、12 条兵法策略库（`references/knowledge/strategy_library.json`）
- **详细定义**：`references/experts/military_strategist.md`

## 阶段二：总参谋综合

把五份专家输出、原始情报批次、一手来源占比一并交给总参谋。总参谋执行
七步综合：交叉验证 → 机会×风险对冲 → 金价裁定 → 裁定专家分歧 → 构造上中下三策 →
拆解部门行动 → 结算证据链与置信度。

- **详细定义**：`references/experts/chief_strategy_officer.md`
- **综合指令**：`references/prompts/synthesis.md`

## 领域铁律（所有专家与总参谋共同遵守）

| 原则 | 说明 |
|------|------|
| 证据绑定 | 没有 `evidence_ids` 的判断不写 |
| 证据不足降置信度 | 单一来源 / 未验证社媒 / 单时间点 → 置信度不得高于 medium |
| 金价不简单等于利好 | 必须区分投资金条 / 饰品金 / 婚庆金 / 悦己消费 |
| 行动具体化 | 落到部门 + 市场 + 品类 + 渠道 + 动作 |
| sentiment ≠ impact | 来源情绪 ≠ 对我方业务的影响方向 |
| 保留分歧 | 专家冲突如实写入 `expert_disagreements`，不和稀泥 |
| 兵法落地 | 计策必须用 `strategy_library.json` 真实存在的 `strategy_id` |
| 可直接执行 | 输出面向管理层，无需二次翻译 |

## 降级与异常

| 情况 | 处理 |
|------|------|
| 某专家调用失败 | 不阻塞其他专家；总参谋标注缺失该视角，整体置信度下调一档 |
| items 少于 3 条 | 仍执行，但整体置信度不得高于 medium |
| 一手来源占比 < 30% | 置信度 level 不得为 high |
| 专家输出非合法 JSON | 对该专家重试一次；仍失败则视为调用失败 |

## 输入格式

接收符合 `references/input_schema.json` 的 JSON 对象：`batch_meta`
（market / region / time_window）+ `items` 结构化情报事件数组。

## 输出格式

产出符合 `references/output_schema.json` 的单个 JSON 对象。必含段落：

`council_summary`、`market`、`time_window`、`key_signals`、`opportunities`、
`risks`、`watch_items`、`strategic_options`（上/中/下策）、`department_actions`
（产品/营销/渠道/管理层/风险）、`evidence_chain`、`expert_disagreements`、
`confidence`、`next_observation_points`。

## 附加资源

- **`references/input_schema.json`** — 完整输入 JSON Schema
- **`references/output_schema.json`** — 完整输出 JSON Schema
- **`references/experts/`** — 五位分析专家 + 总参谋的详细 Skill 定义
- **`references/prompts/`** — 编排 prompt 与综合 prompt
- **`references/knowledge/`** — 兵法谋士的谋略知识库（孙子兵法 / 毛选 / 策略库）
- **`examples/`** — 输入输出样例
