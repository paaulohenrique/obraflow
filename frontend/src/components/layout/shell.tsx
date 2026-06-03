"use client"

import { useState } from "react"
import { Sidebar } from "./sidebar"
import { cn } from "@/lib/utils"

export function Shell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex min-h-screen bg-zinc-50">
      <Sidebar collapsed={collapsed} onCollapsedChange={setCollapsed} />
      <div
        className={cn(
          "flex min-w-0 flex-1 flex-col pb-20 transition-[padding] duration-200 lg:pb-0",
          collapsed ? "lg:pl-20" : "lg:pl-64"
        )}
      >
        {children}
      </div>
    </div>
  )
}
