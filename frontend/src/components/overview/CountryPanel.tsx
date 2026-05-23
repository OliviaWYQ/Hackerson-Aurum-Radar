import Icon from '../ui/Icon'
import type { CountryDetail, PageId } from '../../api/types'

function ScoreRing({ value }: { value: number }) {
  const r = 52, c = 2 * Math.PI * r, pct = value / 100
  return (
    <svg width="140" height="140" viewBox="0 0 140 140">
      <defs>
        <linearGradient id="ring-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#EEDBA8" />
          <stop offset="1" stopColor="#B89150" />
        </linearGradient>
      </defs>
      <circle cx="70" cy="70" r={r} fill="none" stroke="var(--gold-wash)" strokeWidth="10" />
      <circle cx="70" cy="70" r={r} fill="none"
        stroke="url(#ring-g)" strokeWidth="10" strokeLinecap="round"
        strokeDasharray={`${c * pct} ${c}`}
        transform="rotate(-90 70 70)"
        style={{ filter: 'drop-shadow(0 2px 6px rgba(200,165,105,.4))' }} />
      <text x="70" y="65" textAnchor="middle" fontFamily="var(--font-serif)"
        fontSize="34" fontWeight="600" fill="#2A2419" dominantBaseline="middle">{value}</text>
      <text x="70" y="90" textAnchor="middle" fontSize="10" letterSpacing=".15em" fill="#786C53">/ 100</text>
      <text x="70" y="104" textAnchor="middle" fontSize="9.5" letterSpacing=".08em" fill="#A89776">变化强度</text>
    </svg>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center">
      <span style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>{label}</span>
      <span>{value}</span>
    </div>
  )
}

interface CountryPanelProps {
  detail?: CountryDetail | null
  onJumpToMap: (id: PageId) => void
}

