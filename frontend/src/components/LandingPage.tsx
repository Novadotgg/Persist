import React, { useState, useEffect } from 'react'

interface LandingPageProps {
  onLoginSuccess: (token: string) => void
}

export default function LandingPage({ onLoginSuccess }: LandingPageProps) {
  const marqueeItems = [
    { icon: '/drive.jpg', color: '#f87171', name: 'Google Drive', isImg: true },
    { icon: '/mail.jpg', color: '#3b82f6', name: 'Gmail', isImg: true },
    { icon: '/gcal.png', color: '#10b981', name: 'Google Calendar', isImg: true },
    { icon: '/maps.png', color: '#fb923c', name: 'Google Maps', isImg: true },
    { icon: '/yt.jpg', color: '#ef4444', name: 'YouTube', isImg: true },
    { icon: '/notion.jpg', color: '#ffffff', name: 'Notion', isImg: true },
    { icon: '/todoist.jpg', color: '#f87171', name: 'Todoist', isImg: true },
    { icon: '/jira.jpg', color: '#818cf8', name: 'Jira', isImg: true },
    { icon: '/tg.jpg', color: '#34d399', name: 'Telegram', isImg: true },
    { icon: '/dc.jpg', color: '#818cf8', name: 'Discord', isImg: true },
    { icon: '/slack.jpg', color: '#4ade80', name: 'Slack', isImg: true },
    { icon: '/wp.jpg', color: '#4ade80', name: 'WhatsApp', isImg: true },
    { icon: '/github.jpg', color: '#e5e7eb', name: 'GitHub', isImg: true },
    { icon: '🌐', color: '#38bdf8', name: 'Browser', isImg: false },
    { icon: '/spotify.png', color: '#4ade80', name: 'Spotify', isImg: true },
    { icon: '/weather.jpg', color: '#38bdf8', name: 'Weather', isImg: true },
  ]

  const [laptopOpen, setLaptopOpen] = useState(false)
  const [screenGlow, setScreenGlow] = useState(false)
  const [contentVisible, setContentVisible] = useState(false)
  const [authMode, setAuthMode] = useState<'preview' | 'login' | 'register'>('preview')

  // Auth form state
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setLaptopOpen(true), 400)
    const t2 = setTimeout(() => setScreenGlow(true), 1200)
    const t3 = setTimeout(() => setContentVisible(true), 1800)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setIsLoading(true)

    const endpoint = authMode === 'register' ? 'register' : 'login'
    const payload = authMode === 'register' ? { email, password, name } : { email, password }
    try {
      const response = await fetch(`http://localhost:8000/api/v1/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed')
      }

      if (authMode === 'register') {
        if (name.trim()) {
          localStorage.setItem('user_name', name.trim())
        }
        setSuccess('Account created! Please sign in.')
        setAuthMode('login')
        setPassword('')
      } else {
        localStorage.setItem('auth_token', data.access_token)
        localStorage.setItem('user_email', email)
        if (!localStorage.getItem('user_name')) {
          const localPart = email.split('@')[0]
          localStorage.setItem('user_name', localPart.charAt(0).toUpperCase() + localPart.slice(1))
        }
        setIsExiting(true)
        setTimeout(() => {
          onLoginSuccess(data.access_token)
        }, 1200)
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  const showAuth = (mode: 'login' | 'register') => {
    setAuthMode(mode)
    setError(null)
    setSuccess(null)
    setEmail('')
    setPassword('')
    setName('')
  }

  return (
    <div className={`landing-page ${isExiting ? 'zoom-exit' : ''}`}>
      <style>{`
        @keyframes landing-marquee-scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-33.33%); }
        }
        .landing-marquee-track:hover {
          animation-play-state: paused !important;
        }
        .landing-marquee-card:hover {
          transform: translateY(-2px) scale(1.04);
          background: rgba(82, 102, 235, 0.08) !important;
          border-color: rgba(82, 102, 235, 0.45) !important;
          color: var(--color-starlight) !important;
          box-shadow: 0 8px 24px rgba(82, 102, 235, 0.2);
        }
      `}</style>
      {/* Full-bleed atmospheric hero background */}
      <div className="landing-hero-bg">
        <img src="/hero-bg.png" alt="" className="landing-hero-img" />
        <div className="landing-hero-overlay" />
      </div>

      {/* Content layer */}
      <div className="landing-content">
        {/* Top nav */}
        <nav className="landing-nav">
          <div className="landing-nav-brand">
            <div className="mercury-sidebar-logo" style={{ overflow: 'hidden' }}>
              <video
                src="/icon.mp4"
                autoPlay
                loop
                muted
                playsInline
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: 'inherit'
                }}
              />
            </div>
            <span className="landing-nav-title">Persist</span>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="landing-hero-content" style={{ position: 'relative' }}>
          {/* Headline */}
          <div
            className={`landing-headline ${contentVisible ? 'visible' : ''}`}
            style={{
              display: 'flex',
              flexDirection: 'row',
              flexWrap: 'nowrap',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '28px',
              padding: '24px 44px',
              width: '100%',
              maxWidth: '800px',
              boxSizing: 'border-box',
            }}
          >
            <div
              style={{
                width: '200px',
                height: '200px',
                borderRadius: '40px',
                overflow: 'hidden',
                boxShadow: '0 12px 50px rgba(82,102,235,0.5)',
                border: '2px solid rgba(82,102,235,0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'var(--color-mercury-blue)',
                flexShrink: 0,
              }}
            >
              <video
                src="/icon.mp4"
                autoPlay
                loop
                muted
                playsInline
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: 'inherit',
                }}
              />
            </div>
            <h1
              className="landing-title"
              style={{
                margin: 0,
                fontSize: 'clamp(26px, 4.5vw, 40px)',
                letterSpacing: '0.01em',
                textAlign: 'left',
              }}
            >
              Your <span style={{ color: 'var(--color-mercury-blue)', fontWeight: 800 }}>Per</span>sonal As<span style={{ color: 'var(--color-mercury-blue)', fontWeight: 800 }}>sist</span>ant
            </h1>
          </div>

          {/* Curved Arrow SVG pointing from Cloud to Laptop Screen */}
          <div className={`landing-curved-arrow-container ${contentVisible ? 'visible' : ''}`}>
            <svg width="200" height="130" viewBox="0 0 200 130" fill="none" style={{ overflow: 'visible' }}>
              <defs>
                <linearGradient id="arrow-grad" x1="0%" y1="100%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="rgba(82,102,235,0.4)" />
                  <stop offset="100%" stopColor="rgba(165,180,252,0.9)" />
                </linearGradient>
                <filter id="arrow-glow">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <path
                d="M 15 110 C 45 40, 95 15, 80 70 C 65 115, 30 75, 55 45 C 80 15, 140 20, 185 45"
                stroke="url(#arrow-grad)"
                strokeWidth="2.5"
                strokeLinecap="round"
                filter="url(#arrow-glow)"
              />
              <path
                d="M 172 38 L 185 45 L 174 54"
                stroke="url(#arrow-grad)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                filter="url(#arrow-glow)"
              />
            </svg>
          </div>

          {/* Laptop with embedded auth */}
          <div className="landing-laptop-wrapper">
            <div className="landing-laptop-perspective">
              {/* Laptop Lid */}
              <div className={`landing-laptop-lid ${laptopOpen ? 'open' : ''}`}>
                <div className="landing-laptop-screen">
                  <div className={`landing-screen-content ${screenGlow ? 'active' : ''}`}>

                    {/* ─── Preview Mode: Miniature UI ─── */}
                    {authMode === 'preview' && (
                      <div className="screen-preview-container">
                        <div className="screen-ui-topbar">
                          <div className="screen-ui-dots">
                            <span /><span /><span />
                          </div>
                          <div className="screen-ui-tabs">
                            <span className="screen-ui-tab active">Chat</span>
                            <span className="screen-ui-tab">Alerts</span>
                            <span className="screen-ui-tab">Integrations</span>
                          </div>
                        </div>
                        <div className="screen-ui-body">
                          <div className="screen-ui-sidebar">
                            <div className="screen-ui-sidebar-item active" />
                            <div className="screen-ui-sidebar-item" />
                            <div className="screen-ui-sidebar-item" />
                            <div className="screen-ui-sidebar-spacer" />
                            <div className="screen-ui-sidebar-item short" />
                          </div>
                          <div className="screen-ui-main">
                            <div className="screen-ui-message sent" />
                            <div className="screen-ui-message received" />
                            <div className="screen-ui-message received long" />
                            <div className="screen-ui-message sent short" />
                            <div className="screen-ui-input" />
                          </div>
                        </div>

                        {/* CTA overlay on the preview */}
                        <div className="screen-preview-cta-overlay">
                          <button
                            className="screen-cta-btn primary"
                            onClick={() => showAuth('login')}
                          >
                            Sign In
                          </button>
                          <button
                            className="screen-cta-btn secondary"
                            onClick={() => showAuth('register')}
                          >
                            Create Account
                          </button>
                        </div>
                      </div>
                    )}

                    {/* ─── Auth Mode: Login / Register Form ─── */}
                    {(authMode === 'login' || authMode === 'register') && (
                      <div className="screen-auth-container animate-mercury-fade-up">
                        {/* Screen topbar for auth */}
                        <div className="screen-ui-topbar">
                          <div className="screen-ui-dots">
                            <span /><span /><span />
                          </div>
                          <button
                            className="screen-auth-back"
                            onClick={() => setAuthMode('preview')}
                          >
                            ← Back
                          </button>
                        </div>

                        {/* Auth form inside laptop */}
                        <div className="screen-auth-form-area">
                          <div className="screen-auth-header">
                            <div className="screen-auth-logo" style={{ overflow: 'hidden' }}>
                              <video
                                src="/icon.mp4"
                                autoPlay
                                loop
                                muted
                                playsInline
                                style={{
                                  width: '100%',
                                  height: '100%',
                                  objectFit: 'cover',
                                  borderRadius: 'inherit'
                                }}
                              />
                            </div>
                            <h2 className="screen-auth-title">
                              {authMode === 'register' ? 'Create Account' : 'Welcome Back'}
                            </h2>
                            <p className="screen-auth-subtitle">
                              {authMode === 'register'
                                ? 'Set up your credentials'
                                : 'Sign in to your command center'}
                            </p>
                          </div>

                          {/* Alerts */}
                          {error && (
                            <div className="screen-auth-alert error">
                              {error}
                            </div>
                          )}
                          {success && (
                            <div className="screen-auth-alert success">
                              {success}
                            </div>
                          )}

                          <form onSubmit={handleSubmit} className="screen-auth-form">
                            {authMode === 'register' && (
                              <div className="screen-auth-field animate-mercury-fade-up">
                                <label className="screen-auth-label">Full Name</label>
                                <input
                                  type="text"
                                  value={name}
                                  onChange={(e) => setName(e.target.value)}
                                  placeholder="John Doe"
                                  required
                                  className="screen-auth-input"
                                />
                              </div>
                            )}
                            <div className="screen-auth-field">
                              <label className="screen-auth-label">Email</label>
                              <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="name@domain.com"
                                required
                                className="screen-auth-input"
                              />
                            </div>
                            <div className="screen-auth-field">
                              <label className="screen-auth-label">Password</label>
                              <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                className="screen-auth-input"
                              />
                            </div>
                            <button
                              type="submit"
                              disabled={isLoading}
                              className="screen-auth-submit"
                            >
                              {isLoading ? (
                                <>
                                  <span className="screen-auth-spinner animate-mercury-spin" />
                                  Processing...
                                </>
                              ) : (
                                authMode === 'register' ? 'Create Account' : 'Sign In'
                              )}
                            </button>
                          </form>

                          <div className="screen-auth-toggle">
                            <button
                              onClick={() => {
                                showAuth(authMode === 'register' ? 'login' : 'register')
                              }}
                            >
                              {authMode === 'register'
                                ? 'Have an account? Sign in'
                                : "No account? Register"}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Infinite Marquee of Integration Icons */}
        <div
          className={`landing-marquee-container ${contentVisible ? 'visible' : ''}`}
          style={{
            width: '100%',
            maxWidth: '850px',
            overflow: 'hidden',
            margin: '0 auto 28px',
            maskImage: 'linear-gradient(to right, transparent, black 15%, black 85%, transparent)',
            WebkitMaskImage: 'linear-gradient(to right, transparent, black 15%, black 85%, transparent)',
            opacity: contentVisible ? 1 : 0,
            transition: 'opacity 0.8s ease 0.6s',
            boxSizing: 'border-box',
          }}
        >
          <div
            className="landing-marquee-track"
            style={{
              display: 'flex',
              gap: '20px',
              width: 'max-content',
              animation: 'landing-marquee-scroll 32s linear infinite',
            }}
          >
            {[...marqueeItems, ...marqueeItems, ...marqueeItems].map((item, idx) => (
              <div
                key={idx}
                className="landing-marquee-card"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '10px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  padding: '12px 22px',
                  borderRadius: '16px',
                  backdropFilter: 'blur(10px)',
                  color: 'var(--color-silver)',
                  fontFamily: 'var(--font-body)',
                  fontSize: '15px',
                  cursor: 'pointer',
                  transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                }}
              >
                {item.isImg ? (
                  <img
                    src={item.icon}
                    alt={item.name}
                    style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '5px',
                      objectFit: 'cover',
                      display: 'block',
                      flexShrink: 0,
                    }}
                  />
                ) : (
                  <span
                    style={{
                      fontSize: '20px',
                      color: item.color,
                      fontWeight: 700,
                      lineHeight: 1,
                    }}
                  >
                    {item.icon}
                  </span>
                )}
                <span style={{ fontWeight: 500 }}>{item.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Feature indicators at the bottom */}
        <div className={`landing-features ${contentVisible ? 'visible' : ''}`}>
          <div className="landing-feature-item">
            <div className="landing-feature-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <span>AI Agent Chat</span>
          </div>
          <div className="landing-feature-divider" />
          <div className="landing-feature-item">
            <div className="landing-feature-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
            </div>
            <span>Live Notifications</span>
          </div>
          <div className="landing-feature-divider" />
          <div className="landing-feature-item">
            <div className="landing-feature-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="2" width="8" height="8" rx="1" />
                <rect x="14" y="2" width="8" height="8" rx="1" />
                <rect x="2" y="14" width="8" height="8" rx="1" />
                <rect x="14" y="14" width="8" height="8" rx="1" />
              </svg>
            </div>
            <span>Integrations</span>
          </div>
        </div>
      </div>
    </div>
  )
}
