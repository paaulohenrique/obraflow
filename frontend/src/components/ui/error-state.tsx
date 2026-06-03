import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface ErrorStateProps {
  title?: string
  description?: string
  actionLabel?: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({
  title = "Não foi possível carregar os dados",
  description = "Verifique a conexão com o servidor e tente novamente.",
  actionLabel = "Tentar novamente",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-14 text-center", className)}>
      <div className="mb-4 flex size-12 items-center justify-center rounded-lg border border-red-100 bg-red-50">
        <AlertTriangle className="size-5 text-red-500" />
      </div>
      <p className="text-sm font-semibold text-zinc-900">{title}</p>
      <p className="mt-1 max-w-sm text-xs leading-relaxed text-zinc-500">{description}</p>
      {onRetry && (
        <Button type="button" variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
