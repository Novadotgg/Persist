import React, { useState } from 'react'
import ChatTerminal from './components/ChatTerminal'
import NotificationFeed from './components/NotificationFeed'
import IntegrationsPanel from './components/IntegrationsPanel'
import LandingPage from './components/LandingPage'

type Page = 'chat' | 'notifications' | 'integrations'

interface AppScreenProps {
  activePage: Page
  onNavigate: (page: Page) => void
  children: React.ReactNode
}

const SCREEN_PAGES: Array<{ page: Page; label: string; icon: React.ReactNode }> = [
  {
    page: 'chat',
    label: 'Chat',
    icon: (
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    page: 'notifications',
    label: 'Alerts',
    icon: (
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
  },
]

function AppScreen({ activePage, onNavigate, children }: AppScreenProps) {
  const [hoveredTab, setHoveredTab] = React.useState<Page | null>(null)
  const [isMobile, setIsMobile] = React.useState(window.innerWidth < 768)

  React.useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div
      style={{
        width: '100%',
        maxWidth: 'min(1024px, 120vh)',
        margin: '0 auto',
        /* Outer laptop bezel */
        background: '#12121c',
        borderRadius: isMobile ? '12px' : '16px',
        padding: isMobile ? '5px' : '10px',
        boxShadow:
          '0 40px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04), inset 0 1px 0 rgba(255,255,255,0.06)',
        aspectRatio: isMobile ? 'auto' : '16 / 11',
        height: isMobile ? 'calc(100vh - 150px)' : 'auto',
        minHeight: isMobile ? '480px' : 'auto',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Inner screen surface */}
      <div
        style={{
          flex: 1,
          borderRadius: isMobile ? '7px' : '9px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          background: '#0f0f1a',
          boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.05)',
          position: 'relative',
        }}
      >
        {/* Screen top-edge glow line */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: '10%',
            right: '10%',
            height: '1px',
            background: 'linear-gradient(90deg, transparent, rgba(82,102,235,0.4), transparent)',
            zIndex: 10,
            pointerEvents: 'none',
          }}
        />

        {/* ── MacOS-style Titlebar / Navbar ── */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: isMobile ? '8px' : '14px',
            padding: isMobile ? '0 10px' : '0 16px',
            height: '42px',
            flexShrink: 0,
            background: 'rgba(255,255,255,0.03)',
            borderBottom: '1px solid rgba(255,255,255,0.07)',
            backdropFilter: 'blur(20px)',
            position: 'relative',
            zIndex: 5,
          }}
        >
          {/* macOS traffic-light dots */}
          {!isMobile && (
            <>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexShrink: 0 }}>
                <span style={{ display: 'block', width: '11px', height: '11px', borderRadius: '50%', backgroundColor: '#ff5f57', boxShadow: '0 0 6px rgba(255,95,87,0.5)' }} />
                <span style={{ display: 'block', width: '11px', height: '11px', borderRadius: '50%', backgroundColor: '#febc2e', boxShadow: '0 0 6px rgba(254,188,46,0.4)' }} />
                <span style={{ display: 'block', width: '11px', height: '11px', borderRadius: '50%', backgroundColor: '#28c840', boxShadow: '0 0 6px rgba(40,200,64,0.4)' }} />
              </div>
              <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} />
            </>
          )}

          {/* Brand */}
          {!isMobile && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                <div
                  style={{
                    width: '22px',
                    height: '22px',
                    borderRadius: '7px',
                    overflow: 'hidden',
                    flexShrink: 0,
                    boxShadow: '0 2px 10px rgba(82,102,235,0.5)',
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
                <span
                  style={{
                    fontSize: '13px',
                    fontWeight: 600,
                    color: '#e8e8f0',
                    letterSpacing: '0.01em',
                    fontFamily: 'var(--font-display)',
                  }}
                >
                  Persist
                </span>
              </div>
              {/* Vertical divider */}
              <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} />
            </>
          )}

          {/* Page nav tabs */}
          <div
            style={{
              display: 'flex',
              gap: '2px',
              background: 'rgba(0,0,0,0.25)',
              padding: '3px',
              borderRadius: '9px',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            {SCREEN_PAGES.map(({ page, label, icon }) => {
              const isActive = activePage === page
              const isHovered = hoveredTab === page
              return (
                <button
                  key={page}
                  onClick={() => onNavigate(page)}
                  onMouseEnter={() => setHoveredTab(page)}
                  onMouseLeave={() => setHoveredTab(null)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '5px 14px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: isActive ? 500 : 400,
                    color: isActive ? '#a5b4fc' : isHovered ? '#c4c4d4' : '#8888a0',
                    background: isActive
                      ? 'rgba(82,102,235,0.2)'
                      : isHovered
                      ? 'rgba(255,255,255,0.06)'
                      : 'transparent',
                    border: isActive ? '1px solid rgba(82,102,235,0.3)' : '1px solid transparent',
                    cursor: 'pointer',
                    fontFamily: 'var(--font-body)',
                    letterSpacing: '0.02em',
                    transition: 'all 0.16s ease',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <span style={{ opacity: isActive ? 1 : 0.55 }}>{icon}</span>
                  {label}
                </button>
              )
            })}
          </div>


        </div>

        {/* ── Content area ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}>
          {children}
        </div>
      </div>

      {/* Laptop base/chin bar */}
      <div
        style={{
          height: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: '60px',
            height: '3px',
            borderRadius: '2px',
            background: 'rgba(255,255,255,0.08)',
          }}
        />
      </div>
    </div>
  )
}


const PAGE_META: Record<Page, { title: string; subtitle: string; icon: React.ReactNode }> = {
  chat: {
    title: 'Agent Terminal',
    subtitle: 'AI-powered command execution',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  notifications: {
    title: 'Notifications',
    subtitle: 'Live event stream',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
  },
  integrations: {
    title: 'Integrations',
    subtitle: 'Connected services & data sync',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="2" width="8" height="8" rx="1" />
        <rect x="14" y="2" width="8" height="8" rx="1" />
        <rect x="2" y="14" width="8" height="8" rx="1" />
        <rect x="14" y="14" width="8" height="8" rx="1" />
      </svg>
    ),
  },
}

const NAV_ITEMS: Array<{ page: Page; label: string; icon: React.ReactNode }> = [
  {
    page: 'chat',
    label: 'Chat',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    page: 'notifications',
    label: 'Notifications',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
  },
  {
    page: 'integrations',
    label: 'Integrations',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="2" width="8" height="8" rx="1" />
        <rect x="14" y="2" width="8" height="8" rx="1" />
        <rect x="2" y="14" width="8" height="8" rx="1" />
        <rect x="14" y="14" width="8" height="8" rx="1" />
      </svg>
    ),
  },
]

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'))
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activePage, setActivePage] = useState<Page>('chat')
  const [isMounted, setIsMounted] = useState(false)

  React.useEffect(() => {
    if (token) {
      const timer = setTimeout(() => setIsMounted(true), 50)
      return () => clearTimeout(timer)
    } else {
      setIsMounted(false)
    }
  }, [token])

  const handleLoginSuccess = (newToken: string) => {
    setToken(newToken)
  }

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_name')
    localStorage.removeItem('user_email')
    setToken(null)
  }

  const navigateTo = (page: Page) => {
    setActivePage(page)
    setSidebarOpen(false)
  }

  if (!token) {
    return <LandingPage onLoginSuccess={handleLoginSuccess} />
  }

  const meta = PAGE_META[activePage]

  return (
    <>
      <style>{`
        @keyframes app-topbar-in {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes app-content-in {
          from { opacity: 0; transform: translateY(12px) scale(0.99); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .app-nav-item {
          transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
          position: relative;
        }
        .app-nav-item::after {
          content: '';
          position: absolute;
          bottom: -2px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 2px;
          background: var(--color-mercury-blue);
          border-radius: 1px;
          transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .app-nav-item.active::after {
          width: 60%;
        }
        .app-nav-item:hover:not(.active) {
          background-color: rgba(112,112,125,0.08);
        }
        .app-logout-btn {
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .app-logout-btn:hover {
          background: rgba(252,165,165,0.08) !important;
          border-color: rgba(252,165,165,0.2) !important;
          color: #fca5a5 !important;
        }
        .app-sidebar-overlay {
          backdrop-filter: blur(6px);
        }
        .mercury-sidebar {
          box-shadow: 4px 0 32px rgba(0,0,0,0.4);
        }
      `}</style>

      <div className="mercury-layout" key={token}>
        {/* Cinematic Background */}
        <div className="landing-hero-bg" style={{ position: 'fixed', zIndex: 0 }}>
          <img src="/hero-bg.png" alt="" className="landing-hero-img" />
          <div className="landing-hero-overlay" />
        </div>

        {/* Sidebar Overlay */}
        <div
          className={`mercury-sidebar-overlay app-sidebar-overlay ${sidebarOpen ? 'visible' : ''}`}
          onClick={() => setSidebarOpen(false)}
        />

        {/* Sidebar */}
        <aside className={`mercury-sidebar ${sidebarOpen ? 'open' : ''} ${isMounted ? 'sidebar-transition' : ''}`}>
          {/* Brand */}
          <div className="mercury-sidebar-brand">
            <div className="mercury-sidebar-logo" style={{ overflow: 'hidden', boxShadow: '0 2px 12px rgba(82,102,235,0.35)' }}>
              <video
                src="/icon.mp4"
                autoPlay
                loop
                muted
                playsInline
                style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'inherit' }}
              />
            </div>
            <div>
              <span className="mercury-sidebar-title">Persist</span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="mercury-sidebar-nav">
            <div style={{ fontSize: '9px', color: 'var(--color-lead)', letterSpacing: '0.1em', textTransform: 'uppercase', padding: '0 var(--spacing-16)', marginBottom: '8px', marginTop: '4px' }}>
              Navigation
            </div>

            {NAV_ITEMS.map(({ page, label, icon }) => (
              <button
                key={page}
                className={`mercury-nav-item app-nav-item ${activePage === page ? 'active' : ''}`}
                onClick={() => navigateTo(page)}
              >
                <span className="mercury-nav-icon">{icon}</span>
                {label}
                {activePage === page && (
                  <span style={{ marginLeft: 'auto', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--color-mercury-blue)', flexShrink: 0 }} />
                )}
              </button>
            ))}
          </nav>

          {/* Sidebar Footer */}
          <div className="mercury-sidebar-footer">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 12px',
                borderRadius: '10px',
                background: 'rgba(112,112,125,0.06)',
                border: '1px solid rgba(112,112,125,0.1)',
                marginBottom: '12px',
              }}
            >
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, rgba(82,102,235,0.2) 0%, rgba(82,102,235,0.1) 100%)',
                  border: '1px solid rgba(82,102,235,0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-ghost-blue)" strokeWidth="1.8">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '12px', color: 'var(--color-starlight)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {localStorage.getItem('user_name') || 'Operator'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--color-lead)', marginTop: '1px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {localStorage.getItem('user_email') || 'Authenticated'}
                </div>
              </div>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#34d399', flexShrink: 0 }} />
            </div>

            <button
              onClick={handleLogout}
              className="app-logout-btn"
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '10px 16px',
                borderRadius: '10px',
                background: 'rgba(112,112,125,0.08)',
                border: '1px solid rgba(112,112,125,0.12)',
                color: 'var(--color-lead)',
                fontSize: '13px',
                fontFamily: 'var(--font-body)',
                cursor: 'pointer',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Sign Out
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <div className="mercury-main">
          {/* Top Bar */}
          <header
            className="mercury-topbar"
            style={{ animation: 'app-topbar-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <button
                className={`mercury-hamburger ${sidebarOpen ? 'active' : ''}`}
                onClick={() => setSidebarOpen(!sidebarOpen)}
                aria-label="Toggle navigation"
              >
                <span /><span /><span />
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '9px',
                    background: 'rgba(82,102,235,0.12)',
                    border: '1px solid rgba(82,102,235,0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--color-ghost-blue)',
                  }}
                >
                  {meta.icon}
                </div>
                <div>
                  <h1
                    style={{
                      fontFamily: 'var(--font-display)',
                      fontSize: '15px',
                      fontWeight: 500,
                      color: 'var(--color-starlight)',
                      margin: 0,
                      letterSpacing: '0.01em',
                      lineHeight: 1.2,
                    }}
                  >
                    {meta.title}
                  </h1>
                  <div style={{ fontSize: '10px', color: 'var(--color-lead)', marginTop: '1px', letterSpacing: '0.03em' }}>
                    {meta.subtitle}
                  </div>
                </div>
              </div>
            </div>


          </header>

          {/* Page Content */}
          <main
            className="mercury-content"
            style={activePage === 'integrations' ? { maxWidth: '100%', width: '100%', padding: '16px 20px' } : undefined}
          >
            <div
              style={{ animation: 'app-content-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
              key={activePage}
            >
              {(activePage === 'chat' || activePage === 'notifications') && (
                <AppScreen activePage={activePage} onNavigate={navigateTo}>
                  {activePage === 'chat' && <ChatTerminal />}
                  {activePage === 'notifications' && <NotificationFeed />}
                </AppScreen>
              )}
              {activePage === 'integrations' && (
                <div
                  style={{
                    maxWidth: '100%',
                    margin: '0 auto',
                    background: 'rgba(23,23,33,0.6)',
                    backdropFilter: 'blur(16px)',
                    border: '1px solid rgba(112,112,125,0.12)',
                    borderRadius: '16px',
                    overflow: 'hidden',
                    minHeight: '500px',
                  }}
                >
                  <IntegrationsPanel />
                </div>
              )}
            </div>
          </main>
        </div>
      </div>
    </>
  )
}

export default App
