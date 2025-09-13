import React from 'react'
import "@/styles/globals.css"
import type { AppProps } from "next/app"
import { Toaster } from '@/components/ui/toaster'
import AppShell from '@/components/layout/AppShell'

// Development reset component
function DevReset() {
  React.useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const resetOnLoad = async () => {
        try {
          const response = await fetch('http://localhost:8001/dev/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
          })
          if (response.ok) {
            console.log('🔄 Development reset complete - fresh start!')
          }
        } catch (error) {
          console.log('⚠️ Development reset failed (backend not running?)')
        }
      }
      
      // Reset on every page load in development
      resetOnLoad()
    }
  }, [])
  
  return null
}

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <DevReset />
      <AppShell>
        <Component {...pageProps} />
      </AppShell>
      <Toaster />
    </>
  )
} 