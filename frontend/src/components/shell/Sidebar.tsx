import Icon from '../ui/Icon'
import type { PageId } from '../../api/types'

const NAV: { id: PageId; label: string; sub: string; icon: string }[] = [
  { id: 'overview', label: '概览',   sub: 'Overview',     icon: 'home'  },
  { id: 'intel',    label: '情报中心', sub: 'Intelligence', icon: 'feed'  },
  { id: 'actions',  label: '行动建议', sub: 'Actions',      icon: 'check' },
]

interface SidebarProps {
  current: PageId
  onNav: (id: PageId) => void
}

export default function Sidebar({ current, onNav }: SidebarProps) {
  return (
    <aside style={{
      width: 108, flexShrink: 0,
      background: 'linear-gradient(180deg, var(--pearl-warm), var(--ivory))',
      borderRight: '1px solid var(--line-soft)',
      display: 'flex', flexDirection: 'column',
      padding: '24px 14px',
      gap: 8,
      position: 'relative',
    }}>
      {NAV.map(item => {
        const active = current === item.id
        return (
          <button key={item.id} onClick={() => onNav(item.id)}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
              padding: '16px 8px', borderRadius: 14,
              background: active
                ? 'linear-gradient(180deg, var(--gold-tint), var(--gold-wash))'
                : 'transparent',
              border: active ? '1px solid var(--line-strong)' : '1px solid transparent',
              boxShadow: active ? 'var(--shadow-sm), var(--shadow-inner)' : 'none',
              color: active ? 'var(--ink-1)' : 'var(--ink-3)',
              transition: 'all .18s ease',
              position: 'relative',
            }}
            onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(200,165,105,.06)' }}
            onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
          >
            {active && (
              <span style={{
                position: 'absolute', left: -14, top: '50%',
                transform: 'translateY(-50%) rotate(45deg)',
                width: 8, height: 8, background: 'var(--gold-1)',
                boxShadow: '0 0 0 2px var(--ivory), 0 0 0 3px var(--gold-3)',
              }} />
            )}
            <span style={{
              width: 34, height: 34, borderRadius: 10,
              background: active ? 'var(--pearl)' : 'transparent',
              display: 'grid', placeItems: 'center',
              color: active ? 'var(--gold-2)' : 'var(--ink-4)',
              border: active ? '1px solid var(--line)' : '1px solid transparent',
            }}>
              <Icon name={item.icon} size={18} />
            </span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 14, fontWeight: 600, letterSpacing: '.05em' }}>
              {item.label}
            </div>
            <div style={{
              fontSize: 9.5, letterSpacing: '.14em', textTransform: 'uppercase',
              color: active ? 'var(--gold-2)' : 'var(--ink-4)',
            }}>{item.sub}</div>
          </button>
        )
      })}

      <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, paddingTop: 24, opacity: .7 }}>
        <div style={{
          width: 56, height: 80,
          background: 'linear-gradient(135deg, #FFFCF6 0%, #F0E8D6 40%, #E8DFC8 70%, #FFFCF6 100%)',
          borderRadius: '40% 60% 50% 50%',
          filter: 'blur(.4px)',
          boxShadow: 'inset 4px 6px 12px rgba(168,144,96,.18), inset -4px -2px 8px rgba(255,255,255,.6)',
          position: 'relative',
        }}>
          <div style={{
            position: 'absolute', left: '50%', top: '50%',
            transform: 'translate(-50%,-50%) rotate(45deg)',
            width: 18, height: 18,
            background: 'linear-gradient(135deg, #FFFCF6, #DCC089)',
            boxShadow: '0 2px 8px rgba(168,144,96,.4), inset 0 0 0 1px rgba(255,255,255,.5)',
          }} />
        </div>
        <div style={{ fontSize: 9, letterSpacing: '.2em', color: 'var(--ink-4)', textTransform: 'uppercase' }}>v0.1 · MVP</div>
      </div>
    </aside>
  )
}
