"use client"

import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowRightLeft, CircleDollarSign, Package, PackagePlus, PowerOff, Search, AlertTriangle } from "lucide-react"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ErrorState } from "@/components/ui/error-state"
import { Input } from "@/components/ui/input"
import { StatCard } from "@/components/ui/stat-card"
import { EstoqueTable } from "@/features/estoque/estoque-table"
import { MovimentacaoEstoqueDialog } from "@/features/estoque/movimentacao-estoque-dialog"
import { ProdutoFormDialog } from "@/features/estoque/produto-form-dialog"
import { useApiToast } from "@/hooks/use-api-toast"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { formatCurrency } from "@/lib/utils"
import { estoqueService } from "@/services/estoque.service"
import type { FormaVendaProduto, ProdutoAuditoriaGrupo } from "@/types"

type Filter = "todos" | "baixo" | "ativos" | "inativos"

export default function EstoquePage() {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<Filter>("todos")
  const [categoria, setCategoria] = useState("")
  const [produtoDialogOpen, setProdutoDialogOpen] = useState(false)
  const [movimentacaoDialogOpen, setMovimentacaoDialogOpen] = useState(false)
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const produtosQuery = useQuery({
    queryKey: ["estoque", "produtos", { search: debouncedSearch, page, filter, categoria }],
    queryFn: () =>
      estoqueService.list({
        page,
        page_size: 20,
        search: debouncedSearch,
        ordering: "nome",
        ...(categoria ? { categoria } : {}),
        ...(filter === "baixo" ? { estoque_baixo: true } : {}),
        ...(filter === "ativos" ? { is_active: true } : {}),
        ...(filter === "inativos" ? { is_active: false } : {}),
      }),
    staleTime: 30_000,
  })

  const baixoQuery = useQuery({
    queryKey: ["estoque", "baixo", "count"],
    queryFn: () => estoqueService.lowStock({ page_size: 1 }),
    staleTime: 30_000,
  })

  const formasQuery = useQuery({
    queryKey: ["estoque", "formas-venda", "list"],
    queryFn: () => estoqueService.formasVenda({ page_size: 500 }),
    staleTime: 30_000,
  })

  const categoriasQuery = useQuery({
    queryKey: ["estoque", "categorias", "chips"],
    queryFn: () => estoqueService.categorias({ page_size: 20, ordering: "nome" }),
    staleTime: 30_000,
  })

  const auditoriaQuery = useQuery({
    queryKey: ["estoque", "auditoria-operacional"],
    queryFn: estoqueService.auditoriaOperacional,
    staleTime: 30_000,
  })

  const criarFormaMutation = useMutation({
    mutationFn: (produtoId: string) => estoqueService.garantirFormaVenda(produtoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      toast.success("Forma de venda criada")
    },
    onError: (error) => toast.error(error),
  })

  const total = produtosQuery.data?.count ?? 0
  const totalPages = produtosQuery.data?.total_pages ?? 1
  const currentPage = produtosQuery.data?.current_page ?? page
  const produtos = produtosQuery.data?.results ?? []
  const formasVenda = formasQuery.data?.results
  const formasByProduto = useMemo(() => {
    const grouped: Record<string, FormaVendaProduto[]> = {}
    for (const forma of formasVenda ?? []) {
      grouped[forma.produto_id] = [...(grouped[forma.produto_id] ?? []), forma]
    }
    return grouped
  }, [formasVenda])
  const categorias = categoriasQuery.data?.results ?? []

  return (
    <Shell>
      <Topbar
        title="Estoque"
        subtitle="Produtos, saldos, formas de venda e movimentações"
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              icon={<ArrowRightLeft className="size-3.5" />}
              onClick={() => setMovimentacaoDialogOpen(true)}
            >
              Movimentar
            </Button>
            <Button
              size="sm"
              icon={<PackagePlus className="size-3.5" />}
              onClick={() => setProdutoDialogOpen(true)}
            >
              Novo Produto
            </Button>
          </>
        }
      />

      <main className="flex-1 space-y-5 p-4 md:p-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="SKUs Encontrados" value={`${total} ${total === 1 ? "produto" : "produtos"}`} icon={<Package className="size-4" />} />
          <StatCard
            label="Estoque Baixo"
            value={`${baixoQuery.data?.count ?? 0} ${baixoQuery.data?.count === 1 ? "produto" : "produtos"}`}
            accent
            icon={<AlertTriangle className="size-4" />}
          />
          <StatCard label="Página Atual" value={`${produtos.length} itens`} />
          <StatCard label="Formas de Venda" value={`${formasQuery.data?.count ?? 0}`} />
        </div>

        <Card>
          <div className="border-b border-zinc-100 px-5 py-3.5">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4 text-orange-500" />
              <h3 className="text-sm font-semibold text-zinc-900">Produtos Problemáticos</h3>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
            <AuditMetric
              label="Sem forma"
              value={auditoriaQuery.data?.sem_forma_venda.count ?? 0}
              icon={<PackagePlus className="size-4" />}
            />
            <AuditMetric
              label="Sem preço"
              value={auditoriaQuery.data?.sem_preco.count ?? 0}
              icon={<CircleDollarSign className="size-4" />}
            />
            <AuditMetric
              label="Sem categoria"
              value={auditoriaQuery.data?.sem_categoria.count ?? 0}
              icon={<Package className="size-4" />}
            />
            <AuditMetric
              label="Sem unidade"
              value={auditoriaQuery.data?.sem_unidade.count ?? 0}
              icon={<Package className="size-4" />}
            />
            <AuditMetric
              label="Inativos"
              value={auditoriaQuery.data?.inativos.count ?? 0}
              icon={<PowerOff className="size-4" />}
            />
          </div>

          {(auditoriaQuery.data?.sem_forma_venda.count ?? 0) > 0 && (
            <AuditList
              title="Sem forma de venda"
              group={auditoriaQuery.data?.sem_forma_venda}
              actionLabel="Criar agora"
              loading={criarFormaMutation.isPending}
              onAction={(produtoId) => criarFormaMutation.mutate(produtoId)}
            />
          )}

          {(auditoriaQuery.data?.sem_preco.count ?? 0) > 0 && (
            <AuditList title="Sem preço" group={auditoriaQuery.data?.sem_preco} />
          )}

          {(auditoriaQuery.data?.sem_categoria.count ?? 0) > 0 && (
            <AuditList title="Sem categoria" group={auditoriaQuery.data?.sem_categoria} />
          )}

          {(auditoriaQuery.data?.sem_unidade.count ?? 0) > 0 && (
            <AuditList title="Sem unidade" group={auditoriaQuery.data?.sem_unidade} />
          )}

          {(auditoriaQuery.data?.inativos.count ?? 0) > 0 && (
            <AuditList title="Inativos" group={auditoriaQuery.data?.inativos} />
          )}
        </Card>

        <Card>
          <div className="flex flex-wrap items-center gap-3 border-b border-zinc-100 px-5 py-3.5">
            <div className="relative min-w-64 flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-zinc-400" />
              <Input
                placeholder="Buscar produto, SKU, código..."
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
                ["ativos", "Ativos"],
                ["inativos", "Inativos"],
                ["baixo", "Estoque baixo"],
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
          </div>

          <div className="flex gap-1 overflow-x-auto border-b border-zinc-100 px-5 py-3">
            <button
              type="button"
              onClick={() => {
                setPage(1)
                setCategoria("")
              }}
              className={`h-8 whitespace-nowrap rounded-md border px-3 text-xs font-medium transition-colors ${
                !categoria
                  ? "border-zinc-900 bg-zinc-900 text-white"
                  : "border-zinc-200 text-zinc-500 hover:border-zinc-400 hover:text-zinc-800"
              }`}
            >
              Todas categorias
            </button>
            {categorias.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setPage(1)
                  setCategoria(item.id)
                }}
                className={`h-8 whitespace-nowrap rounded-md border px-3 text-xs font-medium transition-colors ${
                  categoria === item.id
                    ? "border-zinc-900 bg-zinc-900 text-white"
                    : "border-zinc-200 text-zinc-500 hover:border-zinc-400 hover:text-zinc-800"
                }`}
              >
                {item.nome}
              </button>
            ))}
          </div>

          {produtosQuery.isError ? (
            <ErrorState onRetry={() => produtosQuery.refetch()} />
          ) : (
            <EstoqueTable
              produtos={produtos}
              formasByProduto={formasByProduto}
              loading={produtosQuery.isLoading}
              onCreateClick={() => setProdutoDialogOpen(true)}
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
                disabled={currentPage <= 1 || produtosQuery.isFetching}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="xs"
                disabled={currentPage >= totalPages || produtosQuery.isFetching}
                onClick={() => setPage((value) => value + 1)}
              >
                Próximo
              </Button>
            </div>
          </div>
        </Card>

        <ProdutoFormDialog open={produtoDialogOpen} onOpenChange={setProdutoDialogOpen} />
        <MovimentacaoEstoqueDialog open={movimentacaoDialogOpen} onOpenChange={setMovimentacaoDialogOpen} />
      </main>
    </Shell>
  )
}

