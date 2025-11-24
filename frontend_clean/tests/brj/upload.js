/**
 * BRJ Upload Test
 * Posts a sample file to POST /api/upload with FormData key "file"
 * Expects HTTP 200 and JSON body with fields: supplier?, date?, value?, confidence?
 */

import { writeFileSync, existsSync, readFileSync } from 'fs'
import { join } from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const FIXTURES_DIR = join(__dirname, '..', 'fixtures')
const SAMPLE_FILE = join(FIXTURES_DIR, 'sample.txt')

async function testUpload() {
  // Create sample file if it doesn't exist
  try {
    if (!existsSync(SAMPLE_FILE)) {
      writeFileSync(SAMPLE_FILE, 'Sample invoice content for testing\n')
      console.log(`[UPLOAD] Created sample file: ${SAMPLE_FILE}`)
    }
  } catch (error) {
    console.error(`[UPLOAD] Failed to create sample file:`, error.message)
    process.exit(1)
  }

  try {
    // Read file and create FormData
    // Node.js 18+ has native fetch, Node.js 20+ has native FormData
    const fileContent = readFileSync(SAMPLE_FILE)
    
    // Use FormData with File-like object
    const formData = new FormData()
    
    // Create a File-like object for Node.js
    // Contract: FormData key must be exactly "file"
    const file = new File([fileContent], 'sample.txt', { type: 'text/plain' })
    formData.append('file', file)

    console.log(`[UPLOAD] Posting to ${API_BASE_URL}/api/upload...`)

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const text = await response.text()
      console.error(`[UPLOAD] Upload failed: HTTP ${response.status} ${response.statusText}`)
      console.error(`[UPLOAD] Response:`, text.substring(0, 200))
      process.exit(1)
    }

    const data = await response.json()

    // Validate response structure
    const expectedFields = ['supplier', 'date', 'value', 'confidence']
    const missingFields = expectedFields.filter((field) => !(field in data))

    if (missingFields.length > 0) {
      console.warn(`[UPLOAD] Warning: Missing optional fields: ${missingFields.join(', ')}`)
      // Note: Fields are optional (nullable), so we warn but don't fail
    }

    console.log(`[UPLOAD] PASS - Upload successful`)
    console.log(`[UPLOAD] Parsed fields:`)
    console.log(`  - supplier: ${data.supplier ?? 'null'}`)
    console.log(`  - date: ${data.date ?? 'null'}`)
    console.log(`  - value: ${data.value ?? 'null'}`)
    console.log(`  - confidence: ${data.confidence ?? 'null'}`)
    console.log(`[UPLOAD] Full response:`, JSON.stringify(data, null, 2))
  } catch (error) {
    console.error(`[UPLOAD] Upload test failed:`, error.message)
    console.error(`[UPLOAD] Stack:`, error.stack)
    console.error(`[UPLOAD] Make sure backend is running at ${API_BASE_URL}`)
    process.exit(1)
  }
}

testUpload()

