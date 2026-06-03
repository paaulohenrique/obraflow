"use client"

import { Button } from "@/components/ui/button"

interface PaginationControlsProps {
  currentPage: number
  totalPages: number
  totalCount: number
  onPageChange: (page: number) => void
}

export function PaginationControls({
  currentPage,
  totalPages,
  totalCount,
  onPageChange,
}: PaginationControlsProps) {
  return (
    <div className="flex items-center justify-between border-t border-zinc-100 bg-white px-4 py-3">
      <span className="text-xs text-zinc-500">{totalCount} registros</span>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="xs"
          variant="outline"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          Anterior
        </Button>
        <span className="min-w-18 text-center text-xs font-medium text-zinc-600">
          {currentPage} / {Math.max(totalPages, 1)}
        </span>
        <Button
          type="button"
          size="xs"
          variant="outline"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
        >
          Próxima
        </Button>
      </div>
    </div>
  )
}
