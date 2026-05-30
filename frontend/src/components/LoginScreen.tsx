import React, { useState } from 'react'

interface LoginScreenProps {
  onLoginSuccess: (token: string) => void
  initialMode?: 'login' | 'register'
  onBack?: () => void
}

export default function LoginScreen({ onLoginSuccess, initialMode = 'login', onBack }: LoginScreenProps) {
  const [isRegister, setIsRegister] = useState(initialMode === 'register')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setIsLoading(true)

    const endpoint = isRegister ? 'register' : 'login'
    try {
      const response = await fetch(`http://localhost:8000/api/v1/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed')
      }

      if (isRegister) {
        setSuccess('Account created successfully! Please log in.')
        setIsRegister(false)
        setPassword('')
      } else {
        localStorage.setItem('auth_token', data.access_token)
        onLoginSuccess(data.access_token)
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="mercury-auth-page">
      {/* Ambient glow effects */}
      <div className="mercury-auth-glow-1" />
      <div className="mercury-auth-glow-2" />

      <div className="mercury-auth-card">
        {/* Back button */}
        {onBack && (
          <button
            onClick={onBack}
            style={{
              position: 'absolute',
              top: 'var(--spacing-20)',
              left: 'var(--spacing-20)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: 'var(--text-body-sm)',
              color: 'var(--color-lead)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              transition: 'color 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
              padding: 'var(--spacing-4)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-starlight)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-lead)')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            Back
          </button>
        )}

        {/* Header / Branding */}
        <div className="mercury-auth-header">
          <div className="mercury-auth-logo">M</div>
          <h1 className="mercury-auth-title">
            {isRegister ? 'Create Account' : 'Welcome Back'}
          </h1>
          <p className="mercury-auth-subtitle">
            {isRegister
              ? 'Set up your command center credentials'
              : 'Sign in to access your command center'}
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <div className="mercury-auth-alert error" style={{ marginBottom: 'var(--spacing-20)' }}>
            {error}
          </div>
        )}

        {success && (
          <div className="mercury-auth-alert success" style={{ marginBottom: 'var(--spacing-20)' }}>
            {success}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mercury-auth-form">
          <div className="mercury-field">
            <label className="mercury-label" htmlFor="auth-email">Email Address</label>
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@domain.com"
              required
              className="mercury-input mercury-input-sm"
            />
          </div>

          <div className="mercury-field">
            <label className="mercury-label" htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="mercury-input mercury-input-sm"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="mercury-btn-primary"
            style={{ width: '100%', marginTop: 'var(--spacing-8)' }}
          >
            {isLoading ? (
              <>
                <span
                  style={{
                    width: '16px',
                    height: '16px',
                    border: '2px solid rgba(255,255,255,0.3)',
                    borderTopColor: '#fff',
                    borderRadius: '50%',
                    display: 'inline-block',
                  }}
                  className="animate-mercury-spin"
                />
                Processing...
              </>
            ) : (
              isRegister ? 'Create Account' : 'Sign In'
            )}
          </button>
        </form>

        {/* Toggle Login / Register */}
        <div className="mercury-auth-toggle">
          <button
            onClick={() => {
              setIsRegister(!isRegister)
              setError(null)
              setSuccess(null)
            }}
          >
            {isRegister
              ? 'Already have an account? Sign in'
              : "Don't have an account? Register"}
          </button>
        </div>
      </div>
    </div>
  )
}
