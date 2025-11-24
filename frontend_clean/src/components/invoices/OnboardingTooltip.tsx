import { memo, useState, useEffect } from 'react'
import './OnboardingTooltip.css'

interface OnboardingTooltipProps {
  id: string
  title: string
  description: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  onDismiss?: () => void
  children: React.ReactNode
}

export const OnboardingTooltip = memo(function OnboardingTooltip({
  id,
  title,
  description,
  position = 'top',
  onDismiss,
  children,
}: OnboardingTooltipProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [hasSeen, setHasSeen] = useState(() => {
    return localStorage.getItem(`onboarding-${id}`) === 'true'
  })

  useEffect(() => {
    if (!hasSeen) {
      const timer = setTimeout(() => setIsVisible(true), 500)
      return () => clearTimeout(timer)
    }
  }, [hasSeen])

  const handleDismiss = () => {
    setIsVisible(false)
    setHasSeen(true)
    localStorage.setItem(`onboarding-${id}`, 'true')
    onDismiss?.()
  }

  if (hasSeen || !isVisible) {
    return <>{children}</>
  }

  return (
    <div className="onboarding-tooltip-wrapper">
      {children}
      <div className={`onboarding-tooltip onboarding-tooltip-${position}`}>
        <div className="onboarding-tooltip-header">
          <h3 className="onboarding-tooltip-title">{title}</h3>
          <button
            className="onboarding-tooltip-close"
            onClick={handleDismiss}
            aria-label="Dismiss"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <p className="onboarding-tooltip-description">{description}</p>
        <button className="onboarding-tooltip-action" onClick={handleDismiss}>
          Got it
        </button>
      </div>
    </div>
  )
})

