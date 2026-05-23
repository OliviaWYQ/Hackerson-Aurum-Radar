import Icon from '../ui/Icon'
import type { Department } from '../../api/types'

const PRIORITY_LABEL = {
  high: { text: '高优先级', k: 'clay' },
  mid:  { text: '中优先级', k: 'bone' },
  low:  { text: '低优先级', k: 'sage' },
} as const

interface DeptCardProps {
  d: Department
  active: boolean
  onPick: (id: string) => void
}

export default function DeptCard({ d, active, onPick }: DeptCardProps) {
  const pl = PRIORITY_LABEL[d.priority]
  return (
    <button onClick={() => onPick(d.id)}
      style={{
        textAlign: 'left', padding: 18,
        background: active ? 'linear-gradient(180deg, var(--gold-wash), var(--pearl-warm))' : 'var(--pearl)',
        border: active ? '1px solid var(--gold-1)' : '1px solid var(--line)',
        borderRadius: 14, cursor: 'pointer',
        boxShadow: active ? 'var(--shadow-md), var(--shadow-inner)' : 'var(--shadow-sm)',
        position: 'relative', transition: 'all .15s ease',
      }}>
      <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
        <div className="flex items-center gap-2">
          <span style={{
            width: 34, height: 34, borderRadius: 10,
            background: active ? 'var(--pearl)' : 'var(--gold-wash)',
            border: '1px solid var(--line)',
            display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
          }}>
            <Icon name={d.icon} size={17} />
          </span>
          <span style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600 }}>{d.name}</span>
        </div>
        <span className={`chip ${pl.k}`}>{pl.text}</span>
      </div>
      <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
        {d.summary.map((s, i) => (
          <li key={i} className="flex justify-between items-center" style={{ fontSize: 12.5 }}>
            <span className="flex items-center gap-2" style={{ color: 'var(--ink-2)' }}>
              <span style={{ width: 4, height: 4, borderRadius: 4, background: 'var(--gold-1)' }} />
              {s.text}
            </span>
            <span style={{ fontSize: 11, color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' }}>{s.when}</span>
          </li>
        ))}
      </ul>
      <div style={{
        padding: '9px 12px',
        background: active ? 'var(--gold-1)' : 'var(--gold-wash)',
        color: active ? 'var(--pearl)' : 'var(--gold-2)',
        border: active ? '1px solid var(--gold-2)' : '1px solid var(--line)',
        borderRadius: 9, fontSize: 12, fontWeight: 600,
        textAlign: 'center',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
      }}>
        查看行动清单 <Icon name="right" size={11} />
      </div>
      {active && (
        <span style={{
          position: 'absolute', right: -1, top: 16,
          width: 6, height: 36, borderRadius: 6,
          background: 'var(--gold-1)',
        }} />
      )}
    </button>
  )
}
