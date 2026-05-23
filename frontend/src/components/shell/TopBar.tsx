import { useEffect, useRef, useState } from 'react'
import DiamondMark from '../ui/DiamondMark'
import Icon from '../ui/Icon'
import { fetchJobsStatus, getMarketDisplayName } from '../../api'
import type { CountryNode, Filters, StatusKind } from '../../api/types'

// ── Agent status bar (top thin strip) ───────────────────────────

function AgentBar({ onOpenBriefing }: { onOpenBriefing: () => void }) {
  const [status, setStatus] = useState('连接中')
  const [lastRun, setLastRun] = useState('—')

  useEffect(() => {
    fetchJobsStatus().then(data => {
      setStatus(data.status === 'success' ? '已完成' : data.status === 'running' ? '运行中' : data.status)
      setLastRun(data.lastRun ? new Date(data.lastRun).toLocaleString('zh-CN', { hour12: false }) : '—')
    }).catch(error => {
      console.error(error)
      setStatus('待连接')
    })
  }, [])

  const items = [
    { label: '流水线状态', value: status, dot: status === '待连接' ? 'bone' : 'sage' },
    { label: '最近运行', value: lastRun, dot: 'bone' },
    { label: '数据源', value: '公开信息', dot: 'bone' },
  ]
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 0,
      padding: '5px 28px',
      background: 'linear-gradient(90deg, rgba(250,242,221,.55), rgba(255,252,246,.45))',
      borderBottom: '1px solid var(--line-soft)',
      fontSize: 11.5,
    }}>
      {/* Agent name + status */}
      <div className="flex items-center gap-2" style={{ paddingRight: 20, marginRight: 20, borderRight: '1px solid var(--line)' }}>
        <span style={{
          width: 7, height: 7, borderRadius: 4,
          background: 'var(--sage)', display: 'inline-block',
          boxShadow: '0 0 0 2px var(--sage-tint)',
        }} />
        <span style={{ fontWeight: 700, color: 'var(--ink-2)', letterSpacing: '.06em', textTransform: 'uppercase', fontSize: 11 }}>
          Market Radar Agent
        </span>
        <button onClick={onOpenBriefing} style={{ background: 'transparent', border: 'none', color: 'var(--sage-deep)', fontWeight: 600, cursor: 'pointer', padding: 0 }}>查看简报</button>
      </div>

      {/* Status items */}
      {items.map((it, i) => (
        <div key={i} className="flex items-center gap-1.5" style={{ paddingRight: 20, marginRight: 20, borderRight: i < items.length - 1 ? '1px solid var(--line)' : 'none' }}>
          <span style={{
            width: 5, height: 5, borderRadius: 3,
            background: it.dot === 'sage' ? 'var(--sage)' : 'var(--ink-4)',
            display: 'inline-block',
          }} />
          {it.label && <span style={{ color: 'var(--ink-4)' }}>{it.label}</span>}
          <span style={{ color: 'var(--ink-2)', fontWeight: 600 }}>{it.value}</span>
        </div>
      ))}
    </div>
  )
}

// ── Filter pill ──────────────────────────────────────────────────

const HEADER_CONTROL_H = 46

