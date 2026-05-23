interface IconProps {
  name: string
  size?: number
  stroke?: number
  className?: string
  style?: React.CSSProperties
}

export default function Icon({ name, size = 16, stroke = 1.6, className = '', style = {} }: IconProps) {
  const common = {
    width: size, height: size, viewBox: '0 0 24 24',
    fill: 'none', stroke: 'currentColor',
    strokeWidth: stroke, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
    className, style,
  }
  switch (name) {
    case 'home':      return <svg {...common}><path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/></svg>
    case 'map':       return <svg {...common}><path d="M9 4l-6 2v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14"/><path d="M15 6v14"/></svg>
    case 'feed':      return <svg {...common}><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>
    case 'check':     return <svg {...common}><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
    case 'calendar':  return <svg {...common}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/></svg>
    case 'globe':     return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>
    case 'tag':       return <svg {...common}><path d="M20 13l-7 7-9-9V4h7l9 9z"/><circle cx="8" cy="8" r="1.4" fill="currentColor"/></svg>
    case 'chevron':   return <svg {...common}><path d="M6 9l6 6 6-6"/></svg>
    case 'right':     return <svg {...common}><path d="M9 6l6 6-6 6"/></svg>
    case 'left':      return <svg {...common}><path d="M15 6l-6 6 6 6"/></svg>
    case 'info':      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg>
    case 'alert':     return <svg {...common}><path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.5"/></svg>
    case 'bookmark':  return <svg {...common}><path d="M6 3h12v18l-6-4-6 4z"/></svg>
    case 'source':    return <svg {...common}><path d="M4 6h12a4 4 0 0 1 4 4v10H8a4 4 0 0 1-4-4z"/><path d="M4 6v10a4 4 0 0 0 4 4"/></svg>
    case 'link':      return <svg {...common}><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 1 0-5.7-5.7L11 7"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7L13 17"/></svg>
    case 'store':     return <svg {...common}><path d="M3 9l2-5h14l2 5"/><path d="M3 9v11h18V9"/><path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/></svg>
    case 'flame':     return <svg {...common}><path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4-1 3 1 5 3 4-1-3 0-7 0-10z"/></svg>
    case 'wave':      return <svg {...common}><path d="M3 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/><path d="M3 17c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/></svg>
    case 'compass':   return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M15 9l-2 6-4 1 2-6z" fill="currentColor" stroke="none"/></svg>
    case 'users':     return <svg {...common}><circle cx="9" cy="8" r="3.5"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6"/><circle cx="17" cy="9" r="2.8"/><path d="M16 15c4 0 6 2 6 6"/></svg>
    case 'clipboard': return <svg {...common}><rect x="5" y="4" width="14" height="17" rx="2"/><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M9 11h6M9 15h4"/></svg>
    case 'clock':     return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
    case 'scale':     return <svg {...common}><path d="M12 3v18"/><path d="M5 21h14"/><path d="M6 7l-3 7a4 4 0 0 0 6 0L6 7zM18 7l-3 7a4 4 0 0 0 6 0l-3-7z"/></svg>
    case 'crown':     return <svg {...common}><path d="M3 7l4 4 5-7 5 7 4-4-2 12H5z"/></svg>
    case 'ring':      return <svg {...common}><circle cx="12" cy="15" r="6"/><path d="M9 5l3-2 3 2-3 4z"/></svg>
    case 'shield':    return <svg {...common}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/></svg>
    case 'target':    return <svg {...common}><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></svg>
    case 'trending':  return <svg {...common}><path d="M3 17l6-6 4 4 8-9"/><path d="M14 6h7v7"/></svg>
    case 'x':         return <svg {...common}><path d="M6 6l12 12M18 6L6 18"/></svg>
    case 'diamond':   return <svg {...common}><path d="M6 9l6-6 6 6-6 12z"/><path d="M3 9h18M9 3l3 6 3-6"/></svg>
    case 'external':  return <svg {...common}><path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/></svg>
    case 'broadcast': return <svg {...common}><circle cx="12" cy="12" r="2"/><path d="M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7"/><path d="M5.5 5.5a9 9 0 0 0 0 13M18.5 5.5a9 9 0 0 1 0 13"/></svg>
    case 'mountain':  return <svg {...common}><path d="M3 20l6-10 4 6 3-4 5 8z"/></svg>
    case 'lab':       return <svg {...common}><path d="M9 3v6L4 19a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-5-10V3"/><path d="M8 3h8"/><path d="M7 14h10"/></svg>
    default: return null
  }
}
