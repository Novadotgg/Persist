import React, { useState, useEffect } from 'react'

interface IntegrationStatus {
  provider: string
  is_active: boolean
  created_at: string
}

interface IntegrationCard {
  id: string
  icon: string
  iconColor: string
  iconBg: string
  iconBorder: string
  name: string
  description: string
  provider: string
  action: () => void
  actionLabel: string
  isExpanded?: boolean
  badge?: string
  guide?: string
}

function StatusIndicator({ active }: { active: boolean }) {
  return (
    <div style={{ position: 'relative', width: '8px', height: '8px', flexShrink: 0 }}>
      {active && (
        <span
          style={{
            position: 'absolute',
            inset: '-3px',
            borderRadius: '50%',
            backgroundColor: '#34d399',
            opacity: 0.3,
            animation: 'integrations-ping 1.5s ease-in-out infinite',
          }}
        />
      )}
      <span
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          backgroundColor: active ? '#34d399' : 'rgba(112,112,125,0.3)',
        }}
      />
    </div>
  )
}

function StatusMessage({ message, onClear }: { message: string; onClear: () => void }) {
  const isSuccess = message.startsWith('Success')
  const isError = message.startsWith('Error')
  const config = isSuccess
    ? { color: '#6ee7b7', bg: 'rgba(52,211,153,0.1)', border: 'rgba(52,211,153,0.25)', icon: '✓' }
    : isError
    ? { color: '#fca5a5', bg: 'rgba(252,165,165,0.1)', border: 'rgba(252,165,165,0.25)', icon: '✕' }
    : { color: '#93c5fd', bg: 'rgba(59,130,246,0.1)', border: 'rgba(59,130,246,0.2)', icon: '⟳' }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '10px 14px',
        borderRadius: '10px',
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
        fontSize: '12px',
        color: config.color,
        animation: 'integrations-fade-up 0.3s ease',
      }}
    >
      <span style={{ fontSize: '14px', flexShrink: 0 }}>{config.icon}</span>
      <span style={{ flex: 1, lineHeight: 1.4 }}>{message}</span>
      <button
        onClick={onClear}
        style={{
          background: 'none',
          border: 'none',
          color: config.color,
          cursor: 'pointer',
          opacity: 0.6,
          padding: '2px',
          display: 'flex',
          alignItems: 'center',
          transition: 'opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
          flexShrink: 0,
        }}
        onMouseEnter={(e) => ((e.target as HTMLButtonElement).style.opacity = '1')}
        onMouseLeave={(e) => ((e.target as HTMLButtonElement).style.opacity = '0.6')}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  )
}

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        background: 'rgba(23,23,33,0.5)',
        border: '1px solid rgba(112,112,125,0.1)',
        borderRadius: '12px',
        padding: '18px 20px',
        animation: 'integrations-fade-up 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)',
      }}
    >
      <h3
        style={{
          fontSize: '10px',
          fontWeight: 600,
          color: 'var(--color-lead)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          margin: '0 0 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <span
          style={{
            width: '16px',
            height: '1px',
            background: 'rgba(112,112,125,0.3)',
            display: 'inline-block',
          }}
        />
        {title}
        <span style={{ flex: 1, height: '1px', background: 'rgba(112,112,125,0.15)', display: 'inline-block' }} />
      </h3>
      {children}
    </div>
  )
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <label
        style={{
          fontSize: '10px',
          fontWeight: 500,
          color: 'var(--color-lead)',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </label>
      {children}
    </div>
  )
}

function InputField(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const [focused, setFocused] = useState(false)
  return (
    <input
      {...props}
      onFocus={(e) => { setFocused(true); props.onFocus?.(e) }}
      onBlur={(e) => { setFocused(false); props.onBlur?.(e) }}
      style={{
        width: '100%',
        padding: '10px 14px',
        background: 'rgba(23,23,33,0.7)',
        color: 'var(--color-starlight)',
        fontFamily: 'var(--font-body)',
        fontSize: '13px',
        border: `1px solid ${focused ? 'rgba(82,102,235,0.45)' : 'rgba(112,112,125,0.2)'}`,
        borderRadius: '9px',
        outline: 'none',
        boxShadow: focused ? '0 0 0 3px rgba(82,102,235,0.1)' : 'none',
        transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        boxSizing: 'border-box',
        ...props.style,
      }}
    />
  )
}

export default function IntegrationsPanel() {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([])
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<string | null>(null)

  const [tgToken, setTgToken] = useState('')
  const [tgChatId, setTgChatId] = useState('')
  const [tgStatus, setTgStatus] = useState<string | null>(null)

  const [jiraProject, setJiraProject] = useState('KAN')
  const [jiraSummary, setJiraSummary] = useState('Test Jira Connection')
  const [jiraDesc, setJiraDesc] = useState('This is a test issue to verify integration.')
  const [jiraUrl, setJiraUrl] = useState('')
  const [jiraToken, setJiraToken] = useState('')
  const [jiraStatus, setJiraStatus] = useState<string | null>(null)

  // New integration state
  const [notionToken, setNotionToken] = useState('')
  const [notionStatus, setNotionStatus] = useState<string | null>(null)
  const [todoistToken, setTodoistToken] = useState('')
  const [todoistStatus, setTodoistStatus] = useState<string | null>(null)
  const [spotifyClientId, setSpotifyClientId] = useState('')
  const [spotifyClientSecret, setSpotifyClientSecret] = useState('')
  const [spotifyStatus, setSpotifyStatus] = useState<string | null>(null)
  const [whatsappToken, setWhatsappToken] = useState('')
  const [whatsappPhoneId, setWhatsappPhoneId] = useState('')
  const [whatsappStatus, setWhatsappStatus] = useState<string | null>(null)
  const [mapsKey, setMapsKey] = useState('')
  const [mapsStatus, setMapsStatus] = useState<string | null>(null)
  const [weatherKey, setWeatherKey] = useState('')
  const [weatherCity, setWeatherCity] = useState('London')
  const [weatherStatus, setWeatherStatus] = useState<string | null>(null)
  const [youtubeKey, setYoutubeKey] = useState('')
  const [youtubeStatus, setYoutubeStatus] = useState<string | null>(null)
  const [githubPat, setGithubPat] = useState('')
  const [githubStatus, setGithubStatus] = useState<string | null>(null)
  const [discordToken, setDiscordToken] = useState('')
  const [discordChannelId, setDiscordChannelId] = useState('')
  const [discordStatus, setDiscordStatus] = useState<string | null>(null)
  const [slackToken, setSlackToken] = useState('')
  const [slackChannel, setSlackChannel] = useState('#general')
  const [slackStatus, setSlackStatus] = useState<string | null>(null)
  const [bbApiKey, setBbApiKey] = useState('')
  const [bbProjectId, setBbProjectId] = useState('')
  const [browserStatus, setBrowserStatus] = useState<string | null>(null)

  const [activeForm, setActiveForm] = useState<'none' | 'telegram' | 'jira' | 'notion' | 'todoist' | 'spotify' | 'whatsapp' | 'google_maps' | 'weather' | 'youtube' | 'github' | 'discord' | 'slack' | 'browser'>('none')
  const [hoveredCard, setHoveredCard] = useState<string | null>(null)

  useEffect(() => {
    fetchIntegrations()
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://localhost:8000/api/v1/integrations/config', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        if (data.telegram?.bot_token) setTgToken(data.telegram.bot_token)
        if (data.telegram?.chat_id) setTgChatId(data.telegram.chat_id)
        if (data.jira?.base_url) setJiraUrl(data.jira.base_url)
      }
    } catch (e) {
      console.error('Failed to load integration config', e)
    }
  }

  const fetchIntegrations = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://localhost:8000/api/v1/integrations', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        setIntegrations(data)
      }
    } catch (e) {
      console.error('Failed to fetch integrations', e)
    }
  }

  const handleGoogleConnect = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://localhost:8000/api/v1/integrations/google/login', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        window.open(data.url, '_blank')
      } else {
        alert('Google OAuth client details are not configured on the backend.')
      }
    } catch (e) {
      console.error(e)
      alert('Failed to connect with Google OAuth.')
    }
  }

  const handleSyncNow = async () => {
    setIsSyncing(true)
    setSyncResult(null)
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://localhost:8000/api/v1/integrations/sync', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      const data = await res.json()
      setSyncResult(res.ok ? 'Success: Mail & Calendar synchronized successfully!' : `Error: ${data.detail || 'Sync failed'}`)
    } catch (e) {
      setSyncResult('Error: Failed to reach backend sync services.')
    } finally {
      setIsSyncing(false)
      fetchIntegrations()
    }
  }

  const handleTestTelegram = async (e: React.FormEvent) => {
    e.preventDefault()
    setTgStatus('Testing...')
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://localhost:8000/api/v1/integrations/test/telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ bot_token: tgToken, chat_id: tgChatId }),
      })
      const data = await res.json()
      setTgStatus(res.ok ? 'Success: Test message sent! Check Telegram.' : `Error: ${data.detail || 'Test failed'}`)
    } catch (e) {
      setTgStatus('Error: Failed to reach backend test services.')
    }
  }

  const handleSaveTelegram = async () => {
    setTgStatus('Saving...')
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://localhost:8000/api/v1/integrations/telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ bot_token: tgToken, chat_id: tgChatId }),
      })
      const data = await res.json()
      setTgStatus(res.ok ? 'Success: Credentials saved permanently!' : `Error: ${data.detail || 'Save failed'}`)
    } catch (e) {
      setTgStatus('Error: Failed to reach backend integration services.')
    }
  }

  const handleTestJira = async (e: React.FormEvent) => {
    e.preventDefault()
    setJiraStatus('Testing...')
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://localhost:8000/api/v1/integrations/test/jira', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          project_key: jiraProject,
          summary: jiraSummary,
          description: jiraDesc,
          base_url: jiraUrl || undefined,
          api_token: jiraToken || undefined,
        }),
      })
      const data = await res.json()
      setJiraStatus(res.ok ? `Success: Created issue ${data.response?.key || 'successfully'}!` : `Error: ${data.detail || 'Test failed'}`)
    } catch (e) {
      setJiraStatus('Error: Failed to reach backend test services.')
    }
  }

  const handleSaveJira = async () => {
    setJiraStatus('Saving...')
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('http://localhost:8000/api/v1/integrations/jira', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ base_url: jiraUrl, api_token: jiraToken }),
      })
      const data = await res.json()
      setJiraStatus(res.ok ? 'Success: Credentials saved permanently!' : `Error: ${data.detail || 'Save failed'}`)
    } catch (e) {
      setJiraStatus('Error: Failed to reach backend integration services.')
    }
  }

  const isProviderActive = (provider: string) =>
    integrations.some((i) => i.provider === provider && i.is_active)

  // Generic save handler for simple single-token integrations
  const makeSaveHandler = (provider: string, body: Record<string, string>, setStatus: (s: string | null) => void) => async () => {
    setStatus('Saving...')
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`http://localhost:8000/api/v1/integrations/${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      setStatus(res.ok ? 'Success: Credentials saved permanently!' : `Error: ${data.detail || 'Save failed'}`)
      if (res.ok) fetchIntegrations()
    } catch { setStatus('Error: Failed to reach backend.') }
  }

  const makeTestHandler = (endpoint: string, body: Record<string, string>, setStatus: (s: string | null) => void, successMsg?: string) => async (e?: React.FormEvent) => {
    e?.preventDefault()
    setStatus('Testing...')
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`http://localhost:8000/api/v1/integrations/test/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      setStatus(res.ok ? (successMsg ? `Success: ${successMsg}` : `Success: ${data.message || 'Connection verified!'}`) : `Error: ${data.detail || 'Test failed'}`)
    } catch { setStatus('Error: Failed to reach backend.') }
  }

  const tf = (provider: string) => activeForm === provider
  const toggle = (provider: string) => () => setActiveForm((tf(provider) ? 'none' : provider) as any)

  const cards: IntegrationCard[] = [
    // ── Google Suite ──
    {
      id: 'google',
      icon: '/drive.jpg',
      iconColor: '#f87171',
      iconBg: 'rgba(239,68,68,0.05)',
      iconBorder: 'rgba(239,68,68,0.15)',
      name: 'Google OAuth',
      description: 'Gmail, Google Calendar and Google Drive via OAuth2. Fetches emails, events and files.',
      provider: 'google',
      action: handleGoogleConnect,
      actionLabel: 'Connect Account',
      badge: 'Gmail · Calendar · Drive',
      guide: 'OAuth credentials are configured on the backend. Click "Connect Account" to authenticate with your Google account.',
    },
    {
      id: 'google_maps',
      icon: '/maps.png',
      iconColor: '#fb923c',
      iconBg: 'rgba(251,146,60,0.05)',
      iconBorder: 'rgba(251,146,60,0.15)',
      name: 'Google Maps',
      description: 'Geocoding, turn-by-turn directions, and place search via the Maps Platform API.',
      provider: 'google_maps',
      action: toggle('google_maps'),
      actionLabel: tf('google_maps') ? 'Close Panel' : 'Configure',
      isExpanded: tf('google_maps'),
      guide: 'Create a Google Cloud project, enable the Geocoding, Directions, and Places APIs, and copy your API Key from the Credentials section.',
    },
    {
      id: 'youtube',
      icon: '/yt.jpg',
      iconColor: '#f87171',
      iconBg: 'rgba(239,68,68,0.05)',
      iconBorder: 'rgba(239,68,68,0.15)',
      name: 'YouTube',
      description: 'Search videos, fetch channel info, and browse playlist content via YouTube Data API v3.',
      provider: 'youtube',
      action: toggle('youtube'),
      actionLabel: tf('youtube') ? 'Close Panel' : 'Configure',
      isExpanded: tf('youtube'),
      guide: 'Enable the YouTube Data API v3 in your Google Cloud Console, and generate an API Key in the Credentials tab.',
    },
    // ── Productivity ──
    {
      id: 'notion',
      icon: '/notion.jpg',
      iconColor: '#e5e7eb',
      iconBg: 'rgba(229,231,235,0.03)',
      iconBorder: 'rgba(229,231,235,0.1)',
      name: 'Notion',
      description: 'Search pages, create notes, and query databases in your Notion workspace.',
      provider: 'notion',
      action: toggle('notion'),
      actionLabel: tf('notion') ? 'Close Panel' : 'Configure',
      isExpanded: tf('notion'),
      guide: 'Go to developers.notion.com, click "View My Integrations", create a new internal integration, and copy its Internal Integration Token.',
    },
    {
      id: 'todoist',
      icon: '/todoist.jpg',
      iconColor: '#f87171',
      iconBg: 'rgba(239,68,68,0.05)',
      iconBorder: 'rgba(239,68,68,0.15)',
      name: 'Todoist',
      description: 'Create, complete, and list tasks across Todoist projects with AI-powered scheduling.',
      provider: 'todoist',
      action: toggle('todoist'),
      actionLabel: tf('todoist') ? 'Close Panel' : 'Configure',
      isExpanded: tf('todoist'),
      guide: 'Log in to Todoist on the web, go to Settings > Integrations > Developer tab, and copy your API Token.',
    },
    {
      id: 'jira',
      icon: '/jira.jpg',
      iconColor: '#818cf8',
      iconBg: 'rgba(99,102,241,0.05)',
      iconBorder: 'rgba(99,102,241,0.15)',
      name: 'Atlassian Jira',
      description: 'Lets the AI agent create, modify, and list tickets directly within project boards.',
      provider: 'jira',
      action: toggle('jira'),
      actionLabel: tf('jira') ? 'Close Panel' : 'Configure',
      isExpanded: tf('jira'),
      guide: 'Generate an API Token at id.atlassian.com/manage-profile/security/api-tokens. Format required: "email:api-token".',
    },
    // ── Communication ──
    {
      id: 'telegram',
      icon: '/tg.jpg',
      iconColor: '#34d399',
      iconBg: 'rgba(52,211,153,0.05)',
      iconBorder: 'rgba(52,211,153,0.15)',
      name: 'Telegram Bot',
      description: 'Dispatches urgent event alerts and summary updates straight to your private chat.',
      provider: 'telegram',
      action: toggle('telegram'),
      actionLabel: tf('telegram') ? 'Close Panel' : 'Configure',
      isExpanded: tf('telegram'),
      guide: 'Create a bot by messaging @BotFather on Telegram to get a Bot Token. To find your Chat ID, send a message to @userinfobot.',
    },
    {
      id: 'discord',
      icon: '/dc.jpg',
      iconColor: '#818cf8',
      iconBg: 'rgba(88,101,242,0.05)',
      iconBorder: 'rgba(88,101,242,0.15)',
      name: 'Discord',
      description: 'Send messages, read channels, and react to messages via a Discord Bot.',
      provider: 'discord',
      action: toggle('discord'),
      actionLabel: tf('discord') ? 'Close Panel' : 'Configure',
      isExpanded: tf('discord'),
      guide: 'Go to discord.com/developers/applications, create an application, add a Bot user, copy the Bot Token, and copy your Target Channel ID.',
    },
    {
      id: 'slack',
      icon: '/slack.jpg',
      iconColor: '#4ade80',
      iconBg: 'rgba(74,222,128,0.05)',
      iconBorder: 'rgba(74,222,128,0.15)',
      name: 'Slack',
      description: 'Post messages, browse channels, and send rich Block Kit messages to your workspace.',
      provider: 'slack',
      action: toggle('slack'),
      actionLabel: tf('slack') ? 'Close Panel' : 'Configure',
      isExpanded: tf('slack'),
      guide: 'Create an app at api.slack.com/apps, install it to your workspace with "chat:write" scopes, and copy the Bot User OAuth Token.',
    },
    {
      id: 'whatsapp',
      icon: '/wp.jpg',
      iconColor: '#4ade80',
      iconBg: 'rgba(74,222,128,0.05)',
      iconBorder: 'rgba(74,222,128,0.15)',
      name: 'WhatsApp Business',
      description: 'Send text and template messages via the WhatsApp Business Cloud API (Meta).',
      provider: 'whatsapp',
      action: toggle('whatsapp'),
      actionLabel: tf('whatsapp') ? 'Close Panel' : 'Configure',
      isExpanded: tf('whatsapp'),
      badge: 'Business API',
      guide: 'Go to developers.facebook.com, add WhatsApp to your application, and copy your Phone Number ID and Permanent Access Token.',
    },
    // ── Developer & Automation ──
    {
      id: 'github',
      icon: '/github.jpg',
      iconColor: '#e5e7eb',
      iconBg: 'rgba(229,231,235,0.03)',
      iconBorder: 'rgba(229,231,235,0.1)',
      name: 'GitHub',
      description: 'List repos, manage issues, browse PRs, and track notifications via GitHub REST API.',
      provider: 'github',
      action: toggle('github'),
      actionLabel: tf('github') ? 'Close Panel' : 'Configure',
      isExpanded: tf('github'),
      guide: 'Go to GitHub Settings > Developer Settings > Personal Access Tokens (Classic or Fine-grained), and generate a token with repo permissions.',
    },
    {
      id: 'browser',
      icon: '🌐',
      iconColor: '#38bdf8',
      iconBg: 'rgba(56,189,248,0.05)',
      iconBorder: 'rgba(56,189,248,0.15)',
      name: 'Browser Automation',
      description: 'Scrape pages, take screenshots, and automate web interactions via local Playwright or Browserbase cloud.',
      provider: 'browser',
      action: toggle('browser'),
      actionLabel: tf('browser') ? 'Close Panel' : 'Configure',
      isExpanded: tf('browser'),
      badge: 'Playwright · Browserbase',
      guide: 'Local Playwright runs out-of-the-box. For cloud sessions, sign up at browserbase.com, and copy your API Key and Project ID.',
    },
    // ── Media & Utilities ──
    {
      id: 'spotify',
      icon: '/spotify.png',
      iconColor: '#4ade80',
      iconBg: 'rgba(29,185,84,0.05)',
      iconBorder: 'rgba(29,185,84,0.15)',
      name: 'Spotify',
      description: 'Control playback, search tracks, browse playlists, and view now-playing status.',
      provider: 'spotify',
      action: toggle('spotify'),
      actionLabel: tf('spotify') ? 'Close Panel' : 'Configure',
      isExpanded: tf('spotify'),
      guide: 'Create an app at developer.spotify.com/dashboard, and copy your Client ID and Client Secret from the App Dashboard Settings page.',
    },
    {
      id: 'weather',
      icon: '/weather.jpg',
      iconColor: '#38bdf8',
      iconBg: 'rgba(56,189,248,0.05)',
      iconBorder: 'rgba(56,189,248,0.15)',
      name: 'Weather',
      description: 'Real-time weather conditions, forecasts, and air quality via OpenWeatherMap API.',
      provider: 'weather',
      action: toggle('weather'),
      actionLabel: tf('weather') ? 'Close Panel' : 'Configure',
      isExpanded: tf('weather'),
      badge: 'OpenWeatherMap',
      guide: 'Sign up on openweathermap.org, navigate to your Member Account Dashboard, and copy your API Key from the "My API Keys" tab.',
    },
  ]

  return (
    <>
      <style>{`
        @keyframes integrations-ping {
          0% { transform: scale(1); opacity: 0.4; }
          50% { transform: scale(2.2); opacity: 0; }
          100% { transform: scale(1); opacity: 0; }
        }
        @keyframes integrations-fade-up {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes integrations-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .integration-card {
          transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
          position: relative;
          overflow: visible;
        }
        .integration-card::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: inherit;
          opacity: 0;
          transition: opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1);
          pointer-events: none;
        }
        .integration-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 12px 32px rgba(0,0,0,0.3);
          z-index: 10;
        }
        .integration-card:hover::before {
          opacity: 1;
        }
        .integration-card-google:hover {
          border-color: rgba(239,68,68,0.3) !important;
          box-shadow: 0 12px 32px rgba(239,68,68,0.1), 0 0 0 1px rgba(239,68,68,0.15) !important;
        }
        .integration-card-telegram:hover {
          border-color: rgba(52,211,153,0.3) !important;
          box-shadow: 0 12px 32px rgba(52,211,153,0.1), 0 0 0 1px rgba(52,211,153,0.15) !important;
        }
        .integration-card-jira:hover {
          border-color: rgba(99,102,241,0.3) !important;
          box-shadow: 0 12px 32px rgba(99,102,241,0.1), 0 0 0 1px rgba(99,102,241,0.15) !important;
        }
        .integration-action-btn {
          transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
          position: relative;
          overflow: hidden;
        }
        .integration-action-btn::after {
          content: '';
          position: absolute;
          inset: 0;
          background: rgba(255,255,255,0.05);
          opacity: 0;
          transition: opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .integration-action-btn:hover {
          transform: translateY(-1px);
        }
        .integration-action-btn:hover::after {
          opacity: 1;
        }
        .integration-action-btn:active {
          transform: scale(0.97);
        }
        .sync-btn {
          transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .sync-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(82,102,235,0.4) !important;
        }
        .sync-btn:active:not(:disabled) {
          transform: scale(0.97);
        }
        .form-submit-btn {
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .form-submit-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 20px rgba(82,102,235,0.35);
        }
        .form-save-btn {
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .form-save-btn:hover {
          background: rgba(112,112,125,0.2) !important;
          border-color: rgba(112,112,125,0.3) !important;
        }
        .integration-tooltip-wrapper:hover .tooltip-content {
          opacity: 1 !important;
          pointer-events: auto !important;
          transform: translateY(-4px) !important;
        }
        .tooltip-trigger:hover {
          border-color: rgba(82, 102, 235, 0.6) !important;
          color: var(--color-starlight) !important;
          background: rgba(82, 102, 235, 0.1);
        }
        .cards-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 14px;
        }
        @media (max-width: 1400px) {
          .cards-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr));
          }
        }
        @media (max-width: 1100px) {
          .cards-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
          }
        }
        @media (max-width: 800px) {
          .cards-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }
        @media (max-width: 500px) {
          .cards-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          height: '100%',
          overflowY: 'auto',
          minHeight: 0,
          padding: '12px 14px',
          boxSizing: 'border-box',
        }}
      >
        {/* ── Header Card ── */}
        <div
          style={{
            background: 'linear-gradient(145deg, rgba(30,30,42,0.95) 0%, rgba(23,23,33,0.9) 100%)',
            border: '1px solid rgba(112,112,125,0.15)',
            borderRadius: '14px',
            padding: '20px 24px',
            backdropFilter: 'blur(12px)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
            <div>
              <h2
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: '16px',
                  fontWeight: 500,
                  color: 'var(--color-starlight)',
                  margin: '0 0 4px',
                  letterSpacing: '0.02em',
                }}
              >
                Connected Integrations
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--color-lead)', margin: 0, lineHeight: 1.4 }}>
                Configure third-party connectors and trigger data syncer
              </p>
            </div>

            <button
              onClick={handleSyncNow}
              disabled={isSyncing}
              className="sync-btn mercury-btn-primary"
              style={{
                padding: '10px 20px',
                fontSize: '13px',
                gap: '8px',
                display: 'flex',
                alignItems: 'center',
                boxShadow: '0 4px 16px rgba(82,102,235,0.3)',
              }}
            >
              {isSyncing ? (
                <>
                  <span
                    style={{
                      width: '13px',
                      height: '13px',
                      border: '2px solid rgba(255,255,255,0.25)',
                      borderTopColor: '#fff',
                      borderRadius: '50%',
                      display: 'inline-block',
                      animation: 'integrations-spin 0.7s linear infinite',
                    }}
                  />
                  Syncing...
                </>
              ) : (
                <>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 4 23 10 17 10" />
                    <polyline points="1 20 1 14 7 14" />
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                  </svg>
                  Sync Now
                </>
              )}
            </button>
          </div>

          {syncResult && (
            <div style={{ marginTop: '14px' }}>
              <StatusMessage message={syncResult} onClear={() => setSyncResult(null)} />
            </div>
          )}

          {/* Active connections summary */}
          {integrations.length > 0 && (
            <div
              style={{
                marginTop: '14px',
                paddingTop: '14px',
                borderTop: '1px solid rgba(112,112,125,0.1)',
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                flexWrap: 'wrap',
              }}
            >
              <span style={{ fontSize: '10px', color: 'var(--color-lead)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                Active Connections
              </span>
              {integrations.filter((i) => i.is_active).map((i) => (
                <div
                  key={i.provider}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '3px 9px',
                    borderRadius: '100px',
                    background: 'rgba(52,211,153,0.08)',
                    border: '1px solid rgba(52,211,153,0.2)',
                    fontSize: '10px',
                    color: '#6ee7b7',
                    fontWeight: 500,
                    letterSpacing: '0.04em',
                    textTransform: 'capitalize',
                  }}
                >
                  <span style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: '#34d399' }} />
                  {i.provider}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Integration Cards ── */}
        <div className="cards-grid">
          {cards.map((card) => {
            const isActive = isProviderActive(card.provider)
            return (
              <div
                key={card.id}
                className={`integration-card integration-card-${card.id}`}
                style={{
                  background: hoveredCard === card.id
                    ? 'linear-gradient(145deg, rgba(39,39,53,0.98) 0%, rgba(30,30,42,0.95) 100%)'
                    : 'linear-gradient(145deg, rgba(30,30,42,0.9) 0%, rgba(23,23,33,0.85) 100%)',
                  border: '1px solid rgba(112,112,125,0.12)',
                  borderRadius: '14px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  backdropFilter: 'blur(8px)',
                  minHeight: '280px',
                  justifyContent: 'space-between',
                  boxSizing: 'border-box',
                }}
                onMouseEnter={() => setHoveredCard(card.id)}
                onMouseLeave={() => setHoveredCard(null)}
              >
                {/* Header row: Icon (left) and Status Indicator (right) */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div
                    style={{
                      width: '38px',
                      height: '38px',
                      borderRadius: '10px',
                      background: card.iconBg,
                      border: `1px solid ${card.iconBorder}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '16px',
                      color: card.iconColor,
                      fontWeight: 700,
                      flexShrink: 0,
                      transition: 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
                      transform: hoveredCard === card.id ? 'scale(1.05)' : 'scale(1)',
                    }}
                  >
                    {card.icon.startsWith('/') ? (
                      <img
                        src={card.icon}
                        alt={card.name}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover',
                          borderRadius: 'inherit',
                          display: 'block',
                        }}
                      />
                    ) : (
                      card.icon
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        background: isActive ? 'rgba(52,211,153,0.08)' : 'rgba(112,112,125,0.06)',
                        border: `1px solid ${isActive ? 'rgba(52,211,153,0.15)' : 'rgba(112,112,125,0.1)'}`,
                        padding: '2px 8px',
                        borderRadius: '100px',
                      }}
                    >
                      <StatusIndicator active={isActive} />
                      <span
                        style={{
                          fontSize: '9px',
                          color: isActive ? '#34d399' : 'var(--color-lead)',
                          fontWeight: 600,
                          letterSpacing: '0.02em',
                        }}
                      >
                        {isActive ? 'Active' : 'Inactive'}
                      </span>
                    </div>

                    {card.guide && (
                      <div className="integration-tooltip-wrapper" style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                        <span
                          className="tooltip-trigger"
                          style={{
                            width: '16px',
                            height: '16px',
                            borderRadius: '50%',
                            border: '1px solid rgba(112,112,125,0.3)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '9px',
                            fontWeight: 600,
                            color: 'var(--color-lead)',
                            cursor: 'help',
                            transition: 'all 0.2s',
                          }}
                        >
                          i
                        </span>
                        <div
                          className="tooltip-content"
                          style={{
                            position: 'absolute',
                            bottom: '100%',
                            right: 0,
                            transform: 'translateY(-8px)',
                            background: 'rgba(20, 20, 30, 0.95)',
                            border: '1px solid rgba(82, 102, 235, 0.3)',
                            borderRadius: '8px',
                            padding: '10px 12px',
                            width: '220px',
                            fontSize: '11px',
                            color: 'var(--color-starlight)',
                            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                            backdropFilter: 'blur(12px)',
                            lineHeight: 1.4,
                            zIndex: 100,
                            whiteSpace: 'normal',
                            pointerEvents: 'none',
                            opacity: 0,
                            transition: 'opacity 0.2s ease, transform 0.2s ease',
                          }}
                        >
                          {card.guide}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Title & Badge */}
                <div>
                  <div
                    style={{
                      fontSize: '14px',
                      fontWeight: 600,
                      color: 'var(--color-starlight)',
                      letterSpacing: '0.01em',
                      marginBottom: card.badge ? '4px' : '0px',
                    }}
                  >
                    {card.name}
                  </div>
                  {card.badge && (
                    <div
                      style={{
                        fontSize: '9px',
                        color: 'var(--color-lead)',
                        letterSpacing: '0.03em',
                        background: 'rgba(112,112,125,0.08)',
                        border: '1px solid rgba(112,112,125,0.12)',
                        padding: '2px 8px',
                        borderRadius: '100px',
                        display: 'inline-block',
                        maxWidth: '100%',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={card.badge}
                    >
                      {card.badge}
                    </div>
                  )}
                </div>

                {/* Description */}
                <p
                  style={{
                    fontSize: '11.5px',
                    color: 'var(--color-lead)',
                    margin: 0,
                    lineHeight: 1.5,
                    flex: 1,
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {card.description}
                </p>

                {/* Action button */}
                <button
                  onClick={card.action}
                  className="integration-action-btn"
                  style={{
                    width: '100%',
                    padding: '8px 0',
                    borderRadius: '9px',
                    fontSize: '11.5px',
                    fontWeight: 500,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    cursor: 'pointer',
                    letterSpacing: '0.02em',
                    boxSizing: 'border-box',
                    ...(card.isExpanded
                      ? {
                          background: 'rgba(112,112,125,0.12)',
                          border: '1px solid rgba(112,112,125,0.2)',
                          color: 'var(--color-silver)',
                        }
                      : isActive
                      ? {
                          background: `${card.iconBg}`,
                          border: `1px solid ${card.iconBorder}`,
                          color: card.iconColor,
                        }
                      : {
                          background: 'linear-gradient(135deg, var(--color-mercury-blue) 0%, #6478f0 100%)',
                          border: 'none',
                          color: '#fff',
                          boxShadow: '0 3px 12px rgba(82,102,235,0.25)',
                        }),
                  }}
                >
                  {card.isExpanded ? (
                    <>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                      Close Panel
                    </>
                  ) : (
                    <>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <circle cx="12" cy="12" r="3" /><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14" />
                      </svg>
                      {card.actionLabel}
                    </>
                  )}
                </button>
              </div>
            )
          })}
        </div>

        {/* ── Telegram Config Form ── */}
        {activeForm === 'telegram' && (
          <FormSection title="Configure Telegram Alert Push">
            <form onSubmit={handleTestTelegram} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                  gap: '14px',
                }}
              >
                <FieldGroup label="Telegram Bot Token">
                  <InputField
                    type="password"
                    value={tgToken}
                    onChange={(e) => setTgToken(e.target.value)}
                    placeholder="Paste bot token here..."
                    required
                  />
                </FieldGroup>
                <FieldGroup label="Telegram Chat ID">
                  <InputField
                    type="text"
                    value={tgChatId}
                    onChange={(e) => setTgChatId(e.target.value)}
                    placeholder="Enter numeric chat ID..."
                    required
                  />
                </FieldGroup>
              </div>

              {tgStatus && (
                <StatusMessage message={tgStatus} onClear={() => setTgStatus(null)} />
              )}

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  type="submit"
                  className="form-submit-btn mercury-btn-primary"
                  style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                  Dispatch Test
                </button>
                <button
                  type="button"
                  onClick={handleSaveTelegram}
                  className="form-save-btn"
                  style={{
                    padding: '10px 20px',
                    fontSize: '13px',
                    borderRadius: 'var(--radius-pill)',
                    background: 'rgba(112,112,125,0.1)',
                    border: '1px solid rgba(112,112,125,0.2)',
                    color: 'var(--color-silver)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontFamily: 'var(--font-body)',
                    fontWeight: 400,
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                    <polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" />
                  </svg>
                  Save Credentials
                </button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Jira Config Form ── */}
        {activeForm === 'jira' && (
          <FormSection title="Configure Jira Integration">
            <form onSubmit={handleTestJira} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '14px',
                }}
              >
                <FieldGroup label="Project Key">
                  <InputField
                    type="text"
                    value={jiraProject}
                    onChange={(e) => setJiraProject(e.target.value)}
                    required
                  />
                </FieldGroup>
                <FieldGroup label="Jira Base URL">
                  <InputField
                    type="text"
                    value={jiraUrl}
                    onChange={(e) => setJiraUrl(e.target.value)}
                    placeholder="https://domain.atlassian.net"
                    required
                  />
                </FieldGroup>
                <FieldGroup label="API Token / Password">
                  <InputField
                    type="password"
                    value={jiraToken}
                    onChange={(e) => setJiraToken(e.target.value)}
                    placeholder="user@co.com:api-token"
                    required
                  />
                </FieldGroup>
              </div>

              <div
                style={{
                  height: '1px',
                  background: 'rgba(112,112,125,0.1)',
                  margin: '2px 0',
                }}
              />

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                  gap: '14px',
                }}
              >
                <FieldGroup label="Test Ticket Summary">
                  <InputField
                    type="text"
                    value={jiraSummary}
                    onChange={(e) => setJiraSummary(e.target.value)}
                    required
                  />
                </FieldGroup>
                <FieldGroup label="Test Description">
                  <InputField
                    type="text"
                    value={jiraDesc}
                    onChange={(e) => setJiraDesc(e.target.value)}
                    required
                  />
                </FieldGroup>
              </div>

              {jiraStatus && (
                <StatusMessage message={jiraStatus} onClear={() => setJiraStatus(null)} />
              )}

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  type="submit"
                  className="form-submit-btn mercury-btn-primary"
                  style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                  </svg>
                  Create Test Issue
                </button>
                <button
                  type="button"
                  onClick={handleSaveJira}
                  className="form-save-btn"
                  style={{
                    padding: '10px 20px',
                    fontSize: '13px',
                    borderRadius: 'var(--radius-pill)',
                    background: 'rgba(112,112,125,0.1)',
                    border: '1px solid rgba(112,112,125,0.2)',
                    color: 'var(--color-silver)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontFamily: 'var(--font-body)',
                    fontWeight: 400,
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                    <polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" />
                  </svg>
                  Save Credentials
                </button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Notion Config Form ── */}
        {activeForm === 'notion' && (
          <FormSection title="Configure Notion Integration">
            <form onSubmit={makeTestHandler('notion', { api_token: notionToken }, setNotionStatus)} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <FieldGroup label="Notion Internal Integration Token">
                <InputField type="password" value={notionToken} onChange={(e) => setNotionToken(e.target.value)} placeholder="secret_..." required />
              </FieldGroup>
              {notionStatus && <StatusMessage message={notionStatus} onClear={() => setNotionStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="submit" className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Test Connection</button>
                <button type="button" onClick={makeSaveHandler('notion', { api_token: notionToken }, setNotionStatus)} className="form-save-btn" style={{ padding: '10px 20px', fontSize: '13px', borderRadius: 'var(--radius-pill)', background: 'rgba(112,112,125,0.1)', border: '1px solid rgba(112,112,125,0.2)', color: 'var(--color-silver)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Save Credentials</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Todoist Config Form ── */}
        {activeForm === 'todoist' && (
          <FormSection title="Configure Todoist Integration">
            <form onSubmit={makeTestHandler('todoist', { api_token: todoistToken }, setTodoistStatus)} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <FieldGroup label="Todoist API Token">
                <InputField type="password" value={todoistToken} onChange={(e) => setTodoistToken(e.target.value)} placeholder="Paste Todoist API token..." required />
              </FieldGroup>
              {todoistStatus && <StatusMessage message={todoistStatus} onClear={() => setTodoistStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="submit" className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Test Connection</button>
                <button type="button" onClick={makeSaveHandler('todoist', { api_token: todoistToken }, setTodoistStatus)} className="form-save-btn" style={{ padding: '10px 20px', fontSize: '13px', borderRadius: 'var(--radius-pill)', background: 'rgba(112,112,125,0.1)', border: '1px solid rgba(112,112,125,0.2)', color: 'var(--color-silver)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Save Credentials</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Spotify Config Form ── */}
        {activeForm === 'spotify' && (
          <FormSection title="Configure Spotify Integration">
            <form style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
                <FieldGroup label="Spotify Client ID">
                  <InputField type="text" value={spotifyClientId} onChange={(e) => setSpotifyClientId(e.target.value)} placeholder="Spotify App Client ID" required />
                </FieldGroup>
                <FieldGroup label="Spotify Client Secret">
                  <InputField type="password" value={spotifyClientSecret} onChange={(e) => setSpotifyClientSecret(e.target.value)} placeholder="Spotify App Client Secret" required />
                </FieldGroup>
              </div>
              {spotifyStatus && <StatusMessage message={spotifyStatus} onClear={() => setSpotifyStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="button" onClick={makeSaveHandler('spotify', { client_id: spotifyClientId, client_secret: spotifyClientSecret }, setSpotifyStatus)} className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Save Credentials</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── WhatsApp Config Form ── */}
        {activeForm === 'whatsapp' && (
          <FormSection title="Configure WhatsApp Business API">
            <form style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
                <FieldGroup label="Meta Access Token">
                  <InputField type="password" value={whatsappToken} onChange={(e) => setWhatsappToken(e.target.value)} placeholder="Permanent access token" required />
                </FieldGroup>
                <FieldGroup label="Phone Number ID">
                  <InputField type="text" value={whatsappPhoneId} onChange={(e) => setWhatsappPhoneId(e.target.value)} placeholder="WhatsApp Phone Number ID" required />
                </FieldGroup>
              </div>
              {whatsappStatus && <StatusMessage message={whatsappStatus} onClear={() => setWhatsappStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="button" onClick={makeSaveHandler('whatsapp', { access_token: whatsappToken, phone_number_id: whatsappPhoneId }, setWhatsappStatus)} className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Save Credentials</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Google Maps Config Form ── */}
        {activeForm === 'google_maps' && (
          <FormSection title="Configure Google Maps Integration">
            <form style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <FieldGroup label="Google Maps Platform API Key">
                <InputField type="password" value={mapsKey} onChange={(e) => setMapsKey(e.target.value)} placeholder="AIza..." required />
              </FieldGroup>
              {mapsStatus && <StatusMessage message={mapsStatus} onClear={() => setMapsStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="button" onClick={makeSaveHandler('google_maps', { api_key: mapsKey }, setMapsStatus)} className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Save API Key</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Weather Config Form ── */}
        {activeForm === 'weather' && (
          <FormSection title="Configure Weather API (OpenWeatherMap)">
            <form onSubmit={makeTestHandler('weather', { api_key: weatherKey, city: weatherCity }, setWeatherStatus)} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
                <FieldGroup label="OpenWeatherMap API Key">
                  <InputField type="password" value={weatherKey} onChange={(e) => setWeatherKey(e.target.value)} placeholder="Your OWM API key..." required />
                </FieldGroup>
                <FieldGroup label="Test City">
                  <InputField type="text" value={weatherCity} onChange={(e) => setWeatherCity(e.target.value)} placeholder="e.g. London" />
                </FieldGroup>
              </div>
              {weatherStatus && <StatusMessage message={weatherStatus} onClear={() => setWeatherStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="submit" className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Test Connection</button>
                <button type="button" onClick={makeSaveHandler('weather', { api_key: weatherKey }, setWeatherStatus)} className="form-save-btn" style={{ padding: '10px 20px', fontSize: '13px', borderRadius: 'var(--radius-pill)', background: 'rgba(112,112,125,0.1)', border: '1px solid rgba(112,112,125,0.2)', color: 'var(--color-silver)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Save Credentials</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── YouTube Config Form ── */}
        {activeForm === 'youtube' && (
          <FormSection title="Configure YouTube Integration">
            <form style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <FieldGroup label="YouTube Data API v3 Key">
                <InputField type="password" value={youtubeKey} onChange={(e) => setYoutubeKey(e.target.value)} placeholder="AIza..." required />
              </FieldGroup>
              {youtubeStatus && <StatusMessage message={youtubeStatus} onClear={() => setYoutubeStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="button" onClick={makeSaveHandler('youtube', { api_key: youtubeKey }, setYoutubeStatus)} className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Save API Key</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── GitHub Config Form ── */}
        {activeForm === 'github' && (
          <FormSection title="Configure GitHub Integration">
            <form onSubmit={makeTestHandler('github', { personal_access_token: githubPat }, setGithubStatus)} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <FieldGroup label="GitHub Personal Access Token">
                <InputField type="password" value={githubPat} onChange={(e) => setGithubPat(e.target.value)} placeholder="ghp_... or github_pat_..." required />
              </FieldGroup>
              {githubStatus && <StatusMessage message={githubStatus} onClear={() => setGithubStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="submit" className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Test Connection</button>
                <button type="button" onClick={makeSaveHandler('github', { personal_access_token: githubPat }, setGithubStatus)} className="form-save-btn" style={{ padding: '10px 20px', fontSize: '13px', borderRadius: 'var(--radius-pill)', background: 'rgba(112,112,125,0.1)', border: '1px solid rgba(112,112,125,0.2)', color: 'var(--color-silver)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Save Credentials</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Discord Config Form ── */}
        {activeForm === 'discord' && (
          <FormSection title="Configure Discord Bot Integration">
            <form onSubmit={makeTestHandler('discord', { bot_token: discordToken, channel_id: discordChannelId }, setDiscordStatus)} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
                <FieldGroup label="Discord Bot Token">
                  <InputField type="password" value={discordToken} onChange={(e) => setDiscordToken(e.target.value)} placeholder="Bot token from Discord Developer Portal" required />
                </FieldGroup>
                <FieldGroup label="Test Channel ID">
                  <InputField type="text" value={discordChannelId} onChange={(e) => setDiscordChannelId(e.target.value)} placeholder="Channel ID to send test message" required />
                </FieldGroup>
              </div>
              {discordStatus && <StatusMessage message={discordStatus} onClear={() => setDiscordStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="submit" className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Send Test Message</button>
                <button type="button" onClick={makeSaveHandler('discord', { bot_token: discordToken }, setDiscordStatus)} className="form-save-btn" style={{ padding: '10px 20px', fontSize: '13px', borderRadius: 'var(--radius-pill)', background: 'rgba(112,112,125,0.1)', border: '1px solid rgba(112,112,125,0.2)', color: 'var(--color-silver)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Save Credentials</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Slack Config Form ── */}
        {activeForm === 'slack' && (
          <FormSection title="Configure Slack Bot Integration">
            <form onSubmit={makeTestHandler('slack', { bot_token: slackToken, channel: slackChannel }, setSlackStatus)} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
                <FieldGroup label="Slack Bot Token (xoxb-...)">
                  <InputField type="password" value={slackToken} onChange={(e) => setSlackToken(e.target.value)} placeholder="xoxb-..." required />
                </FieldGroup>
                <FieldGroup label="Test Channel">
                  <InputField type="text" value={slackChannel} onChange={(e) => setSlackChannel(e.target.value)} placeholder="#general or channel ID" />
                </FieldGroup>
              </div>
              {slackStatus && <StatusMessage message={slackStatus} onClear={() => setSlackStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="submit" className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Send Test Message</button>
                <button type="button" onClick={makeSaveHandler('slack', { bot_token: slackToken }, setSlackStatus)} className="form-save-btn" style={{ padding: '10px 20px', fontSize: '13px', borderRadius: 'var(--radius-pill)', background: 'rgba(112,112,125,0.1)', border: '1px solid rgba(112,112,125,0.2)', color: 'var(--color-silver)', cursor: 'pointer', fontFamily: 'var(--font-body)' }}>Save Credentials</button>
              </div>
            </form>
          </FormSection>
        )}

        {/* ── Browser Automation Config Form ── */}
        {activeForm === 'browser' && (
          <FormSection title="Configure Browser Automation (Playwright / Browserbase)">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <p style={{ fontSize: '12px', color: 'var(--color-lead)', margin: 0, lineHeight: 1.6 }}>
                Local Playwright (headless Chromium) is always available once installed.<br />
                Optionally provide Browserbase credentials below to run browser sessions in the cloud.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
                <FieldGroup label="Browserbase API Key (optional)">
                  <InputField type="password" value={bbApiKey} onChange={(e) => setBbApiKey(e.target.value)} placeholder="Browserbase API key" />
                </FieldGroup>
                <FieldGroup label="Browserbase Project ID (optional)">
                  <InputField type="text" value={bbProjectId} onChange={(e) => setBbProjectId(e.target.value)} placeholder="Project ID" />
                </FieldGroup>
              </div>
              {browserStatus && <StatusMessage message={browserStatus} onClear={() => setBrowserStatus(null)} />}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="button" onClick={makeSaveHandler('browser', { api_key: bbApiKey, project_id: bbProjectId }, setBrowserStatus)} className="form-submit-btn mercury-btn-primary" style={{ padding: '10px 20px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>Save Browserbase Config</button>
              </div>
            </div>
          </FormSection>
        )}

        {/* ── Bottom padding ── */}
        <div style={{ height: '8px', flexShrink: 0 }} />
      </div>
    </>
  )
}
