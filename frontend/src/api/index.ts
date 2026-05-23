import { compareMarketDisplayOrder, DISTRICT_LAYOUT, MARKET_LAYOUT } from './mapLayout'
import type {
  ChipTone,
  ConductionChain,
  ConductionChainId,
  CountryDetail,
  CountryImpact,
  CountryNode,
  CouncilStrategy,
  DailyBrief,
  Department,
  DeptPriority,
  EnvFactor,
  EnvFactorId,
  EventImpact,
  IntelEvent,
  JobsStatus,
  RegionDetail,
  RegionMetric,
  SgRegion,
  SignalDirection,
  StatusKind,
  StrategyOption,
  StrategyTier,
} from './types'

export type {
  BriefAction,
  ConductionChain,
  ConductionChainId,
  CountryDetail,
  CountryNode,
  CouncilStrategy,
  DailyBrief,
  Department,
  EnvFactor,
  EnvFactorId,
  IntelEvent,
  JobsStatus,
  RegionDetail,
  SgRegion,
  SignalDirection,
  StrategyOption,
} from './types'

// ── 影响因子 / 链路 标签与色彩 (architecture.md §7.3) ────────────
export const ENV_FACTOR_LABEL: Record<EnvFactorId, string> = {
  F1: '供给约束',
  F2: '结构重塑',
  F3: '需求迁移',
  F4: '制度摩擦',
  F5: '价格传导',
  F6: '叙事压力',
  F7: '渠道博弈',
}

// 因子 -> chip tone (复用 OverviewPage 的 6 色系)
export const ENV_FACTOR_TONE: Record<EnvFactorId, ChipTone> = {
  F1: 'clay',    // 供给约束 — 风险红
  F2: 'indigo',  // 结构重塑 — 蓝
  F3: 'sage',    // 需求迁移 — 绿（机会）
  F4: 'plum',    // 制度摩擦 — 紫
  F5: 'gold',    // 价格传导 — 金
  F6: 'plum',    // 叙事压力 — 紫
  F7: 'bone',    // 渠道博弈 — 米
}

export const CONDUCTION_CHAIN_LABEL: Record<ConductionChainId, string> = {
  A: '地缘-供给-成本链',
  B: '货币-消费-需求链',
  C: '文化-偏好-结构链',
  D: '制度-合规-成本链',
  E: '技术-替代-颠覆链',
}

export const SIGNAL_DIRECTION_LABEL: Record<SignalDirection, string> = {
  positive: '正向 · 利好',
  negative: '负向 · 利空',
  mixed: '双向 · 复合',
  neutral: '中性 · 观察',
}

export const SIGNAL_DIRECTION_TONE: Record<SignalDirection, ChipTone> = {
  positive: 'sage',
  negative: 'clay',
  mixed: 'gold',
  neutral: 'bone',
}

// ── 行动 strategic_option / category 中文映射 (architecture.md §17.7) ────
export const ACTION_CATEGORY_LABEL: Record<string, string> = {
  investment_gold: '投资金条',
  self_reward_gold: '悦己黄金',
  lightweight_jewelry: '轻量首饰',
  regulatory_compliance: '合规应对',
  brand_narrative: '品牌叙事',
  channel_consolidation: '渠道整合',
  premium_positioning: '高端卡位',
  digital_marketing: '数字营销',
}

// 行动 channel 中文映射
export const ACTION_CHANNEL_LABEL: Record<string, string> = {
  offline_flagship: '线下旗舰',
  offline_mall: '线下商场',
  ecommerce: '电商平台',
  b2b_distribution: 'B2B 分销',
  all_channels: '全渠道',
  regulatory: '监管申报',
  TikTok: 'TikTok',
  Instagram: 'Instagram',
  WeChat: '微信',
  Xiaohongshu: '小红书',
}

function actionCategoryLabel(value: unknown): string {
  const raw = str(value)
  return ACTION_CATEGORY_LABEL[raw] ?? raw
}

