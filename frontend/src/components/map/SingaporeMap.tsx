import type { SgRegion } from '../../api/types'

const SG_LAND_PATH =
  'M 110 280 ' +
  'C 140 240, 200 220, 280 215 ' +
  'C 360 210, 440 215, 540 220 ' +
  'C 640 226, 740 230, 820 245 ' +
  'C 900 260, 970 285, 1010 320 ' +
  'C 1040 345, 1055 380, 1040 410 ' +
  'C 1025 440, 990 460, 940 470 ' +
  'C 880 482, 820 484, 750 478 ' +
  'C 660 470, 580 482, 500 478 ' +
  'C 410 472, 330 470, 250 460 ' +
  'C 170 448, 110 430, 90 390 ' +
  'C 70 350, 80 310, 110 280 Z'

interface SingaporeMapProps {
  selected: string
  regions: SgRegion[]
  onSelect: (id: string) => void
}

export default function SingaporeMap({ selected, regions, onSelect }: SingaporeMapProps) {
  const selectedRegion = regions.find(region => region.id === selected)

  return (
    <svg viewBox="0 0 1150 560" style={{ width: '100%', height: '100%', display: 'block' }}>
      <defs>
        <linearGradient id="sg-island" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#F4EEE1" />
          <stop offset=".55" stopColor="#EBE0C5" />
          <stop offset="1" stopColor="#DECCA0" />
        </linearGradient>
        <radialGradient id="sg-bg" cx="50%" cy="50%" r="60%">
          <stop offset="0" stopColor="#F0F4EE" />
          <stop offset="1" stopColor="#E5EAE2" />
        </radialGradient>
        <radialGradient id="orchard-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#EEDBA8" stopOpacity="0.9" />
          <stop offset="1" stopColor="#C8A569" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="1150" height="560" fill="url(#sg-bg)" />
      {[100, 200, 300, 400, 500].map(y => (
        <path key={y} d={`M 0 ${y} Q 200 ${y - 8}, 400 ${y} T 800 ${y} T 1200 ${y}`}
          fill="none" stroke="rgba(140, 165, 155, .12)" strokeWidth="1" />
      ))}
      <path d={SG_LAND_PATH} fill="url(#sg-island)"
        stroke="#C8A569" strokeWidth="1.2" strokeOpacity=".5"
        style={{ filter: 'drop-shadow(0 8px 18px rgba(120,92,40,.15))' }} />
      <path d={SG_LAND_PATH} fill="none" stroke="rgba(255,252,244,.7)" strokeWidth="2" transform="translate(0,-1.5)" />

      {selectedRegion && <circle cx={selectedRegion.x} cy={selectedRegion.y} r="100" fill="url(#orchard-glow)" />}

      {regions.map(r => {
        const isSel = selected === r.id
        return (
          <g key={r.id} style={{ cursor: 'pointer' }} onClick={() => onSelect(r.id)}>
            {isSel && (
              <circle cx={r.x} cy={r.y} r={48} fill="none" stroke="#C8A569" strokeWidth="1" strokeDasharray="3 4" opacity=".6">
                <animateTransform attributeName="transform" type="rotate"
                  from={`0 ${r.x} ${r.y}`} to={`360 ${r.x} ${r.y}`} dur="22s" repeatCount="indefinite" />
              </circle>
            )}
            <g transform={`translate(${r.x} ${r.y})`}>
              <circle r={isSel ? 38 : 22} fill={isSel ? '#EEDBA8' : 'rgba(238,219,168,.5)'} opacity={isSel ? .8 : .55} />
              <circle r={isSel ? 32 : 18}
                fill={isSel ? 'url(#sg-island)' : '#FFFCF6'}
                stroke="#B89150" strokeWidth="1.5"
                style={{ filter: 'drop-shadow(0 4px 10px rgba(184,145,80,.35))' }} />
              {isSel && <circle r={32} fill="none" stroke="#C8A569" strokeWidth="2" />}
              <text y={isSel ? 4 : 3} textAnchor="middle"
                fontFamily="var(--font-serif)" fontWeight="600"
                fontSize={isSel ? 22 : 14}
                fill={isSel ? '#5D4818' : '#B89150'}>{r.stores}</text>
            </g>
            <g transform={`translate(${r.x + (isSel ? 44 : 30)} ${r.y - (isSel ? 18 : 12)})`}>
              <rect x="0" y="0" rx="6" ry="6"
                width={isSel ? 110 : 90} height={isSel ? 42 : 34}
                fill="#FFFCF6" stroke="rgba(168,144,96,.32)" strokeWidth="1" />
              <text x="10" y="16" fontFamily="var(--font-serif)" fontWeight="600"
                fontSize={isSel ? 16 : 14} fill="#2A2419">{r.name}</text>
              <text x="10" y={isSel ? 33 : 28} fontFamily="var(--font-sans)"
                fontSize="11" fill="#786C53">{r.stores} 家门店</text>
            </g>
          </g>
        )
      })}
    </svg>
  )
}
