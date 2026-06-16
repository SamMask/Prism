import { useState, useRef, useCallback } from 'react'
import { api } from '../../services/api'
import { toast } from '../../components/ui/Toast'
import type { Attachment } from '../../components/editor/AttachmentPanel'
import { t } from '../../i18n'

export function useDragDrop(
  noteId: number | undefined,
  setContent: React.Dispatch<React.SetStateAction<string>>,
  setAttachments: React.Dispatch<React.SetStateAction<Attachment[]>>
) {
  const [isDragging, setIsDragging] = useState(false)
  const dropZoneRef = useRef<HTMLDivElement>(null)

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    e.dataTransfer.dropEffect = 'copy'
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const relatedTarget = e.relatedTarget as Node | null
    const dropZone = dropZoneRef.current
    if (!dropZone || !relatedTarget || !dropZone.contains(relatedTarget)) {
      setIsDragging(false)
    }
  }, [])

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      const files = Array.from(e.dataTransfer.files)
      const imageFiles = files.filter((f) => f.type.startsWith('image/'))
      const mdFiles = files.filter((f) => /\.(md|txt|markdown)$/.test(f.name))

      for (const file of imageFiles) {
        try {
          toast.info(t('editor.uploadToast.imageUploading'))
          const result = await api.uploadImage(file)
          setContent((prev) => prev + '\n' + `![image](${result.url})`)
          toast.success(t('editor.uploadToast.imageUploaded'))
        } catch {
          toast.error(t('editor.uploadToast.imageUploadFailed'))
        }
      }

      if (mdFiles.length > 0 && noteId) {
        for (const file of mdFiles) {
          try {
            toast.info(t('editor.attachmentsToast.uploading', { name: file.name }))
            const result = await api.uploadAttachment(noteId, file)
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
      } else if (mdFiles.length > 0) {
        toast.warning(t('editor.uploadToast.attachmentSaveFirst'))
      }
    },
    [noteId, setContent, setAttachments]
  )

  return {
    isDragging,
    dropZoneRef,
    handleDragEnter,
    handleDragOver,
    handleDragLeave,
    handleDrop,
  }
}