function actionChannelLabel(value: unknown): string {
  const raw = str(value)
  return ACTION_CHANNEL_LABEL[raw] ?? raw
}

const BASE = '/api'

type JsonRecord = Record<string, unknown>

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

function withMarket(url: string, market?: string): string {
  if (!market || market === 'GLOBAL') return url
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}market=${encodeURIComponent(market)}`
}

// 移除 LLM 在文本里塞的内部 ID 引用（用户界面不显示这些）。
// 命中模式：
//   （情报7） / （情报 7, 8）              ← 中文"情报X"列表
//   （segment_signals[1]） / segment_signals[1]   ← snake_case ident 后跟 [N]（不论是否在括号内）
//   compliance_blockers[0][1]              ← 多层下标
//   （main_contradiction） / （key_signals）  ← 单纯 snake_case 标识符（含下划线）在括号内
//   （evidence_ids: 1, 2）                  ← evidence / 证据 开头的内部字段
//   (#5)                                    ← #N 短引用
// 保留正常的中文括号注释（如 "（约15%）"、"（双轨合规失效）"）。
function stripInternalRefs(input: string): string {
  if (!input) return input
  let out = input
    // ① 括号包裹的 "情报X" 列表
    .replace(/[（(]\s*情报\s*[\d\s,，、和]+\s*[)）]/g, '')
    // ② 括号包裹的 ident[N][...] —— 例：(segment_signals[1])、（compliance_blockers[0][1]）
    .replace(/[（(]\s*[a-zA-Z][\w]*(?:\[\d+\])+\s*[)）]/g, '')
    // ③ 括号包裹的 evidence/证据/event_id/signal_id 字段
    .replace(/[（(]\s*(?:evidence_ids?|evidence|证据|event_id|signal_id)[^)）]*[)）]/gi, '')
    // ④ 括号包裹的纯 snake_case 标识符（必须含下划线，避免误伤 "USA" / "IPO" / 中文）
    .replace(/[（(]\s*[a-z][a-z0-9]*(?:_[a-z0-9]+)+\s*[)）]/g, '')
    // ⑤ (#5) 短引用
    .replace(/[（(]\s*#\s*[\d\s,，]+\s*[)）]/g, '')
    // ⑥ 裸露在文本中的 ident[N] / ident[N][M]…（无括号包裹）
    .replace(/[a-zA-Z][\w]*(?:\[\d+\])+/g, '')
  // 收敛多余的空白与孤立标点
  out = out
    .replace(/\s+([，。、；,;.!?])/g, '$1')
    .replace(/[，,]\s*$/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
  return out
}

function str(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

// 同 str() 但顺带清洗 LLM 内部 ID 引用。用于所有面向用户显示的 LLM 文本。
function clean(value: unknown, fallback = ''): string {
  return stripInternalRefs(str(value, fallback))
}

function cleanStrings(value: unknown): string[] {
  return strings(value).map(stripInternalRefs).filter(Boolean)
}

function num(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function list(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.filter((item): item is JsonRecord => item !== null && typeof item === 'object' && !Array.isArray(item)) : []
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.map(item => String(item)).filter(Boolean) : []
}

function formatDateTime(value: unknown): string {
  const raw = str(value)
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}/${dd} ${hh}:${mi}`
}

