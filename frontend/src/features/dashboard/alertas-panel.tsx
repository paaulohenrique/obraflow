"use client"

import Link from "next/link"
import { AlertTriangle, Clock, Package, UserX } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn, formatCurrency } from "@/lib/utils"
import { ErrorState } from "@/components/ui/error-state"
import { useDashboardResumo } from "./use-dashboard-resumo"

const iconBg: Record<"error" | "warning" | "info", string> = {
  error: "bg-red-50 text-red-500",
  warning: "bg-yellow-50 text-yellow-600",
  info: "bg-orange-50 text-orange-600",
}

export function AlertasPanel() {
  const { data, isLoading, isError, refetch } = useDashboardResumo()

  if (isError) {
    return (
      <Card>
        <CardContent className="py-5">
          <ErrorState onRetry={() => refetch()} />
        </CardContent>
      </Card>
    )
  }

  const alertas = [
    {
      tipo: "warning" as const,
      icon: UserX,
      titulo: "Clientes devedores",
      descricao: `${data?.fiado.clientes_devedores ?? 0} clientes com saldo pendente`,
      badge: String(data?.fiado.clientes_devedores ?? 0),
      href: "/clientes",
    },
    {
      tipo: "warning" as const,
      icon: Package,
      titulo: "Estoque crítico",
      descricao: "Produtos com saldo no mínimo operacional",
      badge: String(data?.produtosCriticos.count ?? 0),
      href: "/estoque",
    },
    {
      tipo: "error" as const,
      icon: Clock,
      titulo: "Contas em atraso",
      descricao: "Contas a pagar vencidas no financeiro",
      badge: formatCurrency(data?.financeiro.total_contas_pagar_vencidas),
      href: "/financeiro",
    },
    {
      tipo: "info" as const,
      icon: AlertTriangle,
      titulo: "Fiado vencido",
      descricao: `${data?.fiado.contas_atrasadas ?? 0} contas fiado atrasadas`,
      badge: formatCurrency(data?.fiado.total_atrasado),
      href: "/fiado",
    },
  ]

  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-semibold text-zinc-900">Alertas Operacionais</h3>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {alertas.map((alerta) => (
              <Link
                key={alerta.titulo}
                href={alerta.href}
                className="flex items-start gap-3 px-5 py-3.5 transition-colors hover:bg-zinc-50/50"
              >
                <div className={cn("mt-0.5 flex size-8 flex-shrink-0 items-center justify-center rounded-md", iconBg[alerta.tipo])}>
                  <alerta.icon className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium leading-tight text-zinc-800">{alerta.titulo}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-zinc-500">{alerta.descricao}</p>
                </div>
                <Badge variant={alerta.tipo === "info" ? "info" : alerta.tipo}>{alerta.badge}</Badge>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
