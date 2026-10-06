import { useState, useEffect, useCallback, useRef } from 'react'
import { api, Note, Tag } from '../../services/api'
import { useAppStore } from '../../stores/appStore'
import { confirm } from '../../components/ui/ConfirmDialog'
import { toast } from '../../components/ui/Toast'
import { t } from '../../i18n'
import type { FullContentState } from './useNoteAttachments'

// Moves an auto-extracted long note back into Notes.content so the following PUT replaces the
// full text (and snapshots it in history). 404 means there is nothing left to move.
// Returns true when the server moved it (and deleted that auto-extracted attachment row).
async function restoreSeparatedContent(noteId: number) {
  try {
    await api.restoreContent(noteId)
    return true
  } catch (error) {
    if ((error as { response?: { status?: number } })?.response?.status !== 404) throw error
    return false
  }
}

export function useNoteForm(note: Note | null, onClose: () => void, initialPreview = false) {
  const { fetchNotes, openEditor } = useAppStore()
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
  const savingRef = useRef(false)
  // Bumped after each successful restore so the open attachment panel can drop the deleted row.
  const [restoredCount, setRestoredCount] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Reported by useNoteAttachments; read at save time (also from the Ctrl+S handler).
  const fullContentState = useRef<FullContentState>(note ? 'pending' : 'none')
  // Set when Ctrl+S creates the note and the editor switches to editing it.
  const createdNoteId = useRef<number>()
  const noteId = note?.id
  const setFullContentState = useCallback((state: FullContentState) => {
    // The form already holds the full text of a note it just created; its attachment reload must
    // not block the next save with 'pending'.
    if (noteId !== undefined && noteId === createdNoteId.current) return
    fullContentState.current = state
  }, [noteId])

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

  // Computed every render (not memoized) because a save replaces the snapshot ref.
  const norm = (val: unknown) => (val == null ? '' : String(val))
  const snap = originalSnapshot.current
  const hasUnsavedChanges =
    norm(title) !== norm(snap.title) ||
    norm(content) !== norm(snap.content) ||
    categoryId !== snap.categoryId ||
    norm(remarks) !== norm(snap.remarks) ||
    norm(coverImage) !== norm(snap.coverImage) ||
    norm(coverPosition) !== norm(snap.coverPosition) ||
    norm(editorLayout) !== norm(snap.editorLayout) ||
    JSON.stringify(selectedTags.map((t) => t.name).sort()) !== snap.tags ||
    JSON.stringify([...sourceUrls].sort()) !== snap.urls

  // Closing the tab or window bypasses handleClose; let the browser ask first.
  useEffect(() => {
    if (!hasUnsavedChanges) return
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    // The Windows desktop shell gets no beforeunload prompt on window close; it asks natively
    // with this message instead. Absent in browsers, so this is a no-op there.
    const desktop = window as Window & { prismDesktopSetUnsaved?: (message: string) => unknown }
    desktop.prismDesktopSetUnsaved?.(t('editor.form.unsavedMessage'))
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
      desktop.prismDesktopSetUnsaved?.('')
    }
  }, [hasUnsavedChanges])

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
  // Ctrl+S saves and stays (close: false); the Save button saves and closes.
  const save = useCallback(async ({ close }: { close: boolean }) => {
    if (!title.trim() && !content.trim()) {
      toast.warning(t('editor.form.missingTitleOrContent'))
      return
    }
    // Saving without the full text would let the stale attachment overwrite this edit later.
    if (fullContentState.current === 'pending') {
      toast.info(t('common.loading'))
      return
    }
    if (fullContentState.current === 'failed') {
      toast.error(t('editor.attachmentsToast.loadFullFailed'))
      return
    }
    if (savingRef.current) return
    savingRef.current = true
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
      if (isEditing) {
        if (fullContentState.current === 'loaded') {
          if (await restoreSeparatedContent(note.id)) setRestoredCount((n) => n + 1)
          fullContentState.current = 'none'
        }
        await api.updateNote(note.id, payload)
        toast.success(t('editor.form.updated'))
      } else {
        const { note_id } = await api.createNote(payload)
        toast.success(t('editor.form.created'))
        if (!close) {
          // Keep editing the saved note so the next save is an update; if it can't be fetched,
          // close instead of risking a duplicate create.
          createdNoteId.current = note_id
          const created = await api.getNote(note_id).catch(() => null)
          if (created) openEditor(created, { inPlace: true })
          else close = true
        }
      }
      originalSnapshot.current = {
        title,
        content,
        categoryId,
        remarks,
        coverImage,
        coverPosition,
        editorLayout,
        tags: JSON.stringify(selectedTags.map((t) => t.name).sort()),
        urls: JSON.stringify([...finalUrls].sort()),
      }
      fetchNotes(true)
      if (close) onClose()
    } catch {
      toast.error(t('editor.form.saveFailed'))
    } finally {
      savingRef.current = false
      setIsSaving(false)
    }
  }, [title, content, categoryId, selectedTags, remarks, coverPosition, coverImage, editorLayout, sourceUrls, urlInput, isEditing, note, fetchNotes, openEditor, onClose])

  const handleSave = useCallback(() => save({ close: true }), [save])

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
        case 's': e.preventDefault(); save({ close: false }); break
        case 'b': e.preventDefault(); applyFormat('**'); break
        case 'i': e.preventDefault(); applyFormat('*'); break
        case 'k': e.preventDefault(); applyFormat('[', '](url)'); break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [save, applyFormat])

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
    restoredCount,
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
    setFullContentState,
  }
}
