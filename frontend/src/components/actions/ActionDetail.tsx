import Icon from '../ui/Icon'
import type { Department, DeptRef, EnvFactorId } from '../../api/types'
import { ENV_FACTOR_TONE } from '../../api'

const PRIORITY_LABEL = {
  high: { text: '高优先级', k: 'clay' },
  mid:  { text: '中优先级', k: 'bone' },
  low:  { text: '低优先级', k: 'sage' },
} as const

interface ActionDetailProps {
  d: Department
}

// 单条「关联依据」行 —— 有 sourceUrl 时为外链；否则纯展示，不做跨页跳转。
// 永远不显示 #ID 等内部技术标识。
function RefRow({ r }: { r: DeptRef }) {
  const fid = r.factorId as EnvFactorId | undefined
  const factorTone = fid ? ENV_FACTOR_TONE[fid] : null

  const body = (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, flex: 1, minWidth: 0 }}>
      <span style={{
        color: 'var(--gold-2)', marginTop: 2, flexShrink: 0,
        width: 22, height: 22, borderRadius: 6,
        background: 'var(--gold-wash)', border: '1px solid var(--line)',
        display: 'grid', placeItems: 'center',
      }}>
        <Icon name={r.icon} size={11} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="flex items-center gap-1.5 flex-wrap" style={{ marginBottom: 3 }}>
          <span style={{
            fontSize: 12.5, fontWeight: 600, color: 'var(--ink-1)', lineHeight: 1.4,
            textDecoration: r.sourceUrl ? 'underline dotted var(--gold-3)' : 'none',
            textUnderlineOffset: 3,
          }}>
            {r.text}
          </span>
          {factorTone && r.factorLabel && (
            <span className={`chip ${factorTone}`} style={{ fontSize: 9.5, padding: '1px 6px' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8.5, opacity: .8 }}>{fid} </span>
              {r.factorLabel}
            </span>
          )}
        </div>
        {r.detail && (
          <div style={{ fontSize: 11.5, color: 'var(--ink-3)', lineHeight: 1.45, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
            {r.detail}
          </div>
        )}
      </div>
      {r.sourceUrl && (
        <span style={{ color: 'var(--ink-4)', marginTop: 4, flexShrink: 0 }}>
          <Icon name="external" size={11} />
        </span>
      )}
    </div>
  )

  if (r.sourceUrl) {
    return (
      <a href={r.sourceUrl} target="_blank" rel="noreferrer"
        style={{
          display: 'flex', textDecoration: 'none',
          padding: '8px 10px', borderRadius: 8,
          background: 'transparent', cursor: 'pointer',
        }}
        onMouseEnter={ev => (ev.currentTarget.style.background = 'rgba(184,145,80,.06)')}
        onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}>
        {body}
      </a>
    )
  }
  return <div style={{ display: 'flex', padding: '8px 10px' }}>{body}</div>
}

