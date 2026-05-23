import { useEffect, useState } from 'react'
import SingaporeMap from './SingaporeMap'
import RegionPanel from './RegionPanel'
import Icon from '../ui/Icon'
import { fetchRegionDetail, fetchSgRegions } from '../../api'
import type { Filters, RegionDetail, SgRegion } from '../../api/types'

function StoreDistribution({ regions }: { regions: SgRegion[] }) {
  const rows = [...regions].sort((a, b) => b.stores - a.stores)
  const max = Math.max(1, ...rows.map(r => r.stores))
  const total = rows.reduce((s, r) => s + r.stores, 0)
  return (
    <BottomCard icon="store" title="门店分布概览">
      <div className="flex flex-col gap-1.5">
        {rows.map(r => (
          <div key={r.id} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 32px', alignItems: 'center', gap: 10, fontSize: 12.5 }}>
            <span style={{ color: 'var(--ink-2)' }}>{r.name}</span>
            <div style={{ height: 8, background: 'var(--gold-wash)', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ width: `${(r.stores / max) * 100}%`, height: '100%', background: 'linear-gradient(90deg, var(--gold-3), var(--gold-1))', borderRadius: 8 }} />
            </div>
            <span style={{ textAlign: 'right', color: 'var(--ink-2)', fontWeight: 600 }}>{r.stores}</span>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--line-soft)', display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ color: 'var(--ink-3)' }}>合计</span>
        <span className="num-display" style={{ color: 'var(--ink-1)', fontSize: 15 }}>{total} <span style={{ fontSize: 10, color: 'var(--ink-3)' }}>家门店</span></span>
      </div>
    </BottomCard>
  )
}

function HeatList({ regions, onPick, selected }: { regions: SgRegion[]; onPick: (id: string) => void; selected: string }) {
  const items = regions
    .filter(region => region.hot === 'high' || region.priority)
    .slice(0, 4)
    .map(region => ({
      id: region.id,
      name: region.name,
      desc: `${region.sub} · ${region.stores} 家门店`,
      heat: region.hot === 'high' ? '高' : '中',
    }))
  return (
    <BottomCard icon="flame" title="核心商圈热力">
      <div className="flex flex-col gap-2">
        {items.map(it => (
          <button key={it.id} onClick={() => onPick(it.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: 8, borderRadius: 10,
              background: selected === it.id ? 'var(--gold-wash)' : 'transparent',
              border: selected === it.id ? '1px solid var(--line)' : '1px solid transparent',
              textAlign: 'left', cursor: 'pointer',
            }}>
            <div style={{
              width: 38, height: 38, flexShrink: 0, borderRadius: 8,
              background: 'linear-gradient(135deg, var(--silk), var(--gold-tint))',
              position: 'relative', overflow: 'hidden', border: '1px solid var(--line-soft)',
            }}>
              <svg viewBox="0 0 38 38" style={{ position: 'absolute', inset: 0 }}>
                <rect x="6"  y="20" width="6" height="14" fill="rgba(168,144,96,.5)" />
                <rect x="14" y="14" width="8" height="20" fill="rgba(168,144,96,.65)" />
                <rect x="24" y="18" width="6" height="16" fill="rgba(168,144,96,.5)" />
              </svg>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-1)' }}>{it.name}</div>
              <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 2, lineHeight: 1.35 }}>{it.desc}</div>
            </div>
            <span className={`chip ${it.heat === '高' ? 'sage' : 'bone'}`}>热力{it.heat}</span>
          </button>
        ))}
      </div>
    </BottomCard>
  )
}

function TrafficSignals({ detail }: { detail?: RegionDetail | null }) {
  const sigs = detail?.metrics ?? []
  return (
    <BottomCard icon="broadcast" title="客流与消费信号">
      <div className="flex flex-col gap-2">
        {sigs.map((s, i) => (
          <div key={i} style={{
            display: 'grid', gridTemplateColumns: 'auto 1fr auto auto', alignItems: 'center', gap: 10,
            padding: '10px 12px',
            background: 'var(--ivory)', borderRadius: 10, border: '1px solid var(--line-soft)',
          }}>
            <span style={{ color: 'var(--gold-2)' }}><Icon name={s.icon} size={14} /></span>
            <span style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>{s.label}</span>
            <span style={{ fontSize: 12.5, color: 'var(--sage-deep)', fontWeight: 600 }}>{s.value}</span>
            <span style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>{s.unit ?? ''}</span>
          </div>
        ))}
        {sigs.length === 0 && <div style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>暂无区域指标</div>}
      </div>
    </BottomCard>
  )
}