function formatFullDateTime(value: unknown): string {
  const raw = str(value)
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}/${mm}/${dd} ${hh}:${mi}`
}

function hostFromUrl(value: unknown): string {
  const raw = str(value)
  if (!raw) return ''
  try {
    return new URL(raw).hostname.replace(/^www\./, '')
  } catch {
    return raw
  }
}

// All aliases normalize to the canonical ISO-3166 alpha-2 code used by the
// backend. New markets only need an entry in MARKET_LAYOUT — add aliases
// here only when the source data uses a non-ISO form (long name, Chinese).
const MARKET_ALIASES: Record<string, string> = {
  singapore: 'SG',
  新加坡: 'SG',
  thailand: 'TH',
  泰国: 'TH',
  japan: 'JP',
  日本: 'JP',
  korea: 'KR',
  韩国: 'KR',
  indonesia: 'ID',
  印尼: 'ID',
  malaysia: 'MY',
  马来西亚: 'MY',
  vietnam: 'VN',
  越南: 'VN',
  philippines: 'PH',
  菲律宾: 'PH',
  usa: 'US',
  美国: 'US',
  global: 'GLOBAL',
  全球: 'GLOBAL',
}

function normalizeMarket(value: string): string {
  const trimmed = value.trim()
  // already-canonical ISO codes are kept as-is (upper-case)
  if (MARKET_LAYOUT[trimmed.toUpperCase()]) return trimmed.toUpperCase()
  return MARKET_ALIASES[trimmed.toLowerCase()] ?? MARKET_ALIASES[trimmed] ?? trimmed
}

export function normalizeMarketId(value: string): string {
  return normalizeMarket(value)
}

function marketName(market: string): string {
  return MARKET_LAYOUT[market]?.name ?? market
}

export function getMarketDisplayName(market: string): string {
  return marketName(normalizeMarket(market))
}

function marketStatus(opportunity: number, risk: number): { status: StatusKind; label: string; tone: ChipTone } {
  if (risk >= 65 && risk >= opportunity) return { status: 'risk', label: '风险升温', tone: 'clay' }
  if (opportunity >= 70) return { status: 'high', label: '机会增强', tone: 'sage' }
  if (risk >= 50 && risk > opportunity) return { status: 'risk', label: '风险升温', tone: 'clay' }
  return { status: 'mid', label: '', tone: 'bone' }
}

function statusLabel(status: StatusKind): string {
  const labels: Record<StatusKind, string> = {
    high: '机会增强',
    mid: '',
    risk: '风险升温',
    competition: '竞争加剧',
    regulation: '法规变化',
    watch: '',
  }
  return labels[status]
}

function sourceCategoryLabel(value: unknown): string {
  const raw = str(value)
  // source_category (架构 §7.3 第一坐标轴 7 值) -> 中文
  // legacy event_type 值同表合并，便于历史数据回放
  const map: Record<string, string> = {
    competition: '竞争',
    product: '产品',
    social_media: '社媒',
    regulation: '法规',
    channel: '渠道',
    macro: '宏观',
    supply_chain: '供应链',
    // legacy fallbacks
    platform: '渠道',
    social: '社媒',
    pricing: '宏观',
    festival: '产品',
  }
  return map[raw] ?? raw
}

function priorityLabel(value: unknown): IntelEvent['priority'] {
  const raw = str(value)
  return raw === 'P0' || raw === 'P1' || raw === 'high' ? 'high' : 'mid'
}

function impactKind(value: unknown): EventImpact['kind'] {
  const raw = str(value)
  if (raw === 'competition' || raw === 'competitive') return 'competitive'
  if (raw === 'brand') return 'brand'
  return 'trend'
}

function isEnvFactorId(value: unknown): value is EnvFactorId {
  return typeof value === 'string' && /^F[1-7]$/.test(value)
}

function isChainId(value: unknown): value is ConductionChainId {
  return typeof value === 'string' && /^[A-E]$/.test(value)
}

function isSignalDirection(value: unknown): value is SignalDirection {
  return value === 'positive' || value === 'negative' || value === 'mixed' || value === 'neutral'
}

function mapEnvFactor(raw: JsonRecord): EnvFactor | null {
  const fid = raw.factor_id
  if (!isEnvFactorId(fid)) return null
  return {
    factorId: fid,
    factorName: str(raw.factor_name),
    label: ENV_FACTOR_LABEL[fid],
    isPrimary: Boolean(raw.is_primary),
    evidence: clean(raw.evidence),
  }
}

function mapConductionChain(raw: unknown): ConductionChain | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const r = raw as JsonRecord
  const cid = r.chain_id
  if (!isChainId(cid)) return null
  return {
    chainId: cid,
    chainName: str(r.chain_name, CONDUCTION_CHAIN_LABEL[cid]),
    nodePosition: str(r.node_position),
    lagEstimate: str(r.lag_estimate),
  }
}

function mapEvent(raw: JsonRecord): IntelEvent {
  const sourceCategoryValue = str(raw.source_category ?? raw.event_type ?? raw.cat)
  const sourceName = str(raw.source_name ?? raw.source)
  const sourceUrl = str(raw.source_url)
  const publishedAt = raw.published_at ?? raw.citation_time ?? raw.created_at
  const backendImpact = list(raw.impact)
  const impact: EventImpact[] = backendImpact.length > 0
    ? backendImpact.map(item => ({
        kind: impactKind(item.kind),
        title: str(item.title, '影响判断'),
        text: clean(item.text),
      }))
    : [{
        kind: 'trend',
        title: '业务影响',
        text: clean(raw.business_impact ?? raw.key_claim ?? raw.summary),
      }]

  // 双坐标轴新字段 (architecture.md §7.3)
  const envFactors = list(raw.env_factors)
    .map(mapEnvFactor)
    .filter((f): f is EnvFactor => f !== null)
  const primaryFactor = envFactors.find(f => f.isPrimary) ?? envFactors[0] ?? null
  const conductionChain = mapConductionChain(raw.conduction_chain)
  const signalDirection: SignalDirection = isSignalDirection(raw.signal_direction)
    ? raw.signal_direction
    : 'neutral'

  return {
    id: String(raw.event_id ?? raw.id ?? ''),
    sourceCategory: sourceCategoryValue,
    cat: sourceCategoryLabel(sourceCategoryValue),
    title: clean(raw.title),
    summary: clean(raw.summary),
    keyClaim: clean(raw.key_claim),
    source: sourceName || hostFromUrl(sourceUrl) || '公开来源',
    srcDetail: str(raw.src_detail) || hostFromUrl(sourceUrl),
    time: str(raw.time) || formatDateTime(publishedAt),
    priority: priorityLabel(raw.priority),
    new: Boolean(raw.new),
    impact,
    markets: strings(raw.markets).length > 0 ? strings(raw.markets) : [str(raw.market)].filter(Boolean),
    brands: strings(raw.brands).length > 0 ? strings(raw.brands) : [sourceName].filter(Boolean),
    citation: str(raw.citation) || sourceName || sourceUrl,
    citationTime: str(raw.citation_time) || formatFullDateTime(publishedAt),
    envFactors,
    primaryFactor,
    conductionChain,
    signalDirection,
    intensity: num(raw.intensity),
    impactScope: strings(raw.impact_scope),
    downstreamImplications: cleanStrings(raw.downstream_implications),
    ambiguityFlags: strings(raw.ambiguity_flags),
    confidence: typeof raw.confidence === 'number' ? raw.confidence : num(raw.confidence),
    opportunityScore: num(raw.opportunity_score),
    riskScore: num(raw.risk_score),
  }
}

export interface EventsResponse {
  items: IntelEvent[]
  total: number
  page: number
  size: number
}

export async function fetchEvents(category?: string, page = 1, size = 20, market?: string): Promise<EventsResponse> {
  const params = new URLSearchParams({ page: String(page), size: String(size) })
  if (category && category !== '全部') params.set('category', category)
  if (market && market !== 'GLOBAL') params.set('market', market)
  const raw = await get<{ items: JsonRecord[]; total: number; page: number; size: number }>(`/events?${params}`)
  return { ...raw, items: raw.items.map(mapEvent) }
}

export async function fetchEventDetail(eventId: string): Promise<IntelEvent> {
  return mapEvent(await get<JsonRecord>(`/events/${encodeURIComponent(eventId)}`))
}

export interface DashboardSummary {
  as_of: string
  window_days?: number
  since?: string
  radar: {
    markets_scanned: number
    documents_integrated: number
    high_priority_changes: number
    judgments_generated: number
  }
  events_today: number
  events_today_delta: number
  high_priority_events: number
  pending_actions: number
  pending_actions_delta: number
  key_analysis: {
    opportunities: number
    competition: number
    regulation: number
  }
}

export async function fetchDashboardSummary(market?: string): Promise<DashboardSummary> {
  return get<DashboardSummary>(withMarket('/dashboard/summary', market))
}

function mapCountry(raw: JsonRecord): CountryNode {
  const market = normalizeMarket(str(raw.market))
  const opportunity = num(raw.opportunity_score)
  const risk = num(raw.risk_score)
  const layout = MARKET_LAYOUT[market] ?? { name: market, x: 1120, y: 360, size: 13 }
  return {
    id: market,
    name: layout.name,
    sub: market,
    x: layout.x,
    y: layout.y,
    status: marketStatus(opportunity, risk).status,
    size: layout.size,
    headline: clean(raw.headline),
  }
}

export async function fetchCountries(): Promise<CountryNode[]> {
  const raw = await get<{ markets: JsonRecord[] }>('/overview')
  return raw.markets.map(mapCountry).sort((a, b) => compareMarketDisplayOrder(a.id, b.id))
}

export async function fetchCountryDetail(id: string): Promise<CountryDetail | undefined> {
  const market = normalizeMarket(id)
  const raw = await get<JsonRecord>(`/markets/${encodeURIComponent(market)}`)
  const opportunity = num(raw.opportunity_score)
  const risk = num(raw.risk_score)
  const status = marketStatus(opportunity, risk)
  const opportunities = cleanStrings(raw.key_opportunities)
  const risks = cleanStrings(raw.key_risks)
  const watchItems = cleanStrings(raw.watch_items)
  const triggers = [...opportunities, ...risks, ...watchItems].slice(0, 4)
  const hasPolicyRisk = risks.some(item => /法规|监管|合规|customs|regulation|compliance/i.test(item))

  return {
    name: marketName(str(raw.market, market)),
    sub: str(raw.market, market),
    status: status.label,
    statusKind: status.tone,
    score: opportunity,
    competition: Math.max(1, Math.min(5, Math.ceil(risk / 20))),
    competitionLabel: risk >= 70 ? '高' : risk >= 45 ? '中' : '低',
    policy: hasPolicyRisk ? '需关注' : '稳定',
    policyKind: hasPolicyRisk ? 'clay' : 'sage',
    growth: '—',
    bullets: triggers.map(text => ({ icon: 'diamond', text })),
    triggers,
    impacts: [
      ...opportunities.slice(0, 2).map(text => ({ kind: 'opportunity' as const, text })),
      ...risks.slice(0, 2).map(text => ({ kind: 'risk' as const, text })),
      ...watchItems.slice(0, 2).map(text => ({ kind: 'watch' as const, text })),
    ],
    asOf: str(raw.snapshot_date ?? raw.created_at),
  }
}

function districtSlug(name: string): string {
  const lower = name.toLowerCase()
  if (/orchard|乌节/.test(lower)) return 'orchard'
  if (/marina|滨海/.test(lower)) return 'marina'
  if (/bugis|武吉/.test(lower)) return 'bugis'
  if (/jurong|裕廊/.test(lower)) return 'jurong'
  if (/tampines|淡滨/.test(lower)) return 'tampines'
  if (/changi|樟宜/.test(lower)) return 'changi'
  if (/cbd|市中心|downtown/.test(lower)) return 'cbd'
  return lower.replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

function mapRegion(raw: JsonRecord): SgRegion {
  const name = str(raw.name)
  const slug = districtSlug(name)
  const layout = DISTRICT_LAYOUT[slug] ?? { x: 560, y: 340, sub: name }
  const stores = num(raw.store_count ?? raw.stores)
  const hot = str(raw.heat_level ?? raw.hot) === 'high' || str(raw.heat_level ?? raw.hot) === '高' ? 'high' : 'mid'
  return {
    id: String(raw.id ?? slug),
    name,
    sub: str(raw.sub, layout.sub),
    x: layout.x,
    y: layout.y,
    stores,
    hot,
    priority: hot === 'high',
  }
}

export async function fetchSgRegions(market = 'SG'): Promise<SgRegion[]> {
  const raw = await get<{ items: JsonRecord[] } | JsonRecord[]>(`/markets/${encodeURIComponent(normalizeMarket(market))}/districts`)
  const items = Array.isArray(raw) ? raw : raw.items
  return items.map(mapRegion)
}

function metric(icon: string, label: string, value: string, options: Partial<RegionMetric> = {}): RegionMetric {
  return { icon, label, value, ...options }
}

export async function fetchRegionDetail(id: string): Promise<RegionDetail | undefined> {
  const raw = await get<JsonRecord>(`/districts/${encodeURIComponent(id)}`)
  const name = str(raw.name)
  const profile = raw.profile && typeof raw.profile === 'object' && !Array.isArray(raw.profile) ? raw.profile as JsonRecord : {}
  const stores = num(raw.store_count ?? raw.stores)
  const heat = str(raw.heat_level ?? raw.hot)
  const priority = heat === 'high' || heat === '高' ? '高优先级区域' : '中优先级区域'
  const insights = strings(profile.insights ?? raw.insights)
  const actions = strings(profile.actions ?? raw.actions)

  return {
    name,
    sub: str(profile.sub, DISTRICT_LAYOUT[districtSlug(name)]?.sub ?? name),
    priority,
    metrics: [
      metric('store', '门店数量', String(stores), { unit: '家' }),
      metric('flame', '商圈热力', heat === 'high' ? '高' : heat === 'mid' ? '中' : heat || '—', { valueClass: heat === 'high' ? 'sage' : 'bone' }),
      metric('users', '竞品密度', str(profile.competition_density, '—'), { valueClass: str(profile.competition_density).includes('高') ? 'clay' : 'bone' }),
      metric('broadcast', '客流结构', str(profile.traffic_profile, '—'), { small: true }),
    ],
    profile: {
      type: str(profile.type, '—'),
      scene: str(profile.scene, '—'),
      consumption: str(profile.consumption, '—'),
      action: str(profile.action, '—'),
    },
    insights,
    actions,
  }
}

const DEPT_META: Record<string, { id: string; sub: string; icon: string }> = {
  管理层: { id: 'mgmt', sub: 'Management', icon: 'crown' },
  商品团队: { id: 'pdt', sub: 'Product', icon: 'ring' },
  产品部: { id: 'pdt', sub: 'Product', icon: 'ring' },
  市场营销团队: { id: 'mkt', sub: 'Marketing', icon: 'diamond' },
  市场部: { id: 'mkt', sub: 'Marketing', icon: 'diamond' },
  渠道团队: { id: 'chn', sub: 'Channel', icon: 'store' },
  渠道部: { id: 'chn', sub: 'Channel', icon: 'store' },
  电商运营团队: { id: 'ecom', sub: 'E-commerce', icon: 'store' },
  法务合规团队: { id: 'law', sub: 'Legal', icon: 'scale' },
  法务合规: { id: 'law', sub: 'Legal', icon: 'scale' },
  数据情报团队: { id: 'data', sub: 'Intelligence', icon: 'broadcast' },
}

function deptId(name: string): string {
  return DEPT_META[name]?.id ?? name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

function actionPriority(value: unknown): DeptPriority {
  const raw = str(value)
  if (raw === 'P0' || raw === 'P1' || raw === 'high') return 'high'
  if (raw === 'P2' || raw === 'mid') return 'mid'
  return 'low'
}

function highestPriority(items: JsonRecord[]): DeptPriority {
  if (items.some(item => actionPriority(item.priority) === 'high')) return 'high'
  if (items.some(item => actionPriority(item.priority) === 'mid')) return 'mid'
  return 'low'
}

// 一条 action 的 evidence/strategic 信息拍平为可显示 refs（不含技术 id）
function refsFromAction(action: JsonRecord): import('./types').DeptRef[] {
  const refs: import('./types').DeptRef[] = []
  const evidence = list(action.evidence)
  for (const ev of evidence) {
    const title = clean(ev.title) || clean(ev.key_claim)
    if (!title) continue
    const primary = ev.primary_factor && typeof ev.primary_factor === 'object'
      ? (ev.primary_factor as JsonRecord) : null
    const fid = primary ? str(primary.factor_id) : ''
    const sourceName = str(ev.source_name)
    const keyClaimText = clean(ev.key_claim)
    refs.push({
      icon: 'feed',
      text: title,
      detail: [sourceName, keyClaimText].filter(Boolean).join(' · '),
      sourceUrl: str(ev.source_url) || undefined,
      eventId: str(ev.event_id) || undefined,
      factorLabel: fid && /^F[1-7]$/.test(fid) ? ENV_FACTOR_LABEL[fid as EnvFactorId] : undefined,
      factorId: fid && /^F[1-7]$/.test(fid) ? (fid as EnvFactorId) : undefined,
    })
  }
  // 若没有 evidence 但有 source_url，也作为可点击 ref
  const sourceUrl = str(action.source_url)
  if (refs.length === 0 && sourceUrl) {
    refs.push({ icon: 'external', text: '查看来源', sourceUrl })
  }
  // 仍无可显示证据时，回退展示 strategic_option / category + channel，仍不显示 market 名
  if (refs.length === 0) {
    const cat = actionCategoryLabel(action.strategic_option ?? action.category)
    const channel = actionChannelLabel(action.channel)
    const label = [cat, channel].filter(Boolean).join(' · ')
    if (label) {
      refs.push({ icon: 'target', text: label, detail: '智囊团综合推演（无直接证据链路）' })
    } else {
      refs.push({ icon: 'clipboard', text: '智囊团综合推演' })
    }
  }
  return refs
}

export async function fetchDepartments(market?: string): Promise<Department[]> {
  const raw = await get<{ items: JsonRecord[] } | JsonRecord[]>(withMarket('/actions', market))
  const actions = Array.isArray(raw) ? raw : raw.items
  const byDept = new Map<string, JsonRecord[]>()
  actions.forEach(action => {
    const department = str(action.department, '未指定')
    byDept.set(department, [...(byDept.get(department) ?? []), action])
  })

  return Array.from(byDept.entries()).map(([name, items]) => {
    const meta = DEPT_META[name] ?? { id: deptId(name), sub: name, icon: 'clipboard' }
    const first = items[0]
    const steps = items.map(item => ({
      title: clean(item.action_title, str(item.action_detail, '行动建议')),
      goal: clean(item.reason, '推进 Agent 识别出的市场行动'),
      how: clean(item.action_detail, str(item.action_title)),
      when: str(item.deadline, '待定'),
      expectedOutput: clean(item.expected_output),
      successMetric: clean(item.success_metric),
    }))
    // 收集本部门所有行动的 refs，按 sourceUrl/标题去重
    const seen = new Set<string>()
    const refs: import('./types').DeptRef[] = []
    for (const action of items) {
      for (const ref of refsFromAction(action)) {
        const key = ref.eventId || ref.sourceUrl || ref.text
        if (seen.has(key)) continue
        seen.add(key)
        refs.push(ref)
        if (refs.length >= 6) break
      }
      if (refs.length >= 6) break
    }
    return {
      id: meta.id,
      name,
      sub: meta.sub,
      icon: meta.icon,
      priority: highestPriority(items),
      cycle: str(first?.deadline, '待定'),
      owner: name,
      market: str(first?.market),
      actionCount: items.length,
      summary: items.slice(0, 4).map(item => ({
        text: clean(item.action_title, str(item.action_detail, '行动建议')),
        when: str(item.deadline, '待定'),
      })),
      goal: clean(first?.reason, `推进 ${name} 相关行动`),
      steps,
      refs,
    }
  })
}

export async function fetchCouncilStrategy(market?: string): Promise<CouncilStrategy | null> {
  let raw: JsonRecord
  try {
    const path = market && market !== 'GLOBAL'
      ? `/markets/${encodeURIComponent(market)}/council`
      : '/council/latest'
    raw = await get<JsonRecord>(path)
  } catch {
    return null // 404 — no council report persisted yet
  }
  const so = (raw.strategic_options && typeof raw.strategic_options === 'object'
    ? raw.strategic_options
    : {}) as JsonRecord
  const tiers: { key: string; tier: StrategyTier }[] = [
    { key: 'upper_strategy', tier: 'upper' },
    { key: 'middle_strategy', tier: 'middle' },
    { key: 'lower_strategy', tier: 'lower' },
  ]
  const options: StrategyOption[] = []
  for (const { key, tier } of tiers) {
    const s = so[key]
    if (!s || typeof s !== 'object' || Array.isArray(s)) continue
    const o = s as JsonRecord
    options.push({
      tier,
      name: clean(o.name),
      classicalBasis: clean(o.classical_basis),
      description: clean(o.description),
      preconditions: cleanStrings(o.preconditions),
      cost: clean(o.cost),
      expectedOutcome: clean(o.expected_outcome),
    })
  }
  return {
    market: str(raw.market),
    summary: clean(raw.council_summary),
    timeWindow: str(raw.time_window),
    options,
  }
}

function briefImpact(kind: CountryImpact['kind'], text: string): CountryImpact {
  return { kind, text }
}

export async function fetchLatestBrief(market?: string): Promise<DailyBrief> {
  const [brief, countries, events] = await Promise.all([
    get<JsonRecord>(withMarket('/brief/latest', market)),
    fetchCountries().catch(() => []),
    fetchEvents('全部', 1, 5, market).then(res => res.items).catch(() => []),
  ])

  const recommendedActions = list(brief.recommended_actions)
  const rawMarkets = strings(brief.markets)
  const markets = countries.length > 0
    ? countries.map(country => ({
        id: country.id,
        name: country.name,
        sub: country.sub,
        status: statusLabel(country.status),
        desc: country.headline ?? '',
      }))
    : rawMarkets
      .map(market => ({ id: market, name: marketName(market), sub: market, status: '', desc: '' }))
      .sort((a, b) => compareMarketDisplayOrder(a.id, b.id))

  return {
    briefDate: str(brief.brief_date),
    asOf: str(brief.updated_at ?? brief.created_at),
    executiveSummary: clean(brief.executive_summary),
    markets,
    signalChanges: events.map(event => ({ cat: event.cat, text: event.title })),
    impacts: [
      ...cleanStrings(brief.opportunities).slice(0, 2).map(text => briefImpact('opportunity', text)),
      ...cleanStrings(brief.risks).slice(0, 2).map(text => briefImpact('risk', text)),
      ...cleanStrings(brief.watch_items).slice(0, 2).map(text => briefImpact('watch', text)),
    ],
    actions: recommendedActions.slice(0, 4).map(item => {
      const department = str(item.department, '未指定')
      return {
        dept: department,
        deptId: deptId(department),
        text: clean(item.action_title, str(item.action_detail, '行动建议')),
      }
    }),
    sourceCount: num(brief.source_count),
    eventCount: num(brief.event_count),
  }
}

export async function fetchJobsStatus(): Promise<JobsStatus> {
  const raw = await get<JsonRecord>('/jobs/status')
  return {
    status: str(raw.status, 'unknown'),
    lastRun: str(raw.last_run) || null,
    nextRun: str(raw.next_run) || null,
    stages: list(raw.stages).map(stage => ({
      stage: str(stage.stage),
      status: str(stage.status),
      finishedAt: str(stage.finished_at) || null,
      rowsAffected: typeof stage.rows_affected === 'number' ? stage.rows_affected : null,
    })),
  }
}
