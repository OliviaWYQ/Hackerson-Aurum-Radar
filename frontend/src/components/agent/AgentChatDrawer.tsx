import { useState, useRef, useEffect } from 'react'
import Icon from '../ui/Icon'

const CONTEXT_CHIPS = ['今日战略简报', '新加坡市场判断', '高优先级事件', '部门行动建议', '关联分析']

const SUGGESTED_QUESTIONS = [
  '为什么今天新加坡被判断为机会增强？',
  '金价高位对哪些产品线影响最大？',
  '今天有哪些 P0 / P1 行动建议？',
  '哪些判断有最高可信来源？',
]

interface AgentResponse {
  conclusion: string
  basis: string
  events: string[]
  sources: string[]
  nextStep: string
}

const CANNED: Record<string, AgentResponse> = {
  '为什么今天新加坡被判断为机会增强？': {
    conclusion: '新加坡市场今日判断为「机会增强」，核心驱动力来自旅游消费复苏与高端珠宝需求的双重共振。',
    basis: 'MAS 最新统计显示新加坡零售额环比 +4.2%，奢侈品类增速领跑。鸟节路、滨海湾区客流指数创 2023 年以来新高，竞品亦加速布局印证市场信心。',
    events: [
      '新加坡旅游局 Q2 入境游客同比 +18%',
      'Chow Tai Fook 宣布扩大新加坡门店布局',
      '贝恩 Q1 报告：东南亚高端消费超预期回升',
    ],
    sources: [
      'Singapore Retail Sales Index · MAS · 2026/05',
      'STB Tourism Statistics · May 2026',
      'Bain Luxury Report Q1 2026',
    ],
    nextStep: '建议产品部门优先评估 SKU 投放节奏，门店运营同步更新陈列策略以捕捉旅游客流高峰。',
  },
  '金价高位对哪些产品线影响最大？': {
    conclusion: '当前金价（约 $3,280/oz）对纯金饰品线成本压力最大，但对高端镶嵌宝石线有潜在利好，可借势强化品牌高端调性。',
    basis: 'Au 价自 4 月初累计涨 12.3%，推高纯金饰品生产成本约 8–10%。消费者调研显示高净值客群购买频次不变，入门级消费者购买意愿下降约 22%。',
    events: [
      'COMEX 黄金期货 5/22 收报 $3,281',
      '内部 CRM 调研：入门消费者意愿下滑 22%',
      '竞品启动促销降价 5–8% 清库存',
    ],
    sources: [
      'COMEX Gold Futures · Bloomberg · 2026/05/22',
      'Internal CRM Survey May 2026',
      'Competitor Pricing Monitor · Aurum Intel',
    ],
    nextStep: '短期：入门金饰调价或推分期方案。中期：加大镶嵌系列投入，降低纯金成本敞口。',
  },
  '今天有哪些 P0 / P1 行动建议？': {
    conclusion: '今日共检测到 2 条 P0 行动、3 条 P1 行动，均需本周内完成响应。',
    basis: 'P0 源自竞品突发扩张与平台政策变更，P1 涵盖产品结构调整与社媒内容响应窗口。',
    events: [
      '[P0] 竞品 Luk Fook 新加坡增开 2 门店（ION、Takashimaya）',
      '[P0] Shopee 奢侈品新规 5/28 生效，需提前认证',
      '[P1] Instagram SEA 算法更新，视频权重上升',
      '[P1] 新加坡旅游局 Q3 合作招募截止 5/31',
      '[P1] 建议调整 Au 锁价比例降低汇率风险',
    ],
    sources: [
      'Internal Intelligence Alert · 2026/05/22 09:00',
      'Shopee Platform Policy Notice · 2026/05/20',
      'Instagram Algorithm Update · SearchEngineJournal',
    ],
    nextStep: '立即：启动 Shopee 认证，调取竞品选址情报。本周内：确认旅游局合作，更新社媒内容矩阵。',
  },
  '哪些判断有最高可信来源？': {
    conclusion: '新加坡市场判断与金价影响分析可信度最高，均来自政府级公开权威数据，且经过三源交叉验证。',
    basis: '判断可信度按来源权威性（政府 > 行业报告 > 媒体）、数据时效性（48h 内 > 7日内）、多源验证程度（≥3 个独立来源）综合评分。',
    events: [
      '新加坡零售额：MAS 官方统计，三源验证，A 级',
      '金价走势：COMEX + Bloomberg + 路透社，三方确认，A 级',
      '竞品动态：门店勘察 + 公司公告 + 行业媒体，B+ 级',
    ],
    sources: [
      'MAS Singapore Retail Statistics · Government · A 级',
      'Bloomberg Terminal Gold Spot · Financial · A 级',
      'STB Official Tourism Data · Government · A 级',
    ],
    nextStep: '策略制定时优先参考 A 级来源判断，单一来源情报标注「待验证」后再行动。',
  },
  '解释今日战略判断的主要依据': {
    conclusion: '今日战略判断综合了宏观经济信号、竞品动态、平台数据与消费者行为四个维度，整体置信度为高。',
    basis: '判断框架采用多源信号加权：①宏观层：金价、汇率、政策 ②竞争层：竞品动态、新店布局 ③渠道层：平台流量、社媒声量 ④消费层：CRM、客流、意愿调研。各维度均有明确数据支撑。',
    events: [
      '宏观层：金价高位 + SGD 走强，影响采购成本与定价策略',
      '竞争层：Luk Fook 加速扩张，正面竞争压力上升',
      '渠道层：Shopee 新规影响线上品牌运营合规性',
      '消费层：旅游客流创新高，高净值消费意愿稳定',
    ],
    sources: [
      'Aurum Intelligence Scoring Framework v2.1',
      'Internal Dashboard Pipeline · 2026/05/22',
      'Cross-source Validation Report · May 2026',
    ],
    nextStep: '建议每周对比战略判断与实际业务数据，验证信号有效性；遇重大偏差时触发快速复盘。',
  },
}

