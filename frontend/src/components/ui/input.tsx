import { cn } from "@/lib/utils"
import { forwardRef, InputHTMLAttributes } from "react"

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-9 w-full rounded-md border px-3 text-sm bg-white",
        "placeholder:text-zinc-400 text-zinc-900",
        "transition-colors duration-150",
        "focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-zinc-50",
        error ? "border-red-500 focus:ring-red-500/30 focus:border-red-500" : "border-zinc-300",
        className
      )}
      {...props}
    />
  )
)

Input.displayName = "Input"
