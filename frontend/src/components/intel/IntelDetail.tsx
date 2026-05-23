import Icon from '../ui/Icon'
import { TAB_TONES } from './EventCard'
import type { IntelEvent, EventImpact, EnvFactor } from '../../api/types'
import {
  ENV_FACTOR_TONE,
  SIGNAL_DIRECTION_LABEL,
  SIGNAL_DIRECTION_TONE,
} from '../../api'

const IMPACT_ICONS: Record<string, string> = { competitive: 'users', brand: 'crown', trend: 'trending' }

// impact_scope 标签 -> 中文显示
const IMPACT_SCOPE_LABEL: Record<string, string> = {
  raw_material: '原料',
  brand: '品牌',
  retailer: '零售商',
  consumer: '消费者',
  category_natdiamond: '天然钻',
  category_labdiamond: 'Lab 钻',
  category_gold: '黄金',
  category_gemstone: '彩宝',
  market_CN: '中国',
  market_US: '美国',
  market_IN: '印度',
  market_SG: '新加坡',
  market_TH: '泰国',
  market_JP: '日本',
  market_GLOBAL: '全球',
}

function impactScopeLabel(tag: string): string {
  if (IMPACT_SCOPE_LABEL[tag]) return IMPACT_SCOPE_LABEL[tag]
  if (tag.startsWith('market_')) return tag.replace('market_', '')
  if (tag.startsWith('category_')) return tag.replace('category_', '')
  return tag
}

function ImpactBlock({ items }: { items: EventImpact[] }) {
  return (
    <div className="flex flex-col gap-2">
      {items.map((it, i) => (
        <div key={i} style={{ padding: '12px 14px', background: 'var(--ivory)', border: '1px solid var(--line-soft)', borderRadius: 10 }}>
          <div className="flex items-center gap-2" style={{ marginBottom: 5, color: 'var(--gold-2)' }}>
            <Icon name={IMPACT_ICONS[it.kind] ?? 'info'} size={13} />
            <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink-1)' }}>{it.title}</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.55 }}>{it.text}</div>
        </div>
      ))}
    </div>
  )
}

function BrandTile({ name }: { name: string }) {
  return (
    <div style={{
      padding: '10px 12px', minHeight: 38,
      background: 'var(--pearl)',
      border: '1px solid var(--line)',
      borderRadius: 8,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: name.length % 3 === 0 ? 'var(--font-serif)' : name.length % 3 === 1 ? 'Georgia, serif' : 'var(--font-sans)',
      fontSize: 12, fontWeight: 600, letterSpacing: '.08em',
      color: 'var(--ink-2)',
      textTransform: name.length < 16 ? 'uppercase' : 'none',
      textAlign: 'center',
    }}>{name}</div>
  )
}

function DetailSection({ icon, title, hint, children }: { icon: string; title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div className="flex items-center gap-2" style={{ marginBottom: 8, color: 'var(--gold-2)' }}>
        <Icon name={icon} size={13} />
        <span style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--ink-1)', letterSpacing: '.04em' }}>{title}</span>
        {hint && <span style={{ fontSize: 10.5, color: 'var(--ink-3)', fontWeight: 400, marginLeft: 2 }}>· {hint}</span>}
      </div>
      {children}
    </div>
  )
}

function FactorTile({ factor }: { factor: EnvFactor }) {
  const tone = ENV_FACTOR_TONE[factor.factorId]
  return (
    <div style={{
      padding: '12px 14px',
      background: factor.isPrimary ? 'linear-gradient(135deg, var(--gold-wash), var(--pearl-warm))' : 'var(--ivory)',
      border: `1px solid ${factor.isPrimary ? 'var(--line-strong)' : 'var(--line-soft)'}`,
      borderRadius: 10,
      position: 'relative',
    }}>
      {factor.isPrimary && (
        <span style={{
          position: 'absolute', top: -8, right: 12,
          padding: '2px 8px',
          background: 'var(--gold-1)', color: 'var(--pearl)',
          borderRadius: 999, fontSize: 9.5, fontWeight: 700, letterSpacing: '.08em',
        }}>主因子</span>
      )}
      <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
        <span className={`chip ${tone}`} style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{factor.factorId}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-1)' }}>{factor.label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--ink-4)' }}>{factor.factorName}</span>
      </div>
      {factor.evidence && (
        <div style={{ fontSize: 12.5, color: 'var(--ink-2)', lineHeight: 1.6, borderLeft: '2px solid var(--gold-3)', paddingLeft: 8, marginTop: 6 }}>
          <span style={{ color: 'var(--ink-4)' }}>证据 · </span>{factor.evidence}
        </div>
      )}
    </div>
  )
}

