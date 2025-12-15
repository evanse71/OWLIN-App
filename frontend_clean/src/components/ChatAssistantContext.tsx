import { createContext, useContext, useState, ReactNode, useEffect } from 'react'

interface ChatAssistantContextType {
  isExpanded: boolean
  setIsExpanded: (expanded: boolean) => void
}

const ChatAssistantContext = createContext<ChatAssistantContextType | undefined>(undefined)

export function ChatAssistantProvider({ children }: { children: ReactNode }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <ChatAssistantContext.Provider value={{ isExpanded, setIsExpanded }}>
      {children}
    </ChatAssistantContext.Provider>
  )
}

export function useChatAssistant() {
  const context = useContext(ChatAssistantContext)
  if (context === undefined) {
    // Return a safe default that won't cause errors
    // Components should check if they're using shared state before relying on this
    return { isExpanded: false, setIsExpanded: () => {} }
  }
  return context
}
