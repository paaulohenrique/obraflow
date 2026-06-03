"use client"

import { useQuery } from "@tanstack/react-query"
import { MessageCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { SkeletonTable } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { formatCurrency, formatPhone, initials } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { clientesService } from "@/services/clientes.service"

export default function CobrancasPage() {
  const clientesQuery = useQuery({
    queryKey: ["cobrancas", "clientes-devedores"],
    queryFn: () => clientesService.list({ saldo_devedor__gt: 0, ordering: "-saldo_devedor", page_size: 50 }),
  })

  const clientes = clientesQuery.data?.results ?? []
  const totalPendente = clientes.reduce((sum, cliente) => sum + toNumber(cliente.saldo_devedor), 0)

  const handleWhatsapp = (nome: string, telefone: string) => {
    const cleanPhone = telefone.replace(/\D/g, "")
    if (!cleanPhone) return
    const msg = encodeURIComponent(`Olá, ${nome}. Podemos falar sobre sua pendência na MP Construções?`)
    window.open(`https://wa.me/55${cleanPhone}?text=${msg}`, "_blank")
  }

  return (
    <Shell>
      <Topbar title="Cobranças" subtitle="Clientes com saldo devedor" />

      <main className="flex-1 space-y-5 p-4 md:p-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Clientes Devedores" value={`${clientesQuery.data?.count ?? 0}`} accent />
          <StatCard label="Saldo Pendente" value={formatCurrency(totalPendente)} />
          <StatCard label="Página Atual" value={`${clientes.length} clientes`} />
          <StatCard label="Bloqueados" value={`${clientes.filter((cliente) => cliente.bloqueado).length}`} />
        </div>

        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-zinc-900">Fila de Cobranças</h3>
          </CardHeader>
          <CardContent className="p-0">
            {clientesQuery.isLoading ? (
              <SkeletonTable rows={6} cols={4} />
            ) : clientes.length === 0 ? (
              <EmptyState
                icon={<MessageCircle className="size-5" />}
                title="Nenhum cliente devedor"
                description="Quando houver saldo em aberto, os clientes aparecerão nesta fila para contato e acompanhamento."
              />
            ) : (
              <div className="divide-y divide-zinc-100">
                {clientes.map((cliente) => (
                  <div key={cliente.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-zinc-50/50">
                    <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-zinc-100">
                      <span className="text-xs font-semibold text-zinc-600">{initials(cliente.nome)}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-zinc-800">{cliente.nome}</p>
                      <p className="mt-0.5 text-xs text-zinc-400">{cliente.telefone ? formatPhone(cliente.telefone) : "Sem telefone"}</p>
                    </div>
                    <span className="text-sm font-semibold tabular-nums text-red-600">{formatCurrency(cliente.saldo_devedor)}</span>
                    <Badge variant={cliente.bloqueado ? "error" : "warning"}>{cliente.bloqueado ? "Bloqueado" : "Aberto"}</Badge>
                    <Button
                      size="xs"
                      variant="outline"
                      icon={<MessageCircle className="size-3.5" />}
                      disabled={!cliente.telefone}
                      onClick={() => handleWhatsapp(cliente.nome, cliente.telefone)}
                    >
                      WhatsApp
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </Shell>
  )
}