export default function IntelDetail({ e, onClose }: { e: IntelEvent; onClose: () => void }) {
  const primary = e.primaryFactor
  const dirLabel = SIGNAL_DIRECTION_LABEL[e.signalDirection]
  const dirTone = SIGNAL_DIRECTION_TONE[e.signalDirection]
  const confidencePct = Math.round((e.confidence || 0) * 100)
  // 影响范围拆分品类 / 市场 / 角色
  const scopes = e.impactScope || []
  const scopeCategories = scopes.filter(s => s.startsWith('category_'))
  const scopeMarkets = scopes.filter(s => s.startsWith('market_'))
  const scopeRoles = scopes.filter(s => !s.startsWith('category_') && !s.startsWith('market_'))

  return (
    <div className="card flex flex-col" style={{ padding: 22, height: '100%', overflowY: 'auto' }}>
      <div className="flex justify-between items-start" style={{ marginBottom: 14 }}>
        <div>
          <h3 className="facet-rule" style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 20, fontWeight: 600 }}>事件详情</h3>
          <div className="flex items-center gap-2 flex-wrap" style={{ marginTop: 8 }}>
            <span className={`chip ${TAB_TONES[e.cat] ?? 'bone'}`}>{e.cat}</span>
            {primary && (
              <span className={`chip ${ENV_FACTOR_TONE[primary.factorId]}`}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, opacity: .8 }}>{primary.factorId} </span>
                {primary.label}
              </span>
            )}
            {e.signalDirection !== 'neutral' && (
              <span className={`chip ${dirTone}`} style={{ fontSize: 10 }}>{dirLabel}</span>
            )}
            {e.priority === 'high' && <span className="chip clay" style={{ fontSize: 10 }}>高优先级</span>}
            <span style={{ fontSize: 11.5, color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' }}>{e.time}</span>
          </div>
        </div>
        <button onClick={onClose}
          style={{ background: 'transparent', border: '1px solid var(--line)', borderRadius: 8, width: 30, height: 30, color: 'var(--ink-3)', display: 'grid', placeItems: 'center' }}>
          <Icon name="x" size={14} />
        </button>
      </div>

      <div style={{ position: 'relative', marginBottom: 14, padding: 14, background: 'linear-gradient(135deg, var(--gold-wash), var(--pearl-warm))', border: '1px solid var(--line)', borderRadius: 12 }}>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 600, color: 'var(--ink-1)', lineHeight: 1.45, paddingRight: 56 }}>
          {e.title}
        </div>
        <svg width="48" height="48" viewBox="0 0 48 48" style={{ position: 'absolute', right: 10, top: 10, opacity: .85 }}>
          <defs>
            <linearGradient id="evd-g" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#FFFCF6" />
              <stop offset="1" stopColor="#C8A569" />
            </linearGradient>
          </defs>
          <g transform="translate(24 24)">
            <path d="M0 -16 L10 -4 L0 18 L-10 -4 Z" fill="url(#evd-g)" stroke="#B89150" strokeWidth=".6" />
            <path d="M-10 -4 L10 -4" stroke="#B89150" strokeWidth=".5" />
            <path d="M0 -16 L0 18" stroke="#B89150" strokeWidth=".3" opacity=".5" />
          </g>
        </svg>
      </div>

      {/* Agent processing chain */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 10.5, letterSpacing: '.12em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 600, marginBottom: 8 }}>
          Agent 处理链路
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 0, flexWrap: 'wrap' }}>
          {['原始信息', '清洗去重', '双轴抽取', '因子归类', '规则打分'].map((step, i, arr) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                padding: '5px 10px',
                background: i === arr.length - 1 ? 'var(--gold-tint)' : 'var(--ivory)',
                border: `1px solid ${i === arr.length - 1 ? 'var(--line-strong)' : 'var(--line-soft)'}`,
                borderRadius: 8,
                fontSize: 11, fontWeight: 600,
                color: i === arr.length - 1 ? 'var(--gold-2)' : 'var(--ink-3)',
              }}>{step}</div>
              {i < arr.length - 1 && (
                <span style={{ fontSize: 11, color: 'var(--ink-4)', margin: '0 3px' }}>→</span>
              )}
            </div>
          ))}
        </div>
      </div>

      <DetailSection icon="clipboard" title="核心事实" hint="key_claim · LLM 抽取产物 ≤50 字">
        <div style={{ fontSize: 14, color: 'var(--ink-1)', fontWeight: 600, fontFamily: 'var(--font-serif)', lineHeight: 1.6 }}>
          {e.keyClaim || e.summary}
        </div>
        {e.summary && e.keyClaim && e.summary !== e.keyClaim && (
          <div style={{ fontSize: 12.5, color: 'var(--ink-3)', lineHeight: 1.55, marginTop: 6 }}>{e.summary}</div>
        )}
      </DetailSection>

      {/* ============ 第二坐标轴：底层影响因子 ============ */}
      {e.envFactors.length > 0 && (
        <DetailSection icon="diamond" title="底层影响因子" hint={`F1-F7 · 共 ${e.envFactors.length} 个`}>
          <div className="flex flex-col gap-2">
            {e.envFactors.map((f, i) => <FactorTile key={i} factor={f} />)}
          </div>
        </DetailSection>
      )}

      {/* ============ 传导链路 ============ */}
      {e.conductionChain && (
        <DetailSection icon="trending" title="传导链路" hint={`链路 ${e.conductionChain.chainId}`}>
          <div style={{
            padding: '12px 14px',
            background: 'linear-gradient(135deg, var(--indigo-tint, rgba(107,122,158,.10)), rgba(255,252,246,.6))',
            border: '1px solid rgba(107,122,158,.22)',
            borderRadius: 10,
          }}>
            <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: 8 }}>
              <span className="chip indigo" style={{ fontFamily: 'var(--font-mono)' }}>{e.conductionChain.chainId}</span>
              <span style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--ink-1)' }}>{e.conductionChain.chainName}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', fontSize: 12, color: 'var(--ink-2)' }}>
              {e.conductionChain.nodePosition && (<>
                <span style={{ color: 'var(--ink-4)' }}>当前节点:</span>
                <span style={{ fontWeight: 600 }}>{e.conductionChain.nodePosition}</span>
              </>)}
              {e.conductionChain.lagEstimate && (<>
                <span style={{ color: 'var(--ink-4)' }}>时滞估计:</span>
                <span style={{ fontWeight: 600 }}>{e.conductionChain.lagEstimate}</span>
              </>)}
            </div>
          </div>
        </DetailSection>
      )}

      {/* ============ 信号属性：方向 / 烈度 / 置信度 / 评分 ============ */}
      <DetailSection icon="info" title="信号属性" hint="Stage 3 抽取 + Stage 4 评分">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <SignalCell label="方向" value={dirLabel} valueTone={dirTone} />
          <SignalCell label="烈度" value={`${e.intensity}/5`} bar={e.intensity} />
          <SignalCell label="置信度" value={`${confidencePct}%`} bar={Math.round((e.confidence || 0) * 5)} />
          <SignalCell label="机会 / 风险" value={`${e.opportunityScore} / ${e.riskScore}`} />
        </div>
      </DetailSection>

      {/* ============ 影响范围 ============ */}
      {(scopeCategories.length + scopeMarkets.length + scopeRoles.length) > 0 && (
        <DetailSection icon="globe" title="影响范围" hint="impact_scope · 品类 / 市场 / 角色">
          <div className="flex flex-col gap-2">
            {scopeCategories.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span style={{ fontSize: 11, color: 'var(--ink-4)', minWidth: 36 }}>品类</span>
                {scopeCategories.map((s, i) => (
                  <span key={i} className="chip gold" style={{ fontSize: 10.5 }}>{impactScopeLabel(s)}</span>
                ))}
              </div>
            )}
            {scopeMarkets.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span style={{ fontSize: 11, color: 'var(--ink-4)', minWidth: 36 }}>市场</span>
                {scopeMarkets.map((s, i) => (
                  <span key={i} className="chip sage" style={{ fontSize: 10.5 }}>{impactScopeLabel(s)}</span>
                ))}
              </div>
            )}
            {scopeRoles.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span style={{ fontSize: 11, color: 'var(--ink-4)', minWidth: 36 }}>角色</span>
                {scopeRoles.map((s, i) => (
                  <span key={i} className="chip indigo" style={{ fontSize: 10.5 }}>{impactScopeLabel(s)}</span>
                ))}
              </div>
            )}
          </div>
        </DetailSection>
      )}

      {/* ============ 下游推断 ============ */}
      {e.downstreamImplications.length > 0 && (
        <DetailSection icon="trending" title="下游推断" hint="downstream_implications · LLM 推理 1-3 条">
          <div className="flex flex-col gap-2">
            {e.downstreamImplications.map((text, i) => (
              <div key={i} style={{
                padding: '10px 12px',
                background: 'var(--ivory)',
                border: '1px solid var(--line-soft)',
                borderRadius: 10,
                fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.55,
                display: 'flex', gap: 10, alignItems: 'flex-start',
              }}>
                <span style={{
                  width: 18, height: 18, borderRadius: 999,
                  background: 'var(--gold-tint)', color: 'var(--gold-2)',
                  display: 'grid', placeItems: 'center', flexShrink: 0,
                  fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)',
                }}>{i + 1}</span>
                {text}
              </div>
            ))}
          </div>
        </DetailSection>
      )}

      {/* ============ 业务影响 ============ */}
      <DetailSection icon="diamond" title="对珠宝的业务影响">
        <ImpactBlock items={e.impact} />
      </DetailSection>

      {/* 歧义标记 (如果有) */}
      {e.ambiguityFlags.length > 0 && (
        <div style={{
          marginBottom: 16, padding: '10px 12px',
          background: 'rgba(180, 90, 70, .06)',
          border: '1px dashed rgba(180, 90, 70, .35)',
          borderRadius: 10,
          fontSize: 11.5, color: 'var(--ink-2)',
          display: 'flex', alignItems: 'flex-start', gap: 8,
        }}>
          <Icon name="alert" size={13} style={{ color: 'var(--clay-deep)', marginTop: 1 }} />
          <div>
            <span style={{ fontWeight: 700, color: 'var(--clay-deep)' }}>抽取阶段标记歧义：</span>
            {e.ambiguityFlags.join(' · ')}
          </div>
        </div>
      )}

      <DetailSection icon="globe" title="关联市场">
        <div className="flex flex-wrap gap-2">
          {e.markets.map((m, i) => <span key={i} className="chip sage">{m}</span>)}
        </div>
      </DetailSection>

      <DetailSection icon="users" title="相关品牌 / 平台">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {e.brands.map((b, i) => <BrandTile key={i} name={b} />)}
        </div>
      </DetailSection>

      <div style={{ fontSize: 11, letterSpacing: '.18em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 600, marginBottom: 8, marginTop: 8 }}>
        <Icon name="source" size={11} style={{ verticalAlign: '-1px' }} /> 来源引用 · SOURCE
      </div>
      <div style={{
        padding: 14,
        background: 'linear-gradient(135deg, var(--ivory), var(--pearl-warm))',
        border: '1px solid var(--line)', borderRadius: 10,
      }}>
        <div style={{ fontSize: 13, color: 'var(--ink-1)', fontWeight: 600, marginBottom: 4 }}>{e.citation}</div>
        <div style={{ fontSize: 11.5, color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' }}>发布时间: {e.citationTime}</div>
      </div>

      <div style={{ marginTop: 14, padding: 12, background: 'var(--gold-wash)', borderRadius: 10, border: '1px dashed var(--line-strong)', display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 11.5, color: 'var(--ink-3)' }}>
        <Icon name="info" size={12} style={{ color: 'var(--gold-2)', marginTop: 1, flexShrink: 0 }} />
        <span>以上为 Agent 双坐标轴抽取（架构 §7.3）：来源轴 + 底层影响因子轴。判断结果仅供参考，请结合原始来源核验。</span>
      </div>
    </div>
  )
}

// 信号属性单元格
function SignalCell({ label, value, valueTone, bar }: { label: string; value: string; valueTone?: string; bar?: number }) {
  return (
    <div style={{
      padding: '10px 12px',
      background: 'var(--ivory)',
      border: '1px solid var(--line-soft)',
      borderRadius: 10,
    }}>
      <div style={{ fontSize: 10.5, color: 'var(--ink-4)', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 4 }}>{label}</div>
      {valueTone ? (
        <span className={`chip ${valueTone}`} style={{ fontSize: 11.5, fontWeight: 700 }}>{value}</span>
      ) : (
        <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--ink-1)' }}>{value}</div>
      )}
      {typeof bar === 'number' && (
        <div style={{ display: 'flex', gap: 2, marginTop: 6 }}>
          {[1, 2, 3, 4, 5].map(i => (
            <span key={i} style={{
              flex: 1, height: 4, borderRadius: 1,
              background: i <= bar ? (bar >= 4 ? 'var(--gold-1)' : bar >= 3 ? 'var(--gold-2)' : 'var(--ink-4)') : 'var(--line)',
            }} />
          ))}
        </div>
      )}
    </div>
  )
}
