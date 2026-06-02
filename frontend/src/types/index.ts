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

export type RegimeTributario = "SIMPLES_NACIONAL" | "LUCRO_PRESUMIDO" | "LUCRO_REAL"
export type CrtFiscal = "1" | "2" | "3"
export type AmbienteFiscal = "HOMOLOGACAO" | "PRODUCAO"
export type ProviderFiscal = "FAKE" | "NFEIO" | "FOCUS_NFE" | "PLUGNOTAS"

export interface ConfiguracaoFiscalEmpresa {
  id: string
  company_id: string
  cnpj: string
  razao_social: string
  nome_fantasia: string
  inscricao_estadual: string
  inscricao_municipal: string
  regime_tributario: RegimeTributario | ""
  crt: CrtFiscal | ""
  cnae: string
  uf: string
  municipio: string
  municipio_ibge: string
  logradouro: string
  numero: string
  complemento: string
  bairro: string
  cep: string
  ambiente_fiscal: AmbienteFiscal
  provider_fiscal: ProviderFiscal
  provider_company_id: string
  ativo: boolean
  cadastro_fiscal_pronto: boolean
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
export type IndicadorIE = "CONTRIBUINTE" | "ISENTO" | "NAO_CONTRIBUINTE"

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
  inscricao_estadual: string
  indicador_ie: IndicadorIE
  contribuinte_icms: boolean
  municipio_ibge: string
  codigo_pais: string
  pais: string
  observacao?: string
  limite_credito: ApiDecimal
  saldo_devedor: ApiDecimal
  credito_disponivel: ApiDecimal
  inadimplente: boolean
  cadastro_fiscal_pronto: boolean
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
  inscricao_estadual?: string
  indicador_ie?: IndicadorIE
  contribuinte_icms?: boolean
  municipio_ibge?: string
  codigo_pais?: string
  pais?: string
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
  ncm: string
  cfop_padrao: string
  cst_csosn: string
  cest: string
  origem_mercadoria: string
  unidade_tributavel: string
  ean_tributavel: string
  codigo_beneficio_fiscal: string
  aliquota_icms: ApiDecimal
  aliquota_ipi: ApiDecimal
  aliquota_pis: ApiDecimal
  aliquota_cofins: ApiDecimal
  cadastro_fiscal_pronto: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProdutoPayload {
  nome: string
  descricao?: string
  sku?: string
  codigo_barras?: string
  categoria: string
  fornecedor_principal?: string | null
  unidade: string
  preco_compra?: ApiDecimal
  preco_venda?: ApiDecimal
  custo_medio?: ApiDecimal
  estoque_minimo?: ApiDecimal
  ncm?: string
  cfop_padrao?: string
  cst_csosn?: string
  cest?: string
  origem_mercadoria?: string
  unidade_tributavel?: string
  ean_tributavel?: string
  codigo_beneficio_fiscal?: string
  aliquota_icms?: ApiDecimal
  aliquota_ipi?: ApiDecimal
  aliquota_pis?: ApiDecimal
  aliquota_cofins?: ApiDecimal
}

export interface UnidadeMedida {
  id: string
  company_id: string
  nome: string
  sigla: string
  descricao?: string
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

export interface FormaVendaProdutoPayload {
  produto: string
  nome: string
  codigo?: string
  unidade: string
  fator_conversao: ApiDecimal
  preco_venda?: ApiDecimal
  ativo?: boolean
  padrao?: boolean
  permite_fracionado?: boolean
}

export interface FormaVendaProdutoUpdatePayload {
  nome?: string
  codigo?: string
  unidade?: string
  fator_conversao?: ApiDecimal
  preco_venda?: ApiDecimal
  permite_fracionado?: boolean
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

export interface MovimentacaoEstoquePayload {
  produto: string
  quantidade?: ApiDecimal
  forma_venda?: string | null
  quantidade_informada?: ApiDecimal | null
  custo_unitario?: ApiDecimal | null
  fornecedor?: string | null
  motivo?: string
  observacao?: string
  idempotency_key?: string
  metadata?: Record<string, unknown>
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
  boletosPendentes?: PaginatedResponse<BoletoOCR>
  notasPendentes?: PaginatedResponse<NotaEntrada>
}

export interface Fornecedor {
  id: string
  company_id: string
  razao_social: string
  nome_fantasia: string
  cnpj: string
  telefone?: string
  email?: string
  observacoes?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CategoriaFinanceira {
  id: string
  company_id: string
  nome: string
  tipo: "RECEITA" | "DESPESA"
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface BoletoOCR {
  id: string
  company_id: string
  arquivo_nome_original: string
  tipo_arquivo: string
  content_type: string
  tamanho_bytes: number
  status: "ENVIADO" | "PROCESSANDO" | "AGUARDANDO_REVISAO" | "CONFIRMADO" | "REJEITADO" | "ERRO"
  fornecedor: string | null
  fornecedor_nome: string | null
  fornecedor_nome_final: string
  banco_codigo: string | null
  banco_nome: string | null
  valor: ApiDecimal | null
  vencimento: string | null
  linha_digitavel: string | null
  codigo_barras: string | null
  confianca_ocr: ApiDecimal | null
  conta_pagar: string | null
  created_by: string | null
  created_by_nome: string | null
  erro_codigo: string | null
  erro_mensagem: string | null
  tentativas_ocr: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface BoletoOCRDetail extends BoletoOCR {
  arquivo: string | null
  preview_image: string | null
  preview_pages: number
  sha256: string | null
  documento_beneficiario: string | null
  documento_pagador: string | null
  data_emissao: string | null
  texto_ocr: string | null
  payload_ocr: Record<string, unknown> | null
  raw_provider_response: Record<string, unknown> | null
  campos_extraidos: Record<string, unknown> | null
  campos_confianca: Record<string, unknown> | null
  processado_por: string | null
  processado_por_nome: string | null
  confirmado_por: string | null
  confirmado_por_nome: string | null
  rejeitado_por: string | null
  rejeitado_por_nome: string | null
  ocr_started_at: string | null
  ocr_finished_at: string | null
  confirmado_at: string | null
  rejeitado_at: string | null
  motivo_rejeicao: string | null
  observacao: string | null
  idempotency_key: string | null
}

export interface HistoricoBoleto {
  id: string
  evento: string
  descricao: string
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  metadata: Record<string, unknown>
  request_id: string | null
  created_by: string | null
  created_by_nome: string | null
  created_at: string
}

export interface BoletoDashboard {
  boletos_enviados_hoje: number
  boletos_processados_hoje: number
  pendentes_revisao: number
  ocrs_com_erro: number
  contas_pagar_geradas: number
  valor_total_identificado: ApiDecimal
  valor_total_confirmado: ApiDecimal
  taxa_sucesso_ocr: ApiDecimal
  confianca_media: ApiDecimal
  vencimentos_7_dias: number
  vencimentos_30_dias: number
}

export interface ConfirmarBoletoPayload {
  beneficiario_nome?: string
  beneficiario_documento?: string
  banco_codigo?: string
  banco_nome?: string
  valor: ApiDecimal
  vencimento: string
  data_emissao?: string
  linha_digitavel?: string
  codigo_barras?: string
  categoria: string
  fornecedor?: string | null
  observacao?: string
}

export interface RejeitarBoletoPayload {
  motivo: string
}

export interface NotaEntrada {
  id: string
  status: string
  numero: string
  serie: string
  modelo: string
  data_emissao: string | null
  fornecedor_nome_final: string
  fornecedor_cnpj_xml: string
  fornecedor: string | null
  valor_total: ApiDecimal
  conta_pagar: string | null
  itens_total: number
  itens_sem_produto: number
  created_at: string
}

export interface NotaEntradaUploadPayload {
  arquivo: File
  observacao?: string
  idempotency_key?: string
}

export interface DashboardNotasEntrada {
  notas_importadas_hoje: number
  aguardando_revisao: number
  confirmadas_mes: number
  rejeitadas_mes: number
  valor_total_importado_mes: ApiDecimal
  valor_total_confirmado_mes: ApiDecimal
  movimentacoes_estoque_geradas_mes: number
  contas_pagar_criadas_mes: number
  fornecedores_novos_detectados: number
  itens_sem_produto_pendentes: number
}

export interface NotaItem {
  id: string
  ordem: number
  descricao_original: string
  codigo_fornecedor: string
  codigo_barras: string
  ncm: string
  cfop: string
  unidade: string
  quantidade: ApiDecimal
  valor_unitario: ApiDecimal
  valor_total_item: ApiDecimal
  custo_unitario: ApiDecimal
  valor_ipi_item: ApiDecimal
  valor_icms_item: ApiDecimal
  produto: string | null
  produto_id: string | null
  produto_nome: string | null
  forma_venda: string | null
  forma_venda_nome: string | null
  forma_venda_fator: string | null
  quantidade_convertida: string | null
  movimentacao_estoque: string | null
  ignorado: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductSuggestion {
  id: string
  nome: string
  sku: string | null
  codigo_barras: string | null
  estoque_atual: ApiDecimal
  preco_compra: ApiDecimal
  similarity: number | null
}

export interface NotaHistorico {
  id: string
  evento: string
  descricao: string
  before: unknown
  after: unknown
  metadata: unknown
  request_id: string
  created_by: string
  created_by_nome: string
  created_at: string
}
