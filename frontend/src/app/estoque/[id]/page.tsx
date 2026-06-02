"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, History, Package, Ruler, XCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { formatCurrency, formatDate } from "@/lib/utils"
import { formatNumber, toNumber } from "@/lib/format"
import { estoqueService } from "@/services/estoque.service"

export default function ProdutoDetalhePage() {
  const { id } = useParams<{ id: string }>()

  const produtoQuery = useQuery({
    queryKey: ["estoque", "produtos", id],
    queryFn: () => estoqueService.get(id),
    staleTime: 30_000,
  })

  const formasQuery = useQuery({
    queryKey: ["estoque", "formas-venda", id],
    queryFn: () => estoqueService.formasVenda({ produto: id, page_size: 100 }),
    enabled: Boolean(produtoQuery.data),
    staleTime: 30_000,
  })

  const movimentacoesQuery = useQuery({
    queryKey: ["estoque", "movimentacoes", id],
    queryFn: () => estoqueService.movimentacoes(id, { page_size: 20 }),
    enabled: Boolean(produtoQuery.data),
    staleTime: 30_000,
  })

  const produto = produtoQuery.data

  if (produtoQuery.isLoading) {
    return (
      <Shell>
        <Topbar title="Produto" />
        <main className="flex-1 space-y-5 p-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-80 w-full" />
        </main>
      </Shell>
    )
  }

  if (!produto) {
    return (
      <Shell>
        <Topbar title="Produto não encontrado" />
        <main className="flex flex-1 flex-col items-center justify-center gap-3 p-6">
          <XCircle className="size-12 text-zinc-300" />
          <p className="text-sm text-zinc-500">Este produto não existe ou foi removido.</p>
          <Link href="/estoque">
            <Button variant="outline" size="sm" icon={<ArrowLeft className="size-3.5" />}>
              Voltar
            </Button>
          </Link>
        </main>
      </Shell>
    )
  }

  const estoque = toNumber(produto.estoque_atual)
  const minimo = toNumber(produto.estoque_minimo)
  const baixo = produto.estoque_baixo || estoque <= minimo
  const semEstoque = estoque <= 0
  const formas = formasQuery.data?.results ?? []
  const movimentacoes = movimentacoesQuery.data?.results ?? []

  return (
    <Shell>
      <Topbar
        title={produto.nome}
        subtitle={`SKU ${produto.sku || "-"} · Unidade base ${produto.unidade_sigla}`}
        actions={
          <Link href="/estoque">
            <Button variant="ghost" size="sm" icon={<ArrowLeft className="size-3.5" />}>
              Voltar
            </Button>
          </Link>
        }
      />

      <main className="flex-1 space-y-5 p-6">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <Card>
            <CardContent className="space-y-4 py-5">
              <div className="flex items-center gap-3">
                <div className="flex size-11 flex-shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-50">
                  <Package className="size-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm font-bold leading-tight text-zinc-900">{produto.nome}</p>
                  <p className="mt-1 text-xs text-zinc-400">{produto.categoria_nome || "Sem categoria"}</p>
                </div>
              </div>

              <div className="space-y-2 border-t border-zinc-100 pt-3 text-xs text-zinc-600">
                {produto.descricao && <p className="pb-2 text-[11px] text-zinc-500">{produto.descricao}</p>}
                <div className="flex justify-between gap-3">
                  <span>Custo</span>
                  <span className="font-semibold text-zinc-800">{formatCurrency(produto.preco_compra)}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span>Venda</span>
                  <span className="font-semibold text-zinc-800">{formatCurrency(produto.preco_venda)}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span>Margem</span>
                  <span className="font-semibold text-green-600">{formatNumber(produto.margem_percentual, 2)}%</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardContent className="space-y-5 py-5">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Saldo</span>
                  <p className="mt-1 text-2xl font-black tabular-nums text-zinc-900">
                    {formatNumber(produto.estoque_atual, 3)} <span className="text-xs font-normal text-zinc-500">{produto.unidade_sigla}</span>
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Mínimo</span>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-zinc-700">
                    {formatNumber(produto.estoque_minimo, 3)} <span className="text-xs font-normal text-zinc-500">{produto.unidade_sigla}</span>
                  </p>
                </div>
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Status</span>
                  <div className="mt-2">
                    <Badge variant={semEstoque ? "error" : baixo ? "warning" : "success"}>
                      {semEstoque ? "Sem estoque" : baixo ? "Baixo" : "Normal"}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="border-t border-zinc-100 pt-4">
                <div className="mb-2 flex justify-between text-xs text-zinc-500">
                  <span>Nível de segurança</span>
                  <span className="font-semibold text-zinc-800">
                    {formatNumber(produto.estoque_atual, 3)} / {formatNumber(produto.estoque_minimo, 3)}
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-100">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      estoque <= minimo / 2 ? "bg-red-500" : baixo ? "bg-yellow-500" : "bg-green-500"
                    }`}
                    style={{ width: `${minimo > 0 ? Math.min((estoque / minimo) * 100, 100) : 100}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader className="flex items-center justify-between pb-3">
            <div className="flex items-center gap-2">
              <Ruler className="size-4 text-zinc-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900">Formas de Venda</h3>
            </div>
            <Badge variant="outline">{formasQuery.data?.count ?? 0}</Badge>
          </CardHeader>
          <CardContent className="p-0">
            {formasQuery.isLoading ? (
              <div className="space-y-2 p-5">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-10 w-full" />
                ))}
              </div>
            ) : formas.length === 0 ? (
              <div className="py-12 text-center text-xs text-zinc-400">Nenhuma forma de venda cadastrada.</div>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Nome</Th>
                    <Th>Código</Th>
                    <Th>Unidade</Th>
                    <Th className="text-right">Fator</Th>
                    <Th className="text-right">Preço</Th>
                    <Th>Status</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {formas.map((forma) => (
                    <Tr key={forma.id}>
                      <Td className="font-medium text-zinc-900">{forma.nome}</Td>
                      <Td className="font-mono text-xs text-zinc-500">{forma.codigo || "-"}</Td>
                      <Td>{forma.unidade}</Td>
                      <Td className="text-right tabular-nums">
                        1 {forma.unidade} = {formatNumber(forma.fator_conversao, 3)} {produto.unidade_sigla}
                      </Td>
                      <Td className="text-right tabular-nums">{formatCurrency(forma.preco_venda)}</Td>
                      <Td>
                        <Badge variant={forma.ativo ? "success" : "outline"}>{forma.padrao ? "Padrão" : forma.ativo ? "Ativa" : "Inativa"}</Badge>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex items-center justify-between pb-3">
            <div className="flex items-center gap-2">
              <History className="size-4 text-zinc-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900">Movimentações</h3>
            </div>
            <Badge variant="outline">{movimentacoesQuery.data?.count ?? 0}</Badge>
          </CardHeader>
          <CardContent className="p-0">
            {movimentacoesQuery.isLoading ? (
              <div className="space-y-2 p-5">
                {Array.from({ length: 5 }).map((_, index) => (
                  <Skeleton key={index} className="h-10 w-full" />
                ))}
              </div>
            ) : movimentacoes.length === 0 ? (
              <div className="py-12 text-center text-xs text-zinc-400">Nenhuma movimentação encontrada.</div>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Data</Th>
                    <Th>Tipo</Th>
                    <Th className="text-right">Quantidade</Th>
                    <Th className="text-right">Antes</Th>
                    <Th className="text-right">Depois</Th>
                    <Th>Motivo</Th>
                    <Th>Forma</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {movimentacoes.map((movimentacao) => {
                    const entrada = toNumber(movimentacao.quantidade_delta) > 0
                    return (
                      <Tr key={movimentacao.id}>
                        <Td className="text-xs text-zinc-500">{formatDate(movimentacao.created_at)}</Td>
                        <Td>
                          <Badge variant={entrada ? "success" : movimentacao.tipo === "AJUSTE" ? "default" : "error"}>
                            {movimentacao.tipo}
                          </Badge>
                        </Td>
                        <Td className={`text-right font-bold tabular-nums ${entrada ? "text-green-600" : "text-red-600"}`}>
                          {formatNumber(movimentacao.quantidade_delta, 3)}
                        </Td>
                        <Td className="text-right tabular-nums text-zinc-500">{formatNumber(movimentacao.estoque_antes, 3)}</Td>
                        <Td className="text-right font-semibold tabular-nums text-zinc-800">{formatNumber(movimentacao.estoque_depois, 3)}</Td>
                        <Td className="max-w-[220px] truncate text-xs text-zinc-600">{movimentacao.motivo || "-"}</Td>
                        <Td className="text-xs text-zinc-500">{movimentacao.forma_venda_nome || "-"}</Td>
                      </Tr>
                    )
                  })}
                </Tbody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </Shell>
  )
}
