import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ErrorStateProps {
  title?: string
  description?: string
  actionLabel?: string
  onRetry?: () => void
}

export function ErrorState({
  title = "Não foi possível carregar os dados",
  description = "Verifique a conexão com o servidor e tente novamente.",
  actionLabel = "Tentar novamente",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center px-5 py-14 text-center">
      <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-red-50">
        <AlertTriangle className="size-5 text-red-500" />
      </div>
      <p className="text-sm font-semibold text-zinc-800">{title}</p>
      <p className="mt-1 max-w-sm text-xs leading-relaxed text-zinc-500">{description}</p>
      {onRetry && (
        <Button type="button" variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
