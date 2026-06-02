"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AlertCircle, FileCode, UploadCloud, X } from "lucide-react"
import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { useApiToast } from "@/hooks/use-api-toast"
import { createOperationKey } from "@/lib/estoque"
import { notasEntradaService } from "@/services/notas-entrada.service"

interface NfeUploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (notaId: string) => void
}

const MAX_XML_SIZE = 2 * 1024 * 1024
const ALLOWED_TYPES = new Set(["text/xml", "application/xml", "text/plain", ""])

function formatSize(bytes: number) {
  if (!bytes) return "0 KB"
  const mb = bytes / (1024 * 1024)
  if (mb >= 1) return `${mb.toFixed(2)} MB`
  return `${(bytes / 1024).toFixed(1)} KB`
}

export function NfeUploadModal({ open, onOpenChange, onSuccess }: NfeUploadModalProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [observacao, setObservacao] = useState("")
  const [errorMsg, setErrorMsg] = useState("")
  const [dragActive, setDragActive] = useState(false)

  const reset = () => {
    setFile(null)
    setObservacao("")
    setErrorMsg("")
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Selecione um XML.")
      return notasEntradaService.uploadXML({
        arquivo: file,
        observacao,
        idempotency_key: createOperationKey("nfe-upload"),
      })
    },
    onSuccess: (nota) => {
      queryClient.invalidateQueries({ queryKey: ["notas-entrada"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      toast.success("XML importado para revisão")
      reset()
      onOpenChange(false)
      onSuccess?.(nota.id)
    },
    onError: (error) => toast.error(error, "Falha ao importar XML"),
  })

  const validateFile = (selectedFile: File) => {
    setErrorMsg("")
    const lowerName = selectedFile.name.toLowerCase()
    if (!lowerName.endsWith(".xml")) {
      setErrorMsg("Selecione um arquivo com extensão .xml.")
      return false
    }
    if (!ALLOWED_TYPES.has(selectedFile.type)) {
      setErrorMsg("O tipo do arquivo não parece ser XML.")
      return false
    }
    if (selectedFile.size <= 0) {
      setErrorMsg("O arquivo XML está vazio.")
      return false
    }
    if (selectedFile.size > MAX_XML_SIZE) {
      setErrorMsg("O XML excede o limite de 2MB.")
      return false
    }
    return true
  }

  const chooseFile = (selectedFile: File) => {
    if (validateFile(selectedFile)) setFile(selectedFile)
  }

  const handleDrag = (event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setDragActive(event.type === "dragenter" || event.type === "dragover")
  }

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setDragActive(false)
    const droppedFile = event.dataTransfer.files?.[0]
    if (droppedFile) chooseFile(droppedFile)
  }

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(value) => {
        if (uploadMutation.isPending) return
        onOpenChange(value)
        if (!value) reset()
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-zinc-950/30 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-24px)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-lg border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <Dialog.Title className="flex items-center gap-2 text-sm font-semibold text-zinc-950">
              <FileCode className="size-4 text-orange-600" />
              Adicionar NF-e
            </Dialog.Title>
            <button
              type="button"
              disabled={uploadMutation.isPending}
              onClick={() => onOpenChange(false)}
              className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-50"
              aria-label="Fechar"
            >
              <X className="size-4" />
            </button>
          </div>

          <div className="space-y-4 pt-4">
            {!file ? (
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                  dragActive
                    ? "border-orange-500 bg-orange-50/40"
                    : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xml,text/xml,application/xml"
                  onChange={(event) => {
                    const selectedFile = event.target.files?.[0]
                    if (selectedFile) chooseFile(selectedFile)
                  }}
                  className="hidden"
                />
                <div className="flex size-10 items-center justify-center rounded-full bg-zinc-50 text-zinc-400">
                  <UploadCloud className="size-5" />
                </div>
                <p className="mt-3 text-xs font-semibold text-zinc-700">Arraste o XML ou clique para selecionar</p>
                <p className="mt-1 text-[11px] text-zinc-400">NF-e em XML até 2MB</p>
              </div>
            ) : (
              <div className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50/70 p-4">
                <div className="flex size-10 items-center justify-center rounded-md bg-orange-100 text-orange-600">
                  <FileCode className="size-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-zinc-900">{file.name}</p>
                  <p className="text-[10px] text-zinc-400">{formatSize(file.size)}</p>
                </div>
                <button
                  type="button"
                  disabled={uploadMutation.isPending}
                  onClick={reset}
                  className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-50"
                  aria-label="Remover XML"
                >
                  <X className="size-3.5" />
                </button>
              </div>
            )}

            {errorMsg && (
              <div className="flex items-start gap-2 text-xs font-medium text-red-600">
                <AlertCircle className="size-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <label className="block space-y-1.5">
              <span className="text-xs font-medium text-zinc-600">Observação</span>
              <textarea
                value={observacao}
                onChange={(event) => setObservacao(event.target.value)}
                disabled={uploadMutation.isPending}
                rows={2}
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
              />
            </label>

            <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={uploadMutation.isPending}
                onClick={() => onOpenChange(false)}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                size="sm"
                loading={uploadMutation.isPending}
                disabled={!file || uploadMutation.isPending}
                onClick={() => uploadMutation.mutate()}
              >
                Enviar XML
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
