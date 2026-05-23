---
name: intelligence-correlation-analysis
description: 当用户要求"分析事件关联"、"查找事件间因果链路"、"识别跨市场联动"、"检测情报时序模式"、"发现隐性依赖"、"运行关联分析"，或提到"关联分析"、"传导链路"、"跨市场关联"、"因果分析"、"时序模式"、"信息关联"、"隐性依赖"时应使用此技能。当多条情报事件需要从关系角度而非孤立视角审视时同样适用。
version: 2.0.0
---

# 情报关联分析 Skill

## 这个 Skill 做什么

接收一批已完成预分类和评分的结构化情报事件，识别事件之间不可见的因果传导
链路、隐性依赖和时序模式，输出可直接驱动决策看板与智囊团模块的关联分析 JSON。

单条评分告诉你"这件事有多重要"；关联分析告诉你"这些事合在一起意味着什么"。

---

## 第零步：前置校验（必须先执行，校验失败则拒绝分析）

在执行任何分析之前，对输入执行以下校验。任一项不通过，立即输出
`ANALYSIS_REJECTED` 对象并停止，不得在不合格输入上强行生成结论。

```
校验 V1 · 数量下限
  条件：items 数组长度 ≥ 3
  失败处理：输出 {"status": "ANALYSIS_REJECTED", "reason": "事件数量不足3条，
             无法建立关联，建议补充信号后重新提交"}

校验 V2 · 时间窗口上限
  条件：batch_meta.time_window 跨度 ≤ 90 天
  失败处理：输出 {"status": "ANALYSIS_REJECTED", "reason": "时间跨度超过90天，
             跨期噪音过高，建议拆分为更短时间窗口后分批提交"}

校验 V3 · 结构化完整度
  条件：每条 item 必须包含 env_factors（非空数组）和 impact_scope（非空数组）
  失败处理：列出缺失字段的 event_id，输出
             {"status": "ANALYSIS_REJECTED", "reason": "以下事件缺少必要字段，
             请先完成预分类步骤：[event_ids]"}

校验 V4 · 可关联性
  条件：至少存在 2 对事件共享相同的 env_factor 或 impact_scope 值
  失败处理：输出 {"status": "ANALYSIS_REJECTED", "reason": "事件间无结构化重叠
             字段，关联分析将退化为纯推测，建议补充事件或检查预分类质量"}
```

校验全部通过后，在内部记录 `_validated: true`，然后进入第一步。

---

## 第一步：候选关联对筛选

**目标**：从 N 条事件的 N×(N-1)/2 个可能配对中，筛选出值得深入分析的候选对，
避免对所有配对暴力枚举。

**筛选规则（满足任一即进入候选）**：

```
规则 R1 · 字段重叠
  env_factors 主因子相同，OR impact_scope 有 ≥1 个共同值
  → 候选类型标记：field_overlap

规则 R2 · 传导链路共属
  conduction_chain.chain_id 相同
  → 候选类型标记：same_chain

规则 R3 · 强度异动
  两条事件 intensity ≥ 4，且 collected_at 时间差 ≤ 14 天
  → 候选类型标记：intensity_cluster

规则 R4 · 方向矛盾
  signal_direction 一正一负，且 impact_scope 有重叠
  → 候选类型标记：direction_conflict（此类候选优先处理，矛盾信号价值最高）
```

**筛选后**：将候选对按 `direction_conflict > same_chain > intensity_cluster >
field_overlap` 优先级排序，最多处理前 15 对。超出部分记录 event_id 并标注
`"skipped_pairs": N`，不强行扩展。

---

## 第二步：逐对关联判定

对每个候选对，按以下判定树执行，每个判定节点都是强制检查，不可跳过。

