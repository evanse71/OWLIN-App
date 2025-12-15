import { useState, useRef, useEffect } from 'react'
import { ChatMessage } from './ChatMessage'
import { TaskList } from './TaskList'
import { API_BASE_URL } from '../lib/config'
import { useChatAssistant } from './ChatAssistantContext'
import { Search, Sparkles, Code, CircleAlert, Network, Plus, Send, X, Bot } from 'lucide-react'

// OWLIN Design System Tokens - Dark UI Palette
const OWLIN_COLORS = {
  // Dark backgrounds (matching invoice UI)
  backgroundLevel1: '#101214', // Main background
  backgroundLevel2: '#16191F', // Elevated cards
  backgroundMenu: 'rgba(20, 23, 28, 0.96)', // Menu background
  
  // Primary accent
  primary: '#4CA3FF', // Owlin blue
  primaryHover: '#5DB0FF',
  
  // Secondary
  secondary: '#2A2F38',
  
  // Borders
  border: 'rgba(255, 255, 255, 0.05)',
  borderSoft: 'rgba(255, 255, 255, 0.08)',
  
  // Text colors
  textPrimary: 'rgba(255, 255, 255, 0.87)',
  textSecondary: 'rgba(255, 255, 255, 0.6)',
  textMuted: 'rgba(255, 255, 255, 0.4)',
  textSlate: '#cbd5e1', // slate-300 equivalent
  
  // Interactive states
  hover: 'rgba(255, 255, 255, 0.03)',
  active: 'rgba(255, 255, 255, 0.05)',
  
  // Legacy (for compatibility)
  navy: '#2B3A55',
  sageGreen: '#7B9E87',
  sageGreenLight: 'rgba(123, 158, 135, 0.15)',
  sageGreenBorder: 'rgba(123, 158, 135, 0.2)',
  navyDark: '#101214',
  navyCard: '#16191F',
  backgroundSoft: 'rgba(255, 255, 255, 0.03)',
  backgroundCard: '#16191F',
}

const OWLIN_TYPOGRAPHY = {
  fontFamily: 'Inter, "Work Sans", -apple-system, BlinkMacSystemFont, sans-serif',
  weights: {
    body: 400,
    label: 500,
    title: 600,
  }
}

const OWLIN_SPACING = {
  micro: '8px',
  element: '16px',
  section: '24px',
}

const OWLIN_TRANSITIONS = {
  default: 'all 200ms ease-out',
  fast: 'all 150ms ease-out',
  slow: 'all 250ms ease-out',
}

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

interface ChatAssistantProps {
  compactInputExternal?: boolean
  renderAsWidget?: boolean // When true, renders as a widget in the layout instead of fixed positioning
  useSharedState?: boolean // When true, uses shared state from context
}

