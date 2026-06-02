"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { UploadCloud, X, FileText, AlertCircle } from "lucide-react"
import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { useApiToast } from "@/hooks/use-api-toast"
import { boletosService } from "@/services/boletos.service"

interface BoletoUploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (boletoId: string) => void
}

const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp"
]

const MAX_FILE_SIZE = 15 * 1024 * 1024 // 15MB

export function BoletoUploadModal({ open, onOpenChange, onSuccess }: BoletoUploadModalProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [file, setFile] = useState<File | null>(null)
  const [observacao, setObservacao] = useState("")
  const [errorMsg, setErrorMsg] = useState("")
  const [dragActive, setDragActive] = useState(false)

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Selecione um arquivo.")
      return boletosService.uploadBoleto(file, observacao)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["boletos"] })
      toast.success("Boleto enviado para leitura")
      
      // Reset form
      setFile(null)
      setObservacao("")
      setErrorMsg("")
      
      onOpenChange(false)
      
      if (onSuccess && data?.id) {
        onSuccess(data.id)
      }
    },
    onError: (error) => {
      toast.error(error, "Falha no envio do boleto")
    }
  })

  const validateFile = (selectedFile: File): boolean => {
    setErrorMsg("")
    if (!ALLOWED_TYPES.includes(selectedFile.type)) {
      setErrorMsg("Formato inválido. Selecione um PDF ou imagem (JPG, PNG, WEBP).")
      return false
    }
    if (selectedFile.size > MAX_FILE_SIZE) {
      setErrorMsg("O arquivo excede o limite de tamanho de 15MB.")
      return false
    }
    return true
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (validateFile(droppedFile)) {
        setFile(droppedFile)
      }
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (validateFile(selectedFile)) {
        setFile(selectedFile)
      }
    }
  }

  const removeFile = () => {
    setFile(null)
    setErrorMsg("")
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  return (
    <Dialog.Root open={open} onOpenChange={(val) => {
      if (!uploadMutation.isPending) {
        onOpenChange(val)
        if (!val) {
          setFile(null)
          setObservacao("")
          setErrorMsg("")
        }
      }
    }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] transition-all duration-150 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-xl border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <Dialog.Title className="text-sm font-semibold text-zinc-900">
              Adicionar Boleto
            </Dialog.Title>
            <Dialog.Close asChild disabled={uploadMutation.isPending}>
              <button className="text-zinc-400 transition-colors hover:text-zinc-600 disabled:opacity-50">
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="space-y-4 pt-4">
            {!file ? (
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-all duration-150 cursor-pointer ${
                  dragActive
                    ? "border-orange-500 bg-orange-50/30"
                    : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50/50"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.webp"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="mx-auto flex size-10 items-center justify-center rounded-full bg-zinc-50 text-zinc-400 group-hover:bg-zinc-100 group-hover:text-zinc-600 transition-colors">
                  <UploadCloud className="size-5" />
                </div>
                <p className="mt-3 text-xs font-semibold text-zinc-700">Arrastar e soltar arquivo ou clique para selecionar</p>
                <p className="mt-1 text-[11px] text-zinc-400">PDF, JPG, PNG ou WEBP até 15MB</p>
              </div>
            ) : (
              <div className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50/50 p-4">
                <div className="flex size-10 items-center justify-center rounded-md bg-orange-100 text-orange-600">
                  <FileText className="size-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-zinc-900">{file.name}</p>
                  <p className="text-[10px] text-zinc-400">{formatSize(file.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  disabled={uploadMutation.isPending}
                  className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-50"
                >
                  <X className="size-3.5" />
                </button>
              </div>
            )}

            {errorMsg && (
              <div className="flex items-start gap-2 text-xs text-red-600">
                <AlertCircle className="size-4 flex-shrink-0 text-red-500" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-600">Observação (opcional)</label>
              <textarea
                value={observacao}
                onChange={(e) => setObservacao(e.target.value)}
                placeholder="Ex: Nota de serviço da obra X, vencimento estimado..."
                disabled={uploadMutation.isPending}
                rows={2}
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-55 disabled:opacity-50"
              />
            </div>

            <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
              <Dialog.Close asChild disabled={uploadMutation.isPending}>
                <Button type="button" variant="outline" size="sm">
                  Cancelar
                </Button>
              </Dialog.Close>
              <Button
                type="button"
                size="sm"
                loading={uploadMutation.isPending}
                disabled={!file || uploadMutation.isPending}
                onClick={() => uploadMutation.mutate()}
                className="bg-orange-500 hover:bg-orange-600 text-white font-medium"
              >
                Enviar Boleto
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
