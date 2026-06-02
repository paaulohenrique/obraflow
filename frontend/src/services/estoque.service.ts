import type {
  FormaVendaProduto,
  MovimentacaoEstoque,
  PaginatedResponse,
  PaginationParams,
  Produto,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const estoqueService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<Produto>>(`/estoque/produtos/${toQueryString(params)}`)
    return response.data
  },

  async lowStock(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<Produto>>(
      `/estoque/produtos/baixo-estoque/${toQueryString(params)}`
    )
    return response.data
  },

  async get(id: string) {
    const response = await api.get<Produto>(`/estoque/produtos/${id}/`)
    return response.data
  },

  async movimentacoes(id: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<MovimentacaoEstoque>>(
      `/estoque/produtos/${id}/movimentacoes/${toQueryString(params)}`
    )
    return response.data
  },

  async formasVenda(params?: PaginationParams & { produto?: string }) {
    const response = await api.get<PaginatedResponse<FormaVendaProduto>>(
      `/estoque/formas-venda/${toQueryString(params)}`
    )
    return response.data
  },
}
