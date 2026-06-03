"use client"

import { cn } from "@/lib/utils"

type BadgeVariant = "default" | "success" | "error" | "warning" | "info" | "outline"

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "border border-zinc-200 bg-zinc-100 text-zinc-700",
  success: "border border-green-200 bg-green-50 text-green-700",
  error:   "border border-red-200 bg-red-50 text-red-700",
  warning: "border border-yellow-200 bg-yellow-50 text-yellow-800",
  info:    "border border-zinc-300 bg-white text-zinc-700",
  outline: "border border-zinc-300 bg-white text-zinc-600",
}

export function Badge({ variant = "default", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold",
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}
