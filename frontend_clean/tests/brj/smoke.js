/**
 * BRJ Smoke Test - Health Check
 * Calls GET /api/health and exits non-zero if not {"status":"ok"}
 */

const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`)
    
    if (!response.ok) {
      console.error(`[SMOKE] Health check failed: HTTP ${response.status} ${response.statusText}`)
      process.exit(1)
    }

    const data = await response.json()
    
    if (data.status !== 'ok') {
      console.error(`[SMOKE] Health check failed: Expected status "ok", got "${data.status}"`)
      console.error(`[SMOKE] Response:`, JSON.stringify(data, null, 2))
      process.exit(1)
    }

    console.log(`[SMOKE] PASS - Backend healthy at ${API_BASE_URL}`)
    console.log(`[SMOKE] Response:`, JSON.stringify(data, null, 2))
  } catch (error) {
    console.error(`[SMOKE] Health check failed:`, error.message)
    console.error(`[SMOKE] Make sure backend is running at ${API_BASE_URL}`)
    process.exit(1)
  }
}

checkHealth()

