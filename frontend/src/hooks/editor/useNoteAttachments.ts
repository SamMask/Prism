import { useState, useRef, useCallback } from 'react'
import { api, Note } from '../../services/api'
import { confirm } from '../../components/ui/ConfirmDialog'
import { toast } from '../../components/ui/Toast'
import type { Attachment } from '../../components/editor/AttachmentPanel'
import { t } from '../../i18n'

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
          toast.error(t('editor.attachmentsToast.loadFullFailed'))
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
        toast.info(t('editor.attachmentsToast.uploading', { name: file.name }))
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
        toast.success(t('editor.attachmentsToast.uploaded', { title: result.title }))
      } catch (error: unknown) {
        const axiosErr = error as { response?: { data?: { message?: string } } }
        toast.error(axiosErr?.response?.data?.message || t('editor.attachmentsToast.uploadFailed'))
      }
    }
    if (attachmentInputRef.current) attachmentInputRef.current.value = ''
  }

  const handleDeleteAttachment = async (attachmentId: number) => {
    const ok = await confirm({
      title: t('editor.attachmentsToast.deleteTitle'),
      message: t('editor.attachmentsToast.deleteMessage'),
      variant: 'danger',
    })
    if (!ok) return
    try {
      await api.deleteAttachment(attachmentId)
      setAttachments((prev) => prev.filter((a) => a.id !== attachmentId))
      toast.success(t('editor.attachmentsToast.deleted'))
    } catch {
      toast.error(t('editor.attachmentsToast.deleteFailed'))
    }
  }

  const handleLoadAttachment = async (attachmentId: number, isAutoExtracted: boolean) => {
    try {
      const { content: attachmentContent } = await api.getAttachmentContent(attachmentId)
      if (isAutoExtracted) {
        setContent(attachmentContent)
        toast.success(t('editor.attachmentsToast.loaded'))
      } else {
        const win = window.open('', '_blank')
        if (win) {
          win.document.write(`
            <html>
              <head>
                <title>${t('editor.attachment.contentTitle')}</title>
                <style>body{font-family:monospace;padding:20px;background:#1a1a2e;color:#e0e0e0}pre{white-space:pre-wrap;word-wrap:break-word}</style>
              </head>
              <body><pre>${attachmentContent}</pre></body>
            </html>
          `)
          win.document.close()
        }
      }
    } catch {
      toast.error(t('editor.attachmentsToast.readFailed'))
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
