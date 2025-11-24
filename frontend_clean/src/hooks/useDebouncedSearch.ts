import { useState, useEffect } from 'react'

export function useDebouncedSearch<T>(
  searchFn: (query: string) => Promise<T> | T,
  delay: number = 150
) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [results, setResults] = useState<T | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, delay)

    return () => clearTimeout(timer)
  }, [query, delay])

  useEffect(() => {
    if (!debouncedQuery) {
      setResults(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    const result = searchFn(debouncedQuery)
    
    if (result instanceof Promise) {
      result
        .then((data) => {
          setResults(data)
          setIsLoading(false)
        })
        .catch(() => {
          setResults(null)
          setIsLoading(false)
        })
    } else {
      setResults(result)
      setIsLoading(false)
    }
  }, [debouncedQuery, searchFn])

  return {
    query,
    setQuery,
    debouncedQuery,
    results,
    isLoading,
  }
}

