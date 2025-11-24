import { useEffect, useState } from 'react'
import { checkHealth } from '../../lib/api'
import './HealthStatusIndicator.css'

export function HealthStatusIndicator() {
  const [status, setStatus] = useState<'checking' | 'healthy' | 'unhealthy'>('checking')

  useEffect(() => {
    let mounted = true

    async function check() {
      try {
        const response = await checkHealth()
        if (mounted) {
          setStatus(response.status === 'ok' ? 'healthy' : 'unhealthy')
        }
      } catch {
        if (mounted) {
          setStatus('unhealthy')
        }
      }
    }

    check()
    const interval = setInterval(check, 10000)

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  return (
    <div className={`health-status-indicator status-${status}`} title={`Backend: ${status === 'healthy' ? 'Healthy' : status === 'unhealthy' ? 'Unreachable' : 'Checking...'}`}>
      <div className="health-status-dot" />
      <span className="health-status-text">
        {status === 'healthy' ? 'Healthy' : status === 'unhealthy' ? 'Offline' : 'Checking...'}
      </span>
    </div>
  )
}

