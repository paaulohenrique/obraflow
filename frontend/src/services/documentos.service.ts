import type {
  PaginatedResponse,
  PaginationParams,
  BoletoOCR,
  BoletoDashboard as DashboardBoletos,
  NotaEntrada,
  DashboardNotasEntrada,
  NotaItem,
  ProductSuggestion,
  NotaHistorico,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const boletosService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<BoletoOCR>>(`/boletos/${toQueryString(params)}`)
    return response.data
  },

  async dashboard() {
    const response = await api.get<DashboardBoletos>("/boletos/dashboard/")
    return response.data
  },
}

export const notasEntradaService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<NotaEntrada>>(`/notas-entrada/${toQueryString(params)}`)
    return response.data
  },

  async dashboard() {
    const response = await api.get<DashboardNotasEntrada>("/notas-entrada/dashboard/")
    return response.data
  },

  async get(id: string) {
    const response = await api.get<NotaEntrada & { itens: NotaItem[] }>(`/notas-entrada/${id}/`)
    return response.data
  },

  async itens(id: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<NotaItem>>(`/notas-entrada/${id}/itens/${toQueryString(params)}`)
    return response.data
  },

  async sugestoes(id: string, itemId: string) {
    const response = await api.get<ProductSuggestion[]>(`/notas-entrada/${id}/itens/${itemId}/sugestoes-produto/`)
    return response.data
  },

  async vincularItem(
    id: string,
    itemId: string,
    payload: {
      produto?: string | null
      forma_venda?: string | null
      custo_unitario?: number | string | null
      ignorado?: boolean
    }
  ) {
    const response = await api.patch<NotaItem>(`/notas-entrada/${id}/itens/${itemId}/`, payload)
    return response.data
  },

  async confirmar(
    id: string,
    payload: {
      criar_conta_pagar?: boolean
      dados_conta_pagar?: {
        categoria: string
        data_vencimento: string
        observacao?: string
      } | null
    }
  ) {
    const response = await api.post<NotaEntrada>(`/notas-entrada/${id}/confirmar/`, payload)
    return response.data
  },

  async rejeitar(id: string, payload: { motivo: string }) {
    const response = await api.post<NotaEntrada>(`/notas-entrada/${id}/rejeitar/`, payload)
    return response.data
  },

  async vincularFornecedor(id: string, payload: { fornecedor: string }) {
    const response = await api.post<NotaEntrada>(`/notas-entrada/${id}/vincular-fornecedor/`, payload)
    return response.data
  },

  async historico(id: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<NotaHistorico>>(`/notas-entrada/${id}/historico/${toQueryString(params)}`)
    return response.data
  },
}

