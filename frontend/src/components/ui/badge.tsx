"use client"

import { cn } from "@/lib/utils"

type BadgeVariant = "default" | "success" | "error" | "warning" | "info" | "outline"

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-zinc-100 text-zinc-700",
  success: "bg-green-50 text-green-700 border border-green-200",
  error:   "bg-red-50 text-red-700 border border-red-200",
  warning: "bg-yellow-50 text-yellow-700 border border-yellow-200",
  info:    "bg-blue-50 text-blue-700 border border-blue-200",
  outline: "border border-zinc-300 text-zinc-600",
}

export function Badge({ variant = "default", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium",
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}
