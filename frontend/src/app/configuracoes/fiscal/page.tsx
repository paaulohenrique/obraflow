"use client"

import Link from "next/link"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, ArrowLeft, BadgeCheck, FileCog } from "lucide-react"
import { useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { useApiToast } from "@/hooks/use-api-toast"
import { useCurrentUser } from "@/hooks/use-current-user"
import { empresasService } from "@/services/empresas.service"
import type { ConfiguracaoFiscalEmpresa } from "@/types"

type FiscalForm = Pick<
  ConfiguracaoFiscalEmpresa,
  | "cnpj"
  | "razao_social"
  | "nome_fantasia"
  | "inscricao_estadual"
  | "inscricao_municipal"
  | "regime_tributario"
  | "crt"
  | "cnae"
  | "uf"
  | "municipio"
  | "municipio_ibge"
  | "logradouro"
  | "numero"
  | "complemento"
  | "bairro"
  | "cep"
  | "ambiente_fiscal"
  | "provider_fiscal"
  | "provider_company_id"
  | "ativo"
>

const emptyForm: FiscalForm = {
  cnpj: "",
  razao_social: "",
  nome_fantasia: "",
  inscricao_estadual: "",
  inscricao_municipal: "",
  regime_tributario: "",
  crt: "",
  cnae: "",
  uf: "",
  municipio: "",
  municipio_ibge: "",
  logradouro: "",
  numero: "",
  complemento: "",
  bairro: "",
  cep: "",
  ambiente_fiscal: "HOMOLOGACAO",
  provider_fiscal: "FAKE",
  provider_company_id: "",
  ativo: false,
}

function fromConfig(config?: ConfiguracaoFiscalEmpresa | null): FiscalForm {
  if (!config) return emptyForm
  return {
    cnpj: config.cnpj ?? "",
    razao_social: config.razao_social ?? "",
    nome_fantasia: config.nome_fantasia ?? "",
    inscricao_estadual: config.inscricao_estadual ?? "",
    inscricao_municipal: config.inscricao_municipal ?? "",
    regime_tributario: config.regime_tributario ?? "",
    crt: config.crt ?? "",
    cnae: config.cnae ?? "",
    uf: config.uf ?? "",
    municipio: config.municipio ?? "",
    municipio_ibge: config.municipio_ibge ?? "",
    logradouro: config.logradouro ?? "",
    numero: config.numero ?? "",
    complemento: config.complemento ?? "",
    bairro: config.bairro ?? "",
    cep: config.cep ?? "",
    ambiente_fiscal: config.ambiente_fiscal ?? "HOMOLOGACAO",
    provider_fiscal: config.provider_fiscal ?? "FAKE",
    provider_company_id: config.provider_company_id ?? "",
    ativo: config.ativo ?? false,
  }
}

export default function ConfiguracaoFiscalPage() {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const { user } = useCurrentUser()
  const [form, setForm] = useState<FiscalForm>(emptyForm)
  const [formKey, setFormKey] = useState("")

  const canEdit = user?.role === "admin" || user?.role === "manager"

  const fiscalQuery = useQuery({
    queryKey: ["empresas", "fiscal"],
    queryFn: empresasService.getFiscal,
    staleTime: 60_000,
  })

  const nextKey = fiscalQuery.data?.updated_at ?? "loading"
  if (formKey !== nextKey && fiscalQuery.data) {
    setFormKey(nextKey)
    setForm(fromConfig(fiscalQuery.data))
  }

  const missing = useMemo(
    () =>
      [
        ["CNPJ", form.cnpj],
        ["Razão social", form.razao_social],
        ["IE", form.inscricao_estadual],
        ["Regime tributário", form.regime_tributario],
        ["CRT", form.crt],
        ["CNAE", form.cnae],
        ["UF", form.uf],
        ["Município", form.municipio],
        ["IBGE", form.municipio_ibge],
        ["Logradouro", form.logradouro],
        ["Número", form.numero],
        ["Bairro", form.bairro],
        ["CEP", form.cep],
      ].filter(([, value]) => !String(value ?? "").trim()),
    [form]
  )

  const mutation = useMutation({
    mutationFn: () => empresasService.updateFiscal(form),
    onSuccess: (saved) => {
      queryClient.setQueryData(["empresas", "fiscal"], saved)
      queryClient.invalidateQueries({ queryKey: ["empresas"] })
      toast.success("Configuração fiscal atualizada")
    },
    onError: (error) => toast.error(error),
  })

  const update = <K extends keyof FiscalForm>(field: K, value: FiscalForm[K]) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  return (
    <Shell>
      <Topbar
        title="Configuração Fiscal"
        subtitle="Base cadastral para futura emissão de NF-e modelo 55"
        actions={
          <Link href="/configuracoes">
            <Button variant="ghost" size="sm" icon={<ArrowLeft className="size-3.5" />}>
              Voltar
            </Button>
          </Link>
        }
      />

      <main className="flex-1 space-y-5 p-4 md:p-6">
        <div className="max-w-5xl space-y-5">
          <div className="flex items-start gap-3 rounded-md border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-900">
            <AlertTriangle className="mt-0.5 size-4 flex-shrink-0" />
            <span>Estes dados serão usados futuramente para emissão de NF-e. Confirme as regras fiscais com seu contador.</span>
          </div>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCog className="size-4 text-orange-500" />
                <h3 className="text-sm font-semibold text-zinc-900">Dados fiscais da empresa</h3>
              </div>
              {fiscalQuery.data && (
                <Badge variant={fiscalQuery.data.cadastro_fiscal_pronto ? "success" : "warning"}>
                  {fiscalQuery.data.cadastro_fiscal_pronto ? "Cadastro fiscal pronto para NF-e" : "Cadastro fiscal incompleto"}
                </Badge>
              )}
            </CardHeader>
            <CardContent>
              {fiscalQuery.isLoading ? (
                <Skeleton className="h-96 w-full" />
              ) : (
                <div className="space-y-5">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <Field label="CNPJ"><Input disabled={!canEdit} value={form.cnpj} onChange={(e) => update("cnpj", e.target.value)} /></Field>
                    <Field label="Razão social" span="md:col-span-2"><Input disabled={!canEdit} value={form.razao_social} onChange={(e) => update("razao_social", e.target.value)} /></Field>
                    <Field label="Nome fantasia"><Input disabled={!canEdit} value={form.nome_fantasia} onChange={(e) => update("nome_fantasia", e.target.value)} /></Field>
                    <Field label="Inscrição estadual"><Input disabled={!canEdit} value={form.inscricao_estadual} onChange={(e) => update("inscricao_estadual", e.target.value)} /></Field>
                    <Field label="Inscrição municipal"><Input disabled={!canEdit} value={form.inscricao_municipal} onChange={(e) => update("inscricao_municipal", e.target.value)} /></Field>
                    <Field label="Regime tributário">
                      <select disabled={!canEdit} value={form.regime_tributario} onChange={(e) => update("regime_tributario", e.target.value as FiscalForm["regime_tributario"])} className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm">
                        <option value="">Selecione</option>
                        <option value="SIMPLES_NACIONAL">Simples Nacional</option>
                        <option value="LUCRO_PRESUMIDO">Lucro Presumido</option>
                        <option value="LUCRO_REAL">Lucro Real</option>
                      </select>
                    </Field>
                    <Field label="CRT">
                      <select disabled={!canEdit} value={form.crt} onChange={(e) => update("crt", e.target.value as FiscalForm["crt"])} className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm">
                        <option value="">Selecione</option>
                        <option value="1">1 - Simples Nacional</option>
                        <option value="2">2 - Simples excesso sublimite</option>
                        <option value="3">3 - Regime Normal</option>
                      </select>
                    </Field>
                    <Field label="CNAE"><Input disabled={!canEdit} value={form.cnae} onChange={(e) => update("cnae", e.target.value)} /></Field>
                    <Field label="UF"><Input disabled={!canEdit} maxLength={2} value={form.uf} onChange={(e) => update("uf", e.target.value.toUpperCase())} /></Field>
                    <Field label="Município"><Input disabled={!canEdit} value={form.municipio} onChange={(e) => update("municipio", e.target.value)} /></Field>
                    <Field label="Município IBGE"><Input disabled={!canEdit} value={form.municipio_ibge} onChange={(e) => update("municipio_ibge", e.target.value)} /></Field>
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                    <Field label="Logradouro" span="md:col-span-2"><Input disabled={!canEdit} value={form.logradouro} onChange={(e) => update("logradouro", e.target.value)} /></Field>
                    <Field label="Número"><Input disabled={!canEdit} value={form.numero} onChange={(e) => update("numero", e.target.value)} /></Field>
                    <Field label="Bairro"><Input disabled={!canEdit} value={form.bairro} onChange={(e) => update("bairro", e.target.value)} /></Field>
                    <Field label="Complemento" span="md:col-span-2"><Input disabled={!canEdit} value={form.complemento} onChange={(e) => update("complemento", e.target.value)} /></Field>
                    <Field label="CEP"><Input disabled={!canEdit} value={form.cep} onChange={(e) => update("cep", e.target.value)} /></Field>
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <Field label="Ambiente fiscal">
                      <select disabled={!canEdit} value={form.ambiente_fiscal} onChange={(e) => update("ambiente_fiscal", e.target.value as FiscalForm["ambiente_fiscal"])} className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm">
                        <option value="HOMOLOGACAO">Homologação</option>
                        <option value="PRODUCAO">Produção</option>
                      </select>
                    </Field>
                    <Field label="Provider fiscal">
                      <select disabled={!canEdit} value={form.provider_fiscal} onChange={(e) => update("provider_fiscal", e.target.value as FiscalForm["provider_fiscal"])} className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm">
                        <option value="FAKE">Fake</option>
                        <option value="NFEIO">NFE.io</option>
                        <option value="FOCUS_NFE">Focus NFe</option>
                        <option value="PLUGNOTAS">PlugNotas</option>
                      </select>
                    </Field>
                    <Field label="ID da empresa no provider"><Input disabled={!canEdit} value={form.provider_company_id} onChange={(e) => update("provider_company_id", e.target.value)} /></Field>
                  </div>

                  {missing.length > 0 && (
                    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
                      Pendências: {missing.map(([label]) => label).join(", ")}
                    </div>
                  )}

                  <div className="flex items-center justify-between border-t border-zinc-100 pt-4">
                    <label className="flex items-center gap-2 text-xs font-semibold text-zinc-700">
                      <input type="checkbox" disabled={!canEdit} checked={form.ativo} onChange={(e) => update("ativo", e.target.checked)} />
                      Configuração fiscal ativa
                    </label>
                    <Button disabled={!canEdit || mutation.isPending} loading={mutation.isPending} icon={<BadgeCheck className="size-3.5" />} onClick={() => mutation.mutate()}>
                      Salvar Configuração
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </Shell>
  )
}

function Field({ label, span, children }: { label: string; span?: string; children: React.ReactNode }) {
  return (
    <label className={`block space-y-1.5 ${span ?? ""}`}>
      <span className="text-xs font-medium text-zinc-600">{label}</span>
      {children}
    </label>
  )
}
