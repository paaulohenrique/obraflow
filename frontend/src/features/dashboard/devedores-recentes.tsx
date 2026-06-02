"use client"

import Link from "next/link"
import { ExternalLink } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, initials } from "@/lib/utils"
import { ErrorState } from "@/components/ui/error-state"
import { useDashboardResumo } from "./use-dashboard-resumo"

export function DevedoresRecentes() {
  const { data, isLoading, isError, refetch } = useDashboardResumo()
  const devedores = data?.clientesDevedores.results ?? []

  if (isError) {
    return (
      <Card>
        <CardContent className="py-5">
          <ErrorState onRetry={() => refetch()} />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-900">Maiores Devedores</h3>
          <Link href="/clientes" className="flex items-center gap-1 text-xs font-medium text-orange-600 hover:text-orange-700">
            Ver todos <ExternalLink className="size-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : devedores.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-zinc-400">
            Nenhum cliente devedor.
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {devedores.map((cliente) => (
              <Link
                key={cliente.id}
                href={`/clientes/${cliente.id}`}
                className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-zinc-50/50"
              >
                <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-zinc-100">
                  <span className="text-xs font-semibold text-zinc-600">{initials(cliente.nome)}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-800">{cliente.nome}</p>
                  <p className="text-xs text-zinc-500">{cliente.cpf_cnpj}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold tabular-nums text-zinc-900">
                    {formatCurrency(cliente.saldo_devedor)}
                  </p>
                  <Badge variant={cliente.bloqueado ? "error" : "warning"} className="mt-0.5">
                    {cliente.bloqueado ? "Bloqueado" : "Aberto"}
                  </Badge>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
