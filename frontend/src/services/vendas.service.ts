import type {
  CriarVendaPayload,
  DashboardVendas,
  PaginatedResponse,
  PaginationParams,
  Venda,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const vendasService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<Venda>>(
      `/pdv/vendas/${toQueryString(params)}`
    )
    return response.data
  },

  async get(id: string) {
    const response = await api.get<Venda>(`/pdv/vendas/${id}/`)
    return response.data
  },

  async criar(payload: CriarVendaPayload) {
    const response = await api.post<Venda>("/pdv/vendas/", payload)
    return response.data
  },

  async cancelar(id: string, motivo: string) {
    const response = await api.post<Venda>(`/pdv/vendas/${id}/cancelar/`, { motivo })
    return response.data
  },

  async dashboard() {
    const response = await api.get<DashboardVendas>("/pdv/vendas/dashboard/")
    return response.data
  },

  pdfUrl(id: string): string {
    return `/pdv/vendas/${id}/pdf/`
  },
}
