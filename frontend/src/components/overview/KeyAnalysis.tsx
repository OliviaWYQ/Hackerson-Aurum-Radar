import Icon from '../ui/Icon'
import type { DashboardSummary } from '../../api'
import type { PageId } from '../../api/types'

function Sparkline({ data, color = 'var(--gold-2)' }: { data: number[]; color?: string }) {
  const w = 130, h = 38
  const max = Math.max(...data), min = Math.min(...data)
  const pts = data.map((v, i) =>
    `${(i / (data.length - 1)) * w},${h - ((v - min) / (max - min || 1)) * (h - 6) - 3}`
  ).join(' ')
  const area = `0,${h} ${pts} ${w},${h}`
  const id = `spark-${color.replace(/[^a-z0-9]/gi, '')}`
  return (
    <svg width={w} height={h}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity=".25" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${id})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle
        cx={w}
        cy={h - ((data[data.length - 1]! - min) / (max - min || 1)) * (h - 6) - 3}
        r="2.5" fill={color} />
    </svg>
  )
}

function sparkData(value: number): number[] {
  return [0, value]
}

export default function KeyAnalysis({ summary, onCard }: { summary: DashboardSummary | null; onCard: (id: PageId) => void }) {
  const counts = summary?.key_analysis
  const items = [
    { icon: 'diamond', title: '市场机会', num: counts?.opportunities ?? 0, sub: '机会型情报与增长信号', color: 'var(--gold-2)' },
    { icon: 'users',   title: '竞争动态', num: counts?.competition ?? 0, sub: '主要竞争对手与市场动向', color: '#6B7A9E' },
    { icon: 'shield',  title: '法规关注', num: counts?.regulation ?? 0, sub: '政策法规与合规风险提示', color: 'var(--clay)' },
  ]

  return (
    <div className="card" style={{ padding: 22 }}>
      <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
        <h3 className="facet-rule" style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600 }}>关键分析摘要</h3>
        <span style={{ fontSize: 11, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="info" size={12} /> 点击卡片 → 进入情报中心
        </span>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((it, i) => (
          <button key={i} onClick={() => onCard('intel')}
            className="card-hover min-h-[150px] min-w-0"
            style={{
              padding: 16, textAlign: 'left',
              background: 'var(--ivory)',
              border: '1px solid var(--line-soft)',
              borderRadius: 12, cursor: 'pointer',
            }}>
            <div className="flex items-center gap-2" style={{ marginBottom: 10 }}>
              <span style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--gold-wash)', display: 'grid', placeItems: 'center', color: 'var(--gold-2)' }}>
                <Icon name={it.icon} size={15} />
              </span>
              <span style={{ fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 600 }}>{it.title}</span>
            </div>
            <div className="flex items-end justify-between" style={{ marginBottom: 6 }}>
              <div className="num-display" style={{ fontSize: 38, lineHeight: 1, color: 'var(--ink-1)' }}>
                {it.num}<span style={{ fontSize: 13, color: 'var(--ink-3)', marginLeft: 4, fontWeight: 400 }}>条</span>
              </div>
              <Sparkline data={sparkData(it.num)} color={it.color} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{it.sub}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
