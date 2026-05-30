import { useState, useEffect, useRef } from 'react'

export interface Notification {
  id: string
  source: string
  type: string
  title: string
  summary: string
  priority: number
  processed_at: string
}

const SOURCE_META: Record<string, { icon: string; color: string; bg: string; border: string }> = {
  gmail: {
    icon: '✉',
    color: '#f87171',
    bg: 'rgba(239,68,68,0.1)',
    border: 'rgba(239,68,68,0.2)',
  },
  google_calendar: {
    icon: '📅',
    color: '#60a5fa',
    bg: 'rgba(59,130,246,0.1)',
    border: 'rgba(59,130,246,0.2)',
  },
  'google calendar': {
    icon: '📅',
    color: '#60a5fa',
    bg: 'rgba(59,130,246,0.1)',
    border: 'rgba(59,130,246,0.2)',
  },
  jira: {
    icon: '⬡',
    color: '#818cf8',
    bg: 'rgba(99,102,241,0.1)',
    border: 'rgba(99,102,241,0.2)',
  },
  telegram: {
    icon: '✈',
    color: '#34d399',
    bg: 'rgba(52,211,153,0.1)',
    border: 'rgba(52,211,153,0.2)',
  },
}

const DEFAULT_SOURCE = {
  icon: '◉',
  color: 'var(--color-ghost-blue)',
  bg: 'rgba(82,102,235,0.1)',
  border: 'rgba(82,102,235,0.2)',
}

function getSourceMeta(source: string) {
  return SOURCE_META[source.toLowerCase()] ?? DEFAULT_SOURCE
}

function PriorityIndicator({ priority }: { priority: number }) {
  const bars = 5
  const filled = Math.min(priority, bars)
  const isUrgent = priority >= 4

  return (
    <div
      title={`Priority ${priority}/5`}
      style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '14px' }}
    >
      {Array.from({ length: bars }).map((_, i) => (
        <div
          key={i}
          style={{
            width: '3px',
            height: `${4 + i * 2.2}px`,
            borderRadius: '1px',
            backgroundColor:
              i < filled
                ? isUrgent
                  ? '#f87171'
                  : 'var(--color-mercury-blue)'
                : 'rgba(112,112,125,0.2)',
            transition: 'background-color 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        />
      ))}
    </div>
  )
}

function formatRelativeTime(dateStr: string) {
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return new Date(dateStr).toLocaleDateString()
}

