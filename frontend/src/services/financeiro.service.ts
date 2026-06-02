import type { ContaPagar, DashboardFinanceiro, PaginatedResponse, PaginationParams, CategoriaFinanceira } from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const financeiroService = {
  async dashboard() {
    const response = await api.get<DashboardFinanceiro>("/financeiro/dashboard/")
    return response.data
  },

  async contasPagar(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<ContaPagar>>(
      `/financeiro/contas-pagar/${toQueryString(params)}`
    )
    return response.data
  },

  async categorias(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<CategoriaFinanceira>>(
      `/financeiro/categorias/${toQueryString(params)}`
    )
    return response.data
  },
}