const FALLBACK: AgentResponse = {
  conclusion: '已接收您的问题，正在基于当前情报库进行推理分析。',
  basis: '情报覆盖新加坡、日本、澳大利亚、英国等核心市场，来源包括政府公开统计、行业研究报告及竞品监测。',
  events: ['今日新增情报事件 12 条', '高优先级信号 3 条已推送至行动建议'],
  sources: ['Aurum Radar Intelligence DB · 2026/05/22', 'Multi-source Aggregation Pipeline · Live'],
  nextStep: '建议前往「情报中心」查看完整事件列表，或「行动建议」查看部门级响应方案。',
}

interface ChatMessage {
  id: string
  role: 'user' | 'agent'
  text: string
  response?: AgentResponse
  loading?: boolean
}

export interface AgentChatDrawerProps {
  open: boolean
  onClose: () => void
  initialQuestion?: string
}

function LoadingBubble() {
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
      <AgentAvatar />
      <div style={{
        padding: '12px 16px',
        background: 'var(--pearl)', border: '1px solid var(--line-soft)', borderRadius: '4px 12px 12px 12px',
      }}>
        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 6, height: 6, borderRadius: 3,
              background: 'var(--gold-3)',
              display: 'inline-block',
              animation: 'agent-pulse 1.2s ease infinite',
              animationDelay: `${i * 0.22}s`,
            }} />
          ))}
        </div>
      </div>
    </div>
  )
}

function AgentAvatar() {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: 8, flexShrink: 0,
      background: 'linear-gradient(135deg, var(--gold-tint), var(--gold-wash))',
      border: '1px solid var(--line)',
      display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
    }}>
      <Icon name="diamond" size={12} />
    </div>
  )
}

