"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Barcode, Check, ChevronLeft, ChevronRight, Package, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { cn, formatCurrency } from "@/lib/utils"
import { formatNumber } from "@/lib/format"
import { estoqueService } from "@/services/estoque.service"
import type { Produto } from "@/types"

interface ProdutoAutocompleteProps {
  value: Produto | null
  disabled?: boolean
  error?: boolean
  onSelect: (produto: Produto) => void
  onClear: () => void
}

function Highlight({ text, query }: { text: string; query: string }) {
  const trimmed = query.trim()
  if (!trimmed) return <>{text}</>

  const index = text.toLowerCase().indexOf(trimmed.toLowerCase())
  if (index < 0) return <>{text}</>

  return (
    <>
      {text.slice(0, index)}
      <mark className="rounded-sm bg-orange-100 px-0.5 text-orange-800">{text.slice(index, index + trimmed.length)}</mark>
      {text.slice(index + trimmed.length)}
    </>
  )
}

export function ProdutoAutocomplete({ value, disabled, error, onSelect, onClear }: ProdutoAutocompleteProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [activeIndex, setActiveIndex] = useState(0)
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const produtosQuery = useQuery({
    queryKey: ["estoque", "produtos", "fiado-autocomplete", { search: debouncedSearch, page }],
    queryFn: () =>
      estoqueService.list({
        page,
        page_size: 8,
        search: debouncedSearch,
        ordering: "nome",
        is_active: true,
      }),
    enabled: open && !disabled,
  })

  const produtos = useMemo(
    () => (produtosQuery.data?.results ?? []).filter((produto) => produto.is_active),
    [produtosQuery.data?.results]
  )
  const totalPages = produtosQuery.data?.total_pages ?? 1
  const currentPage = produtosQuery.data?.current_page ?? page

  useEffect(() => {
    if (open) return
    const timeout = window.setTimeout(() => setSearch(value?.nome ?? ""), 0)
    return () => window.clearTimeout(timeout)
  }, [open, value?.nome])

  useEffect(() => {
    const focusSearch = () => {
      inputRef.current?.focus()
      setOpen(true)
    }

    window.addEventListener("obraflow:focus-product-search", focusSearch)
    return () => window.removeEventListener("obraflow:focus-product-search", focusSearch)
  }, [])

  const selectProduto = (produto: Produto) => {
    onSelect(produto)
    setSearch(produto.nome)
    setOpen(false)
    setActiveIndex(0)
  }

  return (
    <div className="relative">
      <div
        className={cn(
          "flex h-10 items-center gap-2 rounded-md border bg-white px-3 transition-colors",
          error ? "border-red-500 ring-2 ring-red-500/20" : "border-zinc-300 focus-within:border-orange-500 focus-within:ring-2 focus-within:ring-orange-500/20",
          disabled && "bg-zinc-50 opacity-60"
        )}
      >
        <Search className="size-4 flex-shrink-0 text-zinc-400" />
        <input
          ref={inputRef}
          value={search}
          disabled={disabled}
          placeholder="Digite produto, SKU ou código de barras"
          className="h-full min-w-0 flex-1 bg-transparent text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none"
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setSearch(event.target.value)
            setPage(1)
            setActiveIndex(0)
            if (value && event.target.value !== value.nome) onClear()
          }}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault()
              setOpen(true)
              setActiveIndex((index) => Math.min(index + 1, Math.max(produtos.length - 1, 0)))
            }

            if (event.key === "ArrowUp") {
              event.preventDefault()
              setActiveIndex((index) => Math.max(index - 1, 0))
            }

            if (event.key === "Enter" && open && produtos[activeIndex]) {
              event.preventDefault()
              selectProduto(produtos[activeIndex])
            }

            if (event.key === "Escape") {
              setOpen(false)
            }
          }}
        />
        {value && (
          <span className="flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-semibold text-green-700">
            <Check className="size-3" />
            selecionado
          </span>
        )}
      </div>

      {open && !disabled && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-lg">
          {produtosQuery.isFetching ? (
            <div className="space-y-2 p-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <p className="text-xs text-zinc-400">Buscando produtos no estoque...</p>
            </div>
          ) : produtos.length === 0 ? (
            <div className="px-3 py-5 text-center">
              <Package className="mx-auto mb-2 size-5 text-zinc-300" />
              <p className="text-xs font-medium text-zinc-600">Nenhum produto encontrado</p>
              <p className="mt-1 text-[11px] text-zinc-400">Revise o nome, SKU ou código de barras.</p>
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto p-1.5">
              {produtos.map((produto, index) => (
                <button
                  key={produto.id}
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectProduto(produto)}
                  onMouseEnter={() => setActiveIndex(index)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-left transition-colors",
                    activeIndex === index ? "bg-zinc-100" : "hover:bg-zinc-50"
                  )}
                >
                  <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-md bg-zinc-100 text-zinc-500">
                    <Package className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-zinc-900">
                      <Highlight text={produto.nome} query={debouncedSearch} />
                    </p>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-zinc-500">
                      <span className="font-mono">{produto.sku || "sem SKU"}</span>
                      {produto.codigo_barras && (
                        <span className="flex items-center gap-1 font-mono">
                          <Barcode className="size-3" />
                          {produto.codigo_barras}
                        </span>
                      )}
                      <span>
                        saldo {formatNumber(produto.estoque_atual, 3)} {produto.unidade_sigla}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-semibold tabular-nums text-zinc-900">
                      {formatCurrency(produto.preco_venda)}
                    </p>
                    <p className="text-[10px] text-zinc-400">/{produto.unidade_sigla}</p>
                  </div>
                </button>
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50 px-2.5 py-2">
              <span className="text-[11px] text-zinc-500">
                Página {currentPage} de {totalPages}
              </span>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  disabled={currentPage <= 1 || produtosQuery.isFetching}
                  icon={<ChevronLeft className="size-3" />}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => {
                    setActiveIndex(0)
                    setPage((value) => Math.max(1, value - 1))
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  disabled={currentPage >= totalPages || produtosQuery.isFetching}
                  icon={<ChevronRight className="size-3" />}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => {
                    setActiveIndex(0)
                    setPage((value) => value + 1)
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
