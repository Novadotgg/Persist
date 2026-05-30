import React, { useState, useRef, useEffect } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  status?: string
  timestamp?: Date
  pendingApproval?: {
    id: string
    type: string
    payload: Record<string, any>
    decision?: 'approved' | 'rejected'
  }
}

const statusConfig: Record<string, { color: string; bg: string; border: string; label: string; dot: string }> = {
  PLANNING: {
    color: '#a5b4fc',
    bg: 'rgba(99,102,241,0.12)',
    border: 'rgba(99,102,241,0.25)',
    label: 'Planning',
    dot: '#818cf8',
  },
  EXECUTING: {
    color: '#93c5fd',
    bg: 'rgba(59,130,246,0.1)',
    border: 'rgba(59,130,246,0.2)',
    label: 'Executing',
    dot: '#60a5fa',
  },
  PAUSED: {
    color: '#fbbf24',
    bg: 'rgba(251,191,36,0.1)',
    border: 'rgba(251,191,36,0.2)',
    label: 'Awaiting Input',
    dot: '#f59e0b',
  },
  COMPLETED: {
    color: '#6ee7b7',
    bg: 'rgba(52,211,153,0.1)',
    border: 'rgba(52,211,153,0.2)',
    label: 'Completed',
    dot: '#34d399',
  },
  FAILED: {
    color: '#fca5a5',
    bg: 'rgba(252,165,165,0.1)',
    border: 'rgba(252,165,165,0.15)',
    label: 'Failed',
    dot: '#f87171',
  },
  IDLE: {
    color: 'var(--color-lead)',
    bg: 'rgba(112,112,125,0.1)',
    border: 'rgba(112,112,125,0.2)',
    label: 'Idle',
    dot: 'var(--color-lead)',
  },
}

function TypingDots() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: 'var(--color-mercury-blue)',
            display: 'inline-block',
            animation: 'chat-typing-bounce 1.2s ease-in-out infinite',
            animationDelay: `${i * 0.18}s`,
          }}
        />
      ))}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const cfg = statusConfig[status] ?? statusConfig.IDLE
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 12px 4px 8px',
        borderRadius: '100px',
        backgroundColor: cfg.bg,
        border: `1px solid ${cfg.border}`,
        fontSize: '11px',
        fontWeight: 500,
        color: cfg.color,
        letterSpacing: '0.04em',
        whiteSpace: 'nowrap',
        backdropFilter: 'blur(8px)',
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: cfg.dot,
          flexShrink: 0,
          animation: ['PLANNING', 'EXECUTING'].includes(status)
            ? 'chat-status-pulse 1.5s ease-in-out infinite'
            : 'none',
        }}
      />
      {cfg.label}
    </div>
  )
}

