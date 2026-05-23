import Icon from '../ui/Icon'
import type { IntelEvent } from '../../api/types'
import { ENV_FACTOR_TONE, SIGNAL_DIRECTION_LABEL, SIGNAL_DIRECTION_TONE } from '../../api'

const TAB_TONES: Record<string, string> = {
  全部: 'bone', 竞争: 'clay', 产品: 'gold', 社媒: 'plum', 法规: 'indigo',
  渠道: 'sage', 宏观: 'gold', 供应链: 'plum',
}

interface EventCardProps {
  e: IntelEvent
  active: boolean
  onClick: (id: string) => void
}

// 烈度 1-5 视觉条
function IntensityBar({ value }: { value: number }) {
  const v = Math.max(0, Math.min(5, value || 0))
  return (
    <span
      title={`烈度 ${v}/5`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 2,
        padding: '2px 6px',
        background: 'var(--pearl)',
        border: '1px solid var(--line)',
        borderRadius: 999,
      }}>
      {[1, 2, 3, 4, 5].map(i => (
        <span key={i} style={{
          width: 3, height: i <= v ? 10 : 5,
          background: i <= v ? (v >= 4 ? 'var(--clay-deep)' : v >= 3 ? 'var(--gold-2)' : 'var(--ink-4)') : 'var(--line)',
          borderRadius: 1,
          transition: 'all .15s ease',
        }} />
      ))}
      <span style={{ marginLeft: 4, fontSize: 10, color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' }}>×{v}</span>
    </span>
  )
}

export default function EventCard({ e, active, onClick }: EventCardProps) {
  const primary = e.primaryFactor
  const dirLabel = SIGNAL_DIRECTION_LABEL[e.signalDirection]
  const dirTone = SIGNAL_DIRECTION_TONE[e.signalDirection]
  return (
    <button onClick={() => onClick(e.id)}
      style={{
        display: 'block', width: '100%', textAlign: 'left',
        padding: '16px 18px',
        background: active ? 'linear-gradient(180deg, var(--gold-wash), var(--pearl-warm))' : 'var(--pearl)',
        border: active ? '1px solid var(--line-strong)' : '1px solid var(--line-soft)',
        borderRadius: 12,
        cursor: 'pointer',
        boxShadow: active ? 'var(--shadow-md), var(--shadow-inner)' : 'var(--shadow-sm)',
        position: 'relative',
        transition: 'all .15s ease',
      }}>
      <span style={{
        position: 'absolute', left: -1, top: 18, width: 4, height: 28, borderRadius: 4,
        background: active ? 'var(--gold-1)' : 'transparent',
      }} />
      <div className="flex flex-wrap items-center gap-3" style={{ marginBottom: 8 }}>
        <span className={`chip ${TAB_TONES[e.cat] ?? 'bone'}`}>{e.cat}</span>
        {primary && (
          <span className={`chip ${ENV_FACTOR_TONE[primary.factorId]}`}
            title={primary.evidence || primary.factorName}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, opacity: .8 }}>{primary.factorId}</span>
            {primary.label}
          </span>
        )}
        {e.signalDirection !== 'neutral' && (
          <span className={`chip ${dirTone}`} style={{ fontSize: 10 }}>{dirLabel}</span>
        )}
        {e.priority === 'high' && <span className="chip clay" style={{ fontSize: 10 }}>高优先级</span>}
        {e.new && <span className="chip gold" style={{ fontSize: 10 }}>NEW</span>}
        <span style={{ marginLeft: 'auto', fontSize: 11.5, color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' }}>{e.time}</span>
        <Icon name="right" size={12} style={{ color: 'var(--ink-4)' }} />
      </div>
      <div style={{ fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 600, color: 'var(--ink-1)', lineHeight: 1.4, marginBottom: 6 }}>
        {e.title}
      </div>
      <div style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.55, marginBottom: 10 }}>
        {e.keyClaim || e.summary}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        <Icon name="source" size={12} style={{ color: 'var(--ink-4)' }} />
        <span style={{ fontSize: 11.5, color: 'var(--ink-2)' }}>{e.source}</span>
        <span style={{ color: 'var(--ink-4)', fontSize: 11 }}>|</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--ink-3)' }}>{e.srcDetail}</span>
        <span style={{ marginLeft: 'auto' }}>
          <IntensityBar value={e.intensity} />
        </span>
      </div>
    </button>
  )
}

export { TAB_TONES }
