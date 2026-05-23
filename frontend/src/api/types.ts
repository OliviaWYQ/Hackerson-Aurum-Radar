export type PageId = 'overview' | 'intel' | 'actions'

export interface Filters {
  country: string
}

// ── Overview types ──────────────────────────────────────────────

export type StatusKind = 'high' | 'mid' | 'risk' | 'competition' | 'regulation' | 'watch'
export type ChipTone = 'sage' | 'clay' | 'gold' | 'indigo' | 'plum' | 'bone'

export interface CountryNode {
  id: string
  name: string
  sub: string
  x: number
  y: number
  status: StatusKind
  size: number
  headline?: string
}

export interface CountryBullet {
  icon: string
  text: string
}

export interface CountryImpact {
  kind: 'opportunity' | 'risk' | 'watch'
  text: string
}

export interface CountryDetail {
  name: string
  sub: string
  status: string
  statusKind: ChipTone
  score: number
  competition: number
  competitionLabel: string
  policy: string
  policyKind: ChipTone
  growth: string
  bullets: CountryBullet[]
  triggers?: string[]
  impacts?: CountryImpact[]
  asOf?: string
}

// ── Map insight types ───────────────────────────────────────────

export type HeatLevel = 'high' | 'mid'

export interface SgRegion {
  id: string
  name: string
  sub: string
  x: number
  y: number
  stores: number
  hot: HeatLevel
  priority?: boolean
}

export interface RegionMetric {
  icon: string
  label: string
  value: string
  unit?: string
  valueClass?: ChipTone
  small?: boolean
}

export interface RegionProfile {
  type: string
  scene: string
  consumption: string
  action: string
}

export interface RegionDetail {
  name: string
  sub: string
  priority: string
  metrics: RegionMetric[]
  profile: RegionProfile
  insights: string[]
  actions: string[]
}

// ── Intelligence types ──────────────────────────────────────────

export type ImpactKind = 'competitive' | 'brand' | 'trend'

export interface EventImpact {
  kind: ImpactKind
  title: string
  text: string
}

// 第二坐标轴 — 底层环境影响因子 (architecture.md §7.3, F1-F7)
export type EnvFactorId = 'F1' | 'F2' | 'F3' | 'F4' | 'F5' | 'F6' | 'F7'

export interface EnvFactor {
  factorId: EnvFactorId
  factorName: string   // structure_disruption / supply_constraint / ...
  label: string        // 中文标签：结构重塑 / 供给约束 / ...
  isPrimary: boolean
  evidence: string
}

// 传导链路 A-E
export type ConductionChainId = 'A' | 'B' | 'C' | 'D' | 'E'

export interface ConductionChain {
  chainId: ConductionChainId
  chainName: string       // 地缘-供给-成本链 / ...
  nodePosition: string    // 信号在链路上的位置
  lagEstimate: string     // 短期/中期/长期
}

export type SignalDirection = 'positive' | 'negative' | 'mixed' | 'neutral'

export interface IntelEvent {
  id: string
  cat: string              // 来源轴中文标签 (向后兼容)
  sourceCategory: string   // 来源轴枚举值 (competition / product / ...)
  title: string
  summary: string
  keyClaim: string         // 纯事实陈述 ≤50 字
  source: string
  srcDetail: string
  time: string
  priority: 'high' | 'mid'
  new?: boolean
  impact: EventImpact[]
  markets: string[]
  brands: string[]
  citation: string
  citationTime: string
  // 新维度 (architecture.md §7.3 双坐标轴抽取产出)
  envFactors: EnvFactor[]
  primaryFactor: EnvFactor | null
  conductionChain: ConductionChain | null
  signalDirection: SignalDirection
  intensity: number              // 1-5
  impactScope: string[]          // category_*/market_*/brand/retailer/...
  downstreamImplications: string[]
  ambiguityFlags: string[]
  confidence: number             // 0-1
  opportunityScore: number
  riskScore: number
}

// ── Actions types ───────────────────────────────────────────────

export type DeptPriority = 'high' | 'mid' | 'low'

export interface DeptStep {
  title: string
  goal: string
  how: string
  when: string
  expectedOutput?: string
  successMetric?: string
}

export interface DeptRef {
  icon: string
  text: string                      // 用户可见的主标题（事件标题 / 策略+渠道）
  detail?: string                   // 副标题（来源 / key_claim）
  sourceUrl?: string                // 可点击外链；为空则不可点击
  eventId?: string                  // 跳转到情报详情用
  factorLabel?: string              // 主因子（如「需求迁移」）
  factorId?: EnvFactorId            // F1-F7
}

export interface DeptSummaryItem {
  text: string
  when: string
}

export interface Department {
  id: string
  name: string
  sub: string
  icon: string
  priority: DeptPriority
  cycle: string
  owner: string
  market?: string
  actionCount?: number
  summary: DeptSummaryItem[]
  goal: string
  steps: DeptStep[]
  refs: DeptRef[]
}

// ── Council strategy (上中下三策) ─────────────────────────────────

export type StrategyTier = 'upper' | 'middle' | 'lower'

export interface StrategyOption {
  tier: StrategyTier
  name: string
  classicalBasis: string
  description: string
  preconditions: string[]
  cost: string
  expectedOutcome: string
}

export interface CouncilStrategy {
  market: string
  summary: string
  timeWindow: string
  options: StrategyOption[]
}

export interface DailyBriefMarket {
  id: string
  name: string
  sub: string
  status: string
  desc: string
}

export interface BriefAction {
  dept: string
  deptId: string
  text: string
}

export interface DailyBrief {
  briefDate: string
  asOf?: string
  executiveSummary: string
  markets: DailyBriefMarket[]
  signalChanges: { cat: string; text: string }[]
  impacts: CountryImpact[]
  actions: BriefAction[]
  sourceCount: number
  eventCount: number
}

export interface JobsStatus {
  status: string
  lastRun?: string | null
  nextRun?: string | null
  stages: { stage: string; status: string; finishedAt?: string | null; rowsAffected?: number | null }[]
}
