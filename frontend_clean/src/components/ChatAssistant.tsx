import { useState, useRef, useEffect } from 'react'
import { ChatMessage } from './ChatMessage'
import { TaskList } from './TaskList'
import { API_BASE_URL } from '../lib/config'

interface Message {
  role: 'user' | 'assistant'
  content: string
  codeReferences?: Array<{
    file: string
    lines?: number[]
    snippet: string
  }>
  error?: boolean
  retryable?: boolean
  requiresOllama?: boolean
  explorationMode?: boolean
  explorationMetadata?: {
    mode?: string
    files_searched?: number
    files_read?: string[]
    searches_executed?: number
    search_terms?: string[]
    findings_count?: number
    exploration_time?: number
    timed_out?: boolean
  }
}

// Token size options
const TOKEN_SIZE_OPTIONS = [
  { value: 10000, label: 'Small (10k)', description: 'Quick questions' },
  { value: 16000, label: 'Medium (16k)', description: 'Standard questions' },
  { value: 32000, label: 'Large (32k)', description: 'Complex debugging' },
  { value: 64000, label: 'XL (64k)', description: 'Multi-file analysis' },
  { value: 100000, label: 'XXL (100k)', description: 'Large codebase review' },
  { value: 128000, label: 'Maximum (128k)', description: 'Full codebase analysis (default)' },
  { value: 200000, label: 'Ultra (200k)', description: 'Extreme analysis (if model supports)' },
]

