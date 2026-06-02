import type {
  PaginationParams,
  ProdutoPayload,
} from "@/types"
import { formasVendaService } from "./formas-venda.service"
import { movimentacoesEstoqueService } from "./movimentacoes-estoque.service"
import { produtosService } from "./produtos.service"

export const estoqueService = {
  async categorias(params?: PaginationParams) {
    return produtosService.categorias(params)
  },

  async unidades(params?: PaginationParams) {
    return produtosService.unidades(params)
  },

  async list(params?: PaginationParams) {
    return produtosService.list(params)
  },

  async lowStock(params?: PaginationParams) {
    return produtosService.lowStock(params)
  },

  async get(id: string) {
    return produtosService.get(id)
  },

  async create(payload: ProdutoPayload) {
    return produtosService.create(payload)
  },

  async update(id: string, payload: Partial<ProdutoPayload>) {
    return produtosService.update(id, payload)
  },

  async ativar(id: string) {
    return produtosService.ativar(id)
  },

  async inativar(id: string) {
    return produtosService.inativar(id)
  },

  async movimentacoes(id: string, params?: PaginationParams) {
    return movimentacoesEstoqueService.byProduto(id, params)
  },

  async formasVenda(params?: PaginationParams & { produto?: string }) {
    return formasVendaService.list(params)
  },

  async fornecedores(params?: PaginationParams) {
    return produtosService.fornecedores(params)
  },
}
