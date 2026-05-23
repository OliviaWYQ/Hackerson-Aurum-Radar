import { useEffect, useState } from 'react'
import WorldMap, { Legend } from './WorldMap'
import CountryPanel from './CountryPanel'
import KeyAnalysis from './KeyAnalysis'
import BusinessImpact from './BusinessImpact'
import Icon from '../ui/Icon'
import { fetchCountryDetail, fetchDashboardSummary } from '../../api'
import type { CountryDetail, CountryNode, Filters, PageId } from '../../api/types'
import type { DashboardSummary } from '../../api'

function AiRadarStrip({ summary }: { summary: DashboardSummary | null }) {
  const stats = [
    { label: '今日已扫描市场', value: summary ? String(summary.radar.markets_scanned) : '—', unit: '个' },
    { label: '整合公开信息',   value: summary ? summary.radar.documents_integrated.toLocaleString() : '—', unit: '条' },
    { label: '高优先级变化',   value: summary ? String(summary.radar.high_priority_changes) : '—', unit: '条' },
    { label: '战略判断生成',   value: summary ? String(summary.radar.judgments_generated) : '—', unit: '条' },
  ]
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      padding: '12px 18px',
      background: 'linear-gradient(135deg, rgba(250,242,221,.7), rgba(255,252,246,.85))',
      border: '1px solid var(--line)', borderRadius: 12,
      marginBottom: 14, gap: 0,
    }}>
      {/* Icon + label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingRight: 20, marginRight: 20, borderRight: '1px solid var(--line-strong)', flexShrink: 0 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10, flexShrink: 0,
          background: 'linear-gradient(135deg, var(--gold-tint), var(--gold-wash))',
          border: '1px solid var(--line)',
          display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
        }}>
          <Icon name="broadcast" size={20} />
        </div>
        <div>
          <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--ink-3)', letterSpacing: '.12em', textTransform: 'uppercase', lineHeight: 1 }}>AI Market Radar</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-1)', marginTop: 2, lineHeight: 1.1 }}>AI 市场雷达·今日扫描</div>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', flex: 1, gap: 0 }}>
        {stats.map((s, i) => (
          <div key={i} style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
            paddingRight: 16, marginRight: 16,
            borderRight: i < stats.length - 1 ? '1px solid var(--line-soft)' : 'none',
          }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
              <span style={{ fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 600, color: 'var(--ink-1)', letterSpacing: '-0.01em' }}>{s.value}</span>
              <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>{s.unit}</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-4)', marginTop: 2, textAlign: 'center' }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function OverviewPage({
  onNav,
  filters,
  countries,
  onCountryChange,
}: {
  onNav: (id: PageId) => void
  filters: Filters
  countries: CountryNode[]
  onCountryChange: (id: string) => void
}) {
  const selected = filters.country
  const [countryDetail, setCountryDetail] = useState<CountryDetail | null>(null)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchDashboardSummary(filters.country).then(s => {
      if (cancelled) return
      setSummary(s)
    }).catch(console.error)
    return () => { cancelled = true }
  }, [filters.country])

  useEffect(() => {
    if (!selected) return
    fetchCountryDetail(selected).then(detail => setCountryDetail(detail ?? null)).catch(error => {
      console.error(error)
      setCountryDetail(null)
    })
  }, [selected])

  return (
    <div className="w-full min-h-0">
      <div className="mx-auto w-full max-w-[1440px] px-6 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
          {/* Left column: map + analysis stacked */}
          <div className="flex min-w-0 flex-col gap-6">
            <div className="card min-w-0" style={{ padding: 20 }}>
        {/* AI Radar strip */}
        <AiRadarStrip summary={summary} />

        <div className="flex justify-between items-center flex-wrap" style={{ marginBottom: 14, gap: 10 }}>
          <div className="flex items-center gap-3">
            <h3 className="facet-rule" style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600 }}>
              全球市场雷达
            </h3>
            <span style={{
              padding: '3px 10px', borderRadius: 999,
              background: 'var(--sage-tint)', border: '1px solid rgba(122,157,126,.3)',
              fontSize: 11, fontWeight: 700, color: 'var(--sage-deep)',
              display: 'flex', alignItems: 'center', gap: 5,
            }}>
              <span style={{ width: 5, height: 5, borderRadius: 3, background: 'var(--sage)', display: 'inline-block' }} />
              Agent · Live
            </span>
          </div>
          <div className="flex gap-3 items-center flex-wrap" style={{ fontSize: 11, color: 'var(--ink-3)' }}>
            <Legend dot="#7A9D7E" label="机会增强" />
            <Legend dot="#5B88B0" label="竞争加剧" />
            <Legend dot="#C97F6E" label="风险升温" />
            <Legend dot="#6B7A9E" label="法规变化" />
          </div>
        </div>
        <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--line-soft)', background: 'linear-gradient(135deg, var(--pearl-warm), var(--ivory))' }}>
          <WorldMap selected={selected} countries={countries} onSelect={onCountryChange} />
          <div style={{
            position: 'absolute', left: 18, bottom: 18,
            padding: '10px 14px',
            background: 'rgba(255,252,244,.92)',
            border: '1px solid var(--line)',
            borderRadius: 10,
            fontSize: 12, color: 'var(--ink-2)',
            display: 'flex', alignItems: 'center', gap: 10,
            backdropFilter: 'blur(6px)',
            boxShadow: 'var(--shadow-sm)',
          }}>
            <Icon name="info" size={14} style={{ color: 'var(--gold-2)' }} />
            <span>点击地图国家，右侧刷新 Agent 今日市场判断</span>
          </div>
        </div>
            </div>

            <KeyAnalysis summary={summary} onCard={onNav} />
            <BusinessImpact detail={countryDetail} onAct={onNav} />
          </div>

          {/* Right column: country panel */}
          <div className="min-w-0 h-full">
            <CountryPanel detail={countryDetail} onJumpToMap={onNav} />
          </div>
        </div>
      </div>
    </div>
  )
}
