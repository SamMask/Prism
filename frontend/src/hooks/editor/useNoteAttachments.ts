import { useState, useRef, useCallback } from 'react'
import { api, Note } from '../../services/api'
import { confirm } from '../../components/ui/ConfirmDialog'
import { toast } from '../../components/ui/Toast'
import type { Attachment } from '../../components/editor/AttachmentPanel'

export function useNoteAttachments(
  note: Note | null,
  setContent: (c: string) => void,
  updateOriginalContent: (c: string) => void
) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const attachmentInputRef = useRef<HTMLInputElement>(null)

  const loadAttachments = useCallback(async () => {
    if (!note?.id) return
    try {
      const data = await api.getNoteAttachments(note.id)
      setAttachments(data)
      const autoExtracted = data.find((a: Attachment) => a.is_auto_extracted)
      if (autoExtracted) {
        try {
          const { content: fullContent } = await api.getAttachmentContent(autoExtracted.id)
          setContent(fullContent)
          updateOriginalContent(fullContent)
        } catch {
          toast.error('無法載入完整內容，目前顯示預覽')
        }
      }
    } catch {
      console.error('Failed to load attachments')
    }
  }, [note?.id, setContent, updateOriginalContent])

  const handleAttachmentSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0 || !note?.id) return
    for (const file of Array.from(files)) {
      try {
        toast.info(`上傳 ${file.name}...`)
        const result = await api.uploadAttachment(note.id, file)
        setAttachments((prev) => [
          ...prev,
          {
            id: result.id,
            file_path: result.file_path,
            file_type: file.name.split('.').pop() || 'md',
            title: result.title,
            size_bytes: result.size_bytes,
            is_auto_extracted: false,
            created_at: new Date().toISOString(),
          },
        ])
        toast.success(`附件 "${result.title}" 已上傳`)
      } catch (error: unknown) {
        const axiosErr = error as { response?: { data?: { message?: string } } }
        toast.error(axiosErr?.response?.data?.message || '附件上傳失敗')
      }
    }
    if (attachmentInputRef.current) attachmentInputRef.current.value = ''
  }

  const handleDeleteAttachment = async (attachmentId: number) => {
    const ok = await confirm({ title: '刪除附件', message: '確定要刪除此附件？', variant: 'danger' })
    if (!ok) return
    try {
      await api.deleteAttachment(attachmentId)
      setAttachments((prev) => prev.filter((a) => a.id !== attachmentId))
      toast.success('附件已刪除')
    } catch {
      toast.error('刪除附件失敗')
    }
  }

  const handleLoadAttachment = async (attachmentId: number, isAutoExtracted: boolean) => {
    try {
      const { content: attachmentContent } = await api.getAttachmentContent(attachmentId)
      if (isAutoExtracted) {
        setContent(attachmentContent)
        toast.success('內容已載入')
      } else {
        const win = window.open('', '_blank')
        if (win) {
          win.document.write(`
            <html>
              <head>
                <title>附件內容</title>
                <style>body{font-family:monospace;padding:20px;background:#1a1a2e;color:#e0e0e0}pre{white-space:pre-wrap;word-wrap:break-word}</style>
              </head>
              <body><pre>${attachmentContent}</pre></body>
            </html>
          `)
          win.document.close()
        }
      }
    } catch {
      toast.error('讀取附件失敗')
    }
  }

  return {
    attachments,
    setAttachments,
    attachmentInputRef,
    loadAttachments,
    handleAttachmentSelect,
    handleDeleteAttachment,
    handleLoadAttachment,
  }
}
