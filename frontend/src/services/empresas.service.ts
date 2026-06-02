import type { ConfiguracaoFiscalEmpresa, Empresa, PaginatedResponse, PaginationParams } from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const empresasService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<Empresa>>(`/empresas/${toQueryString(params)}`)
    return response.data
  },

  async get(id: string) {
    const response = await api.get<Empresa>(`/empresas/${id}/`)
    return response.data
  },

  async getFiscal() {
    const response = await api.get<ConfiguracaoFiscalEmpresa>("/empresas/fiscal/")
    return response.data
  },

  async updateFiscal(data: Partial<ConfiguracaoFiscalEmpresa>) {
    const response = await api.patch<ConfiguracaoFiscalEmpresa>("/empresas/fiscal/", data)
    return response.data
  },
}
