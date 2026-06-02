export type ApiDecimal = string | number

export interface ApiError {
  message: string
  status: number
  errors?: Record<string, string[] | string>
  requestId?: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  total_pages: number
  current_page: number
  results: T[]
}

export interface PaginationParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  [key: string]: string | number | boolean | undefined
}

export interface User {
  id: string
  email: string
  name: string
  role: string
  company_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Empresa {
  id: string
  razao_social: string
  nome_fantasia: string
  cnpj: string
  telefone: string
  email: string
  plano: "basico" | "profissional" | "enterprise"
  limite_usuarios: number
  total_usuarios?: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface AuthUser extends User {
  empresa?: Empresa | null
}

export type TipoPessoa = "PF" | "PJ"

export interface Cliente {
  id: string
  nome: string
  tipo_pessoa: TipoPessoa
  cpf_cnpj: string
  telefone: string
  whatsapp: string
  email: string
  cep?: string
  rua?: string
  numero?: string
  bairro?: string
  cidade?: string
  estado?: string
  complemento?: string
  observacao?: string
  limite_credito: ApiDecimal
  saldo_devedor: ApiDecimal
  credito_disponivel: ApiDecimal
  inadimplente: boolean
  bloqueado: boolean
  data_ultimo_pagamento?: string | null
  is_active: boolean
  company_id?: string
  created_at: string
  updated_at: string
}

export interface ClientePayload {
  nome: string
  tipo_pessoa: TipoPessoa
  cpf_cnpj: string
  telefone?: string
  whatsapp?: string
  email?: string
  cep?: string
  rua?: string
  numero?: string
  bairro?: string
  cidade?: string
  estado?: string
  complemento?: string
  observacao?: string
  limite_credito?: ApiDecimal
  data_ultimo_pagamento?: string | null
}

export interface Produto {
  id: string
  company_id: string
  nome: string
  descricao?: string
  sku: string
  codigo_barras: string
  categoria: string
  categoria_nome: string
  fornecedor_principal: string | null
  fornecedor_nome: string | null
  unidade: string
  unidade_sigla: string
  preco_compra: ApiDecimal
  preco_venda: ApiDecimal
  custo_medio: ApiDecimal
  estoque_atual: ApiDecimal
  estoque_minimo: ApiDecimal
  estoque_baixo: boolean
  margem_percentual: ApiDecimal
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CategoriaProduto {
  id: string
  company_id: string
  nome: string
  descricao?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FormaVendaProduto {
  id: string
  company_id: string
  produto_id: string
  produto_nome: string
  nome: string
  codigo: string
  unidade: string
  fator_conversao: ApiDecimal
  preco_venda: ApiDecimal
  ativo: boolean
  padrao: boolean
  permite_fracionado: boolean
  quantidade_convertida_exemplo: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type TipoMovimentacao = "ENTRADA" | "SAIDA" | "AJUSTE" | "DEVOLUCAO" | "CANCELAMENTO"

export interface MovimentacaoEstoque {
  id: string
  company_id: string
  produto: string
  produto_nome: string
  produto_sku: string
  tipo: TipoMovimentacao
  quantidade_delta: ApiDecimal
  quantidade_convertida: ApiDecimal
  forma_venda: string | null
  forma_venda_nome: string | null
  quantidade_informada: ApiDecimal | null
  estoque_antes: ApiDecimal
  estoque_depois: ApiDecimal
  custo_unitario: ApiDecimal | null
  valor_total: ApiDecimal
  fornecedor: string | null
  fornecedor_nome: string | null
  motivo: string
  observacao: string
  status: "ATIVA" | "CANCELADA"
  created_by: string | null
  created_by_nome: string | null
  movimentacao_cancelada: string | null
  created_at: string
  updated_at: string
}

export type StatusContaFiado = "ABERTA" | "FECHADA" | "CANCELADA"

export interface ContaFiado {
  id: string
  company_id: string
  cliente: string
  cliente_nome: string
  cliente_cpf_cnpj: string
  status: StatusContaFiado
  valor_total: ApiDecimal
  valor_pago: ApiDecimal
  valor_restante: ApiDecimal
  data_abertura: string
  data_vencimento: string | null
  data_fechamento: string | null
  observacao?: string
  is_parcial: boolean
  is_atrasada: boolean
  dias_atraso: number
  created_by: string | null
  created_by_nome: string | null
  closed_by?: string | null
  closed_by_nome?: string | null
  cancelled_by?: string | null
  cancelled_by_nome?: string | null
  cancelled_at?: string | null
  motivo_cancelamento?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ItemFiado {
  id: string
  company_id: string
  conta: string
  produto: string
  produto_nome: string
  produto_sku: string
  forma_venda: string | null
  forma_venda_nome: string | null
  quantidade_informada: ApiDecimal | null
  quantidade: ApiDecimal
  preco_unitario: ApiDecimal
  subtotal: ApiDecimal
  data_lancamento: string
  status: "ATIVO" | "CANCELADO"
  observacao: string
  created_at: string
  updated_at: string
}

export interface ItemFiadoPayload {
  produto: string
  forma_venda?: string | null
  quantidade?: ApiDecimal
  quantidade_informada?: ApiDecimal | null
  preco_unitario?: ApiDecimal | null
  observacao?: string
  idempotency_key?: string
}

export interface PagamentoFiado {
  id: string
  company_id: string
  conta: string
  valor: ApiDecimal
  forma_pagamento: "DINHEIRO" | "PIX" | "CARTAO" | "BOLETO" | "TRANSFERENCIA" | "OUTRO"
  data_pagamento: string
  status: "CONFIRMADO" | "CANCELADO"
  observacao: string
  created_at: string
  updated_at: string
}

export type FormaPagamentoFiado = PagamentoFiado["forma_pagamento"]

export interface PagamentoFiadoPayload {
  valor: ApiDecimal
  forma_pagamento: FormaPagamentoFiado
  data_pagamento?: string
  observacao?: string
  idempotency_key?: string
}

export interface HistoricoFiado {
  id: string
  company_id: string
  conta: string
  item: string | null
  pagamento: string | null
  evento: string
  descricao: string
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  metadata: Record<string, unknown>
  created_by: string | null
  created_by_nome: string | null
  created_at: string
  updated_at: string
}

export interface DashboardFiado {
  total_em_aberto: ApiDecimal
  total_atrasado: ApiDecimal
  total_recebido_hoje: ApiDecimal
  total_recebido_mes: ApiDecimal
  contas_abertas: number
  contas_atrasadas: number
  clientes_devedores: number
  ticket_medio_fiado: ApiDecimal
}

export interface FluxoFinanceiroItem {
  data: string
  tipo: "ENTRADA" | "SAIDA"
  total: ApiDecimal
}

export interface CategoriaFinanceiraTotal {
  categoria: string | null
  total: ApiDecimal
}

export interface DashboardFinanceiro {
  recebido_hoje: ApiDecimal
  recebido_mes: ApiDecimal
  recebido_ano: ApiDecimal
  total_contas_pagar_abertas: ApiDecimal
  total_contas_pagar_vencidas: ApiDecimal
  saldo_caixa: ApiDecimal
  saldo_total_financeiro: ApiDecimal
  fluxo_diario: FluxoFinanceiroItem[]
  entradas_por_categoria: CategoriaFinanceiraTotal[]
  saidas_por_categoria: CategoriaFinanceiraTotal[]
}

export interface ContaPagar {
  id: string
  company_id: string
  fornecedor: string | null
  fornecedor_nome: string
  descricao: string
  categoria: string
  categoria_nome: string
  valor_total: ApiDecimal
  valor_pago: ApiDecimal
  valor_restante: ApiDecimal
  data_emissao: string
  data_vencimento: string
  data_pagamento: string | null
  status: "ABERTA" | "PAGA" | "CANCELADA"
  is_parcial: boolean
  is_atrasada: boolean
  dias_atraso: number
  created_by: string | null
  created_by_nome: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FluxoCaixaItem {
  data: string
  receitas: number
  despesas: number
  saldo: number
}

export interface DashboardResumo {
  financeiro: DashboardFinanceiro
  fiado: DashboardFiado
  clientes: PaginatedResponse<Cliente>
  clientesDevedores: PaginatedResponse<Cliente>
  clientesInadimplentes: PaginatedResponse<Cliente>
  produtosCriticos: PaginatedResponse<Produto>
  contasAtrasadas: PaginatedResponse<ContaPagar>
  fluxoCaixa: FluxoCaixaItem[]
}