```
节点 J1 · 时序确认
  ├─ 问：两事件是否存在明确的时序先后（collected_at 差 > 0）？
  ├─ 是 → 记录 time_lag_days = 日历天数差，进入 J2
  └─ 否（同日）→ 标记 time_lag_days = 0，进入 J2，但 causal 方向不可声称

节点 J2 · 机制验证（铁律 #1 内嵌：相关 ≠ 因果）
  ├─ 问：能否用供需/价格/政策/消费行为机制解释 A 如何作用于 B？
  ├─ 能清晰表达机制 → 候选 correlation_type = causal 或 lead_lag，进入 J3
  ├─ 机制模糊但方向一致 → correlation_type = reinforcing 或 co_occurrence，进入 J4
  └─ 无法表达机制，仅时序接近 → correlation_type = co_occurrence，
     strength 强制设为 weak，confidence ≤ 0.5，跳至 J5

节点 J3 · 共因排查（铁律 #4 内嵌：排除共因）
  ├─ 问：是否存在第三个事件 C，使得 C→A 且 C→B 更合理？
  ├─ 存在 C → 降级：将 causal 改为 co_occurrence，在 description 中记录
  │  "共因假设：[C的描述]，原因果声明降级为共现"
  └─ 不存在 C → 维持 causal/lead_lag，进入 J4

节点 J4 · 强度定级（量化锚点，禁止主观评估）
  strong  要求同时满足：机制有明确经济学/供需逻辑支撑 + time_lag_days 在
          传导时滞参考范围内（见下方时滞参考表）+ evidence_ids ≥ 2 条独立来源
  moderate 满足其中 2 项
  weak    满足其中 ≤ 1 项，或机制为推断性质
  → 记录 strength，进入 J5

节点 J5 · 置信度计算（铁律 #5 内嵌：证据不足降置信度）
  基础分：strong=0.8  moderate=0.65  weak=0.45
  调整规则（叠加）：
    + 0.10：evidence_ids 包含官方公告/财报/监管文件
    + 0.05：有 ≥ 2 条独立来源印证
    - 0.15：evidence_ids 全部为社媒/未验证来源
    - 0.10：time_lag_days 超出传导时滞参考范围上限
    - 0.10：仅单一时间点观测（铁律 #5）
  最终 confidence 取值范围 [0.20, 0.95]，超出则截断
  → 输出该候选对的完整关联边对象
```

**传导时滞参考表**（用于 J4 强度定级和 J5 置信度调整）：

```
价格传导（F5）跨市场：        1–7 天     超出 14 天降级
供给约束（F1）→ 成本传导：   7–30 天    超出 60 天降级
制度摩擦（F4）→ 运营响应：  14–60 天    超出 90 天降级
结构重塑（F2）→ 份额变化：  30–180 天   超出 365 天降级
需求迁移（F3）→ 品类重构：  60–365 天   单季度内不声称因果完成
叙事压力（F6）→ 定价权：    14–90 天    依赖多个验证点
渠道博弈（F7）→ 利润分配：  30–120 天   超出 180 天降级
```

---

## 第三步：因果链组装

完成所有关联边判定后，从 `correlation_type = causal` 或 `lead_lag` 且
`strength ≠ weak` 的边中，尝试拼接多级传导链（A→B→C）。

**组装规则**：

```
规则 C1 · 链路有效性
  一条有效链路：长度 ≥ 2 条边（≥ 3 个节点），且每条边的 confidence ≥ 0.5

规则 C2 · 节点角色分配
  trigger   ：链路起点，且在批次时间窗口内无前驱事件
  amplifier ：自身 intensity ≥ 4，且使下游信号方向强化
  mediator  ：连接两端的中介节点，可以是尚未在输入中出现的推断节点
              （推断节点必须在 mechanism 中标注 "[推断节点，非输入事件]"）
  outcome   ：链路终点，或当前观测窗口内最下游的已知结果

规则 C3 · 替代解释（铁律 #4 强化）
  每条链路必须填写 alternative_explanation。
  不接受"无替代解释"——如果想不到，填写：
  "当前证据不足以排除共因驱动，[列举可能的共因]可能是更合理的解释"

规则 C4 · 链路置信度
  chain.confidence = MIN(所有组成边的 confidence) × 0.9
  （链路越长，整体置信度越低，这是刻意的保守设计）
```

---

## 第四步：时序模式检测

**前提条件**：此步骤仅在以下条件满足时执行，否则跳过并输出
`"temporal_patterns": []`：
- 输入事件跨度 ≥ 14 天，且
- 同一 env_factor 或 impact_scope 值对应的事件 ≥ 2 条（铁律 #2：单次观测不构成模式）

**检测类型及判定标准**：

```
类型 T1 · 领先-滞后对
  判定：市场 A 的信号方向变化，在 time_lag_days 参考范围内，市场 B 出现同向变化
  至少需要：同一对市场有 ≥ 2 次重复观测
  输出字段：leader_market, follower_market, avg_lag_days, observed_count

类型 T2 · 趋势转向
  判定：同一 env_factor 的事件序列中，signal_direction 从正转负（或反向），
        且连续 ≥ 2 条事件维持新方向
  输出字段：factor_id, turning_point_event_id, direction_before, direction_after

类型 T3 · 强度聚集
  判定：7 天内同一 impact_scope 出现 ≥ 3 条 intensity ≥ 3 的事件
  含义：该范围正在形成信号密度异常，可能是结构变化的早期信号
  输出字段：scope, window_start, window_end, event_count, avg_intensity

类型 T4 · 跨市场同步
  判定：不同 market 的事件在 3 天内出现相同 env_factor 主因子，
        且 signal_direction 相同
  输出字段：markets, factor_id, sync_window_days, possible_common_driver
```

