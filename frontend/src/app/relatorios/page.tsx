"use client"

import Link from "next/link"
import { ArrowRight, HandCoins, Package, ShoppingBag, Wallet } from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"

const relatorios = [
  { href: "/relatorios/fiado", icon: HandCoins, titulo: "Fiado", detalhe: "Devedores, vencidos e recebido no mês" },
  { href: "/relatorios/vendas", icon: ShoppingBag, titulo: "Vendas", detalhe: "Ticket médio, rankings e vendas por dia" },
  { href: "/relatorios/financeiro", icon: Wallet, titulo: "Financeiro", detalhe: "Entradas, saídas, saldo e contas" },
  { href: "/relatorios/estoque", icon: Package, titulo: "Estoque", detalhe: "Valor de estoque, giro e produtos parados" },
]

export default function RelatoriosPage() {
  return (
    <Shell>
      <Topbar title="Relatórios" subtitle="Consultas gerenciais" />

      <main className="flex-1 p-4 md:p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {relatorios.map((relatorio) => {
            const Icon = relatorio.icon
            return (
              <Link key={relatorio.href} href={relatorio.href}>
              <Card className="transition-colors hover:border-orange-200 hover:bg-orange-50/20">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 flex-shrink-0 items-center justify-center rounded-lg border border-orange-100 bg-orange-50">
                      <Icon className="size-5 text-orange-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-semibold text-zinc-900">{relatorio.titulo}</h3>
                      <p className="mt-0.5 text-xs text-zinc-500">{relatorio.detalhe}</p>
                    </div>
                    <ArrowRight className="size-4 text-zinc-400" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="h-1 rounded-full bg-zinc-100">
                    <div className="h-1 w-16 rounded-full bg-orange-500" />
                  </div>
                </CardContent>
              </Card>
              </Link>
            )
          })}
        </div>
      </main>
    </Shell>
  )
}
