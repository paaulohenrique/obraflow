import type {
  CategoriaProduto,
  FormaVendaProduto,
  MovimentacaoEstoque,
  PaginatedResponse,
  PaginationParams,
  Produto,
  Fornecedor,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const estoqueService = {
  async categorias(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<CategoriaProduto>>(
      `/estoque/categorias/${toQueryString(params)}`
    )
    return response.data
  },

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

  async fornecedores(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<Fornecedor>>(
      `/estoque/fornecedores/${toQueryString(params)}`
    )
    return response.data
  },
}
