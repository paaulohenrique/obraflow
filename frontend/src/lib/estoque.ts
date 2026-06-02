import type { Fornecedor } from "@/types"

export function fornecedorDisplayName(fornecedor: Fornecedor | null | undefined) {
  if (!fornecedor) return ""
  return fornecedor.nome_fantasia || fornecedor.razao_social
}

export function createOperationKey(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}
