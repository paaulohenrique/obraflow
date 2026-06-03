"use client"

import React, { createContext, useContext, useState, useCallback } from "react"
import * as Toast from "@radix-ui/react-toast"
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react"

type ToastType = "success" | "error" | "info"

interface ToastMessage {
  id: string
  title: string
  description?: string
  type: ToastType
}

interface ToastContextType {
  toast: {
    success: (title: string, description?: string) => void
    error: (title: string, description?: string) => void
    info: (title: string, description?: string) => void
  }
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([])

  const addMessage = useCallback((title: string, type: ToastType, description?: string) => {
    setMessages((prev) => [
      ...prev,
      { id: String(Date.now() + Math.random()), title, description, type }
    ])
  }, [])

  const toast = {
    success: (title: string, description?: string) => addMessage(title, "success", description),
    error: (title: string, description?: string) => addMessage(title, "error", description),
    info: (title: string, description?: string) => addMessage(title, "info", description),
  }

  const removeToast = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      <Toast.Provider swipeDirection="right">
        {children}
        
        {messages.map((m) => {
          const icon = m.type === "success" 
            ? <CheckCircle2 className="size-4 text-green-500" />
            : m.type === "error"
            ? <AlertCircle className="size-4 text-red-500" />
            : <Info className="size-4 text-orange-500" />
            
          return (
            <Toast.Root
              key={m.id}
              duration={3000}
              onOpenChange={(open) => { if (!open) removeToast(m.id) }}
              className="bg-white border border-zinc-200 shadow-xl rounded-lg p-3.5 flex gap-3 items-start w-[320px] max-w-full pointer-events-auto transition-all data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=cancel]:translate-x-0 data-[swipe=end]:animate-out data-[state=open]:slide-in-from-bottom-4 data-[state=closed]:fade-out-80"
            >
              <div className="flex-shrink-0 mt-0.5">{icon}</div>
              <div className="flex-1 min-w-0">
                <Toast.Title className="text-xs font-semibold text-zinc-900 leading-tight">{m.title}</Toast.Title>
                {m.description && (
                  <Toast.Description className="text-[10px] text-zinc-500 mt-1 leading-normal">
                    {m.description}
                  </Toast.Description>
                )}
              </div>
              <button 
                onClick={() => removeToast(m.id)}
                className="text-zinc-400 hover:text-zinc-600 transition-colors flex-shrink-0 cursor-pointer"
              >
                <X className="size-3.5" />
              </button>
            </Toast.Root>
          )
        })}

        <Toast.Viewport className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 w-[320px] max-w-full focus:outline-none" />
      </Toast.Provider>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error("useToast deve ser usado dentro de um ToastProvider")
  return context
}
