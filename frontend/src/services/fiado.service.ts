import type {
  ContaFiado,
  DashboardFiado,
  HistoricoFiado,
  ItemFiado,
  ItemFiadoPayload,
  PagamentoFiado,
  PagamentoFiadoPayload,
  PaginatedResponse,
  PaginationParams,
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

export const fiadoService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<ContaFiado>>(`/fiado/contas/${toQueryString(params)}`)
    return response.data
  },

  async getContasFiadoByCliente(clienteId: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<ContaFiado>>(
      `/fiado/contas/${toQueryString({ cliente: clienteId, ordering: "-created_at", ...params })}`
    )
    return response.data
  },

  async getContaAbertaByCliente(clienteId: string) {
    const response = await api.get<PaginatedResponse<ContaFiado>>(
      `/fiado/contas/${toQueryString({ cliente: clienteId, status: "ABERTA", page_size: 1 })}`
    )
    return response.data.results[0] ?? null
  },

  async getHistoricoFiadoCliente(clienteId: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<ContaFiado>>(
      `/fiado/contas/${toQueryString({
        cliente: clienteId,
        status: "FECHADA",
        ordering: "-data_abertura",
        page_size: 20,
        ...params,
      })}`
    )
    return response.data
  },

  async dashboard() {
    const response = await api.get<DashboardFiado>("/fiado/dashboard/")
    return response.data
  },

  async get(id: string) {
    const response = await api.get<ContaFiado>(`/fiado/contas/${id}/`)
    return response.data
  },

  async itens(id: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<ItemFiado>>(
      `/fiado/contas/${id}/itens/${toQueryString(params)}`
    )
    return response.data
  },

  async adicionarItem(id: string, payload: ItemFiadoPayload) {
    const response = await api.post<ItemFiado>(`/fiado/contas/${id}/itens/`, payload)
    return response.data
  },

  async pagamentos(id: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<PagamentoFiado>>(
      `/fiado/contas/${id}/pagamentos/${toQueryString(params)}`
    )
    return response.data
  },

  async registrarPagamento(id: string, payload: PagamentoFiadoPayload) {
    const response = await api.post<PagamentoFiado>(`/fiado/contas/${id}/pagamentos/`, payload)
    return response.data
  },

  async historico(id: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<HistoricoFiado>>(
      `/fiado/contas/${id}/historico/${toQueryString(params)}`
    )
    return response.data
  },

  async baixarPdfContaFiado(id: string) {
    const response = await api.get<Blob>(`/fiado/contas/${id}/pdf/`, {
      responseType: "blob",
      headers: { Accept: "application/pdf" },
    })
    const filename = filenameFromDisposition(response.headers["content-disposition"], `fiado-${id.slice(0, 8)}.pdf`)
    downloadBlob(response.data, filename)
    return { blob: response.data, filename }
  },

  async abrirOuRecuperarContaFiado(clienteId: string): Promise<ContaFiado> {
    const contaAberta = await fiadoService.getContaAbertaByCliente(clienteId)
    if (contaAberta) return contaAberta

    const created = await api.post<ContaFiado>("/fiado/contas/", {
      cliente: clienteId,
      observacao: "Conta aberta pelo frontend",
    })
    return created.data
  },
}
