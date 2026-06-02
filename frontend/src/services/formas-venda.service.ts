import type {
  FormaVendaProduto,
  FormaVendaProdutoPayload,
  FormaVendaProdutoUpdatePayload,
  PaginatedResponse,
  PaginationParams,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const formasVendaService = {
  async list(params?: PaginationParams & { produto?: string }) {
    const response = await api.get<PaginatedResponse<FormaVendaProduto>>(
      `/estoque/formas-venda/${toQueryString(params)}`
    )
    return response.data
  },

  async get(id: string) {
    const response = await api.get<FormaVendaProduto>(`/estoque/formas-venda/${id}/`)
    return response.data
  },

  async create(payload: FormaVendaProdutoPayload) {
    const response = await api.post<FormaVendaProduto>("/estoque/formas-venda/", payload)
    return response.data
  },

  async update(id: string, payload: FormaVendaProdutoUpdatePayload) {
    const response = await api.patch<FormaVendaProduto>(`/estoque/formas-venda/${id}/`, payload)
    return response.data
  },

  async definirPadrao(id: string) {
    const response = await api.post<FormaVendaProduto>(`/estoque/formas-venda/${id}/definir-padrao/`)
    return response.data
  },

  async ativar(id: string) {
    const response = await api.post<FormaVendaProduto>(`/estoque/formas-venda/${id}/ativar/`)
    return response.data
  },

  async inativar(id: string) {
    const response = await api.post<FormaVendaProduto>(`/estoque/formas-venda/${id}/inativar/`)
    return response.data
  },
}