function OpsRisk({ detail }: { detail?: RegionDetail | null }) {
  const risks = detail?.insights ?? []
  return (
    <BottomCard icon="shield" title="区域运营风险">
      <div className="flex flex-col gap-2">
        {risks.slice(0, 4).map((r, i) => (
          <div key={i} style={{
            display: 'grid', gridTemplateColumns: '10px 1fr', gap: 10, alignItems: 'center',
            padding: '10px 12px',
            background: 'var(--ivory)', borderRadius: 10, border: '1px solid var(--line-soft)',
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: 8,
              background: 'var(--ink-4)',
              boxShadow: '0 0 0 3px var(--gold-wash)',
              marginLeft: 4,
            }} />
            <div>
              <div style={{ fontSize: 12.5, color: 'var(--ink-1)', fontWeight: 600 }}>{r}</div>
            </div>
          </div>
        ))}
        {risks.length === 0 && <div style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>暂无风险洞察</div>}
      </div>
    </BottomCard>
  )
}

function BottomCard({ icon, title, children }: { icon: string; title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="flex items-center gap-2" style={{ marginBottom: 12 }}>
        <span style={{ color: 'var(--gold-2)' }}><Icon name={icon} size={15} /></span>
        <span style={{ fontFamily: 'var(--font-serif)', fontSize: 15, fontWeight: 600, color: 'var(--ink-1)' }}>{title}</span>
      </div>
      {children}
    </div>
  )
}

function SimTag({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: 10.5, color: 'var(--ink-4)' }}>{label}:</span>
      <span style={{ fontSize: 11, fontWeight: 600, color: '#4A597D' }}>{value}</span>
    </div>
  )
}

export default function MapInsightPage({ filters }: { filters: Filters }) {
  const [regions, setRegions] = useState<SgRegion[]>([])
  const [selected, setSelected] = useState('')
  const [detail, setDetail] = useState<RegionDetail | null>(null)
  const market = filters.country
  const regionName = detail?.name ?? regions.find(region => region.id === selected)?.name ?? ''

  useEffect(() => {
    fetchSgRegions(market).then(items => {
      setRegions(items)
      setSelected(current => current || items[0]?.id || '')
    }).catch(console.error)
  }, [market])

  useEffect(() => {
    if (!selected) return
    fetchRegionDetail(selected).then(next => setDetail(next ?? null)).catch(error => {
      console.error(error)
      setDetail(null)
    })
  }, [selected])

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 440px',
      gridTemplateRows: 'auto auto',
      gap: 18,
      padding: 22,
    }}>
      {/* Map */}
      <div className="card" style={{ padding: 20, gridColumn: '1 / 2', gridRow: '1 / 2' }}>
        {/* Strategy simulation strip */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
          padding: '8px 14px', marginBottom: 14,
          background: 'linear-gradient(135deg, var(--indigo-tint), rgba(255,252,246,.8))',
          border: '1px solid rgba(107,122,158,.2)', borderRadius: 10,
          fontSize: 11.5,
        }}>
          <span style={{ fontWeight: 700, color: '#4A597D', letterSpacing: '.02em' }}>区域战略模拟</span>
          <span style={{ color: 'var(--ink-4)' }}>|</span>
          <SimTag label="区域类型" value={detail?.profile.type ?? '—'} />
          <SimTag label="模拟区域" value={regionName || '乌节路'} />
          <SimTag label="适合动作" value={detail?.profile.action ?? '—'} />
          <SimTag label="数据来源" value="后端 districts + market snapshots" />
        </div>

        <div className="flex justify-between items-center flex-wrap" style={{ marginBottom: 14, gap: 12 }}>
          <div className="flex items-center flex-wrap" style={{ gap: 16 }}>
            <h3 className="facet-rule" style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600 }}>地图洞察</h3>
            <div className="flex gap-2 items-center" style={{ fontSize: 12, color: 'var(--ink-3)' }}>
              <span>当前国家:</span>
              <span className="chip sage">{filters.country}</span>
              <span style={{ marginLeft: 10 }}>当前选中区域:</span>
              <span className="chip gold">{regionName}</span>
            </div>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px',
            background: 'var(--gold-wash)', borderRadius: 999, border: '1px solid var(--line)',
            fontSize: 11.5, color: 'var(--ink-2)',
          }}>
            <Icon name="info" size={12} style={{ color: 'var(--gold-2)' }} />
            点击区域卡片，查看该商圈详细洞察与机会建议
          </div>
        </div>
        <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--line-soft)' }}>
          <SingaporeMap selected={selected} regions={regions} onSelect={setSelected} />
          <div style={{
            position: 'absolute', right: 16, top: 16,
            width: 44, height: 44, borderRadius: 22,
            background: 'rgba(255,252,244,.85)', border: '1px solid var(--line)',
            display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
            backdropFilter: 'blur(4px)',
          }}>
            <Icon name="compass" size={20} />
          </div>
        </div>
      </div>

      {/* Right panel */}
      <div style={{ gridColumn: '2 / 3', gridRow: '1 / 3' }}>
        <RegionPanel detail={detail} />
      </div>

      {/* Bottom modules */}
      <div style={{ gridColumn: '1 / 2', gridRow: '2 / 3', display: 'grid', gridTemplateColumns: '1fr 1.1fr 1fr 1fr', gap: 14 }}>
        <StoreDistribution regions={regions} />
        <HeatList regions={regions} onPick={setSelected} selected={selected} />
        <TrafficSignals detail={detail} />
        <OpsRisk detail={detail} />
      </div>
    </div>
  )
}
