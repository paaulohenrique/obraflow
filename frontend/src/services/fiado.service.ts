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

export const fiadoService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<ContaFiado>>(`/fiado/contas/${toQueryString(params)}`)
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

  async abrirOuRecuperarContaFiado(clienteId: string): Promise<ContaFiado> {
    const existing = await api.get<PaginatedResponse<ContaFiado>>(
      `/fiado/contas/?cliente=${clienteId}&status=ABERTA&page_size=1`
    )
    if (existing.data.count > 0) {
      return existing.data.results[0]
    }
    const created = await api.post<ContaFiado>("/fiado/contas/", {
      cliente: clienteId,
      observacao: "Conta aberta pelo frontend",
    })
    return created.data
  },
}
