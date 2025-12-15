/**
 * Line Item Matcher Utility
 * 
 * Provides fuzzy matching, SKU matching, and partial matching for line items
 * between invoices and delivery notes (client-side implementation).
 */

export interface LineItem {
  description?: string
  item?: string
  qty?: number
  quantity?: number
  total?: number
  line_total?: number
  price?: number
  unit_price?: number
  sku?: string
  SKU?: string
  [key: string]: unknown
}

export interface MatchedItem {
  invoiceItem: LineItem
  deliveryItem: LineItem | null
  similarity: number
  matchType: 'exact' | 'sku' | 'fuzzy' | 'partial' | 'none'
}

const DEFAULT_SIMILARITY_THRESHOLD = 0.85

/**
 * Normalize description for comparison
 */
function normalizeDescription(desc: string): string {
  if (!desc) return ''
  return desc.toLowerCase().trim().replace(/\s+/g, ' ')
}

/**
 * Calculate similarity between two strings using Levenshtein-like algorithm
 * Simple implementation using character overlap
 */
function calculateSimilarity(str1: string, str2: string): number {
  if (!str1 || !str2) return 0.0
  
  const norm1 = normalizeDescription(str1)
  const norm2 = normalizeDescription(str2)
  
  if (!norm1 || !norm2) return 0.0
  
  // Exact match after normalization
  if (norm1 === norm2) return 1.0
  
  // Simple similarity calculation using longest common subsequence
  const longer = norm1.length > norm2.length ? norm1 : norm2
  const shorter = norm1.length > norm2.length ? norm2 : norm1
  
  if (longer.length === 0) return 1.0
  
  // Calculate edit distance ratio (simplified)
  let matches = 0
  let shorterIndex = 0
  
  for (let i = 0; i < longer.length && shorterIndex < shorter.length; i++) {
    if (longer[i] === shorter[shorterIndex]) {
      matches++
      shorterIndex++
    }
  }
  
  // Use a combination of character overlap and substring matching
  const overlapRatio = matches / longer.length
  const containsRatio = longer.includes(shorter) || shorter.includes(longer) ? 0.3 : 0
  
  // Token-based similarity
  const tokens1 = new Set(norm1.split(/\s+/))
  const tokens2 = new Set(norm2.split(/\s+/))
  const intersection = new Set([...tokens1].filter(x => tokens2.has(x)))
  const union = new Set([...tokens1, ...tokens2])
  const tokenSimilarity = union.size > 0 ? intersection.size / union.size : 0
  
  // Combine metrics
  return Math.max(overlapRatio + containsRatio, tokenSimilarity)
}

/**
 * Calculate token-based similarity (Jaccard similarity)
 */
function calculateTokenSimilarity(desc1: string, desc2: string): number {
  if (!desc1 || !desc2) return 0.0
  
  const norm1 = normalizeDescription(desc1)
  const norm2 = normalizeDescription(desc2)
  
  if (!norm1 || !norm2) return 0.0
  
  const tokens1 = new Set(norm1.split(/\s+/))
  const tokens2 = new Set(norm2.split(/\s+/))
  
  if (tokens1.size === 0 || tokens2.size === 0) return 0.0
  
  const intersection = new Set([...tokens1].filter(x => tokens2.has(x)))
  const union = new Set([...tokens1, ...tokens2])
  
  return union.size > 0 ? intersection.size / union.size : 0.0
}

/**
 * Check if one description contains key words from the other (partial match)
 */
function checkPartialMatch(desc1: string, desc2: string): boolean {
  if (!desc1 || !desc2) return false
  
  const norm1 = normalizeDescription(desc1)
  const norm2 = normalizeDescription(desc2)
  
  if (!norm1 || !norm2) return false
  
  const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
  const tokens1 = new Set(norm1.split(/\s+/).filter(t => !stopWords.has(t)))
  const tokens2 = new Set(norm2.split(/\s+/).filter(t => !stopWords.has(t)))
  
  if (tokens1.size === 0 || tokens2.size === 0) return false
  
  const intersection = new Set([...tokens1].filter(x => tokens2.has(x)))
  const minTokens = Math.min(tokens1.size, tokens2.size)
  
  return minTokens > 0 && intersection.size / minTokens >= 0.5
}

