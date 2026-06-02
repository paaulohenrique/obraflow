import type {
  MovimentacaoEstoque,
  MovimentacaoEstoquePayload,
  PaginatedResponse,
  PaginationParams,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const movimentacoesEstoqueService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<MovimentacaoEstoque>>(
      `/estoque/movimentacoes/${toQueryString(params)}`
    )
    return response.data
  },

  async byProduto(produtoId: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<MovimentacaoEstoque>>(
      `/estoque/produtos/${produtoId}/movimentacoes/${toQueryString(params)}`
    )
    return response.data
  },

  async entrada(payload: MovimentacaoEstoquePayload) {
    const response = await api.post<MovimentacaoEstoque>("/estoque/movimentacoes/entrada/", payload)
    return response.data
  },

  async saida(payload: MovimentacaoEstoquePayload) {
    const response = await api.post<MovimentacaoEstoque>("/estoque/movimentacoes/saida/", payload)
    return response.data
  },

  async ajuste(payload: MovimentacaoEstoquePayload) {
    const response = await api.post<MovimentacaoEstoque>("/estoque/movimentacoes/ajuste/", payload)
    return response.data
  },

  async devolucao(payload: MovimentacaoEstoquePayload) {
    const response = await api.post<MovimentacaoEstoque>("/estoque/movimentacoes/devolucao/", payload)
    return response.data
  },

  async cancelar(id: string, payload: { motivo: string; observacao?: string; idempotency_key?: string }) {
    const response = await api.post<MovimentacaoEstoque>(
      `/estoque/movimentacoes/${id}/cancelar/`,
      payload
    )
    return response.data
  },
}