function AgentBubble({ msg }: { msg: ChatMessage }) {
  const r = msg.response
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
      <AgentAvatar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 7 }}>
        <div style={{
          padding: '12px 14px',
          background: 'var(--pearl)', border: '1px solid var(--line-soft)', borderRadius: '4px 12px 12px 12px',
          fontSize: 13.5, color: 'var(--ink-1)', lineHeight: 1.65,
        }}>
          {msg.text}
        </div>

        {r && (
          <>
            <div style={{
              padding: '10px 14px',
              background: 'rgba(250,242,221,.5)', border: '1px solid var(--line-soft)', borderRadius: 10,
              fontSize: 12.5, color: 'var(--ink-2)', lineHeight: 1.6,
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--ink-4)', letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 4 }}>判断依据</div>
              {r.basis}
            </div>

            <div style={{
              padding: '10px 14px',
              background: 'var(--ivory)', border: '1px solid var(--line-soft)', borderRadius: 10,
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--ink-4)', letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 8 }}>相关事件</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                {r.events.map((ev, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 12.5, color: 'var(--ink-2)', lineHeight: 1.45 }}>
                    <span style={{ width: 5, height: 5, borderRadius: 3, marginTop: 5, background: 'var(--gold-2)', flexShrink: 0 }} />
                    {ev}
                  </div>
                ))}
              </div>
            </div>

            <div style={{
              padding: '8px 12px',
              border: '1px dashed var(--line-strong)', borderRadius: 8,
              display: 'flex', flexWrap: 'wrap', gap: 5, alignItems: 'center',
            }}>
              <span style={{ fontSize: 10, color: 'var(--ink-4)', fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase', lineHeight: '18px', flexShrink: 0 }}>来源</span>
              {r.sources.map((src, i) => (
                <span key={i} style={{
                  padding: '2px 8px', borderRadius: 20,
                  background: 'var(--gold-wash)', border: '1px solid var(--line-soft)',
                  fontSize: 10.5, color: 'var(--ink-3)',
                }}>{src}</span>
              ))}
            </div>

            <div style={{
              padding: '10px 14px',
              background: 'linear-gradient(135deg, rgba(122,157,126,.08), rgba(122,157,126,.03))',
              border: '1px solid rgba(122,157,126,.25)', borderRadius: 10,
              fontSize: 12.5, color: 'var(--sage-deep)', lineHeight: 1.6,
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 4, opacity: .8 }}>建议下一步</div>
              {r.nextStep}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function AgentChatDrawer({ open, onClose, initialQuestion }: AgentChatDrawerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const didSendRef = useRef(false)

  useEffect(() => {
    if (open) {
      setMessages([])
      setInput('')
      didSendRef.current = false
    }
  }, [open])

  useEffect(() => {
    if (open && initialQuestion && !didSendRef.current) {
      didSendRef.current = true
      doSend(initialQuestion)
    }
  }, [open, initialQuestion])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  function doSend(text: string) {
    const q = text.trim()
    if (!q) return
    const loadingId = String(Date.now()) + '-a'

    setMessages(prev => [
      ...prev,
      { id: String(Date.now()) + '-u', role: 'user', text: q },
      { id: loadingId, role: 'agent', text: '', loading: true },
    ])

    setTimeout(() => {
      const response = CANNED[q] ?? FALLBACK
      setMessages(prev => prev.map(m =>
        m.id === loadingId
          ? { ...m, loading: false, text: response.conclusion, response }
          : m
      ))
    }, 900)
  }

  function handleSend() {
    const q = input.trim()
    if (!q) return
    setInput('')
    doSend(q)
  }

  if (!open) return null

  return (
    <>
      <div onClick={onClose} style={{
        position: 'fixed', inset: 0, zIndex: 50,
        background: 'rgba(42,36,25,.12)',
        animation: 'backdrop-fade-in 0.25s ease both',
      }} />

      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 51,
        width: 420,
        background: 'linear-gradient(180deg, #FDFAF3, #FAF7EE)',
        borderLeft: '1px solid var(--line-strong)',
        boxShadow: '-4px 0 24px rgba(120,92,40,.10)',
        display: 'flex', flexDirection: 'column',
        animation: 'drawer-slide-in 0.32s cubic-bezier(.22,.68,0,1.2) both',
      }}>

        {/* Header */}
        <div style={{
          padding: '18px 20px 14px',
          background: 'linear-gradient(180deg, #FDFAF3 60%, rgba(253,250,243,.5))',
          borderBottom: '1px solid var(--line-soft)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, var(--gold-tint), var(--gold-wash))',
                border: '1px solid var(--line)',
                display: 'grid', placeItems: 'center', color: 'var(--gold-2)',
              }}>
                <Icon name="broadcast" size={18} />
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600, color: 'var(--ink-1)', lineHeight: 1.2 }}>
                  Aurum Agent
                </div>
                <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 2, letterSpacing: '.04em' }}>
                  继续追问今日战略简报
                </div>
              </div>
            </div>
            <button onClick={onClose} style={{
              background: 'transparent', border: '1px solid var(--line)',
              borderRadius: 8, width: 30, height: 30,
              color: 'var(--ink-3)', display: 'grid', placeItems: 'center',
              fontSize: 16, cursor: 'pointer',
            }}>×</button>
          </div>

          {/* Context chips */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 12 }}>
            {CONTEXT_CHIPS.map(chip => (
              <span key={chip} style={{
                padding: '3px 10px', borderRadius: 20,
                background: 'var(--gold-wash)', border: '1px solid var(--line)',
                fontSize: 11, color: 'var(--ink-2)', fontWeight: 500,
              }}>{chip}</span>
            ))}
          </div>
        </div>

        {/* Conversation */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {messages.length === 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--ink-4)', letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 10 }}>
                建议问题
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {SUGGESTED_QUESTIONS.map(q => (
                  <button key={q} onClick={() => doSend(q)}
                    style={{
                      textAlign: 'left', padding: '10px 14px',
                      background: 'var(--pearl)', border: '1px solid var(--line-soft)', borderRadius: 10,
                      fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.5,
                      cursor: 'pointer', transition: 'all .15s ease',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--line-strong)'; e.currentTarget.style.background = 'var(--gold-wash)' }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--line-soft)'; e.currentTarget.style.background = 'var(--pearl)' }}
                  >{q}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map(msg => (
            msg.role === 'user' ? (
              <div key={msg.id} style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <div style={{
                  maxWidth: '82%', padding: '10px 14px',
                  background: 'linear-gradient(135deg, var(--gold-3), var(--gold-1))',
                  border: '1px solid var(--gold-2)',
                  borderRadius: '12px 4px 12px 12px',
                  fontSize: 13.5, color: 'var(--pearl)', lineHeight: 1.5,
                }}>
                  {msg.text}
                </div>
              </div>
            ) : msg.loading ? (
              <LoadingBubble key={msg.id} />
            ) : (
              <AgentBubble key={msg.id} msg={msg} />
            )
          ))}
        </div>

        {/* Input bar */}
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--line-soft)',
          background: 'var(--pearl)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
              placeholder="Ask about market signals, brief, sources, or actions…"
              style={{
                flex: 1, padding: '10px 14px',
                background: 'var(--ivory)', border: '1px solid var(--line)',
                borderRadius: 10, fontSize: 13, color: 'var(--ink-1)',
                outline: 'none', fontFamily: 'inherit',
                transition: 'border-color .15s',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--line-strong)')}
              onBlur={e => (e.target.style.borderColor = 'var(--line)')}
            />
            <button onClick={handleSend} style={{
              padding: '10px 18px',
              background: 'linear-gradient(135deg, var(--gold-3), var(--gold-1))',
              border: '1px solid var(--gold-2)', borderRadius: 10,
              fontSize: 13, fontWeight: 700, color: 'var(--pearl)',
              cursor: 'pointer', whiteSpace: 'nowrap',
              boxShadow: '0 2px 8px rgba(184,145,80,.2)',
            }}>Send</button>
          </div>
        </div>
      </div>
    </>
  )
}
