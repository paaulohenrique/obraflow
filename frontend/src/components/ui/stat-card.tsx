import { cn } from "@/lib/utils"
import { TrendingDown, TrendingUp } from "lucide-react"
import { Skeleton } from "./skeleton"

interface StatCardProps {
  label: string
  value: string
  change?: number
  icon?: React.ReactNode
  loading?: boolean
  accent?: boolean
}

export function StatCard({ label, value, change, icon, loading, accent }: StatCardProps) {
  if (loading) {
    return (
      <div className="bg-white border border-zinc-200 rounded-lg p-4 shadow-xs">
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
        "bg-white border rounded-lg p-4 shadow-xs flex flex-col gap-1.5",
        accent
          ? "border-orange-200 ring-1 ring-orange-100"
          : "border-zinc-200"
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">{label}</span>
        {icon && (
          <span className={cn("text-zinc-400", accent && "text-orange-500")}>{icon}</span>
        )}
      </div>

      <p className={cn("text-2xl font-semibold tabular-nums", accent ? "text-orange-600" : "text-zinc-900")}>
        {value}
      </p>

      {change !== undefined && (
        <div className={cn("flex items-center gap-1 text-xs font-medium", positive ? "text-green-600" : "text-red-600")}>
          {positive ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
          <span>{positive ? "+" : ""}{change.toFixed(1)}% vs mês anterior</span>
        </div>
      )}
    </div>
  )
}