每种模式必须绑定触发该识别的具体 event_id 列表作为 evidence_ids。

---

## 第五步：隐性依赖挖掘

**目标**：识别表面上无直接关联边（未通过第二步筛选），但可能受同一底层宏观
因素驱动的事件群。

**识别流程**：

```
步骤 H1 · 孤立事件识别
  找出未出现在任何 correlation_edge 或 causal_chain 中的事件。

步骤 H2 · 共因假设生成
  对孤立事件两两组合，检查：
  - 是否同期发生（时间差 ≤ 14 天）
  - 是否存在一个未在输入中出现的宏观变量（美元指数/基准利率/地缘事件），
    能同时合理解释两者

步骤 H3 · 假设强度判定
  每条隐性依赖的 confidence 上限为 0.6（铁律 #5：假设性结论不得高置信度）
  evidence 字段必须填写支撑该假设的具体事件特征，不接受"可能受X影响"的模糊表述

步骤 H4 · 分歧记录（铁律 #6 内嵌）
  如果同一事件群存在两种合理的共因假设，两种都写入 hidden_dependencies，
  不取平均，不合并，在每条记录中加 "competing_hypothesis": true
```

---

## 第六步：输出生成

完成以上所有步骤后，按以下 Schema 生成最终 JSON。
**每个字段定义后附有生成约束，这些约束是强制执行的，不是建议。**

```json
{
  "analysis_meta": {
    "skill_version": "2.0.0",
    "input_event_count": "<整数，来自 items 数组长度>",
    "candidate_pairs_evaluated": "<整数，第一步筛选后的候选对数量>",
    "skipped_pairs": "<整数，超出15对上限被跳过的数量，无则填0>",
    "time_window": "<来自 batch_meta.time_window>",
    "validation_passed": true
  },

  "correlation_summary": "<3-5句话。句1：本批次信号的整体市场信号方向。
    句2：最强的一条传导链路描述。句3：最值得关注的矛盾或分歧。
    句4-5（可选）：对下一步观测的具体建议。
    禁止：不得出现'可能'、'或许'等模糊词，不确定性通过置信度字段表达>",

  "correlation_edges": [
    {
      "edge_id": "<格式：edge_01, edge_02 ...>",
      "source_id": "<来自 items 的 event_id>",
      "target_id": "<来自 items 的 event_id>",
      "correlation_type": "<causal|reinforcing|contradicting|co_occurrence|lead_lag>",
      "strength": "<strong|moderate|weak，必须来自 J4 判定树结果，禁止主观填写>",
      "mechanism": "<具体传导机制，必须包含：施力主体 + 传导路径 + 受力客体，
        禁止：'两者相关'、'时序接近'、'市场联动'等无机制内容，限50字>",
      "time_lag_days": "<整数，来自 J1>",
      "within_reference_range": "<boolean，基于传导时滞参考表的判定结果>",
      "evidence_ids": ["<至少1条，填写支撑该关联的 event_id 或外部参考>"],
      "confidence": "<0.20-0.95，必须来自 J5 计算公式结果，禁止主观填写>",
      "downgrade_reasons": ["<J5 中触发了哪些 -0.10/-0.15 调整，无则空数组>"]
    }
  ],

  "causal_chains": [
    {
      "chain_id": "<格式：chain_01, chain_02 ...>",
      "nodes": [
        {
          "event_id": "<event_id 或推断节点描述>",
          "role": "<trigger|amplifier|mediator|outcome>",
          "mechanism": "<该节点在链路中的作用机制，推断节点必须标注[推断节点]>"
        }
      ],
      "description": "<一句话描述整条链路的核心逻辑，格式：[触发事件]
        经由[传导路径]导致[结果]，限60字>",
      "total_lag_days": "<从 trigger 到 outcome 的总估算天数>",
      "alternative_explanation": "<必填，不接受空值。描述可能使本链路失效的
        共因假设或反向因果解释，限60字>",
      "evidence_ids": ["<所有组成边的 source_id 和 target_id 去重后的列表>"],
      "confidence": "<来自规则 C4 的计算结果>"
    }
  ],

  "temporal_patterns": [
    {
      "pattern_id": "<格式：tp_01 ...>",
      "pattern_type": "<lead_lag|trend_turning|intensity_cluster|cross_market_sync>",
      "description": "<模式描述，必须包含观测到的具体数值>",
      "evidence_ids": ["<触发该识别的 event_id 列表，≥2条>"],
      "observed_count": "<触发该模式识别的事件数量>",
      "confidence": "<≤0.6，单一时间窗口观测不得超过此上限>"
    }
  ],

  "hidden_dependencies": [
    {
      "dependency_id": "<格式：hd_01 ...>",
      "affected_event_ids": ["<≥2条>"],
      "hypothesized_driver": "<推测的底层驱动因素，必须是具体的宏观变量或事件，
        禁止'市场环境'、'宏观因素'等泛化表述>",
      "evidence": "<支撑假设的具体特征，不接受模糊表述>",
      "confidence": "<强制 ≤ 0.60>",
      "competing_hypothesis": "<boolean，是否存在另一个同样合理的共因假设>"
    }
  ],

  "expert_disagreements": [
    {
      "disagreement_id": "<格式：dis_01 ...>",
      "event_ids": ["<涉及的事件>"],
      "position_a": "<第一种解读及其支撑理由>",
      "position_b": "<第二种解读及其支撑理由>",
      "resolution": "unresolved"
    }
  ],

  "overall_confidence": {
    "score": "<所有 correlation_edges 的 confidence 均值，保留2位小数>",
    "level": "<high(≥0.75)|medium(0.55-0.74)|low(<0.55)>",
    "limiting_factors": ["<拉低整体置信度的主要原因，最多3条>"]
  },

  "next_observation_points": [
    {
      "observation": "<具体的、可执行的下一步观测建议>",
      "trigger_condition": "<满足什么条件时这个观测点会被确认或否定>",
      "deadline_days": "<建议在多少天内观测，否则信号时效失效>",
      "related_chain_id": "<关联的 chain_id 或 edge_id>"
    }
  ]
}
```

