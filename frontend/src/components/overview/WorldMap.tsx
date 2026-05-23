import { CONTINENT_DOTS } from '../../api/mapLayout'
import type { CountryNode, StatusKind } from '../../api/types'

const STATUS_COLORS: Record<StatusKind, { fill: string; glow: string; label: string }> = {
  high:        { fill: '#7A9D7E', glow: 'rgba(122,157,126,.35)', label: '机会增强' },
  mid:         { fill: '#C8A569', glow: 'rgba(200,165,105,.35)', label: '' },
  risk:        { fill: '#C97F6E', glow: 'rgba(201,127,110,.35)', label: '风险升温' },
  competition: { fill: '#5B88B0', glow: 'rgba(91,136,176,.35)',  label: '竞争加剧' },
  regulation:  { fill: '#6B7A9E', glow: 'rgba(107,122,158,.35)', label: '法规变化' },
  watch:       { fill: '#A89776', glow: 'rgba(168,151,118,.3)',  label: '' },
}

function Arc({ from, to, opacity = 0.5 }: { from: { x: number; y: number }; to: { x: number; y: number }; opacity?: number }) {
  const mx = (from.x + to.x) / 2
  const my = (from.y + to.y) / 2 - Math.abs(from.x - to.x) * 0.15
  return (
    <path d={`M ${from.x} ${from.y} Q ${mx} ${my} ${to.x} ${to.y}`}
      fill="none" stroke="url(#arc-grad)" strokeWidth="1"
      strokeDasharray="2 4" opacity={opacity} />
  )
}

function CountryNodeEl({ c, hot, onClick }: { c: CountryNode; hot: boolean; onClick: (id: string) => void }) {
  const s = STATUS_COLORS[c.status]
  return (
    <g style={{ cursor: 'pointer' }} onClick={() => onClick(c.id)}>
      {hot && (
        <circle cx={c.x} cy={c.y} r={c.size + 14} fill="none" stroke={s.fill} strokeWidth="1" opacity={.4}>
          <animate attributeName="r" values={`${c.size + 6};${c.size + 28};${c.size + 6}`} dur="3.6s" repeatCount="indefinite" />
          <animate attributeName="opacity" values=".5;0;.5" dur="3.6s" repeatCount="indefinite" />
        </circle>
      )}
      <circle cx={c.x} cy={c.y} r={c.size + 6} fill={s.glow} opacity={hot ? .9 : .55} />
      <circle cx={c.x} cy={c.y} r={c.size} fill={s.fill}
        stroke="#FFFCF6" strokeWidth={hot ? 3 : 2}
        style={{ filter: `drop-shadow(0 4px 8px ${s.glow})` }} />
      <circle cx={c.x - c.size * 0.3} cy={c.y - c.size * 0.3} r={c.size * 0.3} fill="rgba(255,255,255,.5)" />
      <g transform={`translate(${c.x + c.size + 12} ${c.y - 4})`}>
        <text fontFamily="var(--font-serif)" fontSize="20" fontWeight="600" fill="#2A2419">{c.name}</text>
        {s.label && (
          <text y="20" fontFamily="var(--font-sans)" fontSize="12" fill={s.fill} fontWeight="600">{s.label}</text>
        )}
      </g>
    </g>
  )
}

interface WorldMapProps {
  selected: string
  countries: CountryNode[]
  onSelect: (id: string) => void
}

export default function WorldMap({ selected, countries, onSelect }: WorldMapProps) {
  const hub = countries.find(c => c.id === 'SG') ?? countries[0]

  return (
    <svg viewBox="0 0 1600 780" style={{ width: '100%', height: '100%', display: 'block' }}>
      <defs>
        <radialGradient id="globe-bg" cx="50%" cy="40%" r="60%">
          <stop offset="0" stopColor="#FBF7EC" />
          <stop offset="1" stopColor="#F4EEE1" />
        </radialGradient>
        <linearGradient id="arc-grad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#C8A569" stopOpacity="0" />
          <stop offset=".5" stopColor="#C8A569" stopOpacity=".7" />
          <stop offset="1" stopColor="#C8A569" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect width="1600" height="780" fill="url(#globe-bg)" />
      {[160, 320, 480, 640].map(y =>
        <line key={y} x1="0" y1={y} x2="1600" y2={y} stroke="rgba(200,165,105,.08)" strokeDasharray="2 8" />
      )}
      {[200, 400, 600, 800, 1000, 1200, 1400].map(x =>
        <line key={x} x1={x} y1="0" x2={x} y2="780" stroke="rgba(200,165,105,.06)" strokeDasharray="2 8" />
      )}
      {CONTINENT_DOTS.map(([x, y, r], i) => (
        <circle key={i} cx={x} cy={y} r={r}
          fill={(x > 1100 && y > 380 && y < 520) || (x > 750 && x < 900 && y < 280) ? '#C8A569' : '#A89776'}
          opacity={(x > 1100 && y > 380 && y < 520) || (x > 750 && x < 900 && y < 280) ? .55 : .35} />
      ))}
      {hub && countries.filter(c => c.id !== hub.id).map(c =>
        <Arc key={c.id} from={{ x: hub.x, y: hub.y }} to={{ x: c.x, y: c.y }}
          opacity={selected === c.id || selected === hub.id ? .55 : .25} />
      )}
      {countries.map(c => (
        <CountryNodeEl key={c.id} c={c} hot={selected === c.id} onClick={onSelect} />
      ))}
    </svg>
  )
}

export function Legend({ dot, label }: { dot: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span style={{ width: 8, height: 8, borderRadius: 8, background: dot, boxShadow: `0 0 0 2px rgba(255,252,244,.8), 0 0 0 3px ${dot}30` }} />
      {label}
    </span>
  )
}
