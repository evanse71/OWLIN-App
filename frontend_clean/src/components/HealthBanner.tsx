import { useEffect, useState } from 'react'
import { checkHealth } from '../lib/api'

export function HealthBanner() {
  const [status, setStatus] = useState<'checking' | 'healthy' | 'unhealthy'>('checking')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function check() {
      try {
        const response = await checkHealth()
        if (mounted) {
          if (response.status === 'ok') {
            setStatus('healthy')
            setError(null)
          } else {
            setStatus('unhealthy')
            setError('Backend returned unexpected status')
          }
        }
      } catch (err) {
        if (mounted) {
          setStatus('unhealthy')
          setError(err instanceof Error ? err.message : 'Unknown error')
        }
      }
    }

    check()

    // Poll every 10 seconds
    const interval = setInterval(check, 10000)

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  return (
    <div
      style={{
        padding: '12px 16px',
        borderRadius: '8px',
        marginBottom: '24px',
        backgroundColor:
          status === 'healthy'
            ? 'rgba(34, 197, 94, 0.1)'
            : status === 'unhealthy'
              ? 'rgba(239, 68, 68, 0.1)'
              : 'rgba(156, 163, 175, 0.1)',
        border: `1px solid ${
          status === 'healthy'
            ? 'rgba(34, 197, 94, 0.3)'
            : status === 'unhealthy'
              ? 'rgba(239, 68, 68, 0.3)'
              : 'rgba(156, 163, 175, 0.3)'
        }`,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}
    >
      <span style={{ fontSize: '18px' }}>
        {status === 'healthy' ? '✅' : status === 'unhealthy' ? '🔴' : '⏳'}
      </span>
      <span
        style={{
          color:
            status === 'healthy'
              ? 'rgb(22, 163, 74)'
              : status === 'unhealthy'
                ? 'rgb(220, 38, 38)'
                : 'rgb(107, 114, 128)',
          fontWeight: 500,
        }}
      >
        Backend:{' '}
        {status === 'healthy'
          ? 'Healthy'
          : status === 'unhealthy'
            ? `Unreachable${error ? ` (${error})` : ''}`
            : 'Checking...'}
      </span>
    </div>
  )
}