export function ChatAssistant({ compactInputExternal = false, renderAsWidget = false, useSharedState = false }: ChatAssistantProps) {
  // Always call the hook (React rules), but only use it if useSharedState is true
  const [localIsExpanded, setLocalIsExpanded] = useState(false)
  const sharedState = useChatAssistant() // Always call, but may return default if context not available
  
  const isExpanded = useSharedState ? sharedState.isExpanded : localIsExpanded
  const setIsExpanded = useSharedState ? sharedState.setIsExpanded : setLocalIsExpanded
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
  const [showOptionsMenu, setShowOptionsMenu] = useState(false)
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

  // Ref for the menu container
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      if (
        showOptionsMenu && 
        menuRef.current && 
        !menuRef.current.contains(target) &&
        containerRef.current &&
        !containerRef.current.contains(target)
      ) {
        setShowOptionsMenu(false)
      }
    }
    
    if (showOptionsMenu) {
      // Use a small delay to avoid closing immediately when opening
      const timeoutId = setTimeout(() => {
        document.addEventListener('mousedown', handleClickOutside)
      }, 0)
      
      return () => {
        clearTimeout(timeoutId)
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [showOptionsMenu])

  // When using external input and expanding, ensure panel is positioned at bottom-right
  useEffect(() => {
    if (compactInputExternal && isExpanded) {
      // Always pin and reset position to ensure bottom-right placement
      setIsPinned(true)
      setPosition({ x: 0, y: 0 })
    }
  }, [compactInputExternal, isExpanded])

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
    // Don't allow dragging when using external input - always keep at bottom-right
    if (compactInputExternal) return
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
        // Don't allow resizing when using external input (keeps panel at bottom-right)
        if (compactInputExternal) return
        
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
  }, [isDragging, isResizing, isPinned, dragStart, resizeStart, size, compactInputExternal])

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
      // When using external input, ensure panel appears at bottom-right
      if (compactInputExternal) {
        setIsPinned(true)
        setPosition({ x: 0, y: 0 })
      }
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
    // When using external input, ensure panel appears at bottom-right when expanding
    if (compactInputExternal) {
      setIsPinned(true)
      setPosition({ x: 0, y: 0 })
    }
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

  // Compact input form component (reusable) - Owlin dark UI style
  const CompactInputForm = () => (
    <form
      onSubmit={handleSubmit}
      className="assistant-input-form"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: OWLIN_SPACING.micro,
        width: compactInputExternal ? '100%' : '280px',
        maxWidth: compactInputExternal ? '320px' : '280px',
        minWidth: compactInputExternal ? '240px' : '280px',
        height: '44px',
        position: compactInputExternal ? 'relative' : 'fixed',
        top: compactInputExternal ? 'auto' : OWLIN_SPACING.section,
        right: compactInputExternal ? 'auto' : OWLIN_SPACING.section,
        zIndex: compactInputExternal ? 'auto' : 999,
        padding: '4px',
        background: OWLIN_COLORS.backgroundLevel2,
        borderRadius: '22px',
        border: `1px solid ${OWLIN_COLORS.border}`,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        transition: OWLIN_TRANSITIONS.default,
        flexShrink: 1,
        fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = OWLIN_COLORS.hover
        e.currentTarget.style.borderColor = OWLIN_COLORS.borderSoft
        e.currentTarget.style.boxShadow = `0 0 0 2px ${OWLIN_COLORS.primary}40`
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = OWLIN_COLORS.backgroundLevel2
        e.currentTarget.style.borderColor = OWLIN_COLORS.border
        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)'
      }}
    >
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        onKeyDown={handleKeyDown}
        placeholder="Ask Owlin Assistant..."
        disabled={isLoading}
        style={{
          flex: 1,
          height: '100%',
          padding: `0 ${OWLIN_SPACING.element}`,
          border: 'none',
          borderRadius: '18px',
          fontSize: '13px',
          outline: 'none',
          background: 'transparent',
          color: OWLIN_COLORS.textPrimary,
          fontWeight: OWLIN_TYPOGRAPHY.weights.body,
          fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
        }}
      />
      <button
        type="submit"
        disabled={isLoading || !inputValue.trim()}
        style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          border: 'none',
          background: isLoading || !inputValue.trim() 
            ? OWLIN_COLORS.backgroundLevel2
            : OWLIN_COLORS.primary,
          color: '#fff',
          cursor: isLoading || !inputValue.trim() ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: OWLIN_TRANSITIONS.default,
          boxShadow: isLoading || !inputValue.trim() 
            ? 'none'
            : '0 2px 6px rgba(0, 0, 0, 0.2)',
          opacity: isLoading || !inputValue.trim() ? 0.5 : 1,
          fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
        }}
        onMouseEnter={(e) => {
          if (!isLoading && inputValue.trim()) {
            e.currentTarget.style.transform = 'scale(1.05)'
            e.currentTarget.style.background = OWLIN_COLORS.primaryHover
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(76, 163, 255, 0.3)'
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.background = isLoading || !inputValue.trim() 
            ? OWLIN_COLORS.backgroundLevel2
            : OWLIN_COLORS.primary
          e.currentTarget.style.boxShadow = isLoading || !inputValue.trim() 
            ? 'none'
            : '0 2px 6px rgba(0, 0, 0, 0.2)'
        }}
      >
        {isLoading ? (
          <X size={16} strokeWidth={2} />
        ) : (
          <Send size={16} strokeWidth={1.5} />
        )}
      </button>
    </form>
  )


  // When renderAsWidget is true, only show the widget when expanded
  // The header input (compactInputExternal) will control the expansion
  if (renderAsWidget) {
    if (!isExpanded) {
      return null // Don't render anything when collapsed - header input handles that
    }
    // Will render expanded panel below (after it's defined)
  }

  // When compactInputExternal is true and not expanded, render compact input for AppHeader
  // When compactInputExternal is true and expanded, DON'T render expanded panel here - let the widget handle it
  if (!isExpanded) {
    if (compactInputExternal) {
      // Render compact input for external use (AppHeader will handle positioning)
      return <CompactInputForm />
    } else {
      // Render compact input with fixed positioning (legacy behavior)
      return <CompactInputForm />
    }
  }
  
  // When compactInputExternal is true and expanded, but we're NOT in widget mode,
  // we should still show the expanded panel (for pages without the widget)
  // But if we're using shared state, the widget will handle the expanded view
  if (compactInputExternal && useSharedState) {
    // Don't render expanded panel in header when using shared state - widget handles it
    return <CompactInputForm />
  }

  // Expanded state - render expanded panel
  // When compactInputExternal is true, ALWAYS position at bottom-right corner
  // When compactInputExternal is false, use normal positioning logic
  const getPanelPosition = () => {
    // Force bottom-right when using external input, regardless of other state
    if (compactInputExternal) {
      return {
        bottom: OWLIN_SPACING.section,
        right: OWLIN_SPACING.section,
        top: 'auto' as const,
        left: 'auto' as const,
      }
    }
    
    // Normal positioning logic for non-external mode
    if (isPinned) {
      return {
        bottom: OWLIN_SPACING.section,
        right: OWLIN_SPACING.section,
        top: 'auto' as const,
        left: 'auto' as const,
      }
    } else {
      return {
        top: `${position.y}px`,
        left: `${position.x}px`,
        bottom: 'auto' as const,
        right: 'auto' as const,
      }
    }
  }

  const panelPosition = getPanelPosition()

  // Render expanded panel as a variable (will be returned conditionally)
  // When renderAsWidget is true, render as a widget in the layout (relative positioning)
  // Otherwise, use fixed positioning at bottom-right
  const expandedPanelStyle: React.CSSProperties = {
    position: renderAsWidget ? 'relative' : 'fixed',
    width: renderAsWidget ? '100%' : `${size.width}px`,
    height: renderAsWidget ? '600px' : `${size.height}px`,
    maxHeight: renderAsWidget ? '600px' : `${size.height}px`,
    background: OWLIN_COLORS.backgroundLevel1,
    borderRadius: '20px',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
    border: `1px solid ${OWLIN_COLORS.border}`,
    display: 'flex',
    flexDirection: 'column',
    zIndex: renderAsWidget ? 1 : 9999,
    cursor: compactInputExternal ? 'default' : (isDragging ? 'grabbing' : (isPinned ? 'default' : 'grab')),
    userSelect: isDragging ? 'none' : 'auto',
    overflow: 'hidden',
    transition: 'all 200ms ease-out, transform 200ms ease-out',
    fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
    // Position based on render mode
    ...(renderAsWidget ? {
      marginTop: OWLIN_SPACING.element,
    } : {
      bottom: OWLIN_SPACING.section,
      right: OWLIN_SPACING.section,
      top: 'auto',
      left: 'auto',
      animation: 'dropIn 200ms ease-out',
    }),
  }

  const expandedPanel = (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      style={expandedPanelStyle}
    >
      {/* Header with OWLIN styling - ChatGPT style (cleaner) */}
      <div
        style={{
          padding: `${OWLIN_SPACING.element} ${OWLIN_SPACING.section}`,
          borderBottom: `1px solid ${OWLIN_COLORS.border}`,
          background: OWLIN_COLORS.backgroundLevel1,
          borderRadius: '20px 20px 0 0',
          cursor: isPinned ? 'default' : 'grab',
          minHeight: '56px',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Back button (left) - Reference image style */}
            {renderAsWidget && (
              <button
                onClick={handleMinimize}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: `1px solid ${OWLIN_COLORS.border}`,
                  background: 'transparent',
                  color: OWLIN_COLORS.textSecondary,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: OWLIN_TRANSITIONS.default,
                  fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = OWLIN_COLORS.hover
                  e.currentTarget.style.borderColor = OWLIN_COLORS.borderSoft
                  e.currentTarget.style.color = OWLIN_COLORS.textPrimary
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.borderColor = OWLIN_COLORS.border
                  e.currentTarget.style.color = OWLIN_COLORS.textSecondary
                }}
                title="Close"
              >
                <X size={18} strokeWidth={1.5} />
              </button>
            )}
            
            {/* Title with avatar - Reference image style */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: OWLIN_COLORS.backgroundLevel2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: `1px solid ${OWLIN_COLORS.border}`,
                  flexShrink: 0,
                }}
              >
                <Bot size={18} strokeWidth={1.5} color={OWLIN_COLORS.textSlate} />
              </div>
              <div style={{ 
                fontWeight: OWLIN_TYPOGRAPHY.weights.title, 
                fontSize: '17px', 
                color: OWLIN_COLORS.textPrimary,
                letterSpacing: '-0.01em',
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
              }}>
                Code Assistant
              </div>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            {!renderAsWidget && (
              <>
                {/* Pin/Unpin button - Only show when not in widget mode */}
                <button
                  onClick={handlePinToggle}
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '8px',
                    border: `1px solid ${OWLIN_COLORS.border}`,
                    background: OWLIN_COLORS.backgroundCard,
                    backdropFilter: 'blur(10px)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '13px',
                    color: OWLIN_COLORS.textSecondary,
                    transition: OWLIN_TRANSITIONS.default,
                    fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = OWLIN_COLORS.backgroundSoft
                    e.currentTarget.style.borderColor = OWLIN_COLORS.sageGreenBorder
                    e.currentTarget.style.transform = 'scale(1.05)'
                    e.currentTarget.style.color = OWLIN_COLORS.textPrimary
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = OWLIN_COLORS.backgroundCard
                    e.currentTarget.style.borderColor = OWLIN_COLORS.border
                    e.currentTarget.style.transform = 'scale(1)'
                    e.currentTarget.style.color = OWLIN_COLORS.textSecondary
                  }}
                  title={isPinned ? 'Unpin to move' : 'Pin to bottom right'}
                >
                  {isPinned ? '📌' : '📍'}
                </button>
                {/* Minimize button - Only show when not in widget mode */}
                <button
                  onClick={handleMinimize}
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '8px',
                    border: `1px solid ${OWLIN_COLORS.border}`,
                    background: OWLIN_COLORS.backgroundCard,
                    backdropFilter: 'blur(10px)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '16px',
                    color: OWLIN_COLORS.textSecondary,
                    transition: OWLIN_TRANSITIONS.default,
                    fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = OWLIN_COLORS.backgroundSoft
                    e.currentTarget.style.borderColor = OWLIN_COLORS.sageGreenBorder
                    e.currentTarget.style.transform = 'scale(1.05)'
                    e.currentTarget.style.color = OWLIN_COLORS.textPrimary
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = OWLIN_COLORS.backgroundCard
                    e.currentTarget.style.borderColor = OWLIN_COLORS.border
                    e.currentTarget.style.transform = 'scale(1)'
                    e.currentTarget.style.color = OWLIN_COLORS.textSecondary
                  }}
                  title="Minimize"
                >
                  −
                </button>
              </>
            )}
          </div>
        </div>
        
      </div>

      {/* Messages area with OWLIN styling - ChatGPT style (cleaner) */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: `40px ${OWLIN_SPACING.section} ${OWLIN_SPACING.section} ${OWLIN_SPACING.section}`,
          background: OWLIN_COLORS.backgroundLevel1,
          fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              color: OWLIN_COLORS.textSecondary,
              fontSize: '14px',
              padding: '60px 20px',
              fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
            }}
          >
            <div style={{ 
              fontWeight: OWLIN_TYPOGRAPHY.weights.title, 
              fontSize: '24px',
              marginBottom: '12px',
              color: OWLIN_COLORS.textPrimary,
              fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
              letterSpacing: '-0.02em',
              lineHeight: '1.3',
            }}>How can I help you today?</div>
            <div style={{ 
              fontSize: '15px', 
              marginBottom: '32px',
              color: OWLIN_COLORS.textSecondary,
              fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
              lineHeight: '1.6',
            }}>
              I can help you understand, debug, and explore your codebase.
            </div>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              maxWidth: '480px',
              margin: '0 auto',
            }}>
              <button
                type="button"
                onClick={() => {
                  setInputValue("Show me the upload code")
                  inputRef.current?.focus()
                }}
                style={{
                  width: '100%',
                  padding: '16px 20px',
                  background: OWLIN_COLORS.backgroundLevel2,
                  borderRadius: '12px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  border: `1px solid ${OWLIN_COLORS.border}`,
                  transition: OWLIN_TRANSITIONS.default,
                  textAlign: 'left',
                  color: OWLIN_COLORS.textPrimary,
                  fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                  fontWeight: OWLIN_TYPOGRAPHY.weights.body,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `linear-gradient(135deg, ${OWLIN_COLORS.backgroundLevel2} 0%, ${OWLIN_COLORS.hover} 100%)`
                  e.currentTarget.style.borderColor = OWLIN_COLORS.borderSoft
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = OWLIN_COLORS.backgroundLevel2
                  e.currentTarget.style.borderColor = OWLIN_COLORS.border
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <Code size={20} strokeWidth={1.5} color={OWLIN_COLORS.textSlate} style={{ flexShrink: 0 }} />
                <span>Show me the upload code</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setInputValue("Why did my upload fail?")
                  inputRef.current?.focus()
                }}
                style={{
                  width: '100%',
                  padding: '16px 20px',
                  background: OWLIN_COLORS.backgroundLevel2,
                  borderRadius: '12px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  border: `1px solid ${OWLIN_COLORS.border}`,
                  transition: OWLIN_TRANSITIONS.default,
                  textAlign: 'left',
                  color: OWLIN_COLORS.textPrimary,
                  fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                  fontWeight: OWLIN_TYPOGRAPHY.weights.body,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `linear-gradient(135deg, ${OWLIN_COLORS.backgroundLevel2} 0%, ${OWLIN_COLORS.hover} 100%)`
                  e.currentTarget.style.borderColor = OWLIN_COLORS.borderSoft
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = OWLIN_COLORS.backgroundLevel2
                  e.currentTarget.style.borderColor = OWLIN_COLORS.border
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <CircleAlert size={20} strokeWidth={1.5} color={OWLIN_COLORS.textSlate} style={{ flexShrink: 0 }} />
                <span>Why did my upload fail?</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setInputValue("Find all API endpoints")
                  inputRef.current?.focus()
                }}
                style={{
                  width: '100%',
                  padding: '16px 20px',
                  background: OWLIN_COLORS.backgroundLevel2,
                  borderRadius: '12px',
                  fontSize: '14px',
                  cursor: 'pointer',
                  border: `1px solid ${OWLIN_COLORS.border}`,
                  transition: OWLIN_TRANSITIONS.default,
                  textAlign: 'left',
                  color: OWLIN_COLORS.textPrimary,
                  fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                  fontWeight: OWLIN_TYPOGRAPHY.weights.body,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `linear-gradient(135deg, ${OWLIN_COLORS.backgroundLevel2} 0%, ${OWLIN_COLORS.hover} 100%)`
                  e.currentTarget.style.borderColor = OWLIN_COLORS.borderSoft
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = OWLIN_COLORS.backgroundLevel2
                  e.currentTarget.style.borderColor = OWLIN_COLORS.border
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <Network size={20} strokeWidth={1.5} color={OWLIN_COLORS.textSlate} style={{ flexShrink: 0 }} />
                <span>Find all API endpoints</span>
              </button>
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
                  padding: `${OWLIN_SPACING.element} ${OWLIN_SPACING.section}`,
                  margin: '12px 0',
                  background: 'transparent',
                  borderRadius: '6px',
                  fontSize: '14px',
                  color: OWLIN_COLORS.textSecondary,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  animation: 'fadeIn 0.3s ease-in',
                  fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
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
                      background: 'rgba(255, 255, 255, 0.4)',
                      animation: 'pulseDot 1.4s ease-in-out infinite',
                      animationDelay: '0s',
                    }}
                  />
                  <div
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: 'rgba(255, 255, 255, 0.4)',
                      animation: 'pulseDot 1.4s ease-in-out infinite',
                      animationDelay: '0.2s',
                    }}
                  />
                  <div
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: 'rgba(255, 255, 255, 0.4)',
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
                    color: OWLIN_COLORS.textSecondary,
                    fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
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
                  padding: OWLIN_SPACING.element,
                  background: OWLIN_COLORS.backgroundCard,
                  backdropFilter: 'blur(10px)',
                  borderRadius: '6px',
                  fontSize: '14px',
                  color: OWLIN_COLORS.textSecondary,
                  border: `1px solid ${OWLIN_COLORS.border}`,
                  fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      width: '20px',
                      height: '20px',
                      border: `2.5px solid ${OWLIN_COLORS.sageGreenLight}`,
                      borderTopColor: OWLIN_COLORS.sageGreen,
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
                        background: OWLIN_COLORS.backgroundCard,
                        borderRadius: '3px',
                        overflow: 'hidden',
                        backdropFilter: 'blur(10px)',
                      }}
                    >
                      <div
                        style={{
                          width: `${explorationProgress.percentage}%`,
                          height: '100%',
                          background: `linear-gradient(90deg, ${OWLIN_COLORS.navy}, ${OWLIN_COLORS.sageGreen})`,
                          borderRadius: '3px',
                          transition: OWLIN_TRANSITIONS.default,
                          boxShadow: `0 0 10px ${OWLIN_COLORS.sageGreen}40`,
                        }}
                      />
                    </div>
                    <div style={{ fontSize: '11px', marginTop: '6px', color: OWLIN_COLORS.textMuted, fontFamily: OWLIN_TYPOGRAPHY.fontFamily }}>
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

      {/* Input area with OWLIN styling - Owlin dark UI style */}
      <form
        onSubmit={handleSubmit}
        style={{
          padding: `${OWLIN_SPACING.element} ${OWLIN_SPACING.section}`,
          borderTop: `1px solid ${OWLIN_COLORS.border}`,
          background: OWLIN_COLORS.backgroundLevel1,
          borderRadius: '0 0 20px 20px',
          position: 'relative',
        }}
      >
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', position: 'relative' }}>
          {/* Plus icon button (left) - Opens options menu - Owlin style */}
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setShowOptionsMenu(!showOptionsMenu)
              }}
              style={{
                width: '36px',
                height: '36px',
                minWidth: '36px',
                borderRadius: '50%',
                border: `1px solid ${OWLIN_COLORS.border}`,
                background: OWLIN_COLORS.backgroundLevel2,
                color: OWLIN_COLORS.textSecondary,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: OWLIN_TRANSITIONS.default,
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = OWLIN_COLORS.hover
                e.currentTarget.style.borderColor = OWLIN_COLORS.borderSoft
                e.currentTarget.style.color = OWLIN_COLORS.textPrimary
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = OWLIN_COLORS.backgroundLevel2
                e.currentTarget.style.borderColor = OWLIN_COLORS.border
                e.currentTarget.style.color = OWLIN_COLORS.textSecondary
              }}
              title="Options"
            >
              <Plus size={20} strokeWidth={1.5} />
            </button>
            
            {/* Options Menu - Appears ABOVE the + button (Owlin dark UI style) */}
            {showOptionsMenu && (
              <div
                ref={menuRef}
                style={{
                  position: 'absolute',
                  bottom: '100%',
                  left: '0',
                  marginBottom: '8px',
                  padding: '8px 12px',
                  background: OWLIN_COLORS.backgroundMenu,
                  borderRadius: '16px',
                  border: `1px solid ${OWLIN_COLORS.border}`,
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
                  minWidth: '220px',
                  zIndex: 1000,
                  animation: 'menuFadeIn 0.15s ease-out',
                }}
                onClick={(e) => e.stopPropagation()}
              >
            {/* Search Mode Toggle */}
            <button
              type="button"
              onClick={() => {
                setUseSearchMode(!useSearchMode)
              }}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '12px',
                borderRadius: '8px',
                border: 'none',
                background: useSearchMode ? OWLIN_COLORS.hover : 'transparent',
                cursor: 'pointer',
                transition: OWLIN_TRANSITIONS.default,
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                textAlign: 'left',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = OWLIN_COLORS.hover
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = useSearchMode ? OWLIN_COLORS.hover : 'transparent'
              }}
            >
              <Search 
                size={20} 
                strokeWidth={1.5} 
                color={useSearchMode ? OWLIN_COLORS.primary : OWLIN_COLORS.textSlate}
                style={{ flexShrink: 0, marginTop: '2px' }}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
                <span style={{ 
                  fontSize: '14px', 
                  color: OWLIN_COLORS.textPrimary,
                  fontWeight: OWLIN_TYPOGRAPHY.weights.label,
                  lineHeight: '1.4',
                }}>
                  Search mode
                </span>
                <span style={{ 
                  fontSize: '12px', 
                  color: OWLIN_COLORS.textMuted,
                  fontWeight: OWLIN_TYPOGRAPHY.weights.body,
                  lineHeight: '1.4',
                }}>
                  Ask questions about code
                </span>
              </div>
            </button>
            
            {/* Agent Mode Toggle */}
            <button
              type="button"
              onClick={() => {
                setUseAgentMode(!useAgentMode)
              }}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '12px',
                borderRadius: '8px',
                border: 'none',
                background: useAgentMode ? OWLIN_COLORS.hover : 'transparent',
                cursor: 'pointer',
                transition: OWLIN_TRANSITIONS.default,
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
                textAlign: 'left',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = OWLIN_COLORS.hover
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = useAgentMode ? OWLIN_COLORS.hover : 'transparent'
              }}
            >
              <Sparkles 
                size={20} 
                strokeWidth={1.5} 
                color={useAgentMode ? OWLIN_COLORS.primary : OWLIN_COLORS.textSlate}
                style={{ flexShrink: 0, marginTop: '2px' }}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
                <span style={{ 
                  fontSize: '14px', 
                  color: OWLIN_COLORS.textPrimary,
                  fontWeight: OWLIN_TYPOGRAPHY.weights.label,
                  lineHeight: '1.4',
                }}>
                  Agent mode
                </span>
                <span style={{ 
                  fontSize: '12px', 
                  color: OWLIN_COLORS.textMuted,
                  fontWeight: OWLIN_TYPOGRAPHY.weights.body,
                  lineHeight: '1.4',
                }}>
                  Autonomous problem-solving
                </span>
              </div>
            </button>
              </div>
            )}
          </div>
          
          {/* Message input field (center) - Owlin style */}
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything"
            disabled={isLoading}
            style={{
              flex: 1,
              height: '44px',
              padding: `0 16px`,
              border: `1px solid ${OWLIN_COLORS.border}`,
              borderRadius: '22px',
              fontSize: '14px',
              outline: 'none',
              background: OWLIN_COLORS.backgroundLevel2,
              color: OWLIN_COLORS.textPrimary,
              transition: OWLIN_TRANSITIONS.default,
              fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
            }}
            onFocus={(e) => {
              e.currentTarget.style.background = OWLIN_COLORS.hover
              e.currentTarget.style.borderColor = OWLIN_COLORS.borderSoft
            }}
            onBlur={(e) => {
              e.currentTarget.style.background = OWLIN_COLORS.backgroundLevel2
              e.currentTarget.style.borderColor = OWLIN_COLORS.border
            }}
          />
          
          {/* Send button (right) - Owlin style */}
          <button
            type={isLoading ? "button" : "submit"}
            onClick={isLoading ? handleStop : undefined}
            disabled={!isLoading && !inputValue.trim()}
            style={{
              width: '36px',
              height: '36px',
              minWidth: '36px',
              borderRadius: '50%',
              border: 'none',
              background: isLoading
                ? 'rgba(239, 68, 68, 0.9)'
                : !inputValue.trim()
                ? OWLIN_COLORS.backgroundLevel2
                : OWLIN_COLORS.primary,
              color: '#fff',
              cursor: isLoading ? 'pointer' : (!inputValue.trim() ? 'not-allowed' : 'pointer'),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: OWLIN_TRANSITIONS.default,
              boxShadow: isLoading || inputValue.trim()
                ? '0 2px 6px rgba(0, 0, 0, 0.2)'
                : 'none',
              fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
              opacity: !inputValue.trim() && !isLoading ? 0.5 : 1,
            }}
            onMouseEnter={(e) => {
              if (isLoading) {
                e.currentTarget.style.transform = 'scale(1.05)'
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(239, 68, 68, 0.4)'
                e.currentTarget.style.background = 'rgba(239, 68, 68, 1)'
              } else if (inputValue.trim()) {
                e.currentTarget.style.transform = 'scale(1.05)'
                e.currentTarget.style.background = OWLIN_COLORS.primaryHover
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(76, 163, 255, 0.3)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)'
              e.currentTarget.style.background = isLoading
                ? 'rgba(239, 68, 68, 0.9)'
                : !inputValue.trim()
                ? OWLIN_COLORS.backgroundLevel2
                : OWLIN_COLORS.primary
              e.currentTarget.style.boxShadow = isLoading || inputValue.trim()
                ? '0 2px 6px rgba(0, 0, 0, 0.2)'
                : 'none'
            }}
            title={isLoading ? 'Stop' : 'Send'}
          >
            {isLoading ? (
              <X size={16} strokeWidth={2} />
            ) : (
              <Send size={16} strokeWidth={1.5} />
            )}
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
            borderBottom: `10px solid ${OWLIN_COLORS.textMuted}`,
          }}
        />
      </div>

      {/* CSS Animations */}
      <style>{`
        @keyframes dropIn {
          from {
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        
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
        
        @keyframes menuFadeIn {
          from {
            opacity: 0;
            transform: scale(1) translateY(4px);
          }
          50% {
            transform: scale(1.02) translateY(2px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
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

  // When renderAsWidget is true and expanded, render the expanded panel as a widget in the layout
  // This is used when the assistant should appear as part of the page layout (right column)
  if (renderAsWidget && isExpanded) {
    return expandedPanel
  }

  // When compactInputExternal is true and expanded, but using shared state,
  // only render the compact input (the widget will handle the expanded view)
  if (compactInputExternal && useSharedState && isExpanded) {
    return <CompactInputForm />
  }

  // When compactInputExternal is true and expanded (without shared state), render both compact input and expanded panel
  if (compactInputExternal && isExpanded) {
    return (
      <>
        <CompactInputForm />
        {expandedPanel}
      </>
    )
  }

  // When compactInputExternal is false, render only expanded panel when expanded
  return expandedPanel
}