export default function CountryPanel({ detail, onJumpToMap }: CountryPanelProps) {
  if (!detail) {
    return (
      <div className="card flex flex-col" style={{ padding: 22, height: '100%', justifyContent: 'center', color: 'var(--ink-3)' }}>
        暂无市场判断数据
      </div>
    )
  }

  const d = detail
  return (
    <div className="card flex flex-col" style={{ padding: 22, height: '100%', overflowY: 'auto' }}>
      {/* Agent judgment header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        fontSize: 10.5, fontWeight: 700, letterSpacing: '.1em',
        textTransform: 'uppercase', color: 'var(--sage-deep)',
        marginBottom: 12,
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: 3,
          background: 'var(--sage)', display: 'inline-block',
          boxShadow: '0 0 0 2px var(--sage-tint)',
        }} />
        Agent 今日市场判断
      </div>

      {/* Country name + chip */}
      <div className="flex justify-between items-start" style={{ marginBottom: 4 }}>
        <div>
          <div className="flex items-center gap-3">
            <h2 style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 28, fontWeight: 600 }}>{d.name}</h2>
            {d.status && <span className={`chip ${d.statusKind}`}>{d.status}</span>}
          </div>
          <div style={{ fontSize: 11, letterSpacing: '.18em', color: 'var(--ink-3)', marginTop: 4, textTransform: 'uppercase' }}>
            {d.sub} · Market Judgment
          </div>
        </div>
        <div style={{
          width: 48, height: 56,
          background: 'linear-gradient(135deg, var(--silk), var(--pearl) 60%, var(--gold-wash))',
          borderRadius: '50% 50% 50% 50% / 60% 60% 40% 40%',
          boxShadow: 'inset -4px -2px 8px rgba(168,144,96,.15), inset 4px 4px 10px rgba(255,255,255,.6)',
          position: 'relative', flexShrink: 0,
        }}>
          <div style={{
            position: 'absolute', top: 9, left: '50%',
            transform: 'translateX(-50%) rotate(45deg)',
            width: 9, height: 9,
            background: 'var(--gold-1)',
            boxShadow: '0 0 0 1px var(--pearl)',
          }} />
        </div>
      </div>

      <div className="gold-divider" style={{ margin: '14px 0 12px' }}>
        <Icon name="diamond" size={10} />
      </div>

      {/* Score ring + metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 16, alignItems: 'center', marginBottom: 18 }}>
        <ScoreRing value={d.score} />
        <div className="flex flex-col gap-3">
          <Row label="竞争强度" value={
            <span className="flex gap-1 items-center">
              {[1, 2, 3, 4, 5].map(i => (
                <Icon key={i} name="diamond" size={13}
                  style={{ color: i <= d.competition ? 'var(--gold-2)' : 'var(--ink-5)', opacity: i <= d.competition ? 1 : .35 }} />
              ))}
              <span style={{ fontSize: 11.5, color: 'var(--ink-3)', marginLeft: 4 }}>{d.competitionLabel}</span>
            </span>
          } />
          <Row label="政策环境" value={<span className={`chip ${d.policyKind}`} style={{ fontSize: 12 }}>{d.policy}</span>} />
          <Row label="市场增速 YoY" value={
            <span style={{ color: 'var(--sage-deep)', fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600 }}>{d.growth}</span>
          } />
        </div>
      </div>

      {/* Triggers grid */}
      {d.triggers && d.triggers.length > 0 && (
        <>
          <div style={{ fontSize: 10.5, letterSpacing: '.16em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 8 }}>
            主要触发因素 · Triggers
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 18 }}>
            {d.triggers.map((t, i) => (
              <div key={i} style={{
                padding: '9px 12px',
                background: 'var(--ivory)', border: '1px solid var(--line-soft)', borderRadius: 9,
                fontSize: 12.5, color: 'var(--ink-2)', fontWeight: 600,
              }}>{t}</div>
            ))}
          </div>
        </>
      )}

      {/* Business impacts */}
      {d.impacts && d.impacts.length > 0 && (
        <>
          <div style={{ fontSize: 10.5, letterSpacing: '.16em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 8 }}>
            业务影响 · Business Impact
          </div>
          <div className="flex flex-col gap-2" style={{ marginBottom: 18 }}>
            {d.impacts.map((im, i) => {
              const cfg = im.kind === 'opportunity'
                ? { bg: 'linear-gradient(135deg, var(--sage-tint), #EFF3EC)', border: 'rgba(122,157,126,.28)', label: '机会', labelColor: 'var(--sage-deep)' }
                : im.kind === 'risk'
                ? { bg: 'linear-gradient(135deg, var(--clay-tint), #F5EBE9)', border: 'rgba(201,127,110,.28)', label: '风险', labelColor: 'var(--clay-deep)' }
                : { bg: 'var(--ivory)', border: 'var(--line-soft)', label: '需关注', labelColor: 'var(--ink-3)' }
              return (
                <div key={i} style={{
                  padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10,
                  background: cfg.bg, border: `1px solid ${cfg.border}`, borderRadius: 10,
                }}>
                  <span style={{ fontSize: 11.5, fontWeight: 700, color: cfg.labelColor, flexShrink: 0, minWidth: 38 }}>{cfg.label}</span>
                  <span style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.4 }}>{im.text}</span>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Fallback bullets (when no triggers/impacts data) */}
      {(!d.triggers || d.triggers.length === 0) && (
        <>
          <div style={{ fontSize: 10.5, letterSpacing: '.16em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 8 }}>
            市场亮点 · Market Highlights
          </div>
          <div className="flex flex-col gap-2" style={{ marginBottom: 18 }}>
            {d.bullets.map((b, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 14px',
                background: 'var(--ivory)', border: '1px solid var(--line-soft)', borderRadius: 10,
                fontSize: 13, color: 'var(--ink-2)',
              }}>
                <span style={{
                  width: 26, height: 26, borderRadius: 8,
                  background: 'var(--gold-wash)', display: 'grid', placeItems: 'center',
                  color: 'var(--gold-2)', flexShrink: 0,
                }}><Icon name={b.icon} size={14} /></span>
                <span>{b.text}</span>
              </div>
            ))}
          </div>
        </>
      )}

      <button onClick={() => onJumpToMap('intel')} style={{
        marginTop: 'auto',
        background: 'linear-gradient(135deg, var(--gold-1), var(--gold-2))',
        color: 'var(--pearl)',
        border: 'none', borderRadius: 12,
        padding: '13px 18px', fontSize: 13.5, fontWeight: 600, letterSpacing: '.04em',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        boxShadow: '0 4px 12px rgba(184,145,80,.25), inset 0 1px 0 rgba(255,252,244,.4)',
        cursor: 'pointer',
      }}>
        查看 {d.name} 情报中心
        <Icon name="right" size={14} />
      </button>
    </div>
  )
}
