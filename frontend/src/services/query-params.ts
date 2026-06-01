import type { PaginationParams } from "@/types"

export function toQueryString(params?: PaginationParams) {
  if (!params) return ""

  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return
    search.set(key, String(value))
  })

  const qs = search.toString()
  return qs ? `?${qs}` : ""
}