export default function ChatTerminal() {
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem('chat_history')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        return parsed.map((m: any) => ({
          ...m,
          timestamp: m.timestamp ? new Date(m.timestamp) : undefined,
        }))
      } catch (e) {
        console.error('Failed to parse saved chat history', e)
      }
    }
    return [
      {
        id: 'welcome',
        role: 'assistant',
        content: 'System initialized. Ready to execute commands, analyze data, and manage your connected workflows.',
        status: 'COMPLETED',
        timestamp: new Date(),
      },
    ]
  })
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const [input, setInput] = useState('')
  const [agentStatus, setAgentStatus] = useState<'IDLE' | 'PLANNING' | 'EXECUTING' | 'PAUSED' | 'FAILED'>('IDLE')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [hoveredMsg, setHoveredMsg] = useState<string | null>(null)
  const feedEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    localStorage.setItem('chat_history', JSON.stringify(messages))
  }, [messages])

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, agentStatus])

  const handleClearHistory = () => {
    setShowClearConfirm(true)
  }

  const confirmClearHistory = () => {
    const welcomeMsg = [
      {
        id: 'welcome',
        role: 'assistant' as const,
        content: 'System initialized. Ready to execute commands, analyze data, and manage your connected workflows.',
        status: 'COMPLETED',
        timestamp: new Date(),
      },
    ]
    setMessages(welcomeMsg)
    localStorage.setItem('chat_history', JSON.stringify(welcomeMsg))
    setShowClearConfirm(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isSubmitting) return

    const userQuery = input.trim()
    setInput('')
    setIsSubmitting(true)
    setAgentStatus('PLANNING')

    const userMsgId = Math.random().toString(36).substring(7)
    const newMessages = [
      ...messages,
      { id: userMsgId, role: 'user' as const, content: userQuery, timestamp: new Date() },
    ]
    setMessages(newMessages)

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch('http://localhost:8000/api/v1/actions/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          query: userQuery,
          chat_history: newMessages.map((m) => ({ role: m.role, content: m.content })),
        }),
      })

      if (!response.ok) throw new Error('API server returned error')
      const data = await response.json()

      setAgentStatus(data.status as any)

      const assistantMsgId = Math.random().toString(36).substring(7)
      const assistantMsg: Message = {
        id: assistantMsgId,
        role: 'assistant',
        content: data.response,
        status: data.status,
        timestamp: new Date(),
      }

      if (data.status === 'PAUSED' && data.pending_approval_id) {
        assistantMsg.pendingApproval = {
          id: data.pending_approval_id,
          type: data.pending_approval_type,
          payload: data.pending_approval_payload,
        }
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      console.error(err)
      setAgentStatus('FAILED')
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(36).substring(7),
          role: 'assistant',
          content: 'Error: Failed to process command. The server might be offline.',
          status: 'FAILED',
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsSubmitting(false)
      if (agentStatus === 'PLANNING') setAgentStatus('IDLE')
    }
  }

  const handleApprovalDecision = async (messageId: string, approvalId: string, decision: 'approve' | 'reject') => {
    setIsSubmitting(true)
    setAgentStatus('EXECUTING')

    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id === messageId && msg.pendingApproval) {
          return {
            ...msg,
            pendingApproval: {
              ...msg.pendingApproval,
              decision: decision === 'approve' ? 'approved' : 'rejected',
            },
          }
        }
        return msg
      }),
    )

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`http://localhost:8000/api/v1/actions/approvals/${approvalId}/${decision}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!response.ok) throw new Error('Action response failed')
      const data = await response.json()

      setAgentStatus(data.status as any)

      const assistantMsgId = Math.random().toString(36).substring(7)
      const assistantMsg: Message = {
        id: assistantMsgId,
        role: 'assistant',
        content: data.response,
        status: data.status,
        timestamp: new Date(),
      }

      if (data.status === 'PAUSED' && data.pending_approval_id) {
        assistantMsg.pendingApproval = {
          id: data.pending_approval_id,
          type: data.pending_approval_type,
          payload: data.pending_approval_payload,
        }
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      console.error(err)
      setAgentStatus('FAILED')
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(36).substring(7),
          role: 'assistant',
          content: 'Error processing approval. The action could not be completed.',
          status: 'FAILED',
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsSubmitting(false)
    }
  }

  const formatTime = (date?: Date) => {
    if (!date) return ''
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <>
      <style>{`
        @keyframes chat-typing-bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.6; }
          30% { transform: translateY(-6px); opacity: 1; }
        }
        @keyframes chat-status-pulse {
          0%, 100% { opacity: 1; box-shadow: 0 0 0 0 currentColor; }
          50% { opacity: 0.7; box-shadow: 0 0 0 4px transparent; }
        }
        @keyframes chat-msg-in {
          from { opacity: 0; transform: translateY(10px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes chat-shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .chat-msg-bubble {
          animation: chat-msg-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
        }
        .chat-input-container:focus-within .chat-input-send-btn {
          opacity: 1;
          transform: translateX(0);
        }
        .chat-msg-user-bubble {
          background: linear-gradient(135deg, var(--color-mercury-blue) 0%, #6478f0 100%);
          box-shadow: 0 4px 20px rgba(82, 102, 235, 0.3);
        }
        .chat-msg-user-bubble:hover {
          box-shadow: 0 6px 28px rgba(82, 102, 235, 0.4);
          transform: translateY(-1px);
        }
        .chat-msg-assistant-bubble {
          background: linear-gradient(145deg, rgba(39,39,53,0.95) 0%, rgba(30,30,42,0.9) 100%);
          backdrop-filter: blur(12px);
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .chat-msg-assistant-bubble:hover {
          background: linear-gradient(145deg, rgba(44,44,60,0.98) 0%, rgba(35,35,50,0.95) 100%);
          box-shadow: 0 4px 24px rgba(0,0,0,0.3);
          transform: translateY(-1px);
        }
        .chat-approval-approve-btn {
          background: linear-gradient(135deg, rgba(52,211,153,0.15) 0%, rgba(16,185,129,0.1) 100%);
          border: 1px solid rgba(52,211,153,0.3);
          color: #6ee7b7;
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .chat-approval-approve-btn:hover:not(:disabled) {
          background: linear-gradient(135deg, rgba(52,211,153,0.25) 0%, rgba(16,185,129,0.18) 100%);
          border-color: rgba(52,211,153,0.5);
          box-shadow: 0 4px 16px rgba(52,211,153,0.2);
          transform: translateY(-1px);
        }
        .chat-approval-reject-btn {
          background: linear-gradient(135deg, rgba(252,165,165,0.1) 0%, rgba(239,68,68,0.08) 100%);
          border: 1px solid rgba(252,165,165,0.2);
          color: #fca5a5;
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .chat-approval-reject-btn:hover:not(:disabled) {
          background: linear-gradient(135deg, rgba(252,165,165,0.18) 0%, rgba(239,68,68,0.15) 100%);
          border-color: rgba(252,165,165,0.35);
          box-shadow: 0 4px 16px rgba(239,68,68,0.15);
          transform: translateY(-1px);
        }
        .chat-send-btn {
          background: linear-gradient(135deg, var(--color-mercury-blue) 0%, #6478f0 100%);
          transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
          box-shadow: 0 4px 16px rgba(82,102,235,0.3);
        }
        .chat-send-btn:hover:not(:disabled) {
          transform: translateY(-2px) scale(1.04);
          box-shadow: 0 8px 24px rgba(82,102,235,0.45);
        }
        .chat-send-btn:active:not(:disabled) {
          transform: scale(0.96);
        }
        .chat-input-field {
          background: rgba(23,23,33,0.6) !important;
          border: 1px solid rgba(112,112,125,0.2) !important;
          transition: all 0.25s ease !important;
          backdrop-filter: blur(8px);
        }
        .chat-clear-btn:hover {
          background: rgba(252,165,165,0.15) !important;
          border-color: rgba(252,165,165,0.3) !important;
          transform: translateY(-1px);
        }
        .chat-clear-btn:active {
          transform: scale(0.97);
        }
      `}</style>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          boxSizing: 'border-box',
          overflow: 'hidden',
          minHeight: 0,
        }}
      >
        {/* ── Header Bar ── */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 16px',
            borderBottom: '1px solid rgba(112,112,125,0.12)',
            background: 'rgba(23,23,33,0.3)',
            flexShrink: 0,
            backdropFilter: 'blur(8px)',
          }}
        >
          <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-lead)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Terminal logs
          </span>
          <button
            onClick={handleClearHistory}
            className="chat-clear-btn"
            style={{
              background: 'rgba(252,165,165,0.06)',
              border: '1px solid rgba(252,165,165,0.15)',
              borderRadius: '6px',
              padding: '5px 10px',
              fontSize: '11px',
              color: '#fca5a5',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
            Clear logs
          </button>
        </div>

        {/* ── Message Feed ── */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px 20px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            minHeight: 0,
          }}
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className="chat-msg-bubble"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                gap: '4px',
              }}
              onMouseEnter={() => setHoveredMsg(msg.id)}
              onMouseLeave={() => setHoveredMsg(null)}
            >
              {msg.role === 'assistant' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', paddingLeft: '4px' }}>
                  <div
                    style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '5px',
                      overflow: 'hidden',
                      flexShrink: 0,
                    }}
                  >
                    <video
                      src="/icon.mp4"
                      autoPlay
                      loop
                      muted
                      playsInline
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--color-lead)', letterSpacing: '0.04em' }}>
                    Persist OS
                  </span>
                  {msg.status && msg.status !== 'COMPLETED' && (
                    <StatusBadge status={msg.status} />
                  )}
                </div>
              )}

              <div
                className={msg.role === 'user' ? 'chat-msg-user-bubble' : 'chat-msg-assistant-bubble'}
                style={{
                  maxWidth: '82%',
                  borderRadius:
                    msg.role === 'user'
                      ? '18px 18px 4px 18px'
                      : '18px 18px 18px 4px',
                  padding: '12px 16px',
                  fontSize: '13px',
                  lineHeight: 1.65,
                  color: msg.role === 'user' ? '#fff' : 'var(--color-starlight)',
                  border:
                    msg.role === 'assistant'
                      ? '1px solid rgba(112,112,125,0.12)'
                      : 'none',
                  position: 'relative',
                  transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
                }}
              >
                <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

                {/* Approval Card */}
                {msg.pendingApproval && (
                  <div
                    style={{
                      marginTop: '14px',
                      paddingTop: '14px',
                      borderTop: '1px solid rgba(251,191,36,0.2)',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '10px',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '11px',
                          color: '#fbbf24',
                          fontWeight: 500,
                        }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                          <line x1="12" y1="9" x2="12" y2="13" />
                          <line x1="12" y1="17" x2="12.01" y2="17" />
                        </svg>
                        Human Approval Required
                      </div>
                      <span
                        style={{
                          backgroundColor: 'rgba(251,191,36,0.1)',
                          border: '1px solid rgba(251,191,36,0.2)',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontFamily: 'monospace',
                          fontSize: '10px',
                          color: '#fbbf24',
                          letterSpacing: '0.04em',
                        }}
                      >
                        {msg.pendingApproval.type}
                      </span>
                    </div>

                    <div
                      style={{
                        background: 'rgba(23,23,33,0.6)',
                        border: '1px solid rgba(112,112,125,0.12)',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        fontSize: '11px',
                        fontFamily: 'monospace',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '5px',
                        marginBottom: '12px',
                      }}
                    >
                      {Object.entries(msg.pendingApproval.payload).map(([k, v]) => (
                        <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                          <span style={{ color: 'var(--color-lead)' }}>{k}:</span>
                          <span
                            style={{
                              color: 'var(--color-silver)',
                              textAlign: 'right',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: '180px',
                            }}
                            title={String(v)}
                          >
                            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>

                    {msg.pendingApproval.decision ? (
                      <div style={{ display: 'flex', justifyContent: 'center' }}>
                        <div
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '6px 16px',
                            borderRadius: '100px',
                            fontSize: '11px',
                            fontWeight: 500,
                            ...(msg.pendingApproval.decision === 'approved'
                              ? {
                                  background: 'rgba(52,211,153,0.12)',
                                  border: '1px solid rgba(52,211,153,0.25)',
                                  color: '#6ee7b7',
                                }
                              : {
                                  background: 'rgba(252,165,165,0.1)',
                                  border: '1px solid rgba(252,165,165,0.2)',
                                  color: '#fca5a5',
                                }),
                          }}
                        >
                          {msg.pendingApproval.decision === 'approved' ? '✓' : '✕'} Action{' '}
                          {msg.pendingApproval.decision === 'approved' ? 'Approved' : 'Rejected'}
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => handleApprovalDecision(msg.id, msg.pendingApproval!.id, 'approve')}
                          disabled={isSubmitting}
                          className="chat-approval-approve-btn"
                          style={{
                            flex: 1,
                            padding: '9px 0',
                            borderRadius: '10px',
                            fontSize: '12px',
                            fontWeight: 500,
                            cursor: isSubmitting ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '5px',
                            opacity: isSubmitting ? 0.5 : 1,
                          }}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          Approve
                        </button>
                        <button
                          onClick={() => handleApprovalDecision(msg.id, msg.pendingApproval!.id, 'reject')}
                          disabled={isSubmitting}
                          className="chat-approval-reject-btn"
                          style={{
                            flex: 1,
                            padding: '9px 0',
                            borderRadius: '10px',
                            fontSize: '12px',
                            fontWeight: 500,
                            cursor: isSubmitting ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '5px',
                            opacity: isSubmitting ? 0.5 : 1,
                          }}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Timestamp */}
              <div
                style={{
                  fontSize: '10px',
                  color: 'var(--color-lead)',
                  paddingLeft: msg.role === 'user' ? '0' : '4px',
                  paddingRight: msg.role === 'user' ? '4px' : '0',
                  opacity: hoveredMsg === msg.id ? 1 : 0,
                  transition: 'opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
                }}
              >
                {formatTime(msg.timestamp)}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {isSubmitting && agentStatus !== 'PAUSED' && (
            <div className="chat-msg-bubble" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', paddingLeft: '4px' }}>
                <div style={{ width: '16px', height: '16px', borderRadius: '5px', overflow: 'hidden' }}>
                  <video src="/icon.mp4" autoPlay loop muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                </div>
                <span style={{ fontSize: '10px', color: 'var(--color-lead)' }}>Persist OS</span>
              </div>
              <div
                className="chat-msg-assistant-bubble"
                style={{
                  borderRadius: '18px 18px 18px 4px',
                  padding: '14px 18px',
                  border: '1px solid rgba(112,112,125,0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                }}
              >
                <TypingDots />
                <span style={{ fontSize: '11px', color: 'var(--color-lead)', letterSpacing: '0.03em' }}>
                  Agent {agentStatus.toLowerCase()}...
                </span>
              </div>
            </div>
          )}

          <div ref={feedEndRef} />
        </div>

        {/* ── Input Bar ── */}
        <div
          style={{
            padding: '12px 16px 14px',
            borderTop: '1px solid rgba(112,112,125,0.1)',
            background: 'linear-gradient(0deg, rgba(23,23,33,0.95) 0%, rgba(23,23,33,0.7) 100%)',
            backdropFilter: 'blur(12px)',
            flexShrink: 0,
          }}
        >
          <form
            onSubmit={handleSubmit}
            className="chat-input-container"
            style={{
              display: 'flex',
              gap: '10px',
              alignItems: 'center',
              background: 'rgba(23,23,33,0.7)',
              border: '1px solid rgba(112,112,125,0.18)',
              borderRadius: '14px',
              padding: '6px 6px 6px 16px',
              transition: 'border-color 0.25s ease, box-shadow 0.25s ease',
            }}
            onFocus={(e) => {
              const el = e.currentTarget
              el.style.borderColor = 'rgba(82,102,235,0.45)'
              el.style.boxShadow = '0 0 0 3px rgba(82,102,235,0.1), 0 4px 20px rgba(0,0,0,0.2)'
            }}
            onBlur={(e) => {
              const el = e.currentTarget
              el.style.borderColor = 'rgba(112,112,125,0.18)'
              el.style.boxShadow = 'none'
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the AI agent to execute tasks..."
              disabled={isSubmitting}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--color-starlight)',
                fontSize: '13px',
                fontFamily: 'var(--font-body)',
                padding: '6px 0',
                letterSpacing: '0.16px',
              }}
            />
            <button
              type="submit"
              disabled={isSubmitting || !input.trim()}
              className="chat-send-btn"
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                border: 'none',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                opacity: isSubmitting || !input.trim() ? 0.4 : 1,
                cursor: isSubmitting || !input.trim() ? 'not-allowed' : 'pointer',
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
          <div style={{ textAlign: 'center', marginTop: '6px', fontSize: '10px', color: 'rgba(112,112,125,0.5)', letterSpacing: '0.03em' }}>
            Press Enter to send · AI responses are automated
          </div>
        </div>
      </div>

      {/* Custom Confirm Modal */}
      {showClearConfirm && (
        <div
          className="animate-mercury-fade-in"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)',
          }}
        >
          <div
            className="animate-mercury-fade-up"
            style={{
              background: 'var(--color-obsidian)',
              border: '1px solid var(--color-glass-border)',
              borderRadius: '16px',
              padding: '24px',
              width: '90%',
              maxWidth: '400px',
              boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
            }}
          >
            <div style={{ color: 'var(--color-starlight)', fontSize: '16px', fontWeight: 500 }}>
              Clear Chat History
            </div>
            <div style={{ color: 'rgba(235, 235, 245, 0.6)', fontSize: '14px', lineHeight: 1.5 }}>
              Are you sure you want to clear your chat history? This action cannot be undone.
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
              <button
                onClick={() => setShowClearConfirm(false)}
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(235, 235, 245, 0.2)',
                  color: 'var(--color-starlight)',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                Cancel
              </button>
              <button
                onClick={confirmClearHistory}
                style={{
                  background: 'rgba(255, 69, 58, 0.15)',
                  border: '1px solid rgba(255, 69, 58, 0.3)',
                  color: '#FF453A',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
                onMouseOver={(e) => (e.currentTarget.style.background = 'rgba(255, 69, 58, 0.25)')}
                onMouseOut={(e) => (e.currentTarget.style.background = 'rgba(255, 69, 58, 0.15)')}
              >
                Clear History
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
