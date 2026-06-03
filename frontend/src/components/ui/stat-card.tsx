import { cn } from "@/lib/utils"
import { TrendingDown, TrendingUp } from "lucide-react"
import { Skeleton } from "./skeleton"

interface StatCardProps {
  label: string
  value: string
  change?: number
  context?: string
  icon?: React.ReactNode
  loading?: boolean
  accent?: boolean
}

export function StatCard({ label, value, change, context, icon, loading, accent }: StatCardProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-zinc-200/80 bg-white p-4 shadow-[0_1px_2px_rgba(24,24,27,0.04)]">
        <Skeleton className="h-4 w-28 mb-3" />
        <Skeleton className="h-7 w-36 mb-2" />
        <Skeleton className="h-3 w-20" />
      </div>
    )
  }

  const positive = (change ?? 0) >= 0

  return (
    <div
      className={cn(
        "relative flex min-h-28 flex-col gap-2 overflow-hidden rounded-lg border bg-white p-4 shadow-[0_1px_2px_rgba(24,24,27,0.04)] transition-colors duration-150",
        accent
          ? "border-orange-200 bg-orange-50/35 ring-1 ring-orange-100"
          : "border-zinc-200/80 hover:border-zinc-300"
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wide">{label}</span>
        {icon && (
          <span className={cn("flex size-7 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-400", accent && "border-orange-200 text-orange-600")}>{icon}</span>
        )}
      </div>

      <p className={cn("text-2xl font-semibold leading-none tabular-nums", accent ? "text-orange-700" : "text-zinc-950")}>
        {value}
      </p>

      {change !== undefined && (
        <div className={cn("flex items-center gap-1 text-xs font-medium", positive ? "text-green-600" : "text-red-600")}>
          {positive ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
          <span>{positive ? "+" : ""}{change.toFixed(1)}% vs mês anterior</span>
        </div>
      )}

      {context && change === undefined && (
        <p className="text-xs leading-relaxed text-zinc-500">{context}</p>
      )}
    </div>
  )
}
