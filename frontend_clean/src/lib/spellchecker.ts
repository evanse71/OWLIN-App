import nspell from 'nspell'
import dictionaryEn from 'dictionary-en'

// Dynamic import for Welsh dictionary
const dictionaryCyLoader = () => import('dictionary-cy').then(m => m.default).catch(() => {
  console.warn('Welsh dictionary not available, only English spelling will be checked')
  return null
})

// Common abbreviations and units that should be ignored
const IGNORED_WORDS = new Set([
  'kg', 'g', 'mg', 'lb', 'oz',
  'L', 'l', 'ml', 'cl', 'dl',
  'm', 'cm', 'mm', 'km',
  'pc', 'pcs', 'pkg', 'pkgs',
  'ea', 'each',
  'x', 'X',
  'no', 'No', 'NO',
  'id', 'ID', 'Id'
])

// Common abbreviations that might appear in item names
const COMMON_ABBREVIATIONS = new Set([
  '12Litre', '12L', '12l',
  'pepsi', 'coca', 'cola',
  'pink', 'red', 'blue', 'green', 'yellow',
  'container', 'bottle', 'can', 'pack', 'box'
])

export interface SpellError {
  word: string
  suggestions: string[]
  position: number
}

export interface SpellCheckResult {
  isValid: boolean
  errors: SpellError[]
  text: string
}

// Initialize spell checkers for both languages
let spellCheckerEn: nspell | null = null
let spellCheckerCy: nspell | null = null
let initializationAttempted = false

async function initializeSpellCheckers(): Promise<void> {
  if (initializationAttempted) {
    return // Already attempted (may have failed)
  }
  initializationAttempted = true

  // Skip spell checker initialization in browser - dictionary-en uses Node.js features
  // This is a known limitation - spell checking will be disabled
  if (typeof window !== 'undefined') {
    console.warn('Spell checking disabled in browser (requires Node.js environment)')
    return
  }

  try {
    // Initialize English dictionary
    const enDict = await dictionaryEn()
    spellCheckerEn = nspell(enDict)

    // Initialize Welsh dictionary if available
    try {
      const cyDict = await dictionaryCyLoader()
      if (cyDict) {
        spellCheckerCy = nspell(cyDict)
      } else {
        spellCheckerCy = nspell({}) // Empty dictionary as fallback
      }
    } catch (cyError) {
      console.warn('Failed to load Welsh dictionary:', cyError)
      spellCheckerCy = nspell({}) // Empty dictionary as fallback
    }
  } catch (error) {
    console.error('Failed to initialize spell checkers:', error)
    // Fallback: create empty checkers that will always return false
    if (!spellCheckerEn) {
      spellCheckerEn = nspell({})
    }
    if (spellCheckerCy === null) {
      spellCheckerCy = nspell({})
    }
  }
}

// Initialize on module load
initializeSpellCheckers().catch(console.error)

/**
 * Check if a word should be ignored (abbreviations, numbers, etc.)
 */
function shouldIgnoreWord(word: string): boolean {
  const normalized = word.toLowerCase().trim()
  
  // Ignore empty strings
  if (!normalized) return true
  
  // Ignore very short words (1-2 characters) unless they're common abbreviations
  if (normalized.length <= 2 && !IGNORED_WORDS.has(normalized) && !COMMON_ABBREVIATIONS.has(normalized)) {
    return true
  }
  
  // Ignore numbers
  if (/^\d+$/.test(normalized)) return true
  
  // Ignore common abbreviations
  if (IGNORED_WORDS.has(normalized)) return true
  
  // Ignore words that are mostly numbers (e.g., "12Litre")
  if (/^\d+[a-z]*$/i.test(normalized)) return true
  
  return false
}

/**
 * Split text into words, handling punctuation and special characters
 */
function splitIntoWords(text: string): Array<{ word: string; position: number }> {
  const words: Array<{ word: string; position: number }> = []
  const regex = /\b[\w']+\b/g
  let match
  
  while ((match = regex.exec(text)) !== null) {
    words.push({
      word: match[0],
      position: match.index
    })
  }
  
  return words
}

/**
 * Get suggestions for a misspelled word
 */
function getSuggestions(word: string, maxSuggestions: number = 5): string[] {
  if (!spellCheckerEn || !spellCheckerCy) {
    return []
  }
  
  // Get suggestions from both dictionaries
  const enSuggestions = spellCheckerEn.suggest(word)
  const cySuggestions = spellCheckerCy.suggest(word)
  
  // Combine and deduplicate
  const allSuggestions = [...new Set([...enSuggestions, ...cySuggestions])]
  
  // Return top suggestions
  return allSuggestions.slice(0, maxSuggestions)
}

/**
 * Check spelling of text against both English and Welsh dictionaries
 * @param text - Text to check
 * @param languages - Languages to check against (default: both English and Welsh)
 * @returns SpellCheckResult with errors and suggestions
 */
export async function checkSpelling(
  text: string,
  languages: ('en' | 'cy')[] = ['en', 'cy']
): Promise<SpellCheckResult> {
  // Ensure spell checkers are initialized
  await initializeSpellCheckers()
  
  // If spell checkers aren't available (e.g., in browser), return valid result
  if (!spellCheckerEn && !spellCheckerCy) {
    return {
      isValid: true,
      errors: [],
      text
    }
  }
  
  if (!text || !text.trim()) {
    return {
      isValid: true,
      errors: [],
      text
    }
  }
  
  const errors: SpellError[] = []
  const words = splitIntoWords(text)
  
  for (const { word, position } of words) {
    // Skip words that should be ignored
    if (shouldIgnoreWord(word)) {
      continue
    }
    
    // Check if word is valid in any of the specified languages
    let isValid = false
    
    if (languages.includes('en') && spellCheckerEn) {
      isValid = isValid || spellCheckerEn.correct(word)
    }
    
    if (languages.includes('cy') && spellCheckerCy) {
      isValid = isValid || spellCheckerCy.correct(word)
    }
    
    // If word is not valid in any language, add it as an error
    if (!isValid) {
      const suggestions = getSuggestions(word)
      errors.push({
        word,
        suggestions,
        position
      })
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    text
  }
}

/**
 * Check spelling for multiple texts (e.g., all line items)
 */
export async function checkSpellingMultiple(
  texts: string[],
  languages: ('en' | 'cy')[] = ['en', 'cy']
): Promise<Array<{ index: number; result: SpellCheckResult }>> {
  const results = await Promise.all(
    texts.map((text, index) =>
      checkSpelling(text, languages).then(result => ({ index, result }))
    )
  )
  
  return results.filter(({ result }) => !result.isValid)
}

