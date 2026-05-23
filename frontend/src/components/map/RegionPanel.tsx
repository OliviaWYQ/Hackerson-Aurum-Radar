import Icon from '../ui/Icon'
import type { RegionDetail, RegionMetric } from '../../api/types'

function MetricCell({ m }: { m: RegionMetric }) {
  return (
    <div style={{
      padding: 12,
      background: 'var(--ivory)',
      border: '1px solid var(--line-soft)',
      borderRadius: 10,
      textAlign: 'center',
    }}>
      <div style={{ color: 'var(--gold-2)', display: 'flex', justifyContent: 'center', marginBottom: 6 }}>
        <Icon name={m.icon} size={14} />
      </div>
      <div style={{ fontSize: 10.5, color: 'var(--ink-3)', marginBottom: 4, letterSpacing: '.05em' }}>{m.label}</div>
      <div className="num-display" style={{
        fontSize: m.small ? 11 : 22, lineHeight: 1.2,
        color: m.valueClass === 'sage' ? 'var(--sage-deep)'
          : m.valueClass === 'clay' ? 'var(--clay-deep)'
          : 'var(--ink-1)',
        fontWeight: m.small ? 500 : 600,
        fontFamily: m.small ? 'var(--font-sans)' : 'var(--font-serif)',
      }}>
        {m.value}
        {m.unit && <span style={{ fontSize: 11, color: 'var(--ink-3)', marginLeft: 2 }}>{m.unit}</span>}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 11, letterSpacing: '.18em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 600, marginBottom: 8 }}>{title}</div>
      <div style={{
        padding: '12px 14px',
        background: 'var(--ivory)',
        border: '1px solid var(--line-soft)',
        borderRadius: 10,
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>{children}</div>
    </div>
  )
}

function ProfileRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3" style={{ fontSize: 13 }}>
      <span style={{ color: 'var(--ink-3)', width: 80, flexShrink: 0 }}>{label}</span>
      <span style={{ color: 'var(--ink-1)', flex: 1 }}>{value}</span>
    </div>
  )
}

export default function RegionPanel({ detail }: { detail?: RegionDetail | null }) {
  if (!detail) {
    return (
      <div className="card flex flex-col" style={{ padding: 24, height: '100%', justifyContent: 'center', color: 'var(--ink-3)' }}>
        暂无商圈详情数据
      </div>
    )
  }

  const d = detail
  return (
    <div className="card flex flex-col" style={{ padding: 24, height: '100%' }}>
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3">
            <h2 style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 26, fontWeight: 600 }}>{d.name}商圈</h2>
            <span className="chip gold">{d.priority}</span>
          </div>
          <div style={{ fontSize: 11, letterSpacing: '.18em', color: 'var(--ink-3)', marginTop: 4, textTransform: 'uppercase' }}>
            {d.sub} · 区域详情
          </div>
        </div>
        <svg width="62" height="62" viewBox="0 0 60 60">
          <defs>
            <linearGradient id="bldg-g" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#EEDBA8" />
              <stop offset="1" stopColor="#B89150" />
            </linearGradient>
          </defs>
          <g fill="url(#bldg-g)" opacity=".55">
            <rect x="6"  y="32" width="10" height="24" rx="1" />
            <rect x="20" y="20" width="12" height="36" rx="1" />
            <polygon points="26,16 26,20 32,20" />
            <rect x="36" y="26" width="10" height="30" rx="1" />
            <rect x="48" y="38" width="8"  height="18" rx="1" />
          </g>
          <g fill="#FFFCF6" opacity=".5">
            {[34,40,46,52].map(y => <rect key={`a${y}`} x="22" y={y} width="2" height="3" />)}
            {[34,40,46,52].map(y => <rect key={`b${y}`} x="28" y={y} width="2" height="3" />)}
            {[28,34,40,46,52].map(y => <rect key={`c${y}`} x="38" y={y} width="2" height="3" />)}
            {[28,34,40,46,52].map(y => <rect key={`d${y}`} x="42" y={y} width="2" height="3" />)}
          </g>
        </svg>
      </div>

      <div className="gold-divider" style={{ margin: '16px 0 14px' }}>
        <Icon name="diamond" size={10} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8, marginBottom: 16 }}>
        {d.metrics.map((m, i) => <MetricCell key={i} m={m} />)}
      </div>

      <Section title="区域画像">
        <ProfileRow label="区域类型" value={d.profile.type} />
        <ProfileRow label="主要场景" value={d.profile.scene} />
        <ProfileRow label="消费特征" value={d.profile.consumption} />
        <ProfileRow label="适合动作" value={d.profile.action} />
      </Section>

      <Section title="门店洞察">
        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {d.insights.map((t, i) => (
            <li key={i} style={{ fontSize: 13, color: 'var(--ink-2)', display: 'flex', gap: 8, lineHeight: 1.5 }}>
              <span style={{ width: 4, height: 4, borderRadius: 4, background: 'var(--gold-1)', marginTop: 7, flexShrink: 0 }} />
              {t}
            </li>
          ))}
        </ul>
      </Section>

      <div style={{ marginTop: 14, fontSize: 11, letterSpacing: '.18em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 600, marginBottom: 8 }}>
        建议动作 · ACTIONS
      </div>
      <div className="flex flex-col gap-2">
        {d.actions.map((a, i) => (
          <button key={i} className="card-hover"
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '11px 14px',
              background: 'var(--pearl)',
              border: '1px solid var(--line)',
              borderRadius: 10, textAlign: 'left',
              fontSize: 13, color: 'var(--ink-1)',
            }}>
            <span className="flex items-center gap-2">
              <span style={{ width: 20, height: 20, borderRadius: 6, background: 'var(--gold-tint)', color: 'var(--gold-2)', display: 'grid', placeItems: 'center', fontSize: 10.5, fontWeight: 700 }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              {a}
            </span>
            <Icon name="right" size={12} style={{ color: 'var(--ink-4)' }} />
          </button>
        ))}
      </div>
    </div>
  )
}