function formatDate(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}/${m}/${day}`
}

function getLast30DaysRange() {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 29)
  return {
    label: '最近 30 天',
    range: `${formatDate(start)} – ${formatDate(end)}`,
  }
}

interface FilterPillProps {
  icon: string
  label: string
  value: string
  subValue?: string
  onClick?: (event: React.MouseEvent) => void
  readOnly?: boolean
  readOnlyTitle?: string
  open?: boolean
}

function FilterPill({ icon, label, value, subValue, onClick, readOnly, readOnlyTitle, open }: FilterPillProps) {
  const sharedStyle: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 10,
    height: HEADER_CONTROL_H,
    boxSizing: 'border-box',
    padding: '0 16px',
    background: 'var(--pearl)',
    border: '1px solid var(--line)',
    borderRadius: 12,
    boxShadow: 'var(--shadow-sm), var(--shadow-inner)',
    minWidth: 190, textAlign: 'left',
    cursor: readOnly ? 'default' : 'pointer',
    transition: readOnly ? 'none' : 'all .15s ease',
  }

  const content = (
    <>
      <span style={{
        width: 28, height: 28, borderRadius: 7, flexShrink: 0,
        background: 'var(--gold-wash)',
        display: 'grid', placeItems: 'center',
        color: 'var(--gold-2)',
        border: '1px solid var(--line-soft)',
      }}>
        <Icon name={icon} size={14} />
      </span>
      <span style={{ flex: 1, lineHeight: 1.2, minWidth: 0 }}>
        <div style={{ fontSize: 10.5, color: 'var(--ink-3)', letterSpacing: '.06em' }}>{label}</div>
        <div style={{ fontSize: 13, color: 'var(--ink-1)', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {value}
          {subValue && (
            <span style={{ fontSize: 11, color: 'var(--ink-4)', fontWeight: 500, fontFamily: 'var(--font-mono)', marginLeft: 6 }}>{subValue}</span>
          )}
        </div>
      </span>
      {!readOnly && (
        <Icon name="chevron" size={13} style={{
          color: 'var(--ink-4)',
          transform: open ? 'rotate(180deg)' : 'none',
          transition: 'transform .15s ease',
        }} />
      )}
    </>
  )

  if (readOnly) {
    return (
      <div style={sharedStyle} title={readOnlyTitle}>
        {content}
      </div>
    )
  }

  return (
    <button onClick={onClick}
      style={{
        ...sharedStyle,
        borderColor: open ? 'var(--line-strong)' : 'var(--line)',
      }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--line-strong)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = open ? 'var(--line-strong)' : 'var(--line)')}>
      {content}
    </button>
  )
}

const STATUS_META: Record<StatusKind, { color: string; label: string }> = {
  high:        { color: '#7A9D7E', label: '机会增强' },
  mid:         { color: '#C8A569', label: '' },
  risk:        { color: '#C97F6E', label: '风险升温' },
  competition: { color: '#5B88B0', label: '竞争加剧' },
  regulation:  { color: '#6B7A9E', label: '法规变化' },
  watch:       { color: '#A89776', label: '' },
}

function CountryFilterPill({
  value,
  countries,
  onChange,
}: {
  value: string
  countries: CountryNode[]
  onChange: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const selected = countries.find(c => c.id === value)
  const displayName = selected?.name ?? getMarketDisplayName(value)

  useEffect(() => {
    if (!open) return

    const onDocumentClick = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }

    const timer = window.setTimeout(() => {
      document.addEventListener('click', onDocumentClick)
    }, 0)
    document.addEventListener('keydown', onKeyDown)

    return () => {
      window.clearTimeout(timer)
      document.removeEventListener('click', onDocumentClick)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const pick = (id: string) => {
    onChange(id)
    setOpen(false)
  }

  const toggleOpen = (event: React.MouseEvent) => {
    event.stopPropagation()
    setOpen(v => !v)
  }

  return (
    <div ref={rootRef} style={{ position: 'relative' }}>
      <FilterPill
        icon="globe"
        label="地区 / REGION"
        value={displayName}
        subValue={selected && selected.name !== selected.sub ? selected.sub : undefined}
        open={open}
        onClick={toggleOpen}
      />

      {open && (
        <div
          onMouseDown={event => event.stopPropagation()}
          style={{
          position: 'absolute',
          top: 'calc(100% + 8px)',
          right: 0,
          width: '100%',
          minWidth: 190,
          padding: '6px',
          background: 'var(--pearl)',
          border: '1px solid var(--line-strong)',
          borderRadius: 12,
          boxShadow: 'var(--shadow-lg)',
          zIndex: 30,
        }}>
          <div style={{
            padding: '4px 8px 6px',
            fontSize: 10,
            letterSpacing: '.08em',
            textTransform: 'uppercase',
            color: 'var(--ink-4)',
            fontWeight: 700,
          }}>
            选择国家 / 地区
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 280, overflowY: 'auto' }}>
            {countries.length === 0 ? (
              <div style={{ padding: '10px 8px', fontSize: 12, color: 'var(--ink-4)' }}>加载市场中…</div>
            ) : countries.map(country => {
              const active = country.id === value
              const status = STATUS_META[country.status]
              return (
                <button
                  key={country.id}
                  type="button"
                  onMouseDown={event => {
                    event.preventDefault()
                    event.stopPropagation()
                    pick(country.id)
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    width: '100%',
                    padding: '7px 8px',
                    borderRadius: 8,
                    border: active ? '1px solid rgba(200,165,105,.45)' : '1px solid transparent',
                    background: active ? 'var(--gold-wash)' : 'transparent',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background .12s ease, border-color .12s ease',
                  }}
                  onMouseEnter={e => {
                    if (!active) e.currentTarget.style.background = 'var(--ivory)'
                  }}
                  onMouseLeave={e => {
                    if (!active) e.currentTarget.style.background = 'transparent'
                  }}
                >
                  <span style={{
                    width: 6,
                    height: 6,
                    borderRadius: 6,
                    background: status.color,
                    boxShadow: `0 0 0 2px rgba(255,252,244,.85), 0 0 0 3px ${status.color}30`,
                    flexShrink: 0,
                  }} />
                  <span style={{
                    flex: 1,
                    minWidth: 0,
                    fontSize: 13,
                    fontWeight: active ? 600 : 500,
                    color: 'var(--ink-1)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>{country.name}</span>
                  <span style={{
                    fontSize: 10,
                    color: 'var(--ink-4)',
                    fontFamily: 'var(--font-mono)',
                    flexShrink: 0,
                  }}>{country.sub}</span>
                  {active && <Icon name="check" size={13} style={{ color: 'var(--gold-2)', flexShrink: 0 }} />}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── TopBar ───────────────────────────────────────────────────────

interface TopBarProps {
  filters: Filters
  countries: CountryNode[]
  onCountryChange: (id: string) => void
  onOpenBriefing: () => void
  onOpenAgentChat: () => void
}

export default function TopBar({ filters, countries, onCountryChange, onOpenBriefing, onOpenAgentChat }: TopBarProps) {
  const timeRange = getLast30DaysRange()

  return (
    <header style={{ borderBottom: '1px solid var(--line-soft)', position: 'relative', zIndex: 5 }}>
      {/* Thin agent status bar */}
      <AgentBar onOpenBriefing={onOpenBriefing} />

      {/* Main header row */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 28px',
        background: 'linear-gradient(180deg, rgba(255,252,244,.8), rgba(250,246,238,.4))',
        backdropFilter: 'blur(6px)',
        gap: 16, flexWrap: 'wrap',
      }}>
        {/* Left: Logo + title */}
        <div className="flex items-center gap-3">
          <DiamondMark size={40} />
          <div>
            <h1 style={{
              margin: 0, fontFamily: 'var(--font-serif)',
              fontSize: 22, fontWeight: 600, letterSpacing: '0.04em',
              color: 'var(--ink-1)',
            }}>全球市场战略情报看板</h1>
            <div style={{
              fontSize: 10.5, color: 'var(--ink-3)', marginTop: 1,
              letterSpacing: '.18em', textTransform: 'uppercase', fontWeight: 500,
            }}>Jewelry Overseas Market Intelligence · Aurum Radar</div>
          </div>
        </div>

        {/* Right: Filters + CTA */}
        <div className="flex items-center gap-3">
          <FilterPill icon="calendar" label="时间 / TIME"
            value={timeRange.label}
            subValue={timeRange.range}
            readOnly
            readOnlyTitle="时间范围固定为最近 30 天，不可修改" />
          <CountryFilterPill
            value={filters.country}
            countries={countries}
            onChange={onCountryChange}
          />

          {/* Ask Agent button */}
          <button onClick={onOpenAgentChat} style={{
            display: 'flex', alignItems: 'center', gap: 7,
            height: HEADER_CONTROL_H,
            boxSizing: 'border-box',
            padding: '0 16px',
            background: 'var(--pearl)',
            border: '1px solid var(--line-strong)',
            borderRadius: 12,
            color: 'var(--gold-2)',
            fontSize: 13, fontWeight: 700, letterSpacing: '.02em',
            boxShadow: 'var(--shadow-sm)',
            whiteSpace: 'nowrap',
            transition: 'all .15s ease',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--gold-wash)'; e.currentTarget.style.borderColor = 'var(--gold-2)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--pearl)'; e.currentTarget.style.borderColor = 'var(--line-strong)' }}
          >
            <Icon name="broadcast" size={14} />
            Ask Agent
          </button>

          {/* Gold CTA */}
          <button onClick={onOpenBriefing} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            height: HEADER_CONTROL_H,
            boxSizing: 'border-box',
            padding: '0 20px',
            background: 'linear-gradient(135deg, var(--gold-1), var(--gold-2))',
            border: '1px solid var(--gold-2)',
            borderRadius: 12,
            color: 'var(--pearl)',
            fontSize: 13.5, fontWeight: 700, letterSpacing: '.02em',
            boxShadow: '0 4px 12px rgba(184,145,80,.3), inset 0 1px 0 rgba(255,252,244,.4)',
            whiteSpace: 'nowrap',
          }}>
            <Icon name="calendar" size={15} />
            查看今日战略简报
            <Icon name="right" size={13} />
          </button>
        </div>
      </div>
    </header>
  )
}