export function ChatAssistant() {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isPinned, setIsPinned] = useState(true) // Pinned = fixed position, unpinned = draggable
  const [position, setPosition] = useState({ x: 0, y: 0 }) // Position when unpinned
  const [size, setSize] = useState({ width: 400, height: 600 }) // Resizable dimensions
  const [isDragging, setIsDragging] = useState(false)
  const [isResizing, setIsResizing] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0 })
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [ollamaAvailable, setOllamaAvailable] = useState(false)
  const [currentModel, setCurrentModel] = useState<string>('Unknown')
  // const [availableModels, setAvailableModels] = useState<string[]>([]) // Unused for now
  const [lastUserMessage, setLastUserMessage] = useState<string>('')
  const [useSearchMode, setUseSearchMode] = useState<boolean>(false)
  const [useAgentMode, setUseAgentMode] = useState<boolean>(false)
  const [explorationProgress, setExplorationProgress] = useState<{
    message: string
    current: number
    total: number
    percentage: number
  } | null>(null)
  const [agentTasks, setAgentTasks] = useState<Array<{
    id: string
    title: string
    type: 'READ' | 'GREP' | 'SEARCH' | 'TRACE' | 'ANALYZE'
    status: 'pending' | 'running' | 'done' | 'failed'
    progress?: number
    startedAt?: number
    endedAt?: number
    durationMs?: number
    note?: string
  }>>([])
  const [showTaskList, setShowTaskList] = useState(false)
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null)
  const [phaseProgress, setPhaseProgress] = useState<{
    reads: { current: number; total: number }
    greps: { current: number; total: number }
    searches: { current: number; total: number }
    traces: { current: number; total: number }
  }>({
    reads: { current: 0, total: 0 },
    greps: { current: 0, total: 0 },
    searches: { current: 0, total: 0 },
    traces: { current: 0, total: 0 },
  })
  const [aliveTs, setAliveTs] = useState<number | null>(null)
  const [lastActivityTs, setLastActivityTs] = useState<number | null>(null)
  const [taskSummary, setTaskSummary] = useState<{
    tasks_total: number
    completed: number
    failed: number
    duration_ms: number
  } | null>(null)
  const [currentTaskActivity, setCurrentTaskActivity] = useState<string | null>(null)
  const [contextSize, setContextSize] = useState<number>(() => {
    // Load from localStorage or default to 32k (better for local models performance)
    const saved = localStorage.getItem('chat_context_size')
    return saved ? parseInt(saved, 10) : 32000
  })
  const [showExplorerTooltip, setShowExplorerTooltip] = useState(false)
  const [showMultiTurnTooltip, setShowMultiTurnTooltip] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const resizeHandleRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Check Ollama status on mount
  useEffect(() => {
    checkStatus()
  }, [])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (isExpanded && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isExpanded])

  // Focus input when expanded
  useEffect(() => {
    if (isExpanded && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isExpanded])

  // Handle pin/unpin toggle
  const handlePinToggle = () => {
    if (isPinned) {
      // Unpin: allow dragging
      setIsPinned(false)
    } else {
      // Pin: reset to bottom right corner
      setIsPinned(true)
      setPosition({ x: 0, y: 0 })
    }
  }

  // Drag handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!isExpanded || isPinned) return
    if ((e.target as HTMLElement).closest('button, input, select, textarea')) return
    
    setIsDragging(true)
    const rect = containerRef.current?.getBoundingClientRect()
    if (rect) {
      setDragStart({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      })
    }
    e.preventDefault()
  }

  // Resize handlers
  const handleResizeStart = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsResizing(true)
    setResizeStart({
      x: e.clientX,
      y: e.clientY,
      width: size.width,
      height: size.height,
    })
  }

  // Mouse move/up effect for drag and resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && !isPinned && containerRef.current) {
        const newX = e.clientX - dragStart.x
        const newY = e.clientY - dragStart.y
        
        // Keep within viewport bounds
        const maxX = window.innerWidth - size.width
        const maxY = window.innerHeight - size.height
        
        setPosition({
          x: Math.max(0, Math.min(newX, maxX)),
          y: Math.max(0, Math.min(newY, maxY)),
        })
      }
      
      if (isResizing && containerRef.current) {
        const deltaX = e.clientX - resizeStart.x
        const deltaY = e.clientY - resizeStart.y
        
        const newWidth = Math.max(300, Math.min(800, resizeStart.width + deltaX))
        const newHeight = Math.max(400, Math.min(window.innerHeight - 100, resizeStart.height + deltaY))
        
        setSize({ width: newWidth, height: newHeight })
        
        // Adjust position if resizing would push it out of bounds
        if (!isPinned) {
          const maxX = window.innerWidth - newWidth
          const maxY = window.innerHeight - newHeight
          setPosition(prev => ({
            x: Math.min(prev.x, maxX),
            y: Math.min(prev.y, maxY),
          }))
        }
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      setIsResizing(false)
    }

    if (isDragging || isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, isResizing, isPinned, dragStart, resizeStart, size])

  const checkStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/status`)
      if (response.ok) {
        const data = await response.json()
        setOllamaAvailable(data.ollama_available || false)
        setCurrentModel(data.primary_model || 'Unknown')
        // setAvailableModels(data.available_models || []) // Unused for now
      }
    } catch (error) {
      console.error('Failed to check chat status:', error)
    }
  }

  const handleContextSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSize = parseInt(e.target.value, 10)
    setContextSize(newSize)
    localStorage.setItem('chat_context_size', newSize.toString())
  }

  const handleInputFocus = () => {
    if (!isExpanded) {
      setIsExpanded(true)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value)
  }

  // Format time helper
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    if (minutes > 0) {
      return `${minutes}m ${secs}s`
    }
    return `${secs}s`
  }

  // Format duration helper
  const formatDuration = (seconds: number): string => {
    if (seconds < 1) {
      return `${(seconds * 1000).toFixed(0)}ms`
    }
    return `${seconds.toFixed(1)}s`
  }

  // Task List Component
  const TaskListComponent = () => {
    if (!showTaskList || agentTasks.length === 0) return null
    
    const completedCount = agentTasks.filter(t => t.status === 'done' || t.status === 'completed').length
    const failedCount = agentTasks.filter(t => t.status === 'failed').length
    const runningTask = agentTasks.find(t => t.status === 'running')
    const totalCount = agentTasks.length
    
    return (
      <div style={{
        margin: '12px 0',
        padding: '16px',
        background: 'rgba(59, 130, 246, 0.05)',
        borderRadius: '12px',
        border: '1px solid rgba(59, 130, 246, 0.15)',
        fontSize: '13px',
        boxShadow: '0 2px 8px rgba(59, 130, 246, 0.1)',
      }}>
        <div 
          onClick={() => setShowTaskList(!showTaskList)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            fontWeight: 600,
            color: '#1f2937',
            marginBottom: showTaskList ? '12px' : 0,
            padding: '4px 0',
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📋</span>
            <span>Agent Tasks ({completedCount}/{totalCount} completed)</span>
            {failedCount > 0 && (
              <span style={{ 
                color: '#ef4444', 
                marginLeft: '8px',
                fontSize: '12px',
                fontWeight: 500,
              }}>
                ⚠️ {failedCount} failed
              </span>
            )}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {timeRemaining !== null && (
              <span style={{ 
                fontSize: '12px', 
                color: '#6b7280',
                padding: '4px 8px',
                background: 'rgba(255, 255, 255, 0.6)',
                borderRadius: '6px',
              }}>
                ⏱️ {formatTime(timeRemaining)}
              </span>
            )}
            <span style={{ fontSize: '12px', color: '#6b7280' }}>
              {showTaskList ? '▼' : '▶'}
            </span>
          </div>
        </div>
        
        {showTaskList && (
          <div style={{ 
            marginTop: '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}>
            {agentTasks.map((task, idx) => {
              const isRunning = task.status === 'running'
              const isDone = task.status === 'done' || task.status === 'completed'
              const isFailed = task.status === 'failed'
              
              return (
                <div 
                  key={task.id || idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                    padding: '10px 12px',
                    fontSize: '13px',
                    background: isRunning 
                      ? 'rgba(59, 130, 246, 0.1)' 
                      : isDone
                      ? 'rgba(16, 185, 129, 0.05)'
                      : isFailed
                      ? 'rgba(239, 68, 68, 0.05)'
                      : 'rgba(255, 255, 255, 0.5)',
                    borderRadius: '8px',
                    border: isRunning 
                      ? '2px solid rgba(59, 130, 246, 0.3)' 
                      : isDone
                      ? '1px solid rgba(16, 185, 129, 0.2)'
                      : isFailed
                      ? '1px solid rgba(239, 68, 68, 0.2)'
                      : '1px solid rgba(0, 0, 0, 0.05)',
                    transition: 'all 0.3s ease',
                    animation: isRunning ? 'taskPulse 2s ease-in-out infinite' : 'none',
                    transform: isRunning ? 'scale(1.01)' : 'scale(1)',
                  }}
                >
                  <span style={{ 
                    minWidth: '24px',
                    fontSize: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    {isDone && '✅'}
                    {isRunning && (
                      <span style={{
                        display: 'inline-block',
                        animation: 'spin 1s linear infinite',
                      }}>⏳</span>
                    )}
                    {isFailed && '❌'}
                    {task.status === 'pending' && '⏸️'}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div style={{
                      fontWeight: isRunning ? 600 : 500,
                      color: isDone 
                        ? '#059669' 
                        : isFailed
                        ? '#ef4444'
                        : isRunning
                        ? '#3b82f6'
                        : '#6b7280',
                      marginBottom: '4px',
                    }}>
                      {task.title}
                    </div>
                    {task.durationMs && !isRunning && (
                      <div style={{ 
                        fontSize: '11px',
                        color: '#9ca3af',
                        marginTop: '2px',
                      }}>
                        ⏱️ {formatDuration(task.durationMs / 1000)}
                      </div>
                    )}
                    {isRunning && task.progress !== undefined && task.progress > 0 && (
                      <div style={{
                        marginTop: '6px',
                        height: '3px',
                        background: 'rgba(59, 130, 246, 0.2)',
                        borderRadius: '2px',
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          background: 'linear-gradient(90deg, #3b82f6, #60a5fa)',
                          width: `${task.progress}%`,
                          transition: 'width 0.3s ease',
                          borderRadius: '2px',
                        }} />
                      </div>
                    )}
                    {task.note && (
                      <div style={{ 
                        marginTop: '4px',
                        fontSize: '11px',
                        color: '#6b7280',
                        fontStyle: 'italic',
                      }}>
                        {task.note}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsLoading(false)
    setExplorationProgress(null)
    
    // Add a message indicating the operation was cancelled
    const cancelMessage: Message = {
      role: 'assistant',
      content: 'Operation cancelled by user.',
      error: false,
    }
    setMessages((prev) => [...prev, cancelMessage])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!inputValue.trim() || isLoading) return

    const userMessage = inputValue.trim()
    setInputValue('')
    setIsExpanded(true)

    // Store the message for retry
    setLastUserMessage(userMessage)

    // Add user message
    const newUserMessage: Message = {
      role: 'user',
      content: userMessage,
    }
    setMessages((prev) => [...prev, newUserMessage])
    setIsLoading(true)

    // Create AbortController for this request
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    try {
      // Build conversation history
      const conversationHistory = messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

      // Get context
      const context = {
        current_page: window.location.pathname,
        error_logs: true,
      }

      // Use streaming for Search or Agent mode, regular API otherwise
      if (useSearchMode || useAgentMode) {
        // Use SSE streaming for real-time progress
        if (!useAgentMode) {
          // Only show exploration progress for search mode, not agent mode
          setExplorationProgress({ message: 'Starting exploration...', current: 0, total: 4, percentage: 0 })
        } else {
          // For agent mode, clear exploration progress and show activity message instead
          setExplorationProgress(null)
          setCurrentTaskActivity('Analyzing your question and planning tasks...')
        }
        // Don't show task list by default - will auto-expand on first task update
        // Task list will be shown when plan event is received
        
        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            message: userMessage,
            conversation_history: conversationHistory,
            context,
            context_size: contextSize,
            use_search_mode: useSearchMode,
            use_agent_mode: useAgentMode,
          }),
          signal: abortController.signal,
        })

        if (!response.ok) {
          throw new Error(`Chat API error: ${response.statusText}`)
        }

        // Read SSE stream
        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        if (reader) {
          while (true) {
            // Check if aborted
            if (abortController.signal.aborted) {
              reader.cancel()
              break
            }
            
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || '' // Keep incomplete line in buffer

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))
                  
                  if (data.type === 'plan') {
                    // Plan event: set initial task list
                    const tasks = (data.tasks || []).map((t: any) => ({
                      id: t.id,
                      title: t.title,
                      type: t.type,
                      status: t.status || 'pending',
                      progress: 0,
                    }))
                    // Replace tasks (removes "Planning..." task when real tasks arrive)
                    setAgentTasks(tasks)
                    setShowTaskList(true) // Auto-expand task list when plan is received
                    // Update current activity
                    const runningTask = tasks.find((t: any) => t.status === 'running')
                    if (runningTask) {
                      // Build detailed activity text
                      let activityText = ''
                      const taskTitle = runningTask.title
                      
                      if (runningTask.type === 'READ') {
                        const match = taskTitle.match(/Reading\s+(.+)/i)
                        const filename = match ? match[1] : taskTitle.replace(/^[📖]\s*/, '')
                        activityText = `Reading file: ${filename}`
                      } else if (runningTask.type === 'GREP') {
                        const match = taskTitle.match(/Searching for ['"](.+?)['"]/i)
                        const pattern = match ? match[1] : taskTitle.replace(/^[🔍]\s*Searching for\s*/i, '')
                        activityText = `Searching codebase for: ${pattern}`
                      } else if (runningTask.type === 'SEARCH') {
                        const match = taskTitle.match(/Exploring ['"](.+?)['"]/i)
                        const term = match ? match[1] : taskTitle.replace(/^[🔎]\s*Exploring\s*/i, '')
                        activityText = `Exploring codebase: ${term}`
                      } else if (runningTask.type === 'TRACE') {
                        const traceInfo = taskTitle.replace(/^[🔗]\s*Tracing\s*/i, '')
                        activityText = `Tracing data flow: ${traceInfo}`
                      } else if (runningTask.type === 'ANALYZE') {
                        activityText = 'Analyzing findings and preparing response...'
                      } else {
                        activityText = taskTitle.replace(/^[📖🔍🔎🔗📊📋⚙️]\s*/, '')
                      }
                      
                      setCurrentTaskActivity(activityText)
                    } else if (tasks.length > 0) {
                      setCurrentTaskActivity(`Planning complete. Starting ${tasks.length} task${tasks.length > 1 ? 's' : ''}...`)
                    }
                  } else if (data.type === 'task_update') {
                    // Task update: update specific task
                    if (data.task) {
                      setAgentTasks((prev) => {
                        const updated = prev.map((task) =>
                          task.id === data.task.id
                            ? {
                                ...task,
                                status: data.task.status,
                                progress: data.task.progress ?? task.progress,
                                startedAt: data.task.started_at ?? task.startedAt,
                                endedAt: data.task.ended_at ?? task.endedAt,
                                durationMs: data.task.duration_ms ?? task.durationMs,
                                note: data.task.note ?? task.note,
                              }
                            : task
                        )
                        // Update current task activity message
                        const runningTask = updated.find(t => t.status === 'running')
                        if (runningTask) {
                          // Build more detailed activity text
                          let activityText = ''
                          const taskTitle = runningTask.title
                          const taskType = runningTask.type
                          
                          // Build activity message based on task type with more detail
                          if (taskType === 'READ') {
                            // Extract filename from title (e.g., "📖 Reading ocr_service.py")
                            const match = taskTitle.match(/Reading\s+(.+)/i)
                            const filename = match ? match[1] : taskTitle.replace(/^[📖]\s*/, '')
                            const phaseInfo = phaseProgress.reads.total > 0 
                              ? ` (${phaseProgress.reads.current + 1}/${phaseProgress.reads.total})`
                              : ''
                            activityText = `Reading file: ${filename}${phaseInfo}`
                            if (runningTask.progress && runningTask.progress > 0) {
                              activityText += ` • ${runningTask.progress}%`
                            }
                          } else if (taskType === 'GREP') {
                            // Extract pattern from title (e.g., "🔍 Searching for 'pattern'")
                            const match = taskTitle.match(/Searching for ['"](.+?)['"]/i) || 
                                         taskTitle.match(/Searching for (.+)/i)
                            const pattern = match ? match[1] : taskTitle.replace(/^[🔍]\s*Searching for\s*/i, '')
                            const phaseInfo = phaseProgress.greps.total > 0 
                              ? ` (${phaseProgress.greps.current + 1}/${phaseProgress.greps.total})`
                              : ''
                            activityText = `Searching codebase for: ${pattern}${phaseInfo}`
                            if (runningTask.progress && runningTask.progress > 0) {
                              activityText += ` • ${runningTask.progress}%`
                            }
                          } else if (taskType === 'SEARCH') {
                            // Extract term from title (e.g., "🔎 Exploring 'term'")
                            const match = taskTitle.match(/Exploring ['"](.+?)['"]/i) || 
                                         taskTitle.match(/Exploring (.+)/i)
                            const term = match ? match[1] : taskTitle.replace(/^[🔎]\s*Exploring\s*/i, '')
                            const phaseInfo = phaseProgress.searches.total > 0 
                              ? ` (${phaseProgress.searches.current + 1}/${phaseProgress.searches.total})`
                              : ''
                            activityText = `Exploring codebase: ${term}${phaseInfo}`
                            if (runningTask.progress && runningTask.progress > 0) {
                              activityText += ` • ${runningTask.progress}%`
                            }
                          } else if (taskType === 'TRACE') {
                            // Extract trace info from title (e.g., "🔗 Tracing start → end")
                            const traceInfo = taskTitle.replace(/^[🔗]\s*Tracing\s*/i, '')
                            const phaseInfo = phaseProgress.traces.total > 0 
                              ? ` (${phaseProgress.traces.current + 1}/${phaseProgress.traces.total})`
                              : ''
                            activityText = `Tracing data flow: ${traceInfo}${phaseInfo}`
                            if (runningTask.progress && runningTask.progress > 0) {
                              activityText += ` • ${runningTask.progress}%`
                            }
                          } else if (taskType === 'ANALYZE') {
                            activityText = 'Analyzing findings and preparing response...'
                            // Show how many tasks completed
                            const completedCount = updated.filter(t => t.status === 'done' || t.status === 'completed').length
                            const totalCount = updated.length
                            if (totalCount > 0) {
                              activityText += ` (${completedCount}/${totalCount} tasks completed)`
                            }
                          } else {
                            // Fallback: use title without emoji
                            activityText = taskTitle.replace(/^[📖🔍🔎🔗📊📋⚙️]\s*/, '')
                          }
                          
                          // Add note if available (e.g., "Found 5 matches")
                          if (runningTask.note) {
                            activityText += ` • ${runningTask.note}`
                          }
                          
                          setCurrentTaskActivity(activityText)
                        } else {
                          // Check if we're waiting for next task
                          const pendingTasks = updated.filter(t => t.status === 'pending')
                          const completedCount = updated.filter(t => t.status === 'done' || t.status === 'completed').length
                          const totalCount = updated.length
                          
                          if (pendingTasks.length > 0) {
                            // Show what's coming next
                            const nextTask = pendingTasks[0]
                            let nextTaskDesc = ''
                            
                            if (nextTask.type === 'READ') {
                              const match = nextTask.title.match(/Reading\s+(.+)/i)
                              const filename = match ? match[1] : nextTask.title.replace(/^[📖]\s*/, '')
                              nextTaskDesc = `Next: Reading ${filename}`
                            } else if (nextTask.type === 'GREP') {
                              const match = nextTask.title.match(/Searching for ['"](.+?)['"]/i)
                              const pattern = match ? match[1] : nextTask.title.replace(/^[🔍]\s*Searching for\s*/i, '')
                              nextTaskDesc = `Next: Searching for ${pattern}`
                            } else if (nextTask.type === 'SEARCH') {
                              const match = nextTask.title.match(/Exploring ['"](.+?)['"]/i)
                              const term = match ? match[1] : nextTask.title.replace(/^[🔎]\s*Exploring\s*/i, '')
                              nextTaskDesc = `Next: Exploring ${term}`
                            } else if (nextTask.type === 'TRACE') {
                              const traceInfo = nextTask.title.replace(/^[🔗]\s*Tracing\s*/i, '')
                              nextTaskDesc = `Next: Tracing ${traceInfo}`
                            } else {
                              nextTaskDesc = 'Preparing next task...'
                            }
                            
                            setCurrentTaskActivity(`${nextTaskDesc} (${completedCount}/${totalCount} completed)`)
                          } else if (totalCount > 0 && completedCount === totalCount) {
                            setCurrentTaskActivity('Finalizing response...')
                          } else {
                            setCurrentTaskActivity(null)
                          }
                        }
                        return updated
                      })
                      setLastActivityTs(Date.now())
                    }
                  } else if (data.type === 'progress') {
                    // Progress event: update phase counters and activity text
                    if (data.phase && data.current !== undefined && data.total !== undefined) {
                      setPhaseProgress((prev) => {
                        const updated = {
                          ...prev,
                          [data.phase]: {
                            current: data.current,
                            total: data.total,
                          },
                        }
                        
                        // Update activity text with phase progress if a task is running
                        setAgentTasks((currentTasks) => {
                          const runningTask = currentTasks.find(t => t.status === 'running')
                          if (runningTask) {
                            const phaseName = data.phase
                            const phaseCurrent = updated[phaseName].current
                            const phaseTotal = updated[phaseName].total
                            
                            // Rebuild activity text with updated phase info
                            let activityText = ''
                            const taskTitle = runningTask.title
                            
                            if (runningTask.type === 'READ') {
                              const match = taskTitle.match(/Reading\s+(.+)/i)
                              const filename = match ? match[1] : taskTitle.replace(/^[📖]\s*/, '')
                              activityText = `Reading file: ${filename} (${phaseCurrent + 1}/${phaseTotal})`
                            } else if (runningTask.type === 'GREP') {
                              const match = taskTitle.match(/Searching for ['"](.+?)['"]/i)
                              const pattern = match ? match[1] : taskTitle.replace(/^[🔍]\s*Searching for\s*/i, '')
                              activityText = `Searching codebase for: ${pattern} (${phaseCurrent + 1}/${phaseTotal})`
                            } else if (runningTask.type === 'SEARCH') {
                              const match = taskTitle.match(/Exploring ['"](.+?)['"]/i)
                              const term = match ? match[1] : taskTitle.replace(/^[🔎]\s*Exploring\s*/i, '')
                              activityText = `Exploring codebase: ${term} (${phaseCurrent + 1}/${phaseTotal})`
                            } else if (runningTask.type === 'TRACE') {
                              const traceInfo = taskTitle.replace(/^[🔗]\s*Tracing\s*/i, '')
                              activityText = `Tracing data flow: ${traceInfo} (${phaseCurrent + 1}/${phaseTotal})`
                            }
                            
                            if (activityText && runningTask.progress && runningTask.progress > 0) {
                              activityText += ` • ${runningTask.progress}%`
                            }
                            
                            if (runningTask.note) {
                              activityText += ` • ${runningTask.note}`
                            }
                            
                            if (activityText) {
                              setCurrentTaskActivity(activityText)
                            }
                          }
                          return currentTasks
                        })
                        
                        return updated
                      })
                    } else {
                      // Fallback to old progress format
                      setExplorationProgress({
                        message: data.message || 'Processing...',
                        current: data.current || 0,
                        total: data.total || 0,
                        percentage: data.percentage || 0,
                      })
                    }
                  } else if (data.type === 'agent_started') {
                    // Agent started: show task list immediately
                    setShowTaskList(true)
                    // Initialize with planning task if no tasks yet
                    if (agentTasks.length === 0) {
                      setAgentTasks([{
                        id: 'planning',
                        title: 'Planning tasks...',
                        type: 'ANALYZE',
                        status: 'running',
                        progress: 0,
                      }])
                      setCurrentTaskActivity('Analyzing your question and planning tasks...')
                    }
                  } else if (data.type === 'heartbeat') {
                    // Heartbeat: update alive timestamp
                    setAliveTs(data.ts || Date.now())
                  } else if (data.type === 'done') {
                    // Done event: freeze task list and show summary
                    setTaskSummary(data.summary || null)
                    setShowTaskList(true)
                    setCurrentTaskActivity('Finalizing response...')
                  } else if (data.type === 'tasks') {
                    // Legacy tasks event (fallback)
                    setAgentTasks(data.tasks || [])
                    setShowTaskList(true)
                  } else if (data.type === 'time_remaining') {
                    // Update time remaining
                    setTimeRemaining(data.seconds || null)
                  } else if (data.type === 'response') {
                    // Final response received
                    setExplorationProgress(null)
                    setCurrentTaskActivity(null) // Clear activity message
                    const assistantMessage: Message = {
                      role: 'assistant',
                      content: data.response,
                      codeReferences: data.code_references || [],
                      explorationMode: data.exploration_mode || false,
                      explorationMetadata: data.exploration_metadata || undefined,
                    }
                    setMessages((prev) => [...prev, assistantMessage])
                    
                    // Update Ollama status
                    if (data.ollama_available !== undefined) {
                      setOllamaAvailable(data.ollama_available)
                    }
                    
                    // Don't reset mode flags - let user control them
                  } else if (data.type === 'error') {
                    setExplorationProgress(null)
                    // Stop heartbeat indicator
                    setAliveTs(null)
                    const errorMessage: Message = {
                      role: 'assistant',
                      content: data.message || 'An error occurred during exploration.',
                      error: true,
                      retryable: true,
                    }
                    setMessages((prev) => [...prev, errorMessage])
                    // Don't reset mode flags on error - let user control them
                  }
                } catch (e) {
                  console.error('Error parsing SSE data:', e)
                }
              }
            }
          }
        }
      } else {
        // Regular non-streaming API call
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage,
            conversation_history: conversationHistory,
            context,
            context_size: contextSize,
            use_search_mode: useSearchMode,
            use_agent_mode: useAgentMode,
          }),
          signal: abortController.signal,
        })

        if (!response.ok) {
          throw new Error(`Chat API error: ${response.statusText}`)
        }

        const data = await response.json()

        // Check if this is an error response
        if (data.error || data.requires_ollama) {
          const errorMessage: Message = {
            role: 'assistant',
            content: data.response || 'Ollama is not available. Please start Ollama and try again.',
            error: true,
            retryable: data.retryable || false,
            requiresOllama: data.requires_ollama || false,
          }
          setMessages((prev) => [...prev, errorMessage])
          
          // Log diagnostics URL for debugging
          console.log('Ollama connection failed. Check diagnostics at:', `${API_BASE_URL}/api/chat/diagnose`)
        } else {
          // Add assistant message
          const assistantMessage: Message = {
            role: 'assistant',
            content: data.response,
            codeReferences: data.code_references || [],
            explorationMode: data.exploration_mode || false,
            explorationMetadata: data.exploration_metadata || undefined,
          }
          setMessages((prev) => [...prev, assistantMessage])
          
          // Update Ollama status
          if (data.ollama_available !== undefined) {
            setOllamaAvailable(data.ollama_available)
          }
          
          // Don't reset mode flags - let user control them
        }
      }
    } catch (error) {
      // Don't show error if it was aborted by user
      if (error instanceof Error && error.name === 'AbortError') {
        // Already handled in handleStop
        return
      }
      
      console.error('Chat error:', error)
      setExplorationProgress(null)
      const errorMessage: Message = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
        error: true,
        retryable: true,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      setExplorationProgress(null)
      abortControllerRef.current = null
    }
  }

  const handleRetry = async () => {
    if (!lastUserMessage.trim() || isLoading) return

    setIsLoading(true)

    try {
      // Get current messages and build conversation history (excluding error messages)
      let conversationHistory: Array<{ role: string; content: string }> = []
      setMessages((prev) => {
        // Filter out error messages for conversation history
        conversationHistory = prev
          .filter((msg) => !msg.error)
          .map((msg) => ({
            role: msg.role,
            content: msg.content,
          }))
        
        // Remove the last error message if it exists
        const newMessages = [...prev]
        if (newMessages.length > 0 && newMessages[newMessages.length - 1].error) {
          newMessages.pop()
          return newMessages
        }
        return prev
      })

      // Get context
      const context = {
        current_page: window.location.pathname,
        error_logs: true,
      }

      // Call chat API with the last user message
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: lastUserMessage,
          conversation_history: conversationHistory,
          context,
          context_size: contextSize,
        }),
      })

      if (!response.ok) {
        throw new Error(`Chat API error: ${response.statusText}`)
      }

      const data = await response.json()

      // Check if this is an error response
      if (data.error || data.requires_ollama) {
        const errorMessage: Message = {
          role: 'assistant',
          content: data.response || 'Ollama is not available. Please start Ollama and try again.',
          error: true,
          retryable: data.retryable || false,
          requiresOllama: data.requires_ollama || false,
        }
        setMessages((prev) => [...prev, errorMessage])
      } else {
        // Add assistant message
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.response,
          codeReferences: data.code_references || [],
        }
        setMessages((prev) => [...prev, assistantMessage])
      }

      // Update Ollama status
      if (data.ollama_available !== undefined) {
        setOllamaAvailable(data.ollama_available)
      }
    } catch (error) {
      console.error('Chat retry error:', error)
      const errorMessage: Message = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
        error: true,
        retryable: true,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleMinimize = () => {
    setIsExpanded(false)
  }

  // Header state (compact input box) - Glassmorphism style
  if (!isExpanded) {
    return (
      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          width: '320px',
          height: '48px',
          position: 'fixed',
          top: '24px',
          right: '24px',
          zIndex: 999,
          padding: '4px',
          background: 'rgba(255, 255, 255, 0.7)',
          backdropFilter: 'blur(20px) saturate(180%)',
          WebkitBackdropFilter: 'blur(20px) saturate(180%)',
          borderRadius: '24px',
          border: '1px solid rgba(255, 255, 255, 0.3)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.6)',
        }}
      >
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onFocus={handleInputFocus}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your code..."
          disabled={isLoading}
          style={{
            flex: 1,
            height: '100%',
            padding: '0 16px',
            border: 'none',
            borderRadius: '20px',
            fontSize: '14px',
            outline: 'none',
            background: 'transparent',
            color: '#1f2937',
            fontWeight: 400,
          }}
        />
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            border: 'none',
            background: isLoading || !inputValue.trim() 
              ? 'linear-gradient(135deg, rgba(156, 163, 175, 0.6), rgba(107, 114, 128, 0.6))'
              : 'linear-gradient(135deg, rgba(59, 130, 246, 0.9), rgba(37, 99, 235, 0.9))',
            color: '#fff',
            cursor: isLoading || !inputValue.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: isLoading || !inputValue.trim() 
              ? 'none'
              : '0 4px 12px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
            transform: 'scale(1)',
          }}
          onMouseEnter={(e) => {
            if (!isLoading && inputValue.trim()) {
              e.currentTarget.style.transform = 'scale(1.05)'
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)'
          }}
        >
          {isLoading ? '⏳' : '→'}
        </button>
      </form>
    )
  }

  // Expanded state (bottom-right panel or draggable)
  const defaultStyle = isPinned
    ? {
        bottom: '20px',
        right: '20px',
        top: 'auto',
        left: 'auto',
      }
    : {
        top: `${position.y}px`,
        left: `${position.x}px`,
        bottom: 'auto',
        right: 'auto',
      }

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      style={{
        position: 'fixed',
        ...defaultStyle,
        width: `${size.width}px`,
        height: `${size.height}px`,
        maxHeight: `${size.height}px`,
        background: 'rgba(255, 255, 255, 0.75)',
        backdropFilter: 'blur(40px) saturate(180%)',
        WebkitBackdropFilter: 'blur(40px) saturate(180%)',
        borderRadius: '24px',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.6)',
        border: '1px solid rgba(255, 255, 255, 0.3)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1000,
        cursor: isDragging ? 'grabbing' : (isPinned ? 'default' : 'grab'),
        userSelect: isDragging ? 'none' : 'auto',
        overflow: 'hidden',
      }}
    >
      {/* Header with glass effect */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(0, 0, 0, 0.06)',
          background: 'linear-gradient(to bottom, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.7))',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: '24px 24px 0 0',
          cursor: isPinned ? 'default' : 'grab',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div>
            <div style={{ 
              fontWeight: 600, 
              fontSize: '15px', 
              color: '#1f2937',
              letterSpacing: '-0.01em',
            }}>
              Code Assistant
            </div>
            {ollamaAvailable && currentModel !== 'Unknown' ? (
              <div style={{ 
                fontSize: '11px', 
                color: '#10b981', 
                marginTop: '6px',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 8px',
                background: 'rgba(16, 185, 129, 0.1)',
                borderRadius: '6px',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                width: 'fit-content',
              }}>
                <span style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: '#10b981',
                  display: 'inline-block',
                  boxShadow: '0 0 8px rgba(16, 185, 129, 0.8), 0 0 16px rgba(16, 185, 129, 0.4)',
                  animation: 'pulse 2s ease-in-out infinite',
                }} />
                <span style={{ fontWeight: 600 }}>{currentModel}</span>
                <span style={{ opacity: 0.7 }}>•</span>
                <span>{contextSize / 1000}k context</span>
              </div>
            ) : (
              <div style={{ 
                fontSize: '11px', 
                color: '#6b7280', 
                marginTop: '6px',
                fontWeight: 400,
                padding: '4px 8px',
                background: 'rgba(107, 114, 128, 0.1)',
                borderRadius: '6px',
                border: '1px solid rgba(107, 114, 128, 0.2)',
                width: 'fit-content',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}>
                <span style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: '#9ca3af',
                  display: 'inline-block',
                }} />
                Code reading mode (Ollama optional)
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            {/* Pin/Unpin button */}
            <button
              onClick={handlePinToggle}
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '8px',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                background: 'rgba(255, 255, 255, 0.6)',
                backdropFilter: 'blur(10px)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '13px',
                color: '#6b7280',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.9)'
                e.currentTarget.style.transform = 'scale(1.05)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.6)'
                e.currentTarget.style.transform = 'scale(1)'
              }}
              title={isPinned ? 'Unpin to move' : 'Pin to bottom right'}
            >
              {isPinned ? '📌' : '📍'}
            </button>
            {/* Minimize button */}
            <button
              onClick={handleMinimize}
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '8px',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                background: 'rgba(255, 255, 255, 0.6)',
                backdropFilter: 'blur(10px)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '16px',
                color: '#6b7280',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.9)'
                e.currentTarget.style.transform = 'scale(1.05)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.6)'
                e.currentTarget.style.transform = 'scale(1)'
              }}
              title="Minimize"
            >
              −
            </button>
          </div>
        </div>
        {/* Token Size Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <label
            htmlFor="context-size-select"
            style={{
              fontSize: '11px',
              color: '#6b7280',
              fontWeight: 500,
            }}
          >
            Context:
          </label>
          <select
            id="context-size-select"
            value={contextSize}
            onChange={handleContextSizeChange}
            disabled={isLoading}
            style={{
              flex: 1,
              padding: '6px 12px',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              borderRadius: '10px',
              fontSize: '12px',
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px)',
              color: '#1f2937',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              outline: 'none',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              if (!isLoading) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.95)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.8)'
            }}
            title="Select context window size"
          >
            {TOKEN_SIZE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label} - {option.description}
              </option>
            ))}
          </select>
        </div>
        
        {/* Exploration Controls */}
        <div style={{ 
          display: 'flex', 
          gap: '8px', 
          alignItems: 'center',
          padding: '8px 12px',
          background: 'rgba(255, 255, 255, 0.4)',
          backdropFilter: 'blur(10px)',
          borderRadius: '10px',
          border: '1px solid rgba(0, 0, 0, 0.05)',
          position: 'relative',
        }}>
          {/* Search Mode Button with Tooltip */}
          <div style={{ flex: 1, position: 'relative' }}>
            <button
              type="button"
              onClick={() => setUseSearchMode(!useSearchMode)}
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '8px 14px',
                border: `1px solid ${useSearchMode ? 'rgba(59, 130, 246, 0.4)' : 'rgba(0, 0, 0, 0.08)'}`,
                borderRadius: '10px',
                fontSize: '12px',
                background: useSearchMode 
                  ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.2))'
                  : 'rgba(255, 255, 255, 0.7)',
                backdropFilter: 'blur(10px)',
                color: useSearchMode ? '#1e40af' : '#6b7280',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontWeight: useSearchMode ? 600 : 500,
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                boxShadow: useSearchMode ? '0 2px 8px rgba(59, 130, 246, 0.2)' : 'none',
              }}
              onMouseEnter={(e) => {
                if (!isLoading) {
                  e.currentTarget.style.transform = 'scale(1.02)'
                  e.currentTarget.style.background = useSearchMode
                    ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(37, 99, 235, 0.25))'
                    : 'rgba(255, 255, 255, 0.9)'
                  e.currentTarget.style.boxShadow = useSearchMode 
                    ? '0 4px 12px rgba(59, 130, 246, 0.3)'
                    : '0 2px 8px rgba(0, 0, 0, 0.1)'
                  setShowExplorerTooltip(true)
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)'
                e.currentTarget.style.background = useSearchMode
                  ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.2))'
                  : 'rgba(255, 255, 255, 0.7)'
                e.currentTarget.style.boxShadow = useSearchMode ? '0 2px 8px rgba(59, 130, 246, 0.2)' : 'none'
                setShowExplorerTooltip(false)
              }}
            >
              <span style={{ fontSize: '14px' }}>🔍</span>
              Search
            </button>
            {/* Tooltip for Search Mode */}
            {showExplorerTooltip && (
            <div
              style={{
                position: 'absolute',
                bottom: '100%',
                left: '50%',
                transform: 'translateX(-50%)',
                marginBottom: '8px',
                padding: '10px 14px',
                background: 'rgba(15, 23, 42, 0.95)',
                backdropFilter: 'blur(20px)',
                color: '#f8fafc',
                fontSize: '12px',
                borderRadius: '10px',
                pointerEvents: 'none',
                transition: 'opacity 0.2s, transform 0.2s',
                transformOrigin: 'bottom',
                zIndex: 10000,
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                maxWidth: '280px',
                whiteSpace: 'normal',
                textAlign: 'left',
              }}
              onMouseEnter={() => setShowExplorerTooltip(true)}
              onMouseLeave={() => setShowExplorerTooltip(false)}
            >
              <div style={{ fontWeight: 600, marginBottom: '4px', color: '#60a5fa' }}>
                🔍 Search Mode
              </div>
              <div style={{ fontSize: '11px', lineHeight: '1.5', color: '#cbd5e1' }}>
                Comprehensive information gathering. Searches your codebase extensively, reads relevant files, and provides a detailed summary of what exists. Perfect for discovering code and understanding structure.
              </div>
            </div>
            )}
          </div>
          
          {/* Agent Mode Button with Tooltip */}
          <div style={{ flex: 1, position: 'relative' }}>
            <button
              type="button"
              onClick={() => setUseAgentMode(!useAgentMode)}
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '8px 14px',
                border: `1px solid ${useAgentMode ? 'rgba(16, 185, 129, 0.4)' : 'rgba(0, 0, 0, 0.08)'}`,
                borderRadius: '10px',
                fontSize: '12px',
                background: useAgentMode
                  ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2))'
                  : 'rgba(255, 255, 255, 0.7)',
                backdropFilter: 'blur(10px)',
                color: useAgentMode ? '#065f46' : '#6b7280',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontWeight: useAgentMode ? 600 : 500,
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                boxShadow: useAgentMode ? '0 2px 8px rgba(16, 185, 129, 0.2)' : 'none',
              }}
              onMouseEnter={(e) => {
                if (!isLoading) {
                  e.currentTarget.style.transform = 'scale(1.02)'
                  e.currentTarget.style.background = useAgentMode
                    ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(5, 150, 105, 0.25))'
                    : 'rgba(255, 255, 255, 0.9)'
                  e.currentTarget.style.boxShadow = useAgentMode
                    ? '0 4px 12px rgba(16, 185, 129, 0.3)'
                    : '0 2px 8px rgba(0, 0, 0, 0.1)'
                  setShowMultiTurnTooltip(true)
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)'
                e.currentTarget.style.background = useAgentMode
                  ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2))'
                  : 'rgba(255, 255, 255, 0.7)'
                e.currentTarget.style.boxShadow = useAgentMode ? '0 2px 8px rgba(16, 185, 129, 0.2)' : 'none'
                setShowMultiTurnTooltip(false)
              }}
            >
              <span style={{ fontSize: '14px' }}>🤖</span>
              Agent
            </button>
            {/* Tooltip for Agent Mode */}
            {showMultiTurnTooltip && (
            <div
              style={{
                position: 'absolute',
                bottom: '100%',
                left: '50%',
                transform: 'translateX(-50%)',
                marginBottom: '8px',
                padding: '10px 14px',
                background: 'rgba(15, 23, 42, 0.95)',
                backdropFilter: 'blur(20px)',
                color: '#f8fafc',
                fontSize: '12px',
                borderRadius: '10px',
                pointerEvents: 'none',
                transition: 'opacity 0.2s, transform 0.2s',
                transformOrigin: 'bottom',
                zIndex: 10000,
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                maxWidth: '280px',
                whiteSpace: 'normal',
                textAlign: 'left',
              }}
              onMouseEnter={() => setShowMultiTurnTooltip(true)}
              onMouseLeave={() => setShowMultiTurnTooltip(false)}
            >
              <div style={{ fontWeight: 600, marginBottom: '4px', color: '#34d399' }}>
                🤖 Agent Mode
              </div>
              <div style={{ fontSize: '11px', lineHeight: '1.5', color: '#cbd5e1' }}>
                Autonomous problem-solving agent. Breaks down problems into tasks, executes them sequentially, analyzes results, and provides solutions with root cause analysis and fixes. Perfect for debugging and problem-solving.
              </div>
            </div>
            )}
          </div>
        </div>
      </div>

      {/* Messages area with subtle gradient */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px',
          maxHeight: `${size.height - 200}px`,
          background: 'linear-gradient(to bottom, rgba(255, 255, 255, 0.5), rgba(249, 250, 251, 0.3))',
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              color: '#6b7280',
              fontSize: '14px',
              padding: '60px 20px',
            }}
          >
            <div style={{ 
              marginBottom: '16px', 
              fontSize: '64px',
              opacity: 0.5,
              filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1))',
            }}>💬</div>
            <div style={{ 
              fontWeight: 600, 
              fontSize: '18px',
              marginBottom: '8px',
              color: '#1f2937',
            }}>Ask me about your code!</div>
            <div style={{ 
              marginTop: '12px', 
              fontSize: '13px', 
              opacity: 0.7,
              marginBottom: '24px',
            }}>
              I can help you understand, debug, and explore your codebase.
            </div>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              maxWidth: '300px',
              margin: '0 auto',
            }}>
              <div
                onClick={() => {
                  setInputValue("Show me the upload code")
                  inputRef.current?.focus()
                }}
                style={{
                  padding: '10px 16px',
                  background: 'rgba(255, 255, 255, 0.6)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: '10px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  border: '1px solid rgba(0, 0, 0, 0.08)',
                  transition: 'all 0.2s',
                  textAlign: 'left',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.8)'
                  e.currentTarget.style.transform = 'translateX(4px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.6)'
                  e.currentTarget.style.transform = 'translateX(0)'
                }}
              >
                💡 "Show me the upload code"
              </div>
              <div
                onClick={() => {
                  setInputValue("Why did my upload fail?")
                  inputRef.current?.focus()
                }}
                style={{
                  padding: '10px 16px',
                  background: 'rgba(255, 255, 255, 0.6)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: '10px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  border: '1px solid rgba(0, 0, 0, 0.08)',
                  transition: 'all 0.2s',
                  textAlign: 'left',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.8)'
                  e.currentTarget.style.transform = 'translateX(4px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.6)'
                  e.currentTarget.style.transform = 'translateX(0)'
                }}
              >
                🔍 "Why did my upload fail?"
              </div>
              <div
                onClick={() => {
                  setInputValue("Find all API endpoints")
                  inputRef.current?.focus()
                }}
                style={{
                  padding: '10px 16px',
                  background: 'rgba(255, 255, 255, 0.6)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: '10px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  border: '1px solid rgba(0, 0, 0, 0.08)',
                  transition: 'all 0.2s',
                  textAlign: 'left',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.8)'
                  e.currentTarget.style.transform = 'translateX(4px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.6)'
                  e.currentTarget.style.transform = 'translateX(0)'
                }}
              >
                🚀 "Find all API endpoints"
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <ChatMessage
                key={index}
                role={message.role}
                content={message.content}
                codeReferences={message.codeReferences}
                error={message.error}
                retryable={message.retryable}
                requiresOllama={message.requiresOllama}
                explorationMode={message.explorationMode}
                explorationMetadata={message.explorationMetadata}
                onRetry={message.error && message.retryable ? handleRetry : undefined}
              />
            ))}
            {/* Show current task activity as a temporary message (ChatGPT-style pulsing text) */}
            {isLoading && useAgentMode && (
              <div
                style={{
                  padding: '16px 20px',
                  margin: '12px 0',
                  background: 'transparent',
                  borderRadius: '12px',
                  fontSize: '14px',
                  color: '#6b7280',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  animation: 'fadeIn 0.3s ease-in',
                }}
              >
                {/* Pulsing dots animation (ChatGPT style) */}
                <div
                  style={{
                    display: 'flex',
                    gap: '4px',
                    alignItems: 'center',
                    flexShrink: 0,
                  }}
                >
                  <div
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: '#9ca3af',
                      animation: 'pulseDot 1.4s ease-in-out infinite',
                      animationDelay: '0s',
                    }}
                  />
                  <div
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: '#9ca3af',
                      animation: 'pulseDot 1.4s ease-in-out infinite',
                      animationDelay: '0.2s',
                    }}
                  />
                  <div
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: '#9ca3af',
                      animation: 'pulseDot 1.4s ease-in-out infinite',
                      animationDelay: '0.4s',
                    }}
                  />
                </div>
                {/* Activity text with subtle pulse */}
                <span
                  style={{
                    fontStyle: 'italic',
                    animation: 'textPulse 2s ease-in-out infinite',
                    color: '#6b7280',
                  }}
                >
                  {currentTaskActivity || 'Planning tasks...'}
                </span>
              </div>
            )}
            {/* Regular loading indicator (for normal and search modes) */}
            {isLoading && !useAgentMode && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  padding: '16px',
                  background: 'rgba(255, 255, 255, 0.6)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: '16px',
                  fontSize: '14px',
                  color: '#6b7280',
                  border: '1px solid rgba(0, 0, 0, 0.05)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      width: '20px',
                      height: '20px',
                      border: '2.5px solid rgba(59, 130, 246, 0.2)',
                      borderTopColor: '#3b82f6',
                      borderRadius: '50%',
                      animation: 'spin 0.8s linear infinite',
                    }}
                  />
                  {explorationProgress ? explorationProgress.message : 'Thinking...'}
                </div>
                {showTaskList && agentTasks.length > 0 && useAgentMode && (
                  <div style={{ 
                    marginLeft: '32px', 
                    marginTop: '12px', 
                    marginBottom: '12px',
                    width: 'calc(100% - 64px)'
                  }}>
                    <TaskList
                      tasks={agentTasks}
                      phaseProgress={phaseProgress}
                      aliveTs={aliveTs}
                      lastActivityTs={lastActivityTs}
                      taskSummary={taskSummary}
                      isCollapsed={false}
                    />
                  </div>
                )}
                {explorationProgress && !useAgentMode && (
                  <div style={{ marginLeft: '32px' }}>
                    <div
                      style={{
                        width: '100%',
                        height: '6px',
                        background: 'rgba(0, 0, 0, 0.05)',
                        borderRadius: '3px',
                        overflow: 'hidden',
                        backdropFilter: 'blur(10px)',
                      }}
                    >
                      <div
                        style={{
                          width: `${explorationProgress.percentage}%`,
                          height: '100%',
                          background: 'linear-gradient(90deg, #3b82f6, #60a5fa)',
                          borderRadius: '3px',
                          transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                          boxShadow: '0 0 10px rgba(59, 130, 246, 0.4)',
                        }}
                      />
                    </div>
                    <div style={{ fontSize: '11px', marginTop: '6px', color: '#9ca3af' }}>
                      Step {explorationProgress.current} of {explorationProgress.total} ({explorationProgress.percentage}%)
                    </div>
                  </div>
                )}
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area with glass effect */}
      <form
        onSubmit={handleSubmit}
        style={{
          padding: '16px 20px',
          borderTop: '1px solid rgba(0, 0, 0, 0.06)',
          background: 'linear-gradient(to top, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.7))',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: '0 0 24px 24px',
        }}
      >
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your code..."
            disabled={isLoading}
            style={{
              flex: 1,
              height: '44px',
              padding: '0 16px',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              borderRadius: '22px',
              fontSize: '14px',
              outline: 'none',
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px)',
              color: '#1f2937',
              transition: 'all 0.2s',
            }}
            onFocus={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.95)'
              e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.3)'
              e.currentTarget.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)'
            }}
            onBlur={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.8)'
              e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.08)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          />
          <button
            type={isLoading ? "button" : "submit"}
            onClick={isLoading ? handleStop : undefined}
            disabled={!isLoading && !inputValue.trim()}
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              border: 'none',
              background: isLoading
                ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.9), rgba(220, 38, 38, 0.9))'
                : !inputValue.trim()
                ? 'linear-gradient(135deg, rgba(156, 163, 175, 0.6), rgba(107, 114, 128, 0.6))'
                : 'linear-gradient(135deg, rgba(59, 130, 246, 0.9), rgba(37, 99, 235, 0.9))',
              color: '#fff',
              cursor: isLoading ? 'pointer' : (!inputValue.trim() ? 'not-allowed' : 'pointer'),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: isLoading
                ? '0 4px 16px rgba(239, 68, 68, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2)'
                : !inputValue.trim()
                ? 'none'
                : '0 4px 16px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2)',
            }}
            onMouseEnter={(e) => {
              if (isLoading) {
                e.currentTarget.style.transform = 'scale(1.08)'
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(239, 68, 68, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)'
              } else if (inputValue.trim()) {
                e.currentTarget.style.transform = 'scale(1.08)'
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(59, 130, 246, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)'
              e.currentTarget.style.boxShadow = isLoading
                ? '0 4px 16px rgba(239, 68, 68, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2)'
                : !inputValue.trim()
                ? 'none'
                : '0 4px 16px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2)'
            }}
            title={isLoading ? 'Stop' : 'Send'}
          >
            {isLoading ? '⏹' : '→'}
          </button>
        </div>
      </form>

      {/* Resize handle */}
      <div
        ref={resizeHandleRef}
        onMouseDown={handleResizeStart}
        style={{
          position: 'absolute',
          bottom: 0,
          right: 0,
          width: '24px',
          height: '24px',
          cursor: 'nwse-resize',
          background: 'transparent',
        }}
        title="Drag to resize"
      >
        <div
          style={{
            position: 'absolute',
            bottom: '4px',
            right: '4px',
            width: 0,
            height: 0,
            borderLeft: '10px solid transparent',
            borderBottom: '10px solid rgba(156, 163, 175, 0.4)',
          }}
        />
      </div>

      {/* CSS Animations */}
      <style>{`
        @keyframes pulseDot {
          0%, 60%, 100% {
            transform: scale(1);
            opacity: 0.5;
          }
          30% {
            transform: scale(1.2);
            opacity: 1;
          }
        }
        
        @keyframes textPulse {
          0%, 100% {
            opacity: 0.7;
          }
          50% {
            opacity: 1;
          }
        }
        
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes taskPulse {
          0%, 100% {
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
          }
          50% {
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0);
          }
        }
      `}</style>
    </div>
  )
}


