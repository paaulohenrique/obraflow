"use client"

import Link from "next/link"
import { AlertCircle, ArrowRight, Package, AlertTriangle, FileCode, Landmark } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency, formatDate } from "@/lib/utils"
import { formatNumber } from "@/lib/format"
import { useDashboardResumo } from "./use-dashboard-resumo"

export function AtencaoPanel() {
  const { data, isLoading, isError } = useDashboardResumo()

  if (isError) return null

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={index} className="border border-zinc-200">
            <CardHeader className="h-10 bg-zinc-50 border-b border-zinc-200 animate-pulse" />
            <CardContent className="p-4 space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const boletos = data?.boletosPendentes?.results ?? []
  const notas = data?.notasPendentes?.results ?? []
  const produtos = data?.produtosCriticos?.results ?? []
  const contas = data?.contasAtrasadas?.results ?? []

  const totalAlertas = boletos.length + notas.length + produtos.length + contas.length

  if (totalAlertas === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 border border-zinc-200 border-dashed rounded-xl bg-white text-center">
        <div className="size-10 rounded-full bg-green-50 border border-green-100 flex items-center justify-center text-green-600 mb-3">
          <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h4 className="text-xs font-semibold text-zinc-900">Operação em dia</h4>
        <p className="text-[11px] text-zinc-400 mt-1">Nenhum boleto, nota fiscal ou estoque precisando de revisão imediata.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-1.5">
          <AlertCircle className="size-4 text-orange-500" /> O que precisa da sua atenção
        </h2>
        <Badge className="bg-orange-500/10 text-orange-600 border border-orange-500/20 font-bold text-[10px]">
          {totalAlertas} pendências
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* 1. Boletos Pendentes */}
        <Card className="border border-zinc-200/80 shadow-sm flex flex-col justify-between overflow-hidden">
          <div>
            <CardHeader className="flex flex-row items-center justify-between bg-zinc-50/50 border-b border-zinc-100 px-4 py-3">
              <span className="text-xs font-bold text-zinc-800 flex items-center gap-2">
                <Landmark className="size-4 text-zinc-400" /> Boletos OCR Pendentes
              </span>
              <span className="text-[10px] font-semibold text-zinc-400 uppercase">
                {data?.boletosPendentes?.count ?? 0} pendentes
              </span>
            </CardHeader>
            <CardContent className="p-0 divide-y divide-zinc-100">
              {boletos.length === 0 ? (
                <div className="p-4 text-center text-xs text-zinc-400">Nenhum boleto aguardando revisão.</div>
              ) : (
                boletos.map((b) => (
                  <div key={b.id} className="p-3 flex items-center justify-between text-xs hover:bg-zinc-50/20 transition-colors">
                    <div className="min-w-0 flex-1 pr-3">
                      <p className="font-semibold text-zinc-800 truncate" title={b.arquivo_nome_original}>
                        {b.arquivo_nome_original}
                      </p>
                      <p className="text-[10px] text-zinc-400 mt-0.5 truncate">
                        {b.fornecedor_nome_final || "Sem fornecedor extraído"} • Venc: {b.vencimento ? formatDate(b.vencimento) : "-"}
                      </p>
                    </div>
                    <div className="text-right flex items-center gap-3">
                      <span className="font-bold tabular-nums text-zinc-900">{b.valor ? formatCurrency(b.valor) : "-"}</span>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </div>
          {boletos.length > 0 && (
            <div className="p-2.5 bg-zinc-50/50 border-t border-zinc-100 text-right">
              <Link href="/boletos" className="inline-flex items-center gap-1 text-[11px] font-bold text-orange-500 hover:text-orange-600">
                Revisar no financeiro <ArrowRight className="size-3" />
              </Link>
            </div>
          )}
        </Card>

        {/* 2. NF-e Aguardando Revisão */}
        <Card className="border border-zinc-200/80 shadow-sm flex flex-col justify-between overflow-hidden">
          <div>
            <CardHeader className="flex flex-row items-center justify-between bg-zinc-50/50 border-b border-zinc-100 px-4 py-3">
              <span className="text-xs font-bold text-zinc-800 flex items-center gap-2">
                <FileCode className="size-4 text-zinc-400" /> NF-e XMLs p/ Conciliar
              </span>
              <span className="text-[10px] font-semibold text-zinc-400 uppercase">
                {data?.notasPendentes?.count ?? 0} pendentes
              </span>
            </CardHeader>
            <CardContent className="p-0 divide-y divide-zinc-100">
              {notas.length === 0 ? (
                <div className="p-4 text-center text-xs text-zinc-400">Nenhuma NF-e aguardando conciliação.</div>
              ) : (
                notas.map((n) => (
                  <div key={n.id} className="p-3 flex items-center justify-between text-xs hover:bg-zinc-50/20 transition-colors">
                    <div className="min-w-0 flex-1 pr-3">
                      <p className="font-semibold text-zinc-800 truncate">
                        Nota #{n.numero || "sem número"}
                      </p>
                      <p className="text-[10px] text-zinc-400 mt-0.5 truncate">
                        Emitido por: {n.fornecedor_nome_final} • {formatDate(n.data_emissao ?? "")}
                      </p>
                    </div>
                    <div className="text-right flex items-center gap-3">
                      <span className="font-bold tabular-nums text-zinc-900">{formatCurrency(n.valor_total)}</span>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </div>
          {notas.length > 0 && (
            <div className="p-2.5 bg-zinc-50/50 border-t border-zinc-100 text-right">
              <Link href="/fiscal" className="inline-flex items-center gap-1 text-[11px] font-bold text-orange-500 hover:text-orange-600">
                Conciliar notas XML <ArrowRight className="size-3" />
              </Link>
            </div>
          )}
        </Card>

        {/* 3. Estoque Crítico */}
        <Card className="border border-zinc-200/80 shadow-sm flex flex-col justify-between overflow-hidden">
          <div>
            <CardHeader className="flex flex-row items-center justify-between bg-zinc-50/50 border-b border-zinc-100 px-4 py-3">
              <span className="text-xs font-bold text-zinc-800 flex items-center gap-2">
                <Package className="size-4 text-zinc-400" /> Estoque Operacional Crítico
              </span>
              <span className="text-[10px] font-semibold text-zinc-400 uppercase">
                {data?.produtosCriticos?.count ?? 0} itens
              </span>
            </CardHeader>
            <CardContent className="p-0 divide-y divide-zinc-100">
              {produtos.length === 0 ? (
                <div className="p-4 text-center text-xs text-zinc-400">Nenhum produto abaixo do estoque mínimo.</div>
              ) : (
                produtos.map((p) => (
                  <div key={p.id} className="p-3 flex items-center justify-between text-xs hover:bg-zinc-50/20 transition-colors">
                    <div className="min-w-0 flex-1 pr-3">
                      <p className="font-semibold text-zinc-800 truncate">{p.nome}</p>
                      <p className="text-[10px] text-zinc-400 mt-0.5 truncate">
                        SKU: {p.sku || "sem SKU"} • Categoria: {p.categoria_nome}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="font-bold tabular-nums text-red-500">
                        {formatNumber(p.estoque_atual, 1)} {p.unidade_sigla}
                      </span>
                      <p className="text-[10px] text-zinc-400">Mín: {formatNumber(p.estoque_minimo, 1)}</p>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </div>
          {produtos.length > 0 && (
            <div className="p-2.5 bg-zinc-50/50 border-t border-zinc-100 text-right">
              <Link href="/estoque" className="inline-flex items-center gap-1 text-[11px] font-bold text-orange-500 hover:text-orange-600">
                Repor estoque de produtos <ArrowRight className="size-3" />
              </Link>
            </div>
          )}
        </Card>

        {/* 4. Contas Atrasadas */}
        <Card className="border border-zinc-200/80 shadow-sm flex flex-col justify-between overflow-hidden">
          <div>
            <CardHeader className="flex flex-row items-center justify-between bg-zinc-50/50 border-b border-zinc-100 px-4 py-3">
              <span className="text-xs font-bold text-zinc-800 flex items-center gap-2">
                <AlertTriangle className="size-4 text-zinc-400" /> Contas a Pagar Atrasadas
              </span>
              <span className="text-[10px] font-semibold text-zinc-400 uppercase">
                {data?.contasAtrasadas?.count ?? 0} vencidas
              </span>
            </CardHeader>
            <CardContent className="p-0 divide-y divide-zinc-100">
              {contas.length === 0 ? (
                <div className="p-4 text-center text-xs text-zinc-400">Nenhuma conta a pagar vencida.</div>
              ) : (
                contas.map((c) => (
                  <div key={c.id} className="p-3 flex items-center justify-between text-xs hover:bg-zinc-50/20 transition-colors">
                    <div className="min-w-0 flex-1 pr-3">
                      <p className="font-semibold text-zinc-800 truncate">{c.descricao}</p>
                      <p className="text-[10px] text-zinc-400 mt-0.5 truncate">
                        Fornecedor: {c.fornecedor_nome || "Direto"} • Vencimento: {formatDate(c.data_vencimento)}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="font-bold tabular-nums text-red-600">{formatCurrency(c.valor_restante)}</span>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </div>
          {contas.length > 0 && (
            <div className="p-2.5 bg-zinc-50/50 border-t border-zinc-100 text-right">
              <Link href="/financeiro" className="inline-flex items-center gap-1 text-[11px] font-bold text-orange-500 hover:text-orange-600">
                Pagar contas vencidas <ArrowRight className="size-3" />
              </Link>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
