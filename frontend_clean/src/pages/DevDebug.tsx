import { useState, useEffect } from 'react'
import { API_BASE_URL } from '../lib/config'

// Types matching backend models
interface CodeIssue {
  id: string
  tool: string
  severity: string
  file_path: string
  line?: number
  column?: number
  rule?: string
  message: string
  code_snippet?: string
}

interface IssueExplanation {
  issue_id: string
  plain_english: string
  technical_cause: string
  suggested_fix: string
  cursor_prompt: string
  confidence: number
  generation_method: string
}

interface RunChecksResponse {
  ok: boolean
  issues: CodeIssue[]
  total_count: number
  by_severity: Record<string, number>
  by_tool: Record<string, number>
  execution_time: number
  errors: string[]
}

interface ExplainResponse {
  ok: boolean
  explanation?: IssueExplanation
  error?: string
}

export function DevDebug() {
  const [issues, setIssues] = useState<CodeIssue[]>([])
  const [selectedIssue, setSelectedIssue] = useState<CodeIssue | null>(null)
  const [explanation, setExplanation] = useState<IssueExplanation | null>(null)
  const [codeContext, setCodeContext] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [runningChecks, setRunningChecks] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<{ by_severity: Record<string, number>; by_tool: Record<string, number> }>({
    by_severity: {},
    by_tool: {}
  })
  const [copiedPrompt, setCopiedPrompt] = useState(false)

  // Run checks on mount
  useEffect(() => {
    runChecks()
  }, [])

  const runChecks = async () => {
    setRunningChecks(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/dev/run_checks`)
      
      if (!response.ok) {
        throw new Error(`Failed to run checks: ${response.statusText}`)
      }
      
      const data: RunChecksResponse = await response.json()
      
      if (data.ok) {
        setIssues(data.issues)
        setStats({
          by_severity: data.by_severity,
          by_tool: data.by_tool
        })
        
        if (data.errors.length > 0) {
          setError(`Some checks failed: ${data.errors.join(', ')}`)
        }
      } else {
        setError('Checks failed to complete')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run checks')
    } finally {
      setRunningChecks(false)
    }
  }

  const explainIssue = async () => {
    if (!selectedIssue) return
    
    setLoading(true)
    setError(null)
    setExplanation(null)
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/dev/llm/explain`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          issue_id: selectedIssue.id,
          file_path: selectedIssue.file_path,
          error_snippet: selectedIssue.message,
          code_region: codeContext || undefined,
          line_number: selectedIssue.line,
          tool: selectedIssue.tool
        })
      })
      
      if (!response.ok) {
        throw new Error(`Failed to explain issue: ${response.statusText}`)
      }
      
      const data: ExplainResponse = await response.json()
      
      if (data.ok && data.explanation) {
        setExplanation(data.explanation)
      } else {
        setError(data.error || 'Failed to generate explanation')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to explain issue')
    } finally {
      setLoading(false)
    }
  }

  const copyCursorPrompt = () => {
    if (explanation) {
      navigator.clipboard.writeText(explanation.cursor_prompt)
      setCopiedPrompt(true)
      setTimeout(() => setCopiedPrompt(false), 2000)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      default:
        return 'bg-blue-100 text-blue-800 border-blue-300'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return '❌'
      case 'warning':
        return '⚠️'
      default:
        return 'ℹ️'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Dev Debug Assistant</h1>
              <p className="mt-1 text-sm text-gray-500">
                Offline code quality checker with AI-powered explanations
              </p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={runChecks}
                disabled={runningChecks}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {runningChecks ? '🔄 Running Checks...' : '🔍 Run Checks'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      {issues.length > 0 && (
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center gap-6 text-sm">
              <div className="font-medium text-gray-700">
                Total: <span className="text-gray-900">{issues.length}</span>
              </div>
              {Object.entries(stats.by_severity).map(([severity, count]) => (
                <div key={severity} className="flex items-center gap-1">
                  <span>{getSeverityIcon(severity)}</span>
                  <span className="text-gray-700">{severity}:</span>
                  <span className="font-medium text-gray-900">{count}</span>
                </div>
              ))}
              <div className="flex items-center gap-2 ml-auto">
                {Object.entries(stats.by_tool).map(([tool, count]) => (
                  <span key={tool} className="px-2 py-1 bg-gray-100 rounded text-xs font-medium text-gray-700">
                    {tool}: {count}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4 mx-4 mt-4 rounded-r">
          <div className="flex">
            <div className="flex-shrink-0">
              <span className="text-red-400">⚠️</span>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Issues List */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Detected Issues</h2>
              <p className="text-sm text-gray-500 mt-1">Select an issue to get an explanation</p>
            </div>
            
            <div className="divide-y divide-gray-200 max-h-[calc(100vh-350px)] overflow-y-auto">
              {issues.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  {runningChecks ? (
                    <div className="flex flex-col items-center gap-3">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      <p>Running checks...</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-3xl mb-2">✅</p>
                      <p>No issues found!</p>
                      <p className="text-sm mt-1">Click "Run Checks" to scan your code</p>
                    </div>
                  )}
                </div>
              ) : (
                issues.map((issue) => (
                  <button
                    key={issue.id}
                    onClick={() => {
                      setSelectedIssue(issue)
                      setExplanation(null)
                      setCodeContext('')
                    }}
                    className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                      selectedIssue?.id === issue.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-xl mt-0.5">{getSeverityIcon(issue.severity)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getSeverityColor(issue.severity)}`}>
                            {issue.severity}
                          </span>
                          <span className="text-xs font-medium text-gray-600">{issue.tool}</span>
                          {issue.rule && (
                            <span className="text-xs text-gray-500">{issue.rule}</span>
                          )}
                        </div>
                        <p className="text-sm font-medium text-gray-900 mb-1 truncate">
                          {issue.file_path}
                          {issue.line && `:${issue.line}`}
                          {issue.column && `:${issue.column}`}
                        </p>
                        <p className="text-sm text-gray-600 line-clamp-2">{issue.message}</p>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Right Column: Explanation Panel */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Issue Explanation</h2>
              <p className="text-sm text-gray-500 mt-1">
                {selectedIssue ? `Analyzing ${selectedIssue.tool} issue` : 'Select an issue to get started'}
              </p>
            </div>

            <div className="p-4 space-y-4 max-h-[calc(100vh-350px)] overflow-y-auto">
              {!selectedIssue ? (
                <div className="text-center py-12 text-gray-500">
                  <p className="text-3xl mb-2">👈</p>
                  <p>Select an issue from the list</p>
                </div>
              ) : (
                <>
                  {/* Selected Issue Details */}
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xl">{getSeverityIcon(selectedIssue.severity)}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getSeverityColor(selectedIssue.severity)}`}>
                        {selectedIssue.severity}
                      </span>
                      <span className="text-xs font-medium text-gray-600">{selectedIssue.tool}</span>
                    </div>
                    <p className="text-sm font-mono text-gray-700 mb-2">{selectedIssue.file_path}</p>
                    <p className="text-sm text-gray-900">{selectedIssue.message}</p>
                  </div>

                  {/* Code Context Input */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Code Context (optional, 30-60 lines around the error)
                    </label>
                    <textarea
                      value={codeContext}
                      onChange={(e) => setCodeContext(e.target.value)}
                      placeholder="Paste 30-60 lines of code around the error for better explanation..."
                      className="w-full h-32 px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Generate Button */}
                  <button
                    onClick={explainIssue}
                    disabled={loading}
                    className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
                  >
                    {loading ? '⏳ Generating Explanation...' : '🤖 Generate Explanation & Patch Suggestion'}
                  </button>

                  {/* Explanation Results */}
                  {explanation && (
                    <div className="space-y-4 border-t border-gray-200 pt-4">
                      {/* Plain English */}
                      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                        <h3 className="text-sm font-semibold text-blue-900 mb-2">📖 Plain English</h3>
                        <p className="text-sm text-blue-800">{explanation.plain_english}</p>
                      </div>

                      {/* Technical Cause */}
                      <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                        <h3 className="text-sm font-semibold text-purple-900 mb-2">🔧 Technical Cause</h3>
                        <p className="text-sm text-purple-800">{explanation.technical_cause}</p>
                      </div>

                      {/* Suggested Fix */}
                      <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                        <h3 className="text-sm font-semibold text-green-900 mb-2">✅ Suggested Fix</h3>
                        <pre className="text-sm text-green-800 whitespace-pre-wrap">{explanation.suggested_fix}</pre>
                      </div>

                      {/* Cursor Prompt */}
                      <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="text-sm font-semibold text-orange-900">🎯 Cursor Prompt (Copy & Paste)</h3>
                          <button
                            onClick={copyCursorPrompt}
                            className="px-3 py-1 bg-orange-600 text-white text-xs rounded hover:bg-orange-700 transition-colors"
                          >
                            {copiedPrompt ? '✓ Copied!' : '📋 Copy'}
                          </button>
                        </div>
                        <p className="text-sm text-orange-800 font-mono bg-white p-2 rounded border border-orange-200">
                          {explanation.cursor_prompt}
                        </p>
                      </div>

                      {/* Metadata */}
                      <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-200">
                        <span>Confidence: {(explanation.confidence * 100).toFixed(0)}%</span>
                        <span>Method: {explanation.generation_method === 'ollama_llm' ? '🤖 AI (Ollama)' : '📋 Template'}</span>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

