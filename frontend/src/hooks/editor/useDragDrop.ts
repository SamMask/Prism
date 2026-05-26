import { useState, useRef, useCallback } from 'react'
import { api } from '../../services/api'
import { toast } from '../../components/ui/Toast'
import type { Attachment } from '../../components/editor/AttachmentPanel'

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
          toast.info('上傳圖片中...')
          const result = await api.uploadImage(file)
          setContent((prev) => prev + '\n' + `![image](${result.url})`)
          toast.success('圖片已上傳')
        } catch {
          toast.error('圖片上傳失敗')
        }
      }

      if (mdFiles.length > 0 && noteId) {
        for (const file of mdFiles) {
          try {
            toast.info(`上傳 ${file.name}...`)
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
            toast.success(`附件 "${result.title}" 已上傳`)
          } catch (error: unknown) {
            const axiosErr = error as { response?: { data?: { message?: string } } }
            toast.error(axiosErr?.response?.data?.message || '附件上傳失敗')
          }
        }
      } else if (mdFiles.length > 0) {
        toast.warning('請先儲存筆記後再上傳附件')
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
