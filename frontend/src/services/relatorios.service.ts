import type {
  DashboardExecutivo,
  PaginationParams,
  RelatorioEstoque,
  RelatorioFiado,
  RelatorioFinanceiro,
  RelatorioVendas,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

function filenameFromDisposition(value: string | undefined, fallback: string) {
  if (!value) return fallback
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1])
  const match = value.match(/filename="?([^";]+)"?/i)
  return match?.[1] ?? fallback
}

function downloadBlob(blob: Blob, filename: string) {
  if (typeof window === "undefined") return
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

async function baixarPdf(path: string, fallback: string, params?: PaginationParams) {
  const response = await api.get<Blob>(`${path}${toQueryString(params)}`, {
    responseType: "blob",
    headers: { Accept: "application/pdf" },
  })
  const filename = filenameFromDisposition(response.headers["content-disposition"], fallback)
  downloadBlob(response.data, filename)
  return { blob: response.data, filename }
}

export const relatoriosService = {
  async dashboardExecutivo() {
    const response = await api.get<DashboardExecutivo>("/relatorios/dashboard-executivo/")
    return response.data
  },

  async fiado(params?: PaginationParams) {
    const response = await api.get<RelatorioFiado>(`/relatorios/fiado/${toQueryString(params)}`)
    return response.data
  },

  async vendas(params?: PaginationParams) {
    const response = await api.get<RelatorioVendas>(`/relatorios/vendas/${toQueryString(params)}`)
    return response.data
  },

  async financeiro(params?: PaginationParams) {
    const response = await api.get<RelatorioFinanceiro>(`/relatorios/financeiro/${toQueryString(params)}`)
    return response.data
  },

  async estoque(params?: PaginationParams) {
    const response = await api.get<RelatorioEstoque>(`/relatorios/estoque/${toQueryString(params)}`)
    return response.data
  },

  async baixarPdfFiado(params?: PaginationParams) {
    return baixarPdf("/relatorios/fiado/pdf/", "relatorio-fiado.pdf", params)
  },

  async baixarPdfVendas(params?: PaginationParams) {
    return baixarPdf("/relatorios/vendas/pdf/", "relatorio-vendas.pdf", params)
  },

  async baixarPdfFinanceiro(params?: PaginationParams) {
    return baixarPdf("/relatorios/financeiro/pdf/", "relatorio-financeiro.pdf", params)
  },
}