export default function NotificationFeed() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [activeTab, setActiveTab] = useState<'all' | 'urgent' | 'standard'>('all')
  const [status, setStatus] = useState<'connecting' | 'connected' | 'error'>('connecting')
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const connectStream = () => {
      setStatus('connecting')
      const token = localStorage.getItem('auth_token')
      const source = new EventSource(`http://localhost:8000/api/v1/notifications/stream?token=${token || ''}`)
      eventSourceRef.current = source

      source.onopen = () => {
        setStatus('connected')
      }

      source.onmessage = (event) => {
        try {
          if (event.data.trim() === ': keep-alive' || event.data.trim() === '') return
          const parsed: Notification = JSON.parse(event.data)
          setNotifications((prev) => {
            if (prev.some((n) => n.id === parsed.id)) return prev
            return [parsed, ...prev].slice(0, 50)
          })
        } catch (e) {
          console.error('Error parsing SSE message', e)
        }
      }

      source.onerror = (err) => {
        console.error('SSE notification stream error', err)
        setStatus('error')
        source.close()
        setTimeout(connectStream, 5000)
      }
    }

    connectStream()

    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close()
    }
  }, [])

  const filteredNotifications = notifications.filter((n) => {
    if (activeTab === 'urgent') return n.priority >= 4
    if (activeTab === 'standard') return n.priority < 4
    return true
  })

  const tabs: Array<{ id: 'all' | 'urgent' | 'standard'; label: string; count: number }> = [
    { id: 'all', label: 'All', count: notifications.length },
    { id: 'urgent', label: 'Urgent', count: notifications.filter((n) => n.priority >= 4).length },
    { id: 'standard', label: 'Standard', count: notifications.filter((n) => n.priority < 4).length },
  ]

  const statusInfo = {
    connected: { color: '#34d399', bg: 'rgba(52,211,153,0.1)', border: 'rgba(52,211,153,0.25)', label: 'Live' },
    connecting: { color: '#fbbf24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.25)', label: 'Connecting' },
    error: { color: '#f87171', bg: 'rgba(248,113,113,0.1)', border: 'rgba(248,113,113,0.25)', label: 'Reconnecting' },
  }[status]

  return (
    <>
      <style>{`
        @keyframes notif-slide-in {
          from { opacity: 0; transform: translateX(-12px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes notif-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes notif-dot-ping {
          0% { transform: scale(1); opacity: 1; }
          75%, 100% { transform: scale(2.5); opacity: 0; }
        }
        .notif-item {
          animation: notif-slide-in 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both;
          transition: all 0.22s ease;
          cursor: pointer;
          border-radius: 12px;
        }
        .notif-item:hover {
          background: rgba(39,39,53,0.95) !important;
          border-color: rgba(82,102,235,0.2) !important;
          transform: translateX(3px);
          box-shadow: 0 4px 24px rgba(0,0,0,0.25), inset 0 0 0 1px rgba(82,102,235,0.1);
        }
        .notif-tab {
          padding: 6px 14px;
          border-radius: 100px;
          font-size: 11px;
          font-weight: 500;
          letter-spacing: 0.04em;
          border: none;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
          white-space: nowrap;
        }
        .notif-tab:hover {
          transform: translateY(-1px);
        }
        .notif-tab-active {
          background: linear-gradient(135deg, var(--color-mercury-blue) 0%, #6478f0 100%);
          color: white;
          box-shadow: 0 3px 12px rgba(82,102,235,0.35);
        }
        .notif-tab-inactive {
          background: transparent;
          color: var(--color-lead);
        }
        .notif-tab-inactive:hover {
          background: rgba(112,112,125,0.1);
          color: var(--color-silver);
        }
        .notif-source-badge {
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .notif-item:hover .notif-source-badge {
          transform: scale(1.05);
        }
        .notif-expand-btn {
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
          opacity: 0;
        }
        .notif-item:hover .notif-expand-btn {
          opacity: 1;
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
        {/* ── Header ── */}
        <div
          style={{
            padding: '14px 20px',
            borderBottom: '1px solid rgba(112,112,125,0.1)',
            background: 'linear-gradient(180deg, rgba(30,30,42,0.95) 0%, rgba(23,23,33,0.8) 100%)',
            backdropFilter: 'blur(12px)',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '14px', flexWrap: 'wrap' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                borderRadius: '100px',
                backgroundColor: statusInfo.bg,
                border: `1px solid ${statusInfo.border}`,
                color: statusInfo.color,
                fontSize: '11px',
                fontWeight: 500,
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: statusInfo.color,
                  display: 'inline-block',
                  animation: status === 'connecting' ? 'notif-pulse 1s infinite' : 'none',
                }}
              />
              {statusInfo.label}
            </div>

            {/* Stats */}
            <div style={{ display: 'flex', gap: '8px' }}>
              {[
                { label: 'Total', val: notifications.length, color: 'var(--color-ghost-blue)' },
                { label: 'Urgent', val: notifications.filter((n) => n.priority >= 4).length, color: '#f87171' },
              ].map((s) => (
                <div
                  key={s.label}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    background: 'rgba(23,23,33,0.6)',
                    border: '1px solid rgba(112,112,125,0.1)',
                    minWidth: '48px',
                  }}
                >
                  <span style={{ fontSize: '16px', fontWeight: 600, color: s.color, lineHeight: 1.1 }}>
                    {s.val}
                  </span>
                  <span style={{ fontSize: '9px', color: 'var(--color-lead)', letterSpacing: '0.06em', marginTop: '2px' }}>
                    {s.label.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Tabs */}
          <div
            style={{
              display: 'flex',
              gap: '4px',
              backgroundColor: 'rgba(23,23,33,0.6)',
              padding: '4px',
              borderRadius: '100px',
              border: '1px solid rgba(112,112,125,0.1)',
              width: 'fit-content',
            }}
          >
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`notif-tab ${activeTab === tab.id ? 'notif-tab-active' : 'notif-tab-inactive'}`}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span
                    style={{
                      marginLeft: '5px',
                      fontSize: '9px',
                      backgroundColor: activeTab === tab.id ? 'rgba(255,255,255,0.25)' : 'rgba(112,112,125,0.2)',
                      padding: '1px 5px',
                      borderRadius: '100px',
                      fontWeight: 600,
                    }}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* ── Notifications List ── */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            minHeight: 0,
          }}
        >
          {filteredNotifications.length === 0 ? (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '60px 0',
                gap: '12px',
              }}
            >
              <div
                style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '16px',
                  background: 'rgba(82,102,235,0.08)',
                  border: '1px solid rgba(82,102,235,0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '22px',
                }}
              >
                📡
              </div>
              <div style={{ textAlign: 'center' }}>
                <p style={{ fontSize: '13px', color: 'var(--color-silver)', margin: 0, fontWeight: 400 }}>
                  No notifications received yet
                </p>
                <p style={{ fontSize: '11px', color: 'var(--color-lead)', margin: '4px 0 0' }}>
                  Events will stream here automatically
                </p>
              </div>
            </div>
          ) : (
            filteredNotifications.map((notif, idx) => {
              const meta = getSourceMeta(notif.source)
              const isExpanded = expandedId === notif.id
              const isHovered = hoveredId === notif.id
              const isUrgent = notif.priority >= 4

              return (
                <div
                  key={notif.id}
                  className="notif-item"
                  style={{
                    padding: '12px 14px',
                    background: isHovered
                      ? 'rgba(39,39,53,0.95)'
                      : 'rgba(30,30,42,0.6)',
                    border: `1px solid ${
                      isHovered ? 'rgba(82,102,235,0.2)' : 'rgba(112,112,125,0.1)'
                    }`,
                    animationDelay: `${Math.min(idx * 0.04, 0.3)}s`,
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                  onClick={() => setExpandedId(isExpanded ? null : notif.id)}
                  onMouseEnter={() => setHoveredId(notif.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  {/* Urgent left accent */}
                  {isUrgent && (
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        top: '10%',
                        bottom: '10%',
                        width: '2px',
                        borderRadius: '0 2px 2px 0',
                        background: 'linear-gradient(180deg, #f87171 0%, #ef4444 100%)',
                      }}
                    />
                  )}

                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                    {/* Source icon */}
                    <div
                      className="notif-source-badge"
                      style={{
                        width: '34px',
                        height: '34px',
                        borderRadius: '10px',
                        background: meta.bg,
                        border: `1px solid ${meta.border}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '15px',
                        flexShrink: 0,
                        color: meta.color,
                      }}
                    >
                      {meta.icon}
                    </div>

                    {/* Content */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' }}>
                        <h3
                          style={{
                            fontWeight: 500,
                            fontSize: '12px',
                            color: 'var(--color-starlight)',
                            margin: 0,
                            lineHeight: 1.4,
                            flex: 1,
                          }}
                        >
                          {notif.title}
                        </h3>
                        <PriorityIndicator priority={notif.priority} />
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <span
                          style={{
                            fontSize: '9px',
                            padding: '2px 7px',
                            borderRadius: '100px',
                            backgroundColor: meta.bg,
                            color: meta.color,
                            fontWeight: 600,
                            letterSpacing: '0.05em',
                            border: `1px solid ${meta.border}`,
                            textTransform: 'uppercase',
                          }}
                        >
                          {notif.source.replace('_', ' ')}
                        </span>
                        <span
                          style={{
                            fontSize: '9px',
                            padding: '2px 7px',
                            borderRadius: '100px',
                            background: 'rgba(112,112,125,0.1)',
                            color: 'var(--color-lead)',
                            fontFamily: 'monospace',
                            border: '1px solid rgba(112,112,125,0.12)',
                          }}
                        >
                          {notif.type}
                        </span>
                        <span style={{ fontSize: '10px', color: 'var(--color-lead)', marginLeft: 'auto' }}>
                          {formatRelativeTime(notif.processed_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Summary — always shown or expandable */}
                  {notif.summary && (
                    <div
                      style={{
                        marginTop: '10px',
                        paddingTop: '10px',
                        borderTop: '1px solid rgba(112,112,125,0.08)',
                        fontSize: '11px',
                        color: 'var(--color-silver)',
                        lineHeight: 1.6,
                        paddingLeft: '46px',
                        maxHeight: isExpanded ? '200px' : '2.8em',
                        overflow: 'hidden',
                        transition: 'max-height 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
                        position: 'relative',
                      }}
                    >
                      {notif.summary}
                      {!isExpanded && notif.summary.length > 80 && (
                        <div
                          style={{
                            position: 'absolute',
                            bottom: 0,
                            left: '46px',
                            right: 0,
                            height: '1.4em',
                            background: 'linear-gradient(0deg, rgba(30,30,42,0.9) 0%, transparent 100%)',
                          }}
                        />
                      )}
                    </div>
                  )}

                  {/* Expand chevron */}
                  {notif.summary && notif.summary.length > 80 && (
                    <div
                      className="notif-expand-btn"
                      style={{
                        display: 'flex',
                        justifyContent: 'center',
                        marginTop: '6px',
                        paddingLeft: '46px',
                      }}
                    >
                      <svg
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="var(--color-lead)"
                        strokeWidth="2"
                        style={{
                          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                          transition: 'transform 0.25s ease',
                        }}
                      >
                        <polyline points="6 9 12 15 18 9" />
                      </svg>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>
    </>
  )
}
