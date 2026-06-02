"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  X,
  Download,
  Check,
  AlertOctagon,
  RefreshCw,
  Clock,
  Eye,
  FileText,
  HelpCircle,
  Calendar,
  Building,
  Tag,
  Hash
} from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { useApiToast } from "@/hooks/use-api-toast"
import { boletosService } from "@/services/boletos.service"
import { estoqueService } from "@/services/estoque.service"
import { financeiroService } from "@/services/financeiro.service"
import { fornecedorDisplayName } from "@/lib/estoque"
import { formatDate, cn } from "@/lib/utils"
import { formatNumber } from "@/lib/format"

const confirmarBoletoSchema = z.object({
  beneficiario_nome: z.string().max(300, "Máximo de 300 caracteres").optional(),
  beneficiario_documento: z.string().max(20, "Documento inválido").optional(),
  banco_codigo: z.string().max(10, "Código do banco inválido").optional(),
  banco_nome: z.string().max(120, "Nome do banco inválido").optional(),
  valor: z.number().min(0.01, "Valor mínimo de R$ 0,01"),
  vencimento: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Data inválida. Use AAAA-MM-DD"),
  data_emissao: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Data inválida. Use AAAA-MM-DD").optional().or(z.literal("")),
  linha_digitavel: z.string().max(80, "Linha digitável muito longa").optional(),
  codigo_barras: z.string().max(60, "Código de barras muito longo").optional(),
  categoria: z.string().uuid("Selecione uma categoria de despesa"),
  fornecedor: z.string().uuid("Selecione um fornecedor").optional().or(z.literal("")),
  observacao: z.string().optional()
})

type ConfirmarBoletoFormValues = z.infer<typeof confirmarBoletoSchema>

interface BoletoReviewDrawerProps {
  boletoId: string | null
  onClose: () => void
}

