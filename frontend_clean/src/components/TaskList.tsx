import React, { useState, useEffect } from 'react'

type TaskStatus = 'pending' | 'running' | 'done' | 'failed'
type TaskType = 'READ' | 'GREP' | 'SEARCH' | 'TRACE' | 'ANALYZE'

interface AgentTask {
  id: string
  title: string
  type: TaskType
  status: TaskStatus
  progress?: number
  startedAt?: number
  endedAt?: number
  durationMs?: number
  note?: string
}

interface PhaseProgress {
  reads: { current: number; total: number }
  greps: { current: number; total: number }
  searches: { current: number; total: number }
  traces: { current: number; total: number }
}

interface TaskListProps {
  tasks: AgentTask[]
  phaseProgress: PhaseProgress
  aliveTs: number | null
  lastActivityTs: number | null
  taskSummary: {
    tasks_total: number
    completed: number
    failed: number
    duration_ms: number
  } | null
  isCollapsed?: boolean
}

export function TaskList({
  tasks,
  phaseProgress,
  aliveTs,
  lastActivityTs,
  taskSummary,
  isCollapsed: initialCollapsed = false,
}: TaskListProps) {
  const [isCollapsed, setIsCollapsed] = useState(initialCollapsed)
  const [isPulsing, setIsPulsing] = useState(false)

  // Pulse animation for heartbeat
  useEffect(() => {
    if (aliveTs) {
      setIsPulsing(true)
      const timer = setTimeout(() => setIsPulsing(false), 300)
      return () => clearTimeout(timer)
    }
  }, [aliveTs])

  const getStatusIcon = (task: AgentTask) => {
    switch (task.status) {
      case 'pending':
        return <span className="task-icon-pending">○</span>
      case 'running':
        return (
          <span className="task-icon-running">
            <span className="spinner">⟳</span>
            {task.progress !== undefined && task.progress > 0 && (
              <span className="progress-text">{task.progress}%</span>
            )}
          </span>
        )
      case 'done':
        return <span className="task-icon-done">✓</span>
      case 'failed':
        return (
          <span className="task-icon-failed" title={task.note || 'Failed'}>
            ×
          </span>
        )
      default:
        return <span>○</span>
    }
  }

  const formatDuration = (ms?: number) => {
    if (!ms) return ''
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  const formatSummaryDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    const seconds = ms / 1000
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = seconds / 60
    return `${minutes.toFixed(1)}m`
  }

  const hasActiveTasks = tasks.some((t) => t.status === 'running' || t.status === 'pending')
  const isDone = taskSummary !== null

  return (
    <div className="task-list-container">
      <div
        className="task-list-header"
        onClick={() => setIsCollapsed(!isCollapsed)}
        style={{ cursor: 'pointer', userSelect: 'none' }}
      >
        <span className="task-list-title">
          Agent Tasks {isDone && `(${taskSummary.completed}/${taskSummary.tasks_total})`}
        </span>
        <span className="task-list-toggle">{isCollapsed ? '▼' : '▲'}</span>
      </div>

      {!isCollapsed && (
        <div className="task-list-content">
          {/* Heartbeat indicator */}
          {aliveTs && (
            <div className="heartbeat-indicator">
              <span className={`heartbeat-dot ${isPulsing ? 'pulsing' : ''}`}></span>
              <span className="heartbeat-text">Agent alive</span>
            </div>
          )}

          {/* Phase progress meters */}
          {(phaseProgress.reads.total > 0 ||
            phaseProgress.greps.total > 0 ||
            phaseProgress.searches.total > 0 ||
            phaseProgress.traces.total > 0) && (
            <div className="phase-progress">
              {phaseProgress.reads.total > 0 && (
                <div className="phase-meter">
                  reads {phaseProgress.reads.current}/{phaseProgress.reads.total}
                </div>
              )}
              {phaseProgress.greps.total > 0 && (
                <div className="phase-meter">
                  greps {phaseProgress.greps.current}/{phaseProgress.greps.total}
                </div>
              )}
              {phaseProgress.searches.total > 0 && (
                <div className="phase-meter">
                  searches {phaseProgress.searches.current}/{phaseProgress.searches.total}
                </div>
              )}
              {phaseProgress.traces.total > 0 && (
                <div className="phase-meter">
                  traces {phaseProgress.traces.current}/{phaseProgress.traces.total}
                </div>
              )}
            </div>
          )}

          {/* Task list */}
          <div className="task-items">
            {tasks.map((task) => (
              <div key={task.id} className={`task-item task-${task.status}`}>
                <div className="task-status-icon">{getStatusIcon(task)}</div>
                <div className="task-details">
                  <div className="task-title">{task.title}</div>
                  {task.durationMs && task.status !== 'running' && (
                    <div className="task-duration">{formatDuration(task.durationMs)}</div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Summary on done */}
          {isDone && taskSummary && (
            <div className="task-summary">
              {taskSummary.completed}/{taskSummary.tasks_total} completed
              {taskSummary.failed > 0 && ` • ${taskSummary.failed} failed`} •{' '}
              {formatSummaryDuration(taskSummary.duration_ms)}
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .task-list-container {
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          margin: 8px 0;
          background: #f9f9f9;
        }

        .task-list-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: #f0f0f0;
          border-bottom: 1px solid #e0e0e0;
          font-weight: 500;
          font-size: 13px;
        }

        .task-list-title {
          flex: 1;
        }

        .task-list-toggle {
          font-size: 10px;
          color: #666;
        }

        .task-list-content {
          padding: 8px 12px;
        }

        .heartbeat-indicator {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
          font-size: 12px;
          color: #666;
        }

        .heartbeat-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #4caf50;
          display: inline-block;
        }

        .heartbeat-dot.pulsing {
          animation: pulse 1s ease-in-out;
        }

        @keyframes pulse {
          0%,
          100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.5;
            transform: scale(1.2);
          }
        }

        .heartbeat-text {
          font-size: 11px;
        }

        .phase-progress {
          display: flex;
          gap: 12px;
          margin-bottom: 8px;
          font-size: 11px;
          color: #666;
          flex-wrap: wrap;
        }

        .phase-meter {
          padding: 2px 6px;
          background: #e8e8e8;
          border-radius: 3px;
        }

        .task-items {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .task-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 4px 0;
          font-size: 12px;
        }

        .task-status-icon {
          width: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .task-icon-pending {
          color: #999;
          font-size: 14px;
        }

        .task-icon-running {
          display: flex;
          align-items: center;
          gap: 4px;
          color: #2196f3;
        }

        .spinner {
          animation: spin 1s linear infinite;
          font-size: 14px;
        }

        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        .progress-text {
          font-size: 10px;
        }

        .task-icon-done {
          color: #4caf50;
          font-size: 16px;
          font-weight: bold;
        }

        .task-icon-failed {
          color: #f44336;
          font-size: 16px;
          font-weight: bold;
          cursor: help;
        }

        .task-details {
          flex: 1;
        }

        .task-title {
          font-size: 12px;
          color: #333;
        }

        .task-duration {
          font-size: 10px;
          color: #666;
          margin-top: 2px;
        }

        .task-summary {
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid #e0e0e0;
          font-size: 11px;
          color: #666;
          text-align: center;
        }
      `}</style>
    </div>
  )
}

