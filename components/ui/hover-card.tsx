"use client"

import * as React from "react"

interface HoverCardProps {
  children: React.ReactNode
}

interface HoverCardTriggerProps {
  children: React.ReactNode
  asChild?: boolean
}

interface HoverCardContentProps {
  children: React.ReactNode
  className?: string
}

const HoverCardContext = React.createContext<{
  isOpen: boolean
  setIsOpen: (open: boolean) => void
}>({
  isOpen: false,
  setIsOpen: () => {},
})

const HoverCard: React.FC<HoverCardProps> = ({ children }) => {
  const [isOpen, setIsOpen] = React.useState(false)
  
  return (
    <HoverCardContext.Provider value={{ isOpen, setIsOpen }}>
      <div className="relative inline-block">
        {children}
      </div>
    </HoverCardContext.Provider>
  )
}

const HoverCardTrigger: React.FC<HoverCardTriggerProps> = ({ children, asChild }) => {
  const { setIsOpen } = React.useContext(HoverCardContext)
  
  const handleMouseEnter = () => setIsOpen(true)
  const handleMouseLeave = () => setIsOpen(false)
  
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<any>, {
      onMouseEnter: handleMouseEnter,
      onMouseLeave: handleMouseLeave,
    })
  }
  
  return (
    <div onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      {children}
    </div>
  )
}

const HoverCardContent: React.FC<HoverCardContentProps> = ({ children, className = "" }) => {
  const { isOpen } = React.useContext(HoverCardContext)
  
  if (!isOpen) return null
  
  return (
    <div
      className={`
        absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 
        z-50 w-64 rounded-md border border-gray-200 dark:border-gray-700 
        bg-white dark:bg-gray-800 p-4 text-sm text-gray-700 dark:text-gray-300 
        shadow-lg outline-none
        opacity-100 transition-all duration-200 ease-out
        ${className}
      `}
    >
      {children}
      <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-200 dark:border-t-gray-700"></div>
    </div>
  )
}

export { HoverCard, HoverCardTrigger, HoverCardContent } 