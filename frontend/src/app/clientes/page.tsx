"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Plus, Search } from "lucide-react"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ErrorState } from "@/components/ui/error-state"
import { Input } from "@/components/ui/input"
import { ClienteActionDrawer } from "@/features/clientes/cliente-action-drawer"
import { ClienteFormDialog } from "@/features/clientes/cliente-form-dialog"
import { ClientesTable } from "@/features/clientes/clientes-table"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { clientesService } from "@/services/clientes.service"
import type { Cliente } from "@/types"

type Filter = "todos" | "devedores" | "bloqueados"

export default function ClientesPage() {
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<Filter>("todos")
  const [open, setOpen] = useState(false)
  const [drawerCliente, setDrawerCliente] = useState<Cliente | null>(null)
  const [editCliente, setEditCliente] = useState<Cliente | null>(null)
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const clientesQuery = useQuery({
    queryKey: ["clientes", { search: debouncedSearch, page, filter }],
    queryFn: () =>
      clientesService.list({
        page,
        page_size: 20,
        search: debouncedSearch,
        ordering: "nome",
        ...(filter === "devedores" ? { saldo_devedor__gt: 0 } : {}),
        ...(filter === "bloqueados" ? { bloqueado: true } : {}),
      }),
  })

  const total = clientesQuery.data?.count ?? 0
  const currentPage = clientesQuery.data?.current_page ?? page
  const totalPages = clientesQuery.data?.total_pages ?? 1
  const clientes = clientesQuery.data?.results ?? []

  return (
    <Shell>
      <Topbar
        title="Clientes"
        subtitle="Gestão de clientes e crédito"
        actions={
          <Button size="sm" icon={<Plus className="size-3.5" />} onClick={() => setOpen(true)}>
            Novo Cliente
          </Button>
        }
      />

      <ClienteFormDialog
        open={open || Boolean(editCliente)}
        onOpenChange={(v) => {
          if (!v) { setOpen(false); setEditCliente(null) }
          else setOpen(true)
        }}
        cliente={editCliente ?? undefined}
      />

      <ClienteActionDrawer
        cliente={drawerCliente}
        onClose={() => setDrawerCliente(null)}
        onEdit={(c) => { setDrawerCliente(null); setEditCliente(c) }}
      />

      <main className="flex-1 p-6">
        <Card>
          <div className="flex flex-wrap items-center gap-3 border-b border-zinc-100 px-5 py-3.5">
            <div className="relative min-w-64 flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-zinc-400" />
              <Input
                placeholder="Buscar por nome, CPF/CNPJ, telefone..."
                value={search}
                onChange={(event) => {
                  setPage(1)
                  setSearch(event.target.value)
                }}
                className="pl-8"
              />
            </div>

            <div className="flex gap-1">
              {[
                ["todos", "Todos"],
                ["devedores", "Devedores"],
                ["bloqueados", "Bloqueados"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => {
                    setPage(1)
                    setFilter(value as Filter)
                  }}
                  className={`h-8 rounded-md border px-3 text-xs font-medium transition-colors ${
                    filter === value
                      ? "border-orange-300 bg-orange-50 text-orange-700"
                      : "border-zinc-200 text-zinc-500 hover:border-zinc-400 hover:text-zinc-800"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="ml-auto text-xs text-zinc-500">
              <span className="font-medium text-zinc-800">{total}</span> {total === 1 ? "cliente" : "clientes"}
            </div>
          </div>

          {clientesQuery.isError ? (
            <ErrorState onRetry={() => clientesQuery.refetch()} />
          ) : (
            <ClientesTable
              clientes={clientes}
              loading={clientesQuery.isLoading}
              onClienteClick={setDrawerCliente}
            />
          )}

          <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50/50 px-5 py-3">
            <span className="text-xs text-zinc-500">
              Página {currentPage} de {Math.max(totalPages, 1)}
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="xs"
                disabled={currentPage <= 1 || clientesQuery.isFetching}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="xs"
                disabled={currentPage >= totalPages || clientesQuery.isFetching}
                onClick={() => setPage((value) => value + 1)}
              >
                Próximo
              </Button>
            </div>
          </div>
        </Card>
      </main>
    </Shell>
  )
}