function AuditMetric({
  label,
  value,
  icon,
}: {
  label: string
  value: number
  icon: React.ReactNode
}) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2">
      <div className="flex items-center gap-2 text-[11px] font-medium text-zinc-500">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-lg font-semibold text-zinc-900 tabular-nums">{value}</p>
    </div>
  )
}

function AuditList({
  title,
  group,
  actionLabel,
  loading,
  onAction,
}: {
  title: string
  group?: ProdutoAuditoriaGrupo
  actionLabel?: string
  loading?: boolean
  onAction?: (produtoId: string) => void
}) {
  if (!group || group.results.length === 0) return null

  return (
    <div className="border-t border-zinc-100 px-5 py-3">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">{title}</h4>
        <span className="text-[11px] text-zinc-400">{group.count} encontrados</span>
      </div>
      <div className="divide-y divide-zinc-100 rounded-md border border-zinc-100">
        {group.results.map((produto) => (
          <div key={produto.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-zinc-900">{produto.nome}</p>
              <p className="text-[11px] text-zinc-500">
                {produto.sku || "Sem SKU"} · {produto.unidade_sigla || "sem unidade"} · {formatCurrency(produto.preco_venda)}
              </p>
            </div>
            {actionLabel && onAction && (
              <Button
                type="button"
                size="xs"
                variant="outline"
                loading={loading}
                disabled={loading}
                onClick={() => onAction(produto.id)}
              >
                {actionLabel}
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