---

## 全局执行约束

以下约束在整个执行过程中始终有效，优先级高于任何步骤描述：

```
GC-1  没有 evidence_ids → 不写结论
      任何输出字段如果无法绑定至少一个具体 event_id，该字段必须输出空数组
      或 null，不得用推断内容填充。

GC-2  不得输出 JSON 之外的任何文字
      包括前置说明、分析过程叙述、后置总结。所有内容必须在 JSON 结构内表达。

GC-3  推断与事实必须在字段中区分
      事实陈述放入 description/mechanism；
      推断和假设放入 alternative_explanation/hypothesized_driver，
      并在文本中显式标注"[推断]"。

GC-4  品类分化不得被平均
      （铁律 #3）同一信号对不同品类方向相反时，必须为每个品类方向生成
      独立的关联边，不得合并为"mixed"后不再区分。

GC-5  置信度不得向上调整
      所有置信度计算只允许从基础分向下调整。如果认为某个关联"应该更高"，
      检查是否遗漏了应降级的因素，而不是向上修正。

GC-6  校验失败优先于任何分析
      第零步校验不通过时，后续步骤一律不执行。
```

---

## 输入格式

接收 JSON 对象，包含以下字段：

```json
{
  "batch_meta": {
    "market": "CN|US|IN|GLOBAL|...",
    "region": "<可选>",
    "time_window": {"start": "ISO8601", "end": "ISO8601"}
  },
  "items": [
    {
      "event_id": "<唯一标识符>",
      "collected_at": "<ISO8601>",
      "source_category": "<来自预分类>",
      "env_factors": [{"factor_id": "F1-F7", "is_primary": true}],
      "conduction_chain": {"chain_id": "A-E", "node_position": "..."},
      "signal_direction": "positive|negative|mixed|neutral",
      "intensity": "<1-5>",
      "impact_scope": ["<范围列表>"],
      "key_claim": "<50字内核心事实>",
      "confidence": "<0.20-0.95>"
    }
  ],
  "historical_context": "<可选，用于时序模式匹配的历史批次摘要>"
}
```

完整 Schema 定义见 `references/input_schema.json`。

---

## 附加资源

- `references/input_schema.json` — 完整输入 JSON Schema
- `references/output_schema.json` — 完整输出 JSON Schema（与本文档第六步 Schema 同步）
- `examples/` — 输入输出样例（待补充）
