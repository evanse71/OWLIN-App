/**
 * Notification Stack Component
 * Floating bottom-right notifications with color coding and gentle timeouts
 */

import { useState, useEffect, useCallback } from 'react'
import { X, Info, CheckCircle2, AlertCircle } from 'lucide-react'
import './NotificationStack.css'

export type NotificationType = 'info' | 'success' | 'error'

export interface Notification {
  id: string
  type: NotificationType
  message: string
  duration?: number // milliseconds, default 5000
}

interface NotificationStackProps {
  notifications?: Notification[]
}

// Global notification state
let notificationListeners: Array<(notifications: Notification[]) => void> = []
let currentNotifications: Notification[] = []

export function addNotification(notification: Omit<Notification, 'id'>) {
  const id = `notification-${Date.now()}-${Math.random()}`
  const newNotification: Notification = {
    ...notification,
    id,
    duration: notification.duration || 5000,
  }
  currentNotifications = [...currentNotifications, newNotification]
  notificationListeners.forEach((listener) => listener([...currentNotifications]))
}

export function removeNotification(id: string) {
  currentNotifications = currentNotifications.filter((n) => n.id !== id)
  notificationListeners.forEach((listener) => listener([...currentNotifications]))
}

export function NotificationStack({ notifications: externalNotifications }: NotificationStackProps) {
  const [notifications, setNotifications] = useState<Notification[]>(
    externalNotifications || currentNotifications
  )

  useEffect(() => {
    if (externalNotifications) {
      setNotifications(externalNotifications)
      return
    }

    // Subscribe to global notifications
    const listener = (newNotifications: Notification[]) => {
      setNotifications(newNotifications)
    }
    notificationListeners.push(listener)
    setNotifications([...currentNotifications])

    return () => {
      notificationListeners = notificationListeners.filter((l) => l !== listener)
    }
  }, [externalNotifications])

  const handleDismiss = useCallback((id: string) => {
    if (externalNotifications) {
      // If using external notifications, just update local state
      setNotifications((prev) => prev.filter((n) => n.id !== id))
    } else {
      removeNotification(id)
    }
  }, [externalNotifications])

  useEffect(() => {
    notifications.forEach((notification) => {
      if (notification.duration && notification.duration > 0) {
        const timer = setTimeout(() => {
          handleDismiss(notification.id)
        }, notification.duration)

        return () => clearTimeout(timer)
      }
    })
  }, [notifications, handleDismiss])

  const getIcon = (type: NotificationType) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 size={18} />
      case 'error':
        return <AlertCircle size={18} />
      default:
        return <Info size={18} />
    }
  }

  if (notifications.length === 0) {
    return null
  }

  return (
    <div className="notification-stack">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`notification notification-${notification.type}`}
          style={{
            animation: 'slideInRight 300ms ease',
          }}
        >
          <div className="notification-icon">{getIcon(notification.type)}</div>
          <div className="notification-content">
            <div className="notification-message">{notification.message}</div>
          </div>
          <button
            className="notification-dismiss"
            onClick={() => handleDismiss(notification.id)}
            aria-label="Dismiss notification"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  )
}