export function BoletoReviewDrawer({ boletoId, onClose }: BoletoReviewDrawerProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const open = Boolean(boletoId)

  // Estados locais para preview e rejeição
  const [fileUrl, setFileUrl] = useState<string | null>(null)
  const [fileType, setFileType] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState(false)
  const [rejeitando, setRejeitando] = useState(false)
  const [motivoRejeicao, setMotivoRejeicao] = useState("")

  // Fetch detalhes do boleto
  const boletoQuery = useQuery({
    queryKey: ["boletos", "detail", boletoId],
    queryFn: () => boletosService.getBoleto(boletoId!),
    enabled: open && Boolean(boletoId),
  })

  // Fetch histórico do boleto
  const historicoQuery = useQuery({
    queryKey: ["boletos", "historico", boletoId],
    queryFn: () => boletosService.getHistoricoBoleto(boletoId!, { page_size: 20 }),
    enabled: open && Boolean(boletoId),
  })

  // Fetch fornecedores
  const fornecedoresQuery = useQuery({
    queryKey: ["estoque", "fornecedores"],
    queryFn: () => estoqueService.fornecedores({ page_size: 100 }),
    enabled: open,
  })

  // Fetch categorias financeiras (despesas)
  const categoriasQuery = useQuery({
    queryKey: ["financeiro", "categorias"],
    queryFn: () => financeiroService.categorias({ page_size: 100 }),
    enabled: open,
  })

  const boleto = boletoQuery.data
  const historico = historicoQuery.data?.results ?? []
  const fornecedores = fornecedoresQuery.data?.results ?? []
  const categorias = categoriasQuery.data?.results.filter(c => c.tipo === "DESPESA" && c.is_active) ?? []

  // Setup formulário
  const form = useForm<ConfirmarBoletoFormValues>({
    resolver: zodResolver(confirmarBoletoSchema),
    defaultValues: {
      beneficiario_nome: "",
      beneficiario_documento: "",
      banco_codigo: "",
      banco_nome: "",
      valor: 0,
      vencimento: "",
      data_emissao: "",
      linha_digitavel: "",
      codigo_barras: "",
      categoria: "",
      fornecedor: "",
      observacao: ""
    }
  })

  const { formState: { errors } } = form

  // Preencher formulário ao carregar boleto
  useEffect(() => {
    if (boleto) {
      form.reset({
        beneficiario_nome: boleto.fornecedor_nome || "",
        beneficiario_documento: boleto.documento_beneficiario || "",
        banco_codigo: boleto.banco_codigo || "",
        banco_nome: boleto.banco_nome || "",
        valor: Number(boleto.valor ?? 0),
        vencimento: boleto.vencimento ?? "",
        data_emissao: boleto.data_emissao ?? "",
        linha_digitavel: boleto.linha_digitavel || "",
        codigo_barras: boleto.codigo_barras || "",
        categoria: "", // Obriga o operador a escolher a categoria apropriada
        fornecedor: boleto.fornecedor || "",
        observacao: boleto.observacao || ""
      })
    }
  }, [boleto, form])

  // Download e geração de URL de Blob para Preview autenticado
  useEffect(() => {
    if (!boletoId) return

    let isSubscribed = true

    boletosService.baixarBoleto(boletoId)
      .then((blob) => {
        if (!isSubscribed) return
        const url = URL.createObjectURL(blob)
        setFileUrl(url)
        setFileType(blob.type)
      })
      .catch((err) => {
        if (!isSubscribed) return
        console.error("Erro ao obter arquivo para preview:", err)
        setPreviewError(true)
      })

    return () => {
      isSubscribed = false
    }
  }, [boletoId])

  // Limpeza de URL de blob quando fechar
  useEffect(() => {
    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl)
      }
    }
  }, [fileUrl])

  // MUTAÇÕES
  const confirmarMutation = useMutation({
    mutationFn: (data: ConfirmarBoletoFormValues) => {
      const payload = {
        ...data,
        fornecedor: data.fornecedor || null,
        data_emissao: data.data_emissao || undefined
      }
      return boletosService.confirmarBoleto(boletoId!, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["boletos"] })
      queryClient.invalidateQueries({ queryKey: ["financeiro"] }) // atualiza contas a pagar no ERP
      toast.success("Boleto confirmado e conta a pagar criada!")
      onClose()
    },
    onError: (error) => {
      toast.error(error, "Erro ao confirmar boleto")
    }
  })

  const rejeitarMutation = useMutation({
    mutationFn: () => {
      if (!motivoRejeicao.trim()) throw new Error("Informe o motivo da rejeição.")
      return boletosService.rejeitarBoleto(boletoId!, motivoRejeicao)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["boletos"] })
      toast.success("Boleto rejeitado com sucesso")
      onClose()
    },
    onError: (error) => {
      toast.error(error, "Erro ao rejeitar boleto")
    }
  })

  const reprocessarMutation = useMutation({
    mutationFn: () => boletosService.reprocessarBoleto(boletoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["boletos"] })
      toast.success("Leitura OCR reiniciada")
      onClose()
    },
    onError: (error) => {
      toast.error(error, "Erro ao reprocessar OCR")
    }
  })

  const downloadFile = () => {
    if (!fileUrl || !boleto) return
    const a = document.createElement("a")
    a.href = fileUrl
    a.download = boleto.arquivo_nome_original || `boleto-${boletoId}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  if (!open) return null

  const isLoading = boletoQuery.isLoading || historicoQuery.isLoading
  const statusBoleto = boleto?.status
  const isAguardandoRevisao = statusBoleto === "AGUARDANDO_REVISAO"
  const isProcessavel = statusBoleto === "ERRO" || statusBoleto === "AGUARDANDO_REVISAO"

  return (
    <Dialog.Root open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className={cn(
            "fixed right-0 top-0 z-50 flex h-full w-full max-w-5xl flex-col bg-white shadow-2xl transition-transform duration-200",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right"
          )}
          aria-describedby={undefined}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-zinc-100 px-6 py-4">
            <div className="min-w-0">
              <Dialog.Title className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                <span>Painel de Revisão de Boleto</span>
                {boleto && (
                  <Badge variant={
                    boleto.status === "CONFIRMADO" ? "success" : 
                    boleto.status === "REJEITADO" || boleto.status === "ERRO" ? "error" : 
                    "warning"
                  }>
                    {boleto.status}
                  </Badge>
                )}
              </Dialog.Title>
              {boleto && (
                <p className="mt-0.5 text-xs text-zinc-400 truncate">
                  Arquivo: {boleto.arquivo_nome_original} • Tamanho: {formatNumber(boleto.tamanho_bytes / 1024, 1)} KB
                </p>
              )}
            </div>
            <Dialog.Close asChild>
              <button className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700">
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          {isLoading ? (
            <div className="flex flex-1 items-center justify-center p-8">
              <div className="text-center space-y-3">
                <RefreshCw className="size-8 animate-spin mx-auto text-orange-500" />
                <p className="text-sm text-zinc-500">Carregando dados do boleto...</p>
              </div>
            </div>
          ) : !boleto ? (
            <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-zinc-400">
              Não foi possível encontrar o boleto.
            </div>
          ) : (
            <div className="flex flex-1 overflow-hidden">
              {/* Esquerda: Preview */}
              <div className="w-[55%] border-r border-zinc-100 bg-zinc-50 flex flex-col relative">
                <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-100 bg-white">
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1">
                    <Eye className="size-3" /> Visualização do Documento
                  </span>
                  {fileUrl && (
                    <button
                      onClick={downloadFile}
                      className="text-xs text-orange-600 font-semibold hover:text-orange-700 flex items-center gap-1 cursor-pointer"
                    >
                      <Download className="size-3.5" /> Baixar original
                    </button>
                  )}
                </div>

                <div className="flex-1 p-4 flex items-center justify-center overflow-auto">
                  {previewError ? (
                    <div className="text-center p-6 space-y-2">
                      <AlertOctagon className="size-8 mx-auto text-zinc-400" />
                      <p className="text-xs text-zinc-500">Visualização indisponível</p>
                      <Button variant="outline" size="xs" onClick={downloadFile}>
                        Baixar arquivo para abrir
                      </Button>
                    </div>
                  ) : !fileUrl ? (
                    <div className="text-center space-y-2">
                      <RefreshCw className="size-5 animate-spin mx-auto text-zinc-400" />
                      <p className="text-xs text-zinc-500">Carregando preview...</p>
                    </div>
                  ) : fileType?.startsWith("image/") ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img src={fileUrl} alt="Preview do Boleto" className="max-w-full max-h-[70vh] rounded-md border border-zinc-200 shadow-sm object-contain" />
                  ) : fileType === "application/pdf" ? (
                    <object data={fileUrl} type="application/pdf" className="w-full h-full min-h-[60vh] rounded-md border border-zinc-200 shadow-sm">
                      <iframe src={fileUrl} className="w-full h-full border-none">
                        <div className="p-4 text-center">
                          <p className="text-xs text-zinc-500">O seu navegador não suporta visualização de PDF integrada.</p>
                          <Button variant="outline" size="xs" className="mt-2" onClick={downloadFile}>
                            Baixar para ler
                          </Button>
                        </div>
                      </iframe>
                    </object>
                  ) : (
                    <div className="text-center p-6 space-y-2">
                      <FileText className="size-8 mx-auto text-zinc-400" />
                      <p className="text-xs text-zinc-500">Visualização indisponível para o formato ({fileType})</p>
                      <Button variant="outline" size="xs" onClick={downloadFile}>
                        Baixar arquivo
                      </Button>
                    </div>
                  )}
                </div>

                {/* Confiança OCR Info */}
                {boleto.confianca_ocr !== null && (
                  <div className="p-3 bg-zinc-100/80 border-t border-zinc-200/80 flex items-center justify-between text-xs text-zinc-600">
                    <span className="flex items-center gap-1.5 font-medium">
                      <HelpCircle className="size-3.5 text-zinc-400" /> Confiança do OCR automático:
                    </span>
                    <span className={cn(
                      "font-bold tabular-nums",
                      Number(boleto.confianca_ocr) > 85 ? "text-green-600" :
                      Number(boleto.confianca_ocr) > 60 ? "text-yellow-600" : "text-red-500"
                    )}>
                      {formatNumber(boleto.confianca_ocr, 1)}%
                    </span>
                  </div>
                )}
              </div>

              {/* Direita: Formulário e Informações */}
              <div className="flex-1 flex flex-col overflow-y-auto">
                <form
                  onSubmit={form.handleSubmit((data) => confirmarMutation.mutate(data))}
                  className="flex-1 p-5 space-y-5"
                >
                  <div className="border-b border-zinc-100 pb-3 flex items-center justify-between">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                      Dados Extraídos e Validação
                    </span>
                    {!isAguardandoRevisao && (
                      <span className="text-xs text-zinc-500 italic">Modo visualização (concluído)</span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="space-y-1 md:col-span-2">
                      <label className="text-xs font-semibold text-zinc-700 flex items-center gap-1">
                        <Building className="size-3.5 text-zinc-400" /> Beneficiário / Fornecedor Extraído
                      </label>
                      <Input
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.beneficiario_nome)}
                        {...form.register("beneficiario_nome")}
                      />
                      {errors.beneficiario_nome && <p className="text-xs text-red-600">{errors.beneficiario_nome.message}</p>}
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-zinc-700">Beneficiário CNPJ/CPF</label>
                      <Input
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.beneficiario_documento)}
                        {...form.register("beneficiario_documento")}
                      />
                      {errors.beneficiario_documento && <p className="text-xs text-red-600">{errors.beneficiario_documento.message}</p>}
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-zinc-700">Código do Banco</label>
                      <Input
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.banco_codigo)}
                        {...form.register("banco_codigo")}
                      />
                      {errors.banco_codigo && <p className="text-xs text-red-600">{errors.banco_codigo.message}</p>}
                    </div>

                    <div className="space-y-1 md:col-span-2">
                      <label className="text-xs font-semibold text-zinc-700">Nome do Banco</label>
                      <Input
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.banco_nome)}
                        {...form.register("banco_nome")}
                      />
                      {errors.banco_nome && <p className="text-xs text-red-600">{errors.banco_nome.message}</p>}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-zinc-700 flex items-center gap-1">
                        Valor (R$)
                      </label>
                      <Input
                        type="number"
                        step="0.01"
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.valor)}
                        {...form.register("valor", { valueAsNumber: true })}
                      />
                      {errors.valor && <p className="text-xs text-red-600">{errors.valor.message}</p>}
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-zinc-700 flex items-center gap-1">
                        <Calendar className="size-3.5 text-zinc-400" /> Vencimento
                      </label>
                      <Input
                        type="date"
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.vencimento)}
                        {...form.register("vencimento")}
                      />
                      {errors.vencimento && <p className="text-xs text-red-600">{errors.vencimento.message}</p>}
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-zinc-700 flex items-center gap-1">
                        <Calendar className="size-3.5 text-zinc-400" /> Emissão
                      </label>
                      <Input
                        type="date"
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.data_emissao)}
                        {...form.register("data_emissao")}
                      />
                      {errors.data_emissao && <p className="text-xs text-red-600">{errors.data_emissao.message}</p>}
                    </div>
                  </div>

                  <div className="space-y-3 rounded-lg bg-zinc-50 border border-zinc-100 p-4">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">
                      Vinculação ERP (MP Construções)
                    </span>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-zinc-700 flex items-center gap-1">
                          <Tag className="size-3.5 text-orange-500" /> Categoria Financeira *
                        </label>
                        <select
                          disabled={!isAguardandoRevisao}
                          className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-100"
                          {...form.register("categoria")}
                        >
                          <option value="">Selecione categoria de despesa...</option>
                          {categorias.map(cat => (
                            <option key={cat.id} value={cat.id}>{cat.nome}</option>
                          ))}
                        </select>
                        {errors.categoria && <p className="text-xs text-red-600">{errors.categoria.message}</p>}
                      </div>

                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-zinc-700 flex items-center gap-1">
                          Fornecedor Vinculado
                        </label>
                        <select
                          disabled={!isAguardandoRevisao}
                          className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-100"
                          {...form.register("fornecedor")}
                        >
                          <option value="">Selecione fornecedor (opcional)...</option>
                          {fornecedores.map(forn => (
                            <option key={forn.id} value={forn.id}>{fornecedorDisplayName(forn)} ({forn.cnpj})</option>
                          ))}
                        </select>
                        {errors.fornecedor && <p className="text-xs text-red-600">{errors.fornecedor.message}</p>}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-zinc-700 flex items-center gap-1">
                        <Hash className="size-3.5 text-zinc-400" /> Linha Digitável
                      </label>
                      <Input
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.linha_digitavel)}
                        {...form.register("linha_digitavel")}
                      />
                      {errors.linha_digitavel && <p className="text-xs text-red-600">{errors.linha_digitavel.message}</p>}
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-zinc-700">Código de Barras</label>
                      <Input
                        disabled={!isAguardandoRevisao}
                        error={Boolean(errors.codigo_barras)}
                        {...form.register("codigo_barras")}
                      />
                      {errors.codigo_barras && <p className="text-xs text-red-600">{errors.codigo_barras.message}</p>}
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-zinc-700">Observações adicionais</label>
                      <Input
                        disabled={!isAguardandoRevisao}
                        {...form.register("observacao")}
                      />
                    </div>
                  </div>

                  {boleto.erro_mensagem && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs text-red-800">
                      <p className="font-semibold flex items-center gap-1"><AlertOctagon className="size-4 text-red-600" /> Erro no processamento automático:</p>
                      <p className="mt-1 font-mono text-[11px] leading-relaxed">{boleto.erro_mensagem}</p>
                    </div>
                  )}

                  {/* Rejeição interface */}
                  {rejeitando && (
                    <div className="space-y-3 rounded-lg border border-yellow-200 bg-yellow-50/60 p-4">
                      <label className="text-xs font-semibold text-yellow-800 block">
                        Motivo da rejeição (Obrigatório)
                      </label>
                      <textarea
                        value={motivoRejeicao}
                        onChange={(e) => setMotivoRejeicao(e.target.value)}
                        placeholder="Ex: Valor incorreto, fatura rasurada, não pertence a esta filial..."
                        rows={2}
                        className="w-full rounded-md border border-yellow-300 bg-white px-3 py-2 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none"
                      />
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="xs"
                          onClick={() => {
                            setRejeitando(false)
                            setMotivoRejeicao("")
                          }}
                        >
                          Cancelar
                        </Button>
                        <Button
                          type="button"
                          size="xs"
                          loading={rejeitarMutation.isPending}
                          onClick={() => rejeitarMutation.mutate()}
                          className="bg-red-600 hover:bg-red-700 text-white"
                        >
                          Confirmar Rejeição
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Ações operacionais */}
                  <div className="flex flex-wrap gap-2 pt-4 border-t border-zinc-100 justify-between items-center">
                    <div className="flex gap-2">
                      {isAguardandoRevisao && !rejeitando && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setRejeitando(true)}
                          className="text-red-600 hover:bg-red-50 border-red-200"
                        >
                          Rejeitar
                        </Button>
                      )}
                      {isProcessavel && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          loading={reprocessarMutation.isPending}
                          disabled={reprocessarMutation.isPending}
                          onClick={() => reprocessarMutation.mutate()}
                          icon={<RefreshCw className="size-3.5" />}
                        >
                          Reprocessar OCR
                        </Button>
                      )}
                    </div>

                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={onClose}
                      >
                        Fechar
                      </Button>
                      {isAguardandoRevisao && (
                        <Button
                          type="submit"
                          size="sm"
                          loading={confirmarMutation.isPending}
                          disabled={confirmarMutation.isPending || rejeitando}
                          className="bg-orange-500 hover:bg-orange-600 text-white font-medium"
                          icon={<Check className="size-4" />}
                        >
                          Confirmar e Criar Conta a Pagar
                        </Button>
                      )}
                    </div>
                  </div>
                </form>

                {/* Audit Log / Histórico */}
                {historico.length > 0 && (
                  <div className="border-t border-zinc-100 bg-zinc-50/50 p-5 space-y-3">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="size-3.5 text-zinc-400" /> Histórico Operacional
                    </span>
                    <div className="space-y-3 relative before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-zinc-200">
                      {historico.map((h) => (
                        <div key={h.id} className="text-xs pl-6 relative">
                          <div className="absolute left-[5px] top-1.5 size-2 rounded-full bg-zinc-400 border border-white" />
                          <div className="flex justify-between text-[11px] text-zinc-400">
                            <span className="font-semibold text-zinc-700">{h.evento}</span>
                            <span>{formatDate(h.created_at)}</span>
                          </div>
                          <p className="mt-0.5 text-zinc-500">{h.descricao}</p>
                          {h.created_by_nome && (
                            <p className="mt-0.5 text-[10px] text-zinc-400">Por: {h.created_by_nome}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
