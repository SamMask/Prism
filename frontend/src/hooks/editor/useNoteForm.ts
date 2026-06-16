import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { api, Note, Tag } from '../../services/api'
import { useAppStore } from '../../stores/appStore'
import { confirm } from '../../components/ui/ConfirmDialog'
import { toast } from '../../components/ui/Toast'
import { t } from '../../i18n'

const SEPARATION_THRESHOLD = 5000

export function useNoteForm(note: Note | null, onClose: () => void, initialPreview = false) {
  const { fetchNotes } = useAppStore()
  const isEditing = !!note

  // ---- Form state ----
  const [title, setTitle] = useState(note?.title || '')
  const [content, setContent] = useState(note?.content || '')
  const [categoryId, setCategoryId] = useState<number | undefined>(() => {
    if (note) return note.category_id
    const saved = localStorage.getItem('quickAddDefaultCategory')
    return saved ? Number(saved) : undefined
  })
  const [selectedTags, setSelectedTags] = useState<Tag[]>(note?.tags || [])
  const [remarks, setRemarks] = useState(note?.remarks || '')
  const [coverPosition, setCoverPosition] = useState<'top' | 'center' | 'bottom'>(note?.cover_position || 'center')
  const [editorLayout, setEditorLayout] = useState<'single' | 'dual'>(note?.editor_layout || 'single')
  const [sourceUrls, setSourceUrls] = useState<string[]>(note?.urls || [])
  const [urlInput, setUrlInput] = useState('')
  const [coverImage, setCoverImage] = useState<string | undefined>(note?.cover_image)
  const [tagInput, setTagInput] = useState('')
  const [isPreview, setIsPreview] = useState(initialPreview)
  const [isSaving, setIsSaving] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // ---- Unsaved changes detection ----
  const originalSnapshot = useRef({
    title: note?.title || '',
    content: note?.content || '',
    categoryId: note
      ? note.category_id
      : (localStorage.getItem('quickAddDefaultCategory')
        ? Number(localStorage.getItem('quickAddDefaultCategory') ?? '0')
        : undefined),
    remarks: note?.remarks || '',
    coverImage: note?.cover_image,
    coverPosition: note?.cover_position || 'center',
    editorLayout: note?.editor_layout || 'single',
    tags: JSON.stringify((note?.tags || []).map((t) => t.name).sort()),
    urls: JSON.stringify((note?.urls || []).sort()),
  })

  // Let attachment loader update the content baseline without triggering unsaved warning
  const updateOriginalContent = useCallback((c: string) => {
    originalSnapshot.current.content = c
  }, [])

  const hasUnsavedChanges = useMemo(() => {
    const norm = (val: unknown) => (val == null ? '' : String(val))
    const snap = originalSnapshot.current
    return (
      norm(title) !== norm(snap.title) ||
      norm(content) !== norm(snap.content) ||
      categoryId !== snap.categoryId ||
      norm(remarks) !== norm(snap.remarks) ||
      norm(coverImage) !== norm(snap.coverImage) ||
      norm(coverPosition) !== norm(snap.coverPosition) ||
      norm(editorLayout) !== norm(snap.editorLayout) ||
      JSON.stringify(selectedTags.map((t) => t.name).sort()) !== snap.tags ||
      JSON.stringify([...sourceUrls].sort()) !== snap.urls
    )
  }, [title, content, categoryId, remarks, coverImage, coverPosition, editorLayout, selectedTags, sourceUrls])

  // ---- Close guard ----
  const handleClose = useCallback(async () => {
    if (hasUnsavedChanges) {
      const shouldDiscard = await confirm({
        title: t('editor.form.unsavedTitle'),
        message: t('editor.form.unsavedMessage'),
        confirmText: t('editor.form.discard'),
        variant: 'warning',
      })
      if (!shouldDiscard) return
    }
    onClose()
  }, [hasUnsavedChanges, onClose])

  // ---- Save ----
  const handleSave = useCallback(async () => {
    if (!title.trim() && !content.trim()) {
      toast.warning(t('editor.form.missingTitleOrContent'))
      return
    }
    setIsSaving(true)
    try {
      let finalUrls = [...sourceUrls]
      if (urlInput.trim()) {
        let url = urlInput.trim()
        if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'https://' + url
        if (!finalUrls.includes(url)) finalUrls.push(url)
        setUrlInput('')
        setSourceUrls(finalUrls)
      }
      const payload = {
        title: title.trim() || t('editor.form.untitled'),
        content,
        category_id: categoryId,
        remarks,
        tags: selectedTags.map((t) => t.name),
        cover_position: coverPosition,
        cover_image: coverImage || undefined,
        editor_layout: editorLayout,
        urls: finalUrls,
      }
      let savedNoteId: number
      if (isEditing) {
        await api.updateNote(note.id, payload)
        savedNoteId = note.id
        toast.success(t('editor.form.updated'))
      } else {
        const result = await api.createNote(payload)
        savedNoteId = result.note_id
        toast.success(t('editor.form.created'))
      }
      if (content.length > SEPARATION_THRESHOLD) {
        try {
          await api.separateContent(savedNoteId)
        } catch {
          toast.warning(t('editor.form.separationFailed'))
        }
      }
      fetchNotes(true)
      onClose()
    } catch {
      toast.error(t('editor.form.saveFailed'))
    } finally {
      setIsSaving(false)
    }
  }, [title, content, categoryId, selectedTags, remarks, coverPosition, coverImage, editorLayout, sourceUrls, urlInput, isEditing, note, fetchNotes, onClose])

  // ---- Tag helpers ----
  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault()
      const newTag = { id: Date.now(), name: tagInput.trim() }
      if (!selectedTags.find((t) => t.name.toLowerCase() === newTag.name.toLowerCase())) {
        setSelectedTags((prev) => [...prev, newTag])
      }
      setTagInput('')
    }
  }

  const removeTag = (tagId: number) =>
    setSelectedTags((prev) => prev.filter((t) => t.id !== tagId))

  // ---- Formatting ----
  const applyFormat = useCallback(
    (prefix: string, suffix: string = prefix) => {
      const textarea = textareaRef.current
      if (!textarea) return
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const newText =
        content.substring(0, start) +
        prefix +
        content.substring(start, end) +
        suffix +
        content.substring(end)
      setContent(newText)
      setTimeout(() => {
        textarea.focus()
        textarea.setSelectionRange(start + prefix.length, end + prefix.length)
      }, 0)
    },
    [content]
  )

  // ---- Keyboard shortcuts ----
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return
      switch (e.key.toLowerCase()) {
        case 's': e.preventDefault(); handleSave(); break
        case 'b': e.preventDefault(); applyFormat('**'); break
        case 'i': e.preventDefault(); applyFormat('*'); break
        case 'k': e.preventDefault(); applyFormat('[', '](url)'); break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleSave, applyFormat])

  return {
    // form state
    title, setTitle,
    content, setContent,
    categoryId, setCategoryId,
    selectedTags, setSelectedTags,
    remarks, setRemarks,
    coverPosition, setCoverPosition,
    editorLayout, setEditorLayout,
    sourceUrls, setSourceUrls,
    urlInput, setUrlInput,
    coverImage, setCoverImage,
    tagInput, setTagInput,
    isPreview, setIsPreview,
    isSaving,
    textareaRef,
    isEditing,
    // derived
    hasUnsavedChanges,
    // actions
    handleClose,
    handleSave,
    handleTagKeyDown,
    removeTag,
    applyFormat,
    updateOriginalContent,
  }
}
