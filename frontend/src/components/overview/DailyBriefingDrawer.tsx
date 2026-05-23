import { useEffect, useState } from 'react'
import Icon from '../ui/Icon'
import { fetchLatestBrief } from '../../api'

import type { DailyBrief, Filters } from '../../api/types'

interface DailyBriefingDrawerProps {
  open: boolean
  onClose: () => void
  onNavToActions: (deptId: string) => void
  onOpenAgentChat: (q?: string) => void
  filters: Filters
}

// ── Section header ───────────────────────────────────────────────
function SectionHeader({ title, sub }: { title: string; sub: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
      <div className="flex items-center gap-2">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M6 9l6-6 6 6-6 12z" fill="var(--gold-1)" stroke="var(--gold-2)" strokeWidth="1" />
          <path d="M3 9h18M9 3l3 6 3-6" stroke="var(--gold-2)" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
        <span style={{ fontFamily: 'var(--font-serif)', fontSize: 20, fontWeight: 600, color: 'var(--ink-1)' }}>
          {title}
        </span>
      </div>
      <span style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: '.18em', color: 'var(--ink-4)', textTransform: 'uppercase' }}>
        {sub}
      </span>
    </div>
  )
}

// ── Market card ──────────────────────────────────────────────────
const STATUS_CHIP: Record<string, string> = {
  '机会增强': 'sage',
  '风险升温': 'clay',
  '法规变化': 'indigo',
  '竞争加剧': 'bone',
}

function MarketCard({ name, sub, status, desc, delay }: { name: string; sub: string; status: string; desc: string; delay: number }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 16,
      padding: '16px 18px',
      background: 'var(--pearl)', border: '1px solid var(--line-soft)', borderRadius: 14,
      animation: `item-fade-up 0.4s ease both`,
      animationDelay: `${delay}ms`,
    }}>
      <div style={{ minWidth: 90 }}>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: 20, fontWeight: 600, color: 'var(--ink-1)', lineHeight: 1.2 }}>{name}</div>
        <div style={{ fontSize: 10, letterSpacing: '.14em', color: 'var(--ink-4)', textTransform: 'uppercase', marginTop: 2 }}>{sub}</div>
      </div>
      {status && (
        <span className={`chip ${STATUS_CHIP[status] ?? 'bone'}`} style={{ padding: '4px 12px', fontSize: 12, fontWeight: 700, flexShrink: 0 }}>{status}</span>
      )}
      <span style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.5, flex: 1 }}>{desc || '暂无摘要'}</span>
    </div>
  )
}

// ── Signal change row ────────────────────────────────────────────
const CAT_ICONS: Record<string, string> = {
  竞争: 'users', 产品: 'diamond', 平台: 'store', 社媒: 'broadcast', 法规: 'shield',
}
const CAT_CHIP: Record<string, string> = {
  竞争: 'clay', 产品: 'gold', 平台: 'sage', 社媒: 'plum', 法规: 'indigo',
}

function SignalRow({ cat, text, delay }: { cat: string; text: string; delay: number }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '14px 18px',
      background: 'var(--pearl)', border: '1px solid var(--line-soft)', borderRadius: 12,
      animation: `item-fade-up 0.4s ease both`,
      animationDelay: `${delay}ms`,
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 16, flexShrink: 0,
        background: 'var(--gold-wash)', border: '1px solid var(--line-soft)',
        display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
      }}>
        <Icon name={CAT_ICONS[cat] ?? 'info'} size={15} />
      </div>
      <span className={`chip ${CAT_CHIP[cat] ?? 'bone'}`} style={{ padding: '3px 10px', fontSize: 12, fontWeight: 700, flexShrink: 0 }}>{cat}</span>
      <span style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.5 }}>{text}</span>
    </div>
  )
}

// ── Impact card (3-column) ───────────────────────────────────────
function ImpactCard({ kind, text, delay }: { kind: 'opportunity' | 'risk' | 'watch'; text: string; delay: number }) {
  const cfg = kind === 'opportunity'
    ? { label: '机会', bg: 'linear-gradient(160deg, var(--sage-tint), #E8F0E4)', border: 'rgba(122,157,126,.28)', labelColor: 'var(--sage-deep)' }
    : kind === 'risk'
    ? { label: '风险', bg: 'linear-gradient(160deg, var(--clay-tint), #F4E6E2)', border: 'rgba(201,127,110,.28)', labelColor: 'var(--clay-deep)' }
    : { label: '需关注', bg: 'var(--ivory)', border: 'var(--line-soft)', labelColor: 'var(--ink-3)' }
  return (
    <div style={{
      flex: 1, padding: '14px 16px', borderRadius: 14,
      background: cfg.bg, border: `1px solid ${cfg.border}`,
      animation: `item-fade-up 0.4s ease both`,
      animationDelay: `${delay}ms`,
    }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: cfg.labelColor, marginBottom: 8 }}>{cfg.label}</div>
      <div style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.55 }}>{text}</div>
    </div>
  )
}

