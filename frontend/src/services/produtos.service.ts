import type {
  CategoriaProduto,
  Fornecedor,
  PaginatedResponse,
  PaginationParams,
  Produto,
  ProdutoPayload,
  UnidadeMedida,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const produtosService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<Produto>>(
      `/estoque/produtos/${toQueryString(params)}`
    )
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

  async create(payload: ProdutoPayload) {
    const response = await api.post<Produto>("/estoque/produtos/", payload)
    return response.data
  },

  async update(id: string, payload: Partial<ProdutoPayload>) {
    const response = await api.patch<Produto>(`/estoque/produtos/${id}/`, payload)
    return response.data
  },

  async ativar(id: string) {
    const response = await api.post<Produto>(`/estoque/produtos/${id}/ativar/`)
    return response.data
  },

  async inativar(id: string) {
    const response = await api.post<Produto>(`/estoque/produtos/${id}/inativar/`)
    return response.data
  },

  async categorias(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<CategoriaProduto>>(
      `/estoque/categorias/${toQueryString(params)}`
    )
    return response.data
  },

  async unidades(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<UnidadeMedida>>(
      `/estoque/unidades/${toQueryString(params)}`
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
