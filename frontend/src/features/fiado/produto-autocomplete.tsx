"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Barcode, Check, ChevronLeft, ChevronRight, CornerDownLeft, Package, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { cn, formatCurrency } from "@/lib/utils"
import { formatNumber, toNumber } from "@/lib/format"
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
      <mark className="rounded-sm bg-orange-100 px-0.5 text-orange-850 font-semibold">{text.slice(index, index + trimmed.length)}</mark>
      {text.slice(index + trimmed.length)}
    </>
  )
}

export function ProdutoAutocomplete({ value, disabled, error, onSelect, onClear }: ProdutoAutocompleteProps) {
  const queryClient = useQueryClient()
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
      {/* Search Input Container */}
      <div
        className={cn(
          "flex h-11 items-center gap-3 rounded-lg border bg-white px-3.5 transition-all shadow-sm",
          error
            ? "border-red-500 ring-2 ring-red-500/20"
            : "border-zinc-300 focus-within:border-zinc-900 focus-within:ring-2 focus-within:ring-zinc-900/10",
          disabled && "bg-zinc-50 opacity-60"
        )}
      >
        <Barcode className="size-5 flex-shrink-0 text-zinc-500" />
        <input
          ref={inputRef}
          value={search}
          disabled={disabled}
          placeholder="Código de barras, SKU ou descrição do produto..."
          className="h-full min-w-0 flex-1 bg-transparent text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none font-medium"
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setSearch(event.target.value)
            setPage(1)
            setActiveIndex(0)
            if (value && event.target.value !== value.nome) onClear()
          }}
          onBlur={() => window.setTimeout(() => setOpen(false), 180)}
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
        
        {value ? (
          <span className="flex items-center gap-1 rounded-full bg-green-50 border border-green-200 px-2 py-0.5 text-[10px] font-bold text-green-700">
            <Check className="size-3" />
            VINCULADO
          </span>
        ) : (
          <div className="hidden md:flex items-center gap-1.5 text-[9px] text-zinc-400 font-mono select-none">
            <kbd className="bg-zinc-100 border border-zinc-200 px-1 py-0.2 rounded font-mono text-[8px] font-bold">F2</kbd>
            <span>Buscar</span>
          </div>
        )}
      </div>

      {/* Autocomplete Dropdown List */}
      {open && !disabled && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1.5 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-xl">
          {produtosQuery.isFetching ? (
            <div className="space-y-2 p-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <p className="text-[11px] text-zinc-400 text-center">Pesquisando no catálogo de estoque...</p>
            </div>
          ) : produtos.length === 0 ? (
            <div className="px-4 py-6 text-center">
              <Package className="mx-auto mb-2 size-6 text-zinc-300 animate-pulse" />
              <p className="text-xs font-semibold text-zinc-700">Nenhum produto correspondente</p>
              <p className="mt-1 text-[11px] text-zinc-400">Verifique a ortografia ou informe outro código.</p>
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto p-1.5 divide-y divide-zinc-50">
              {produtos.map((produto, index) => {
                const isSelected = activeIndex === index
                const semEstoque = toNumber(produto.estoque_atual) <= 0
                const baixoEstoque = produto.estoque_baixo || toNumber(produto.estoque_atual) <= toNumber(produto.estoque_minimo)
                
                return (
                  <button
                    key={produto.id}
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectProduto(produto)}
                    onMouseEnter={() => {
                      setActiveIndex(index)
                      queryClient.prefetchQuery({
                        queryKey: ["estoque", "formas-venda", produto.id],
                        queryFn: () => estoqueService.formasVenda({ produto: produto.id, page_size: 100 }),
                        staleTime: 30_000,
                      })
                    }}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors",
                      isSelected ? "bg-zinc-100/90" : "hover:bg-zinc-50"
                    )}
                  >
                    <div className={cn(
                      "flex size-8 flex-shrink-0 items-center justify-center rounded bg-zinc-100 text-zinc-500",
                      isSelected && "bg-zinc-200 text-zinc-700"
                    )}>
                      <Package className="size-4" />
                    </div>
                    
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-bold text-zinc-950">
                        <Highlight text={produto.nome} query={debouncedSearch} />
                      </p>
                      
                      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-zinc-450">
                        <span className="font-mono bg-zinc-50 px-1 py-0.2 rounded border border-zinc-150">{produto.sku || "sem SKU"}</span>
                        {produto.codigo_barras && (
                          <span className="flex items-center gap-0.5 font-mono">
                            <Barcode className="size-3 text-zinc-400" />
                            {produto.codigo_barras}
                          </span>
                        )}
                        <span>•</span>
                        <span className={cn(
                          "font-semibold",
                          semEstoque ? "text-red-650" : baixoEstoque ? "text-yellow-650" : "text-zinc-600"
                        )}>
                          Estoque: {formatNumber(produto.estoque_atual, 2)} {produto.unidade_sigla}
                        </span>
                      </div>
                    </div>

                    <div className="text-right flex-shrink-0 min-w-[70px]">
                      <p className="text-xs font-extrabold tabular-nums text-zinc-950">
                        {formatCurrency(produto.preco_venda)}
                      </p>
                      <p className="text-[10px] font-medium text-zinc-400">/{produto.unidade_sigla}</p>
                    </div>

                    {isSelected && (
                      <div className="flex-shrink-0 text-zinc-400 self-center pl-1">
                        <CornerDownLeft className="size-3.5" />
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Footer controls & Keyboard shortcuts guide */}
          <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50/80 px-3.5 py-2.5 text-[10px] text-zinc-450 font-medium">
            <div className="flex items-center gap-3">
              {totalPages > 1 && (
                <div className="flex items-center gap-1.5">
                  <span>
                    Pág. {currentPage}/{totalPages}
                  </span>
                  <div className="flex items-center gap-0.5">
                    <Button
                      type="button"
                      variant="outline"
                      size="xs"
                      className="size-5 p-0"
                      disabled={currentPage <= 1 || produtosQuery.isFetching}
                      icon={<ChevronLeft className="size-2.5" />}
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
                      className="size-5 p-0"
                      disabled={currentPage >= totalPages || produtosQuery.isFetching}
                      icon={<ChevronRight className="size-2.5" />}
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

            <div className="hidden sm:flex items-center gap-2.5 font-mono text-[9px] text-zinc-400 select-none">
              <span><kbd className="bg-zinc-150 px-1 py-0.2 rounded font-bold">↑↓</kbd> Navegar</span>
              <span><kbd className="bg-zinc-150 px-1 py-0.2 rounded font-bold">Enter</kbd> Confirmar</span>
              <span><kbd className="bg-zinc-150 px-1 py-0.2 rounded font-bold">Esc</kbd> Fechar</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