/**
 * Get description from a line item
 */
function getItemDescription(item: LineItem): string {
  return item.description || item.item || ''
}

/**
 * Get SKU from a line item
 */
function getItemSku(item: LineItem): string {
  return (item.sku || item.SKU || '').toString().trim()
}

/**
 * Match invoice items to delivery items using multiple strategies
 * 
 * Matching priority:
 * 1. SKU match (if both have SKU)
 * 2. Exact description match
 * 3. Fuzzy description match (similarity >= threshold)
 * 4. Partial match (token overlap)
 */
export function matchLineItems(
  invoiceItems: LineItem[],
  deliveryItems: LineItem[],
  threshold: number = DEFAULT_SIMILARITY_THRESHOLD
): MatchedItem[] {
  const matched: MatchedItem[] = []
  const usedDeliveryIndices = new Set<number>()
  
  for (const invItem of invoiceItems) {
    const invDesc = getItemDescription(invItem)
    const invSku = getItemSku(invItem)
    
    let bestMatch: LineItem | null = null
    let bestSimilarity = 0.0
    let bestMatchType: 'exact' | 'sku' | 'fuzzy' | 'partial' | 'none' = 'none'
    let bestIndex = -1
    
    // Try to match against each delivery item
    for (let idx = 0; idx < deliveryItems.length; idx++) {
      if (usedDeliveryIndices.has(idx)) continue
      
      const delItem = deliveryItems[idx]
      const delDesc = getItemDescription(delItem)
      const delSku = getItemSku(delItem)
      
      let matchType: 'exact' | 'sku' | 'fuzzy' | 'partial' | 'none' = 'none'
      let similarity = 0.0
      
      // Strategy 1: SKU match (highest priority)
      if (invSku && delSku) {
        const invSkuNorm = invSku.toUpperCase()
        const delSkuNorm = delSku.toUpperCase()
        if (invSkuNorm === delSkuNorm) {
          matchType = 'sku'
          similarity = 1.0
          if (similarity > bestSimilarity) {
            bestMatch = delItem
            bestSimilarity = similarity
            bestMatchType = matchType
            bestIndex = idx
          }
          continue // SKU match is definitive
        }
      }
      
      // Strategy 2: Exact description match
      if (invDesc && delDesc) {
        const norm1 = normalizeDescription(invDesc)
        const norm2 = normalizeDescription(delDesc)
        if (norm1 === norm2 && norm1) {
          matchType = 'exact'
          similarity = 1.0
          if (similarity > bestSimilarity) {
            bestMatch = delItem
            bestSimilarity = similarity
            bestMatchType = matchType
            bestIndex = idx
          }
          continue // Exact match is definitive
        }
      }
      
      // Strategy 3: Fuzzy description match
      if (invDesc && delDesc) {
        const seqSimilarity = calculateSimilarity(invDesc, delDesc)
        const tokenSimilarity = calculateTokenSimilarity(invDesc, delDesc)
        similarity = Math.max(seqSimilarity, tokenSimilarity)
        
        if (similarity >= threshold) {
          matchType = 'fuzzy'
          if (similarity > bestSimilarity) {
            bestMatch = delItem
            bestSimilarity = similarity
            bestMatchType = matchType
            bestIndex = idx
          }
        }
      }
      
      // Strategy 4: Partial match (only if no better match found)
      if (bestSimilarity < threshold && invDesc && delDesc) {
        if (checkPartialMatch(invDesc, delDesc)) {
          similarity = calculateTokenSimilarity(invDesc, delDesc)
          if (similarity > bestSimilarity) {
            matchType = 'partial'
            bestMatch = delItem
            bestSimilarity = similarity
            bestMatchType = matchType
            bestIndex = idx
          }
        }
      }
    }
    
    // Mark delivery item as used if we found a good match
    if (bestMatch && bestIndex >= 0 && bestSimilarity >= threshold) {
      usedDeliveryIndices.add(bestIndex)
    }
    
    // Add to results (even if no match found, similarity will be 0.0)
    matched.push({
      invoiceItem: invItem,
      deliveryItem: bestMatch,
      similarity: bestSimilarity,
      matchType: bestMatchType
    })
  }
  
  return matched
}