export default function ActionDetail({ d }: ActionDetailProps) {
  const pl = PRIORITY_LABEL[d.priority]
  return (
    <div className="card flex flex-col" style={{ padding: 24, height: '100%' }}>
      <div className="flex items-center gap-3">
        <span style={{
          width: 40, height: 40, borderRadius: 12,
          background: 'var(--gold-wash)', border: '1px solid var(--line)',
          display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
        }}>
          <Icon name={d.icon} size={20} />
        </span>
        <div>
          <h3 style={{ margin: 0, fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 600 }}>{d.name}行动清单</h3>
          <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 2 }}>
            基于{d.market || '当前市场'}洞察生成 · {d.sub} Action Plan
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 5 }}>
            <span style={{ width: 6, height: 6, borderRadius: 3, background: 'var(--sage)', display: 'inline-block', boxShadow: '0 0 0 2px var(--sage-tint)' }} />
            <span style={{ fontSize: 11, color: 'var(--sage-deep)', fontWeight: 600 }}>基于今日战略简报生成</span>
          </div>
        </div>
      </div>

      <div className="gold-divider" style={{ margin: '16px 0 14px' }}>
        <Icon name="diamond" size={10} />
      </div>

      <div className="flex flex-wrap gap-2" style={{ marginBottom: 16 }}>
        <span className={`chip ${pl.k}`} style={{ padding: '4px 12px', fontSize: 11.5 }}>{pl.text}</span>
        <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>
          建议周期: <span style={{ color: 'var(--ink-1)', fontWeight: 600 }}>{d.cycle}</span>
        </span>
        <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>
          负责人: <span style={{ color: 'var(--ink-1)', fontWeight: 600 }}>{d.owner}</span>
        </span>
      </div>

      <div style={{ fontSize: 11, letterSpacing: '.18em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 8 }}>
        A. 核心目标
      </div>
      <div style={{
        padding: '14px 16px',
        background: 'linear-gradient(135deg, var(--sage-tint), #EEF2EB)',
        border: '1px solid rgba(122,157,126,.3)',
        borderRadius: 10, marginBottom: 18,
        fontFamily: 'var(--font-serif)', fontSize: 15, fontWeight: 600, color: 'var(--sage-deep)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <Icon name="target" size={16} />
        {d.goal}
      </div>

      <div style={{ fontSize: 11, letterSpacing: '.18em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 700, marginBottom: 8 }}>
        B. 行动步骤
      </div>
      <div className="flex flex-col gap-2" style={{ marginBottom: 18, position: 'relative' }}>
        <div style={{ position: 'absolute', left: 16, top: 22, bottom: 22, width: 1, background: 'var(--line-strong)', opacity: .4 }} />
        {d.steps.map((s, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '34px 1fr', gap: 12, alignItems: 'stretch', position: 'relative' }}>
            <div style={{
              width: 34, height: 34, borderRadius: 17,
              background: 'var(--pearl)', border: '2px solid var(--gold-1)',
              display: 'grid', placeItems: 'center',
              fontFamily: 'var(--font-serif)', fontSize: 14, fontWeight: 600,
              color: 'var(--gold-2)', zIndex: 1,
              boxShadow: '0 2px 6px rgba(184,145,80,.18)',
            }}>{String(i + 1).padStart(2, '0')}</div>
            <div style={{
              padding: '12px 14px',
              background: 'var(--ivory)',
              border: '1px solid var(--line-soft)',
              borderRadius: 10,
              display: 'grid', gridTemplateColumns: '1fr auto', gap: 12,
            }}>
              <div>
                <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink-1)', marginBottom: 6 }}>{s.title}</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', fontSize: 12, color: 'var(--ink-2)' }}>
                  <span style={{ color: 'var(--ink-3)' }}>目标:</span><span>{s.goal}</span>
                  <span style={{ color: 'var(--ink-3)' }}>执行:</span><span>{s.how}</span>
                  {s.expectedOutput && (
                    <>
                      <span style={{ color: 'var(--ink-3)' }}>产出:</span><span>{s.expectedOutput}</span>
                    </>
                  )}
                  {s.successMetric && (
                    <>
                      <span style={{ color: 'var(--ink-3)' }}>指标:</span><span>{s.successMetric}</span>
                    </>
                  )}
                  <span style={{ color: 'var(--ink-3)' }}>时间:</span><span style={{ color: 'var(--gold-2)', fontWeight: 600 }}>{s.when}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 11, letterSpacing: '.18em', color: 'var(--ink-3)', textTransform: 'uppercase', fontWeight: 700 }}>
          C. 关联依据
        </div>
        <div style={{ fontSize: 11, color: 'var(--ink-3)' }}>{d.refs.length} 条证据</div>
      </div>
      <div style={{
        padding: 6,
        background: 'linear-gradient(135deg, var(--pearl-warm), var(--ivory))',
        border: '1px solid var(--line-soft)',
        borderRadius: 10,
        display: 'flex', flexDirection: 'column', gap: 2, marginBottom: 18,
      }}>
        {d.refs.length === 0 && (
          <div style={{ padding: '12px 10px', fontSize: 12.5, color: 'var(--ink-3)' }}>
            智囊团基于综合推演产出，未关联单一情报事件
          </div>
        )}
        {d.refs.map((r, i) => (
          <RefRow key={i} r={r} />
        ))}
      </div>
    </div>
  )
}
