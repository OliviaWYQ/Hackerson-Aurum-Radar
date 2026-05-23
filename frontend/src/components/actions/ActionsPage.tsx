import { useEffect, useState } from 'react'
import DeptCard from './DeptCard'
import ActionDetail from './ActionDetail'
import StrategyBoard from './StrategyBoard'
import Icon from '../ui/Icon'
import { fetchCouncilStrategy, fetchDepartments } from '../../api'
import type { CouncilStrategy, Department, Filters } from '../../api/types'

function ActStat({ icon, label, value, unit, delta, deltaKind = 'sage', color }: {
  icon: string; label: string; value: string; unit: string;
  delta?: string; deltaKind?: 'sage' | 'clay'; color?: string
}) {
  const bgColor = color === 'clay'
    ? 'linear-gradient(135deg, var(--clay-tint), #F8EBE7)'
    : color === 'indigo'
    ? 'linear-gradient(135deg, var(--indigo-tint), #ECEFF5)'
    : 'linear-gradient(135deg, var(--gold-tint), var(--gold-wash))'
  const iconColor = color === 'clay' ? 'var(--clay-deep)' : color === 'indigo' ? '#4A597D' : 'var(--gold-2)'
  return (
    <div className="card flex items-center gap-3" style={{ padding: 18 }}>
      <div style={{
        width: 56, height: 56, borderRadius: 14,
        background: bgColor, border: '1px solid var(--line-soft)',
        display: 'grid', placeItems: 'center', color: iconColor,
      }}>
        <Icon name={icon} size={22} />
      </div>
      <div>
        <div style={{ fontSize: 12.5, color: 'var(--ink-3)', marginBottom: 4 }}>{label}</div>
        <div className="flex items-baseline gap-1.5">
          <span className="num-display" style={{ fontSize: 30, color: 'var(--ink-1)' }}>{value}</span>
          <span style={{ fontSize: 13, color: 'var(--ink-3)' }}>{unit}</span>
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--ink-3)', marginTop: 4 }}>
          {delta ? (
            <>
              较上月
              <span style={{ marginLeft: 6, fontWeight: 600, color: deltaKind === 'sage' ? 'var(--sage-deep)' : 'var(--clay-deep)' }}>
                {delta}
              </span>
            </>
          ) : '库内最新状态'}
        </div>
      </div>
    </div>
  )
}

interface ActionsPageProps {
  activeDept?: string
  onDeptChange?: (id: string) => void
  filters?: Filters
}

export default function ActionsPage({ activeDept, onDeptChange, filters }: ActionsPageProps = {}) {
  const [localActive, setLocalActive] = useState('mkt')
  const [departments, setDepartments] = useState<Department[]>([])
  const [strategy, setStrategy] = useState<CouncilStrategy | null>(null)
  const active = activeDept ?? localActive
  const setActive = (id: string) => { setLocalActive(id); onDeptChange?.(id) }
  const d = departments.find(x => x.id === active) ?? departments[0]
  const totalActions = departments.reduce((sum, item) => sum + (item.actionCount ?? item.steps.length), 0)
  const highPriority = departments.filter(item => item.priority === 'high').reduce((sum, item) => sum + (item.actionCount ?? 1), 0)
  const pending = departments.reduce((sum, item) => sum + item.steps.length, 0)

  useEffect(() => {
    let cancelled = false
    fetchDepartments(filters?.country).then(items => {
      if (cancelled) return
      setDepartments(items)
      if (items.length > 0 && !items.some(item => item.id === active)) {
        setActive(items[0]!.id)
      }
    }).catch(console.error)
    return () => { cancelled = true }
  }, [filters?.country]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let cancelled = false
    fetchCouncilStrategy(filters?.country).then(s => {
      if (cancelled) return
      setStrategy(s)
    }).catch(console.error)
    return () => { cancelled = true }
  }, [filters?.country])

  return (
    <div className="flex flex-col gap-4" style={{ padding: 22 }}>
      <StrategyBoard strategy={strategy} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 480px', gap: 18 }}>
        {/* Left */}
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-end flex-wrap gap-3">
            <div>
              <h2 style={{ margin: '2px 0 4px', fontFamily: 'var(--font-serif)', fontSize: 26, fontWeight: 600 }}>行动建议</h2>
              <div style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>先看智囊团总策，再按部门拆解下一步行动</div>
            </div>
            <div className="flex items-center gap-1.5" style={{ fontSize: 11.5, color: 'var(--ink-3)' }}>
              <Icon name="info" size={12} style={{ color: 'var(--gold-2)' }} />
              点击部门卡片 → 右侧查看具体行动清单
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
            <ActStat icon="clipboard" label="建议事项总数" value={String(totalActions)} unit="项" />
            <ActStat icon="alert"     label="高优先级"     value={String(highPriority)} unit="项" deltaKind="clay" color="clay" />
            <ActStat icon="clock"     label="待推进"       value={String(pending)} unit="项" color="indigo" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
            {departments.map(dx => <DeptCard key={dx.id} d={dx} active={dx.id === active} onPick={setActive} />)}
            {departments.length === 0 && (
              <div className="card" style={{ padding: 18, color: 'var(--ink-3)' }}>暂无行动建议数据</div>
            )}
          </div>

          <div className="card flex items-center gap-3" style={{ padding: 14 }}>
            <span style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--gold-wash)', display: 'grid', placeItems: 'center', color: 'var(--gold-2)', border: '1px solid var(--line)' }}>
              <Icon name="info" size={16} />
            </span>
            <div style={{ fontSize: 12.5, color: 'var(--ink-2)', flex: 1 }}>
              <span style={{ color: 'var(--ink-3)' }}>更新频率: </span>
              <span style={{ fontWeight: 600 }}>每日更新</span>
              <span style={{ margin: '0 12px', color: 'var(--ink-4)' }}>|</span>
              <span style={{ color: 'var(--ink-3)' }}>说明: </span>
              基于本期市场洞察与情报分析，结合历史执行数据，智能生成行动建议。
            </div>
          </div>
        </div>

        {/* Right detail */}
        <div style={{ position: 'sticky', top: 18, maxHeight: 'calc(100vh - 140px)' }}>
          {d ? <ActionDetail d={d} /> : <div className="card" style={{ padding: 24, color: 'var(--ink-3)' }}>请选择行动部门</div>}
        </div>
      </div>
    </div>
  )
}