// ── Drawer ───────────────────────────────────────────────────────
export default function DailyBriefingDrawer({ open, onClose, onNavToActions, onOpenAgentChat, filters }: DailyBriefingDrawerProps) {
  const [brief, setBrief] = useState<DailyBrief | null>(null)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    fetchLatestBrief(filters.country).then(b => {
      if (cancelled) return
      setBrief(b)
    }).catch(error => {
      console.error(error)
      if (!cancelled) setBrief(null)
    })
    return () => { cancelled = true }
  }, [open, filters.country])

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div onClick={onClose} style={{
        position: 'fixed', inset: 0, zIndex: 50,
        background: 'rgba(42, 36, 25, 0.30)',
        backdropFilter: 'blur(2px)',
        animation: 'backdrop-fade-in 0.25s ease both',
      }} />

      {/* Drawer panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 51,
        width: 560,
        background: 'var(--ivory)',
        borderLeft: '1px solid var(--line)',
        boxShadow: '-8px 0 40px rgba(120,92,40,.12)',
        display: 'flex', flexDirection: 'column',
        animation: 'drawer-slide-in 0.32s cubic-bezier(.22,.68,0,1.2) both',
      }}>

        {/* Header */}
        <div style={{
          padding: '22px 24px 18px',
          background: 'linear-gradient(180deg, var(--pearl) 60%, rgba(255,252,244,.6))',
          borderBottom: '1px solid var(--line-soft)',
          flexShrink: 0,
        }}>
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-3">
              <div style={{
                width: 44, height: 44, borderRadius: 12,
                background: 'linear-gradient(135deg, var(--gold-tint), var(--gold-wash))',
                border: '1px solid var(--line)',
                display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
              }}>
                <Icon name="clipboard" size={22} />
              </div>
              <div>
                <h2 style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 24, fontWeight: 600, color: 'var(--ink-1)', lineHeight: 1.2 }}>
                  每日战略简报
                </h2>
              </div>
            </div>
            <button onClick={onClose} style={{
              background: 'transparent', border: '1px solid var(--line)',
              borderRadius: 8, width: 34, height: 34,
              color: 'var(--ink-3)', display: 'grid', placeItems: 'center',
              fontSize: 16, fontWeight: 400, cursor: 'pointer',
            }}>×</button>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            marginTop: 10, fontSize: 13, color: 'var(--ink-3)',
          }}>
            <span style={{ fontFamily: 'var(--font-mono)' }}>{brief?.asOf ? new Date(brief.asOf).toLocaleString('zh-CN', { hour12: false }) : brief?.briefDate ?? '—'}</span>
            <span style={{ color: 'var(--ink-5)' }}>·</span>
            <span style={{ fontWeight: 600, letterSpacing: '.06em', color: 'var(--ink-4)', textTransform: 'uppercase', fontSize: 11.5 }}>Agent 自动生成</span>
            <span style={{
              width: 7, height: 7, borderRadius: 4,
              background: 'var(--sage)', display: 'inline-block',
              boxShadow: '0 0 0 2px var(--sage-tint)',
            }} />
          </div>
        </div>

        {/* Scrollable content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* 今日重点市场 */}
          <div>
            <SectionHeader title="今日重点市场" sub="Key Markets" />
            <div className="flex flex-col gap-3">
              {(brief?.markets.length ? brief.markets : []).map((market, i) => (
                <MarketCard key={market.id} name={market.name} sub={market.sub} status={market.status} desc={market.desc} delay={60 + i * 40} />
              ))}
              {!brief?.markets.length && <div style={{ fontSize: 13, color: 'var(--ink-3)' }}>暂无市场简报数据</div>}
            </div>
          </div>

          {/* 关键变化 */}
          <div>
            <SectionHeader title="关键变化" sub="Signal Changes" />
            <div className="flex flex-col gap-2">
              {(brief?.signalChanges ?? []).map((item, i) => (
                <SignalRow key={`${item.cat}-${item.text}`} cat={item.cat} text={item.text} delay={220 + i * 30} />
              ))}
              {!brief?.signalChanges.length && <div style={{ fontSize: 13, color: 'var(--ink-3)' }}>暂无关键变化</div>}
            </div>
          </div>

          {/* 业务影响判断 */}
          <div>
            <SectionHeader title="业务影响判断" sub="Business Impact" />
            <div style={{ display: 'flex', gap: 12 }}>
              {(brief?.impacts ?? []).slice(0, 3).map((impact, i) => (
                <ImpactCard key={`${impact.kind}-${impact.text}`} kind={impact.kind} text={impact.text} delay={380 + i * 30} />
              ))}
              {!brief?.impacts.length && <div style={{ fontSize: 13, color: 'var(--ink-3)' }}>暂无业务影响判断</div>}
            </div>
          </div>

          {/* 建议后续行动 */}
          <div>
            <SectionHeader title="建议后续行动" sub="Suggested Actions" />
            <div className="flex flex-col gap-3">
              {(brief?.actions ?? []).map((a, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '14px 18px',
                  background: 'var(--pearl)', border: '1px solid var(--line-soft)', borderRadius: 12,
                  animation: `item-fade-up 0.4s ease both`,
                  animationDelay: `${460 + i * 30}ms`,
                }}>
                  <span style={{
                    padding: '5px 12px', borderRadius: 20, flexShrink: 0,
                    background: 'var(--ivory)', border: '1px solid var(--line)',
                    fontSize: 12.5, fontWeight: 700, color: 'var(--ink-2)',
                  }}>{a.dept}</span>
                  <span style={{ fontSize: 13.5, color: 'var(--ink-2)', lineHeight: 1.5, flex: 1 }}>{a.text}</span>
                  <button onClick={() => onNavToActions(a.deptId)} style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    background: 'transparent', border: 'none',
                    fontSize: 13, fontWeight: 700, color: 'var(--gold-2)',
                    cursor: 'pointer', flexShrink: 0, padding: '4px 0',
                  }}>
                    跳转 <Icon name="right" size={12} />
                  </button>
                </div>
              ))}
              {!brief?.actions.length && <div style={{ fontSize: 13, color: 'var(--ink-3)' }}>暂无行动建议</div>}
            </div>
          </div>

          {/* Disclaimer */}
          <div style={{
            padding: '14px 16px',
            background: 'var(--ivory)', border: '1px dashed var(--line-strong)', borderRadius: 12,
            display: 'flex', alignItems: 'flex-start', gap: 10,
            fontSize: 12.5, color: 'var(--ink-3)', lineHeight: 1.65,
            animation: `item-fade-up 0.4s ease both`,
            animationDelay: '560ms',
          }}>
            <Icon name="clipboard" size={14} style={{ color: 'var(--ink-4)', marginTop: 2, flexShrink: 0 }} />
            <span>本简报由 Market Radar Agent 基于库内最新公开信息自动整合；当前简报覆盖 {brief?.sourceCount ?? 0} 条来源、{brief?.eventCount ?? 0} 条情报事件。</span>
          </div>

        </div>

        {/* Bottom action bar — 4 agent-linked actions */}
        <div style={{
          padding: '14px 24px',
          background: 'var(--pearl)',
          borderTop: '1px solid var(--line-soft)',
          flexShrink: 0,
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--ink-4)', letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 9 }}>
            继续推理 · Ask Agent
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[
              { label: '继续追问', q: undefined, icon: 'broadcast' },
              { label: '解释这个判断', q: '解释今日战略判断的主要依据', icon: 'info' },
              { label: '查看来源', q: '哪些判断有最高可信来源？', icon: 'source' },
              { label: '生成部门行动', q: '今天有哪些 P0 / P1 行动建议？', icon: 'check' },
            ].map(({ label, q, icon }) => (
              <button key={label} onClick={() => { onOpenAgentChat(q); onClose(); }} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                padding: '9px 10px',
                background: 'var(--ivory)', border: '1px solid var(--line)',
                borderRadius: 10, fontSize: 12.5, fontWeight: 600, color: 'var(--ink-2)',
                cursor: 'pointer', transition: 'all .15s ease',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--line-strong)'; e.currentTarget.style.background = 'var(--gold-wash)'; e.currentTarget.style.color = 'var(--ink-1)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--line)'; e.currentTarget.style.background = 'var(--ivory)'; e.currentTarget.style.color = 'var(--ink-2)' }}
              >
                <Icon name={icon} size={13} style={{ color: 'var(--gold-2)' }} />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
