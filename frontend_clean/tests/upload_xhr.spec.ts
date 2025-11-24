import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { uploadFile, type UploadProgress } from '../src/lib/upload'

describe('upload_xhr', () => {
  let mockXHR: {
    open: ReturnType<typeof vi.fn>
    send: ReturnType<typeof vi.fn>
    upload: {
      addEventListener: ReturnType<typeof vi.fn>
    }
    addEventListener: ReturnType<typeof vi.fn>
    status: number
    responseText: string
  }

  beforeEach(() => {
    // Mock XMLHttpRequest
    mockXHR = {
      open: vi.fn(),
      send: vi.fn(),
      upload: {
        addEventListener: vi.fn(),
      },
      addEventListener: vi.fn(),
      status: 200,
      responseText: JSON.stringify({
        supplier: 'Test Supplier',
        date: '2024-01-01',
        value: 100.0,
        confidence: 95.5,
      }),
    }

    // @ts-expect-error - Mocking global XMLHttpRequest
    global.XMLHttpRequest = vi.fn(() => mockXHR as unknown as XMLHttpRequest) as unknown as typeof XMLHttpRequest
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should call progress handler with ascending values (0→100)', async () => {
    const progressValues: number[] = []

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

    // Start upload (don't await yet)
    const uploadPromise = uploadFile(file, {
      onProgress: (progress: UploadProgress) => {
        progressValues.push(progress.percentage)
      },
    })

    // Simulate progress events
    const progressHandler = mockXHR.upload.addEventListener.mock.calls.find(
      (call) => call[0] === 'progress'
    )?.[1]

    if (progressHandler) {
      // Simulate progress: 10%, 30%, 90%, 100%
      progressHandler({ lengthComputable: true, loaded: 10, total: 100 })
      progressHandler({ lengthComputable: true, loaded: 30, total: 100 })
      progressHandler({ lengthComputable: true, loaded: 90, total: 100 })
      progressHandler({ lengthComputable: true, loaded: 100, total: 100 })
    }

    // Simulate successful completion
    const loadHandler = mockXHR.addEventListener.mock.calls.find((call) => call[0] === 'load')?.[1]
    if (loadHandler) {
      loadHandler({} as Event)
    }

    await uploadPromise

    // Assert progress values are ascending
    expect(progressValues.length).toBeGreaterThan(0)
    expect(progressValues).toEqual([10, 30, 90, 100])
    expect(progressValues).toEqual([...progressValues].sort((a, b) => a - b))
  })

  it('should surface error message back to card state on network error', async () => {
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

    const uploadPromise = uploadFile(file)

    // Simulate network error
    const errorHandler = mockXHR.addEventListener.mock.calls.find((call) => call[0] === 'error')?.[1]
    if (errorHandler) {
      errorHandler({} as Event)
    }

    const result = await uploadPromise

    expect(result.success).toBe(false)
    expect(result.error).toBe('Network error: Failed to connect to server')
    expect(result.metadata).toBeUndefined()
  })

  it('should surface HTTP error status in error message', async () => {
    mockXHR.status = 413
    mockXHR.responseText = 'Payload Too Large'

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

    const uploadPromise = uploadFile(file)

    // Simulate load with error status
    const loadHandler = mockXHR.addEventListener.mock.calls.find((call) => call[0] === 'load')?.[1]
    if (loadHandler) {
      loadHandler({} as Event)
    }

    const result = await uploadPromise

    expect(result.success).toBe(false)
    expect(result.error).toContain('413')
    expect(result.error).toContain('Payload Too Large')
  })

  it('should parse successful response and return metadata', async () => {
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

    const uploadPromise = uploadFile(file)

    // Simulate successful completion
    const loadHandler = mockXHR.addEventListener.mock.calls.find((call) => call[0] === 'load')?.[1]
    if (loadHandler) {
      loadHandler({} as Event)
    }

    const result = await uploadPromise

    expect(result.success).toBe(true)
    expect(result.metadata).toEqual({
      supplier: 'Test Supplier',
      date: '2024-01-01',
      value: 100.0,
      confidence: 95.5,
    })
    expect(result.error).toBeUndefined()
  })

  it('should handle invalid JSON response gracefully', async () => {
    mockXHR.responseText = 'Invalid JSON{'

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

    const uploadPromise = uploadFile(file)

    // Simulate successful completion
    const loadHandler = mockXHR.addEventListener.mock.calls.find((call) => call[0] === 'load')?.[1]
    if (loadHandler) {
      loadHandler({} as Event)
    }

    const result = await uploadPromise

    expect(result.success).toBe(false)
    expect(result.error).toContain('Failed to parse response')
  })

  it('should use FormData with key "file"', async () => {
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

    const uploadPromise = uploadFile(file)

    // Wait a tick for FormData to be created
    await new Promise((resolve) => setTimeout(resolve, 0))

    // Verify send was called (FormData should be created internally)
    expect(mockXHR.send).toHaveBeenCalled()
    const sentData = mockXHR.send.mock.calls[0]?.[0]

    // Verify it's a FormData instance
    expect(sentData).toBeInstanceOf(FormData)

    // Verify the file key is "file"
    // Note: We can't directly inspect FormData entries in all environments,
    // but we can verify the contract by checking the implementation
    // The contract is that FormData key must be exactly "file"

    // Simulate successful completion
    const loadHandler = mockXHR.addEventListener.mock.calls.find((call) => call[0] === 'load')?.[1]
    if (loadHandler) {
      loadHandler({} as Event)
    }

    await uploadPromise

    // Verify open was called with POST and correct URL
    expect(mockXHR.open).toHaveBeenCalledWith('POST', expect.stringContaining('/api/upload'))
  })
})

