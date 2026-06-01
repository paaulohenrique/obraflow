"use client"

import { BarChart3, HandCoins, Package, Users, Wallet } from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"

const relatorios = [
  { icon: HandCoins, titulo: "Fiado" },
  { icon: Users, titulo: "Clientes" },
  { icon: Package, titulo: "Estoque" },
  { icon: Wallet, titulo: "Financeiro" },
]

export default function RelatoriosPage() {
  return (
    <Shell>
      <Topbar title="Relatórios" subtitle="Consultas gerenciais" />

      <main className="flex-1 p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {relatorios.map((relatorio) => {
            const Icon = relatorio.icon
            return (
              <Card key={relatorio.titulo}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 flex-shrink-0 items-center justify-center rounded-lg border border-orange-100 bg-orange-50">
                      <Icon className="size-5 text-orange-500" />
                    </div>
                    <h3 className="text-sm font-semibold text-zinc-900">{relatorio.titulo}</h3>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2 text-sm text-zinc-500">
                    <BarChart3 className="size-4" />
                    Disponível após integração dos endpoints de relatórios.
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </main>
    </Shell>
  )
}
