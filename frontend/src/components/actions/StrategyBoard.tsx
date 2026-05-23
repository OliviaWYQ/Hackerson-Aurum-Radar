import Icon from '../ui/Icon'
import type { CouncilStrategy, StrategyOption, StrategyTier } from '../../api/types'

const TIER_META: Record<StrategyTier, { label: string; tag: string; accent: string; wash: string; border: string }> = {
  upper:  { label: '上策', tag: '进取', accent: 'var(--gold-2)', wash: 'var(--gold-wash)', border: 'var(--gold-1)' },
  middle: { label: '中策', tag: '稳健 · 默认推荐', accent: 'var(--sage-deep)', wash: 'var(--sage-tint)', border: 'rgba(122,157,126,.5)' },
  lower:  { label: '下策', tag: '保守', accent: 'var(--ink-3)', wash: 'var(--pearl-warm)', border: 'var(--line)' },
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '40px 1fr', gap: 8, alignItems: 'start' }}>
      <span style={{ fontSize: 11, color: 'var(--ink-3)', fontWeight: 600 }}>{label}</span>
      <div>{children}</div>
    </div>
  )
}

function StrategyCard({ o }: { o: StrategyOption }) {
  const m = TIER_META[o.tier]
  const recommended = o.tier === 'middle'
  return (
    <div style={{
      padding: 18, borderRadius: 14,
      background: recommended ? `linear-gradient(180deg, ${m.wash}, var(--pearl))` : 'var(--pearl)',
      border: `1px solid ${m.border}`,
      boxShadow: recommended ? 'var(--shadow-md)' : 'var(--shadow-sm)',
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span style={{
            padding: '3px 10px', borderRadius: 7, fontSize: 13, fontWeight: 700,
            fontFamily: 'var(--font-serif)', color: 'var(--pearl)', background: m.accent,
          }}>{m.label}</span>
          <span style={{ fontSize: 11.5, color: m.accent, fontWeight: 600 }}>{m.tag}</span>
        </div>
        {recommended && <Icon name="diamond" size={13} style={{ color: 'var(--sage-deep)' }} />}
      </div>

      <div style={{ fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 600, color: 'var(--ink-1)' }}>
        {o.name || `${m.label}方案`}
      </div>

      {o.classicalBasis && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 6,
          padding: '7px 10px', borderRadius: 8,
          background: 'var(--gold-wash)', border: '1px solid var(--line)',
          fontSize: 12, color: 'var(--gold-2)', fontWeight: 600,
        }}>
          <Icon name="diamond" size={11} style={{ marginTop: 2, flexShrink: 0 }} />
          <span>兵法依据 · {o.classicalBasis}</span>
        </div>
      )}

      {o.description && (
        <div style={{ fontSize: 12.5, color: 'var(--ink-2)', lineHeight: 1.6 }}>{o.description}</div>
      )}

      <div style={{
        display: 'flex', flexDirection: 'column', gap: 7,
        marginTop: 'auto', paddingTop: 10, borderTop: '1px solid var(--line-soft)',
      }}>
        {o.preconditions.length > 0 && (
          <Field label="前提">
            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 3 }}>
              {o.preconditions.map((p, i) => (
                <li key={i} style={{ fontSize: 12, color: 'var(--ink-2)', display: 'flex', gap: 6 }}>
                  <span style={{ color: m.accent, flexShrink: 0 }}>·</span>{p}
                </li>
              ))}
            </ul>
          </Field>
        )}
        {o.cost && <Field label="代价"><span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{o.cost}</span></Field>}
        {o.expectedOutcome && (
          <Field label="预期"><span style={{ fontSize: 12, color: 'var(--ink-2)' }}>{o.expectedOutcome}</span></Field>
        )}
      </div>
    </div>
  )
}

export default function StrategyBoard({ strategy }: { strategy: CouncilStrategy | null }) {
  if (!strategy || strategy.options.length === 0) return null
  const meta = [strategy.market, strategy.timeWindow].filter(Boolean).join(' · ')
  return (
    <div className="card" style={{ padding: 24 }}>
      <div className="flex items-center gap-3">
        <span style={{
          width: 40, height: 40, borderRadius: 12,
          background: 'var(--gold-wash)', border: '1px solid var(--line)',
          display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
        }}>
          <Icon name="target" size={20} />
        </span>
        <div>
          <h3 style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 600 }}>战略选择 · 上中下三策</h3>
          <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 2 }}>
            智囊团综合研判{meta ? ` · ${meta}` : ''}
          </div>
        </div>
      </div>

      {strategy.summary && (
        <div style={{
          marginTop: 14, padding: '14px 16px', borderRadius: 10,
          background: 'linear-gradient(135deg, var(--sage-tint), #EEF2EB)',
          border: '1px solid rgba(122,157,126,.3)',
          fontSize: 13, color: 'var(--ink-1)', lineHeight: 1.7,
        }}>
          {strategy.summary}
        </div>
      )}

      <div className="gold-divider" style={{ margin: '16px 0 14px' }}>
        <Icon name="diamond" size={10} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
        {strategy.options.map(o => <StrategyCard key={o.tier} o={o} />)}
      </div>
    </div>
  )
}
