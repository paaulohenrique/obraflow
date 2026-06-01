"use client"

import { cn } from "@/lib/utils"
import { Loader2 } from "lucide-react"
import { ButtonHTMLAttributes, forwardRef } from "react"

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline"
type ButtonSize = "xs" | "sm" | "md" | "lg"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: React.ReactNode
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:   "bg-orange-500 hover:bg-orange-600 text-white border-transparent shadow-sm",
  secondary: "bg-zinc-100 hover:bg-zinc-200 text-zinc-800 border-transparent",
  ghost:     "bg-transparent hover:bg-zinc-100 text-zinc-700 border-transparent",
  danger:    "bg-red-600 hover:bg-red-700 text-white border-transparent shadow-sm",
  outline:   "bg-white hover:bg-zinc-50 text-zinc-800 border-zinc-300",
}

const sizeClasses: Record<ButtonSize, string> = {
  xs: "h-7  px-2.5 text-xs gap-1.5",
  sm: "h-8  px-3   text-sm gap-1.5",
  md: "h-9  px-4   text-sm gap-2",
  lg: "h-10 px-5   text-sm gap-2",
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", loading, icon, className, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center font-medium rounded-md border",
          "transition-colors duration-150 cursor-pointer",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {loading ? <Loader2 className="size-3.5 animate-spin" /> : icon}
        {children}
      </button>
    )
  }
)

Button.displayName = "Button"
