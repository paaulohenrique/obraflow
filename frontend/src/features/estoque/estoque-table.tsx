"use client"

import Link from "next/link"
import { AlertTriangle, ChevronRight, PackageSearch } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { formatCurrency } from "@/lib/utils"
import { formatNumber, toNumber } from "@/lib/format"
import type { FormaVendaProduto, Produto } from "@/types"

interface EstoqueTableProps {
  produtos: Produto[]
  formasByProduto?: Record<string, FormaVendaProduto[]>
  loading?: boolean
}

export function EstoqueTable({ produtos, formasByProduto = {}, loading }: EstoqueTableProps) {
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
        <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-zinc-100">
          <PackageSearch className="size-5 text-zinc-400" />
        </div>
        <p className="text-sm font-medium text-zinc-700">Nenhum produto encontrado</p>
        <p className="mt-1 text-xs text-zinc-400">Ajuste os filtros e tente novamente.</p>
      </div>
    )
  }

  return (
    <Table>
      <Thead>
        <tr>
          <Th>SKU</Th>
          <Th>Produto</Th>
          <Th>Categoria</Th>
          <Th className="text-right">Saldo</Th>
          <Th className="text-right">Mínimo</Th>
          <Th className="text-right">Custo</Th>
          <Th className="text-right">Venda</Th>
          <Th className="text-right">Margem</Th>
          <Th>Status</Th>
          <Th />
        </tr>
      </Thead>
      <Tbody>
        {produtos.map((produto) => {
          const estoque = toNumber(produto.estoque_atual)
          const minimo = toNumber(produto.estoque_minimo)
          const semEstoque = estoque <= 0
          const baixo = produto.estoque_baixo || estoque <= minimo

          return (
            <Tr key={produto.id} clickable>
              <Td className="font-mono text-xs text-zinc-400">{produto.sku || produto.codigo_barras || "-"}</Td>
              <Td className="min-w-[280px] whitespace-normal">
                <div className="flex items-center gap-2">
                  {baixo && <AlertTriangle className="size-3.5 flex-shrink-0 text-yellow-500" />}
                  <span className="font-medium text-zinc-900">{produto.nome}</span>
                </div>
                {formasByProduto[produto.id]?.length ? (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {formasByProduto[produto.id].slice(0, 4).map((forma) => (
                      <span
                        key={forma.id}
                        title={`1 ${forma.unidade} = ${formatNumber(forma.fator_conversao, 3)} ${produto.unidade_sigla}`}
                        className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[11px] font-medium text-zinc-600"
                      >
                        {forma.nome}
                      </span>
                    ))}
                    {formasByProduto[produto.id].length > 4 && (
                      <span className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-zinc-400">
                        +{formasByProduto[produto.id].length - 4}
                      </span>
                    )}
                  </div>
                ) : null}
              </Td>
              <Td>
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600">
                  {produto.categoria_nome || "-"}
                </span>
              </Td>
              <Td className="text-right font-semibold tabular-nums text-zinc-900">
                {formatNumber(produto.estoque_atual, 3)} <span className="text-xs font-normal text-zinc-400">{produto.unidade_sigla}</span>
              </Td>
              <Td className="text-right tabular-nums text-zinc-400">{formatNumber(produto.estoque_minimo, 3)}</Td>
              <Td className="text-right tabular-nums text-zinc-600">{formatCurrency(produto.preco_compra)}</Td>
              <Td className="text-right font-medium tabular-nums text-zinc-900">{formatCurrency(produto.preco_venda)}</Td>
              <Td className="text-right">
                <span className="font-medium tabular-nums text-green-600">{formatNumber(produto.margem_percentual, 2)}%</span>
              </Td>
              <Td>
                <Badge variant={semEstoque ? "error" : baixo ? "warning" : "success"}>
                  {semEstoque ? "Sem estoque" : baixo ? "Baixo" : "Normal"}
                </Badge>
              </Td>
              <Td>
                <Link href={`/estoque/${produto.id}`}>
                  <Button variant="ghost" size="xs" icon={<ChevronRight className="size-3.5" />} />
                </Link>
              </Td>
            </Tr>
          )
        })}
      </Tbody>
    </Table>
  )
}
