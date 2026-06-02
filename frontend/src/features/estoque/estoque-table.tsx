"use client"

import Link from "next/link"
import { AlertTriangle, ArrowRight, PackageOpen } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { cn, formatCurrency, formatDate } from "@/lib/utils"
import { formatNumber, toNumber } from "@/lib/format"
import { estoqueService } from "@/services/estoque.service"
import type { FormaVendaProduto, Produto } from "@/types"

interface EstoqueTableProps {
  produtos: Produto[]
  formasByProduto?: Record<string, FormaVendaProduto[]>
  loading?: boolean
}

function formatRelativeDate(dateStr: string) {
  try {
    const d = new Date(dateStr)
    const now = new Date()
    
    // Zera horas para comparação de dias
    const dZero = new Date(d.getFullYear(), d.getMonth(), d.getDate())
    const nowZero = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    
    const diffTime = nowZero.getTime() - dZero.getTime()
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return "Hoje"
    if (diffDays === 1) return "Ontem"
    if (diffDays < 7) return `Há ${diffDays} dias`
    
    return formatDate(dateStr)
  } catch {
    return formatDate(dateStr)
  }
}

export function EstoqueTable({ produtos, formasByProduto = {}, loading }: EstoqueTableProps) {
  const queryClient = useQueryClient()

  const handlePrefetch = (id: string) => {
    queryClient.prefetchQuery({
      queryKey: ["estoque", "produtos", id],
      queryFn: () => estoqueService.get(id),
      staleTime: 30_000,
    })
    queryClient.prefetchQuery({
      queryKey: ["estoque", "formas-venda", id],
      queryFn: () => estoqueService.formasVenda({ produto: id, page_size: 100 }),
      staleTime: 30_000,
    })
    queryClient.prefetchQuery({
      queryKey: ["estoque", "movimentacoes", id],
      queryFn: () => estoqueService.movimentacoes(id, { page_size: 20 }),
      staleTime: 30_000,
    })
  }

  if (loading) {
    return (
      <div className="space-y-2 p-5">
        {Array.from({ length: 8 }).map((_, index) => (
          <Skeleton key={index} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (produtos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-zinc-50 border border-zinc-150 text-zinc-400">
          <PackageOpen className="size-5" />
        </div>
        <p className="text-sm font-semibold text-zinc-700">Nenhum produto encontrado</p>
        <p className="mt-1 text-xs text-zinc-400">Ajuste os filtros de busca ou de categorias.</p>
      </div>
    )
  }

  return (
    <Table>
      <Thead>
        <tr>
          <Th>Produto</Th>
          <Th className="text-right">Saldo Operacional</Th>
          <Th>Formas de Venda</Th>
          <Th className="text-right">Valores</Th>
          <Th>Última Movimentação</Th>
          <Th />
        </tr>
      </Thead>
      <Tbody>
        {produtos.map((produto) => {
          const estoque = toNumber(produto.estoque_atual)
          const minimo = toNumber(produto.estoque_minimo)
          const semEstoque = estoque <= 0
          const baixo = produto.estoque_baixo || estoque <= minimo

          const formas = formasByProduto[produto.id] ?? []
          const totalFormasStr = formas.length > 0 
            ? formas.map(f => f.nome).join(" • ") 
            : `Unidade (${produto.unidade_sigla})`

          return (
            <Tr
              key={produto.id}
              clickable
              onMouseEnter={() => handlePrefetch(produto.id)}
              className="hover:bg-zinc-50/40 transition-colors"
            >
              {/* Produto Typography Stack */}
              <Td className="py-3">
                <div className="flex items-start gap-2.5">
                  {baixo && (
                    <div className="mt-0.5" title="Estoque abaixo do mínimo">
                      <AlertTriangle className="size-4 text-yellow-500 flex-shrink-0" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <span className="font-semibold text-zinc-950 block text-xs">{produto.nome}</span>
                    <span className="mt-1 text-[10px] text-zinc-400 flex items-center gap-1.5 font-mono">
                      <span>SKU: {produto.sku || "sem SKU"}</span>
                      {produto.codigo_barras && (
                        <>
                          <span>•</span>
                          <span>EAN: {produto.codigo_barras}</span>
                        </>
                      )}
                      <span>•</span>
                      <span className="rounded bg-zinc-100 px-1 py-0.2 text-[9px] text-zinc-500 uppercase">{produto.categoria_nome}</span>
                    </span>
                  </div>
                </div>
              </Td>

              {/* Saldo Operacional */}
              <Td className="text-right py-3">
                <span className={cn(
                  "font-bold tabular-nums block text-xs",
                  semEstoque ? "text-red-650" : baixo ? "text-yellow-600" : "text-zinc-900"
                )}>
                  {formatNumber(produto.estoque_atual, 2)} <span className="text-[10px] font-normal text-zinc-450">{produto.unidade_sigla}</span>
                </span>
                <span className="text-[10px] text-zinc-400 block mt-0.5">
                  Mínimo: {formatNumber(produto.estoque_minimo, 1)}
                </span>
              </Td>

              {/* Formas de Venda */}
              <Td className="py-3 max-w-[200px] truncate text-xs text-zinc-600">
                <span className="font-medium" title={totalFormasStr}>{totalFormasStr}</span>
              </Td>

              {/* Valores Compra/Venda e Margem */}
              <Td className="text-right py-3">
                <span className="font-semibold tabular-nums block text-xs text-zinc-950">
                  {formatCurrency(produto.preco_venda)}
                </span>
                <span className="text-[10px] text-zinc-400 block mt-0.5 tabular-nums">
                  Custo: {formatCurrency(produto.preco_compra)} • <span className="text-green-600 font-medium">Margem {formatNumber(produto.margem_percentual, 1)}%</span>
                </span>
              </Td>

              {/* Última Movimentação & Status */}
              <Td className="py-3">
                <div className="flex items-center gap-2">
                  <Badge variant={semEstoque ? "error" : baixo ? "warning" : "success"}>
                    {semEstoque ? "Sem estoque" : baixo ? "Baixo" : "Normal"}
                  </Badge>
                  <span className="text-xs text-zinc-500">
                    {formatRelativeDate(produto.updated_at)}
                  </span>
                </div>
              </Td>

              {/* Ação */}
              <Td className="py-3 text-right">
                <Link href={`/estoque/${produto.id}`} passHref>
                  <Button variant="ghost" size="xs" icon={<ArrowRight className="size-3.5" />} />
                </Link>
              </Td>
            </Tr>
          )
        })}
      </Tbody>
    </Table>
  )
}
