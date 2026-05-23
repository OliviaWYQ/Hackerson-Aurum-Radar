interface DiamondMarkProps {
  size?: number
}

export default function DiamondMark({ size = 36 }: DiamondMarkProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
      <defs>
        <linearGradient id="dm-g1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#EEDBA8" />
          <stop offset=".55" stopColor="#C8A569" />
          <stop offset="1" stopColor="#9C7A3E" />
        </linearGradient>
        <linearGradient id="dm-g2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FFFCF6" />
          <stop offset="1" stopColor="#F0E2BB" />
        </linearGradient>
      </defs>
      <g transform="translate(20 20)">
        {[0, 1, 2, 3, 4, 5].map(i => (
          <path key={i}
            d="M0 -14 L7 -4 L0 14 L-7 -4 Z"
            fill={i % 2 ? 'url(#dm-g1)' : 'url(#dm-g2)'}
            stroke="#B89150" strokeWidth=".5"
            transform={`rotate(${i * 60})`}
            opacity={i % 2 ? .85 : .95}
          />
        ))}
        <circle r="3" fill="#FFFCF6" stroke="#C8A569" strokeWidth=".8" />
      </g>
    </svg>
  )
}
