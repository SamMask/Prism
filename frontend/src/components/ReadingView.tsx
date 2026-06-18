import { marked } from 'marked'
import { Archive, Copy, Edit2, GitBranch, ListPlus, ListX, Loader2, Pin, X } from 'lucide-react'
import { type MouseEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Note, api } from '../services/api'
import { useAppStore } from '../stores/appStore'
import { Modal, Button } from './ui'
import { toast } from './ui/Toast'
import { useTranslation } from '../hooks/useTranslation'
import { useReadingWorkspace } from '../hooks/useReadingWorkspace'
import { getCategoryDisplayName } from '../utils/categoryDisplay'
import { extractImageReferences } from './editor/imageReferences'
import { ImageLightbox, type LightboxImage } from './ImageLightbox'

interface ReadingViewProps {
  note: Note
  onClose: () => void
}

function extractFirstImage(content: string): string | null {
  const markdownMatch = content.match(/!\[.*?\]\((.*?)\)/)
  if (markdownMatch) return markdownMatch[1]

  const htmlMatch = content.match(/<img[^>]+src=["']([^"']+)["']/i)
  return htmlMatch?.[1] ?? null
}

function renderMarkdown(markdown: string, emptyContent: string): string {
  if (!markdown.trim()) return `<p class="text-text-muted">${emptyContent}</p>`
  try {
    marked.setOptions({ breaks: true, gfm: true })
    return marked(markdown) as string
  } catch {
    return markdown
  }
}

function collectReadingImages(coverImage: string | null, content: string, title: string): LightboxImage[] {
  const images: LightboxImage[] = []
  const addImage = (src: string | null | undefined) => {
    if (!src || images.some((image) => image.src === src)) return
    images.push({ src, alt: title })
  }

  addImage(coverImage)
  extractImageReferences(content).forEach((src) => addImage(src))
  return images
}

function imageSourceMatches(candidate: string, observed: string): boolean {
  return candidate === observed || observed.endsWith(candidate)
}

export function ReadingView({ note, onClose }: ReadingViewProps) {
  const { openEditor, fetchNotes } = useAppStore()
  const { locale, t } = useTranslation()
  const {
    workspace,
    addNote,
    removeNote,
    clearWorkspace,
    setActiveNote,
    saveScrollPosition,
    getScrollPosition,
  } = useReadingWorkspace()
  const [localNote, setLocalNote] = useState(note)
  const [childVariants, setChildVariants] = useState<Note[]>([])
  const [isVariantsLoading, setIsVariantsLoading] = useState(false)
  const [isAutoContentLoading, setIsAutoContentLoading] = useState(false)
  const [workspaceNotes, setWorkspaceNotes] = useState<Record<number, Note>>({})
  const [workspaceUnavailableIds, setWorkspaceUnavailableIds] = useState<number[]>([])
  const [isWorkspaceSwitching, setIsWorkspaceSwitching] = useState(false)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const readingScrollRef = useRef<HTMLDivElement>(null)
  const pendingScrollRestoreIdRef = useRef<number | null>(null)
  const workspaceIdsKey = workspace.noteIds.join(',')
  const isCurrentInWorkspace = workspace.noteIds.includes(localNote.id)
  const coverImage = localNote.cover_image || extractFirstImage(localNote.content || '')
  const readingImages = useMemo(
    () => collectReadingImages(coverImage, localNote.content || '', localNote.title || t('reading.untitled')),
    [coverImage, localNote.content, localNote.title, t],
  )
  const renderedContent = useMemo(() => renderMarkdown(localNote.content || '', t('reading.emptyContent')), [localNote.content, t])
  const updatedAt = new Date(localNote.updated_at).toLocaleString(locale)
  const categoryName = getCategoryDisplayName(
    localNote.category_name || localNote.type,
    t,
    t('reading.uncategorized'),
  )

  useEffect(() => {
    let isMounted = true
    setLocalNote(note)
    setWorkspaceNotes((current) => ({ ...current, [note.id]: note }))
    if (workspace.noteIds.includes(note.id)) {
      setActiveNote(note.id)
      pendingScrollRestoreIdRef.current = note.id
    }
    api.getNote(note.id)
      .then((detail) => {
        if (!isMounted) return
        setLocalNote(detail)
        setWorkspaceNotes((current) => ({ ...current, [detail.id]: detail }))
      })
      .catch(() => {
        toast.error(t('reading.loadFailed'))
      })

    return () => {
      isMounted = false
    }
  }, [note.id])

  useEffect(() => {
    setWorkspaceNotes((current) => ({ ...current, [localNote.id]: localNote }))
  }, [localNote])

  useEffect(() => {
    let isMounted = true
    const missingIds = workspace.noteIds.filter((id) => (
      id !== localNote.id && !workspaceNotes[id] && !workspaceUnavailableIds.includes(id)
    ))

    missingIds.forEach((noteId) => {
      api.getNote(noteId)
        .then((detail) => {
          if (!isMounted) return
          setWorkspaceNotes((current) => ({ ...current, [detail.id]: detail }))
        })
        .catch(() => {
          if (!isMounted) return
          setWorkspaceUnavailableIds((current) => (
            current.includes(noteId) ? current : [...current, noteId]
          ))
        })
    })

    return () => {
      isMounted = false
    }
  }, [workspaceIdsKey, localNote.id])

  useEffect(() => {
    if (pendingScrollRestoreIdRef.current !== localNote.id) return
    const node = readingScrollRef.current
    if (!node) return

    const frame = window.requestAnimationFrame(() => {
      node.scrollTop = getScrollPosition(localNote.id)
      if (pendingScrollRestoreIdRef.current === localNote.id) {
        pendingScrollRestoreIdRef.current = null
      }
    })

    return () => window.cancelAnimationFrame(frame)
  }, [localNote.id, renderedContent, getScrollPosition])

  useEffect(() => {
    let isMounted = true
    setIsAutoContentLoading(true)
    api.getNoteAttachments(localNote.id)
      .then(async (attachments) => {
        const autoExtracted = attachments.find((attachment) => attachment.is_auto_extracted)
        if (!autoExtracted) return
        const { content } = await api.getAttachmentContent(autoExtracted.id)
        if (!isMounted) return
        setLocalNote((current) => (
          current.id === localNote.id ? { ...current, content } : current
        ))
      })
      .catch(() => {
        if (isMounted) toast.error(t('editor.attachmentsToast.loadFullFailed'))
      })
      .finally(() => {
        if (isMounted) setIsAutoContentLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [localNote.id, t])

  useEffect(() => {
    let isMounted = true
    setIsVariantsLoading(true)
    api.getNotes({
      parent_id: localNote.id,
      per_page: 100,
      include_archived: true,
      sort: 'updated',
    })
      .then((response) => {
        if (isMounted) setChildVariants(response.notes)
      })
      .catch(() => {
        if (isMounted) setChildVariants([])
      })
      .finally(() => {
        if (isMounted) setIsVariantsLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [localNote.id])

  const persistCurrentScroll = useCallback(() => {
    const scrollTop = readingScrollRef.current?.scrollTop ?? 0
    if (workspace.noteIds.includes(localNote.id)) {
      saveScrollPosition(localNote.id, scrollTop)
    }
  }, [localNote.id, saveScrollPosition, workspace.noteIds])

  const handleClose = useCallback(() => {
    persistCurrentScroll()
    onClose()
  }, [onClose, persistCurrentScroll])

  const handleEdit = () => {
    handleClose()
    openEditor(localNote)
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(localNote.content || '')
      toast.success(t('noteCard.copied'))
    } catch {
      toast.error(t('noteCard.copyFailed'))
    }
  }

  const handleOpenWorkspaceNote = async (noteId: number) => {
    if (noteId === localNote.id) return
    persistCurrentScroll()
    setIsWorkspaceSwitching(true)

    try {
      const detail = workspaceNotes[noteId] ?? await api.getNote(noteId)
      setActiveNote(noteId)
      pendingScrollRestoreIdRef.current = noteId
      setWorkspaceNotes((current) => ({ ...current, [detail.id]: detail }))
      setWorkspaceUnavailableIds((current) => current.filter((id) => id !== noteId))
      setLocalNote(detail)
    } catch {
      setWorkspaceUnavailableIds((current) => (
        current.includes(noteId) ? current : [...current, noteId]
      ))
      toast.error(t('reading.workspaceLoadFailed'))
    } finally {
      setIsWorkspaceSwitching(false)
    }
  }

  const handleOpenRelatedNote = async (noteId: number) => {
    if (noteId === localNote.id) return
    persistCurrentScroll()
    try {
      const detail = await api.getNote(noteId)
      if (workspace.noteIds.includes(noteId)) {
        setActiveNote(noteId)
        pendingScrollRestoreIdRef.current = noteId
      }
      setWorkspaceNotes((current) => ({ ...current, [detail.id]: detail }))
      setWorkspaceUnavailableIds((current) => current.filter((id) => id !== noteId))
      setLocalNote(detail)
    } catch {
      toast.error(t('reading.openRelatedFailed'))
    }
  }

  const handleAddCurrentToWorkspace = () => {
    addNote(localNote.id, { activate: true })
    setWorkspaceNotes((current) => ({ ...current, [localNote.id]: localNote }))
    setWorkspaceUnavailableIds((current) => current.filter((id) => id !== localNote.id))
    toast.success(t('reading.workspaceAdded'))
  }

  const handleRemoveWorkspaceNote = (noteId: number) => {
    removeNote(noteId)
    setWorkspaceUnavailableIds((current) => current.filter((id) => id !== noteId))
  }

  const handleClearWorkspace = () => {
    clearWorkspace()
    setWorkspaceUnavailableIds([])
  }

  const handleReadingScroll = () => {
    if (!isCurrentInWorkspace) return
    saveScrollPosition(localNote.id, readingScrollRef.current?.scrollTop ?? 0)
  }

  const openLightboxForSource = (src: string | null | undefined) => {
    if (!src) return
    const index = readingImages.findIndex((image) => imageSourceMatches(image.src, src))
    if (index >= 0) setLightboxIndex(index)
  }

  const handleMarkdownImageClick = (event: MouseEvent<HTMLDivElement>) => {
    const target = event.target
    if (!(target instanceof HTMLImageElement)) return
    openLightboxForSource(target.getAttribute('src') || target.src)
  }

  const handleTogglePin = async () => {
    try {
      const result = await api.togglePin(localNote.id)
      setLocalNote({ ...localNote, is_pinned: result.is_pinned })
      fetchNotes(true)
      toast.success(result.is_pinned ? t('noteCard.pinned') : t('noteCard.unpinned'))
    } catch {
      toast.error(t('noteCard.togglePinFailed'))
    }
  }

  const handleToggleArchive = async () => {
    try {
      const result = await api.toggleArchive(localNote.id)
      setLocalNote({ ...localNote, is_archived: result.is_archived })
      fetchNotes(true)
      toast.success(result.is_archived ? t('noteCard.archived') : t('noteCard.unarchived'))
    } catch {
      toast.error(t('noteCard.toggleArchiveFailed'))
    }
  }

  const workspaceItems = workspace.noteIds.map((noteId) => {
    const workspaceNote = noteId === localNote.id ? localNote : workspaceNotes[noteId]
    return {
      id: noteId,
      note: workspaceNote,
      title: workspaceNote?.title || t('reading.untitled'),
      updatedAt: workspaceNote?.updated_at,
      isUnavailable: workspaceUnavailableIds.includes(noteId),
    }
  })

  return (
    <Modal isOpen onClose={lightboxIndex === null ? handleClose : () => setLightboxIndex(null)} size="full">
      <article className="flex max-h-[88vh] flex-col overflow-hidden" data-testid="reading-view">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border-subtle px-5 py-4 lg:px-6">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-text-muted">
              {localNote.is_pinned && (
                <span className="inline-flex items-center gap-1 rounded-md bg-warning/10 px-2 py-1 text-warning">
                  <Pin size={12} />
                  {t('reading.pinnedBadge')}
                </span>
              )}
              {localNote.is_archived && (
                <span className="inline-flex items-center gap-1 rounded-md bg-bg-elevated px-2 py-1 text-text-secondary">
                  <Archive size={12} />
                  {t('reading.archivedBadge')}
                </span>
              )}
              <span>{categoryName}</span>
              <span>·</span>
              <span>{updatedAt}</span>
              {localNote.parent_id && localNote.parent_title && (
                <>
                  <span>·</span>
                  <button
                    type="button"
                    onClick={() => handleOpenRelatedNote(localNote.parent_id!)}
                    className="inline-flex items-center gap-1 text-accent transition-colors hover:text-primary-light"
                    title={t('reading.parentNote')}
                  >
                    <GitBranch size={12} />
                    {localNote.parent_title}
                  </button>
                </>
              )}
            </div>
            <h1 className="truncate text-2xl font-semibold leading-tight text-text-primary lg:text-3xl">
              {localNote.title || t('reading.untitled')}
            </h1>
            {localNote.tags?.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {localNote.tags.map((tag) => (
                  <span key={tag.id} className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary-light">
                    #{tag.name}
                  </span>
                ))}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleClose}
            className="rounded-md p-2 text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
            aria-label={t('reading.closePanel')}
          >
            <X size={20} />
          </button>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_220px]">
          <div
            ref={readingScrollRef}
            onScroll={handleReadingScroll}
            className="overflow-y-auto px-5 py-5 lg:px-8 lg:py-7"
            data-testid="reading-scroll-container"
          >
            {coverImage && (
              <button
                type="button"
                onClick={() => openLightboxForSource(coverImage)}
                className="mb-6 block w-full overflow-hidden rounded-lg border border-border-subtle bg-bg-elevated text-left"
                aria-label={t('reading.lightboxOpenImage')}
              >
                <img
                  src={coverImage}
                  alt=""
                  className="max-h-[360px] w-full object-cover"
                  style={{ objectPosition: localNote.cover_position || 'center' }}
                  data-testid="reading-cover-image"
                />
              </button>
            )}
            <div
              className="prose prose-invert max-w-none text-text-primary prose-headings:text-text-primary prose-a:text-primary prose-strong:text-text-primary prose-code:rounded prose-code:bg-bg-elevated prose-code:px-1 prose-img:cursor-zoom-in prose-img:rounded-lg"
              aria-busy={isAutoContentLoading}
              data-testid="reading-content"
              onClick={handleMarkdownImageClick}
              dangerouslySetInnerHTML={{ __html: renderedContent }}
            />
            {localNote.remarks && (
              <aside className="mt-8 rounded-lg border border-border-subtle bg-bg-elevated/40 p-4">
                <div className="mb-2 text-xs font-medium uppercase tracking-wider text-text-muted">{t('reading.remarks')}</div>
                <p className="whitespace-pre-wrap text-sm text-text-secondary">{localNote.remarks}</p>
              </aside>
            )}
          </div>

          <aside className="flex shrink-0 flex-col gap-3 border-t border-border-subtle bg-bg-elevated/25 p-4 lg:border-l lg:border-t-0">
            {workspaceItems.length > 0 && (
              <section
                className="rounded-md border border-border-subtle bg-bg-base/40 p-3"
                data-testid="reading-workspace-panel"
                data-layout={workspace.layout}
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="min-w-0 text-xs font-medium uppercase tracking-wider text-text-muted">
                    {t('reading.workspaceTitle', { count: workspaceItems.length })}
                  </div>
                  <button
                    type="button"
                    onClick={handleClearWorkspace}
                    className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
                    aria-label={t('reading.workspaceClear')}
                    title={t('reading.workspaceClear')}
                    data-testid="reading-workspace-clear"
                  >
                    <ListX size={14} />
                  </button>
                </div>
                <div className="flex max-h-48 flex-col gap-2 overflow-y-auto">
                  {workspaceItems.map((item) => (
                    <div
                      key={item.id}
                      className={`flex min-w-0 items-stretch rounded-md border transition-colors ${
                        item.id === localNote.id
                          ? 'border-primary/50 bg-primary/10'
                          : 'border-border-subtle bg-bg-surface/80 hover:bg-bg-hover'
                      }`}
                      data-testid={`reading-workspace-item-${item.id}`}
                      data-active={item.id === localNote.id}
                      data-unavailable={item.isUnavailable}
                    >
                      <button
                        type="button"
                        onClick={() => handleOpenWorkspaceNote(item.id)}
                        className="flex min-w-0 flex-1 flex-col px-2.5 py-2 text-left"
                        disabled={isWorkspaceSwitching && item.id !== localNote.id}
                      >
                        <span className="truncate text-sm text-text-primary">
                          {item.title}
                        </span>
                        <span className="mt-0.5 text-xs text-text-muted">
                          {item.isUnavailable
                            ? t('reading.workspaceUnavailable')
                            : item.updatedAt
                              ? new Date(item.updatedAt).toLocaleDateString(locale)
                              : t('reading.workspacePending')}
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRemoveWorkspaceNote(item.id)}
                        className="flex w-8 shrink-0 items-center justify-center rounded-r-md text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
                        aria-label={t('reading.workspaceRemove')}
                        title={t('reading.workspaceRemove')}
                        data-testid={`reading-workspace-remove-${item.id}`}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {!isCurrentInWorkspace && (
              <button
                type="button"
                onClick={handleAddCurrentToWorkspace}
                className="flex items-center justify-center gap-2 rounded-md border border-border-default px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
                data-testid="reading-workspace-add-current"
              >
                <ListPlus size={16} />
                {t('reading.workspaceAddCurrent')}
              </button>
            )}
            {isWorkspaceSwitching && (
              <div className="flex items-center justify-center gap-2 rounded-md border border-border-subtle px-3 py-2 text-sm text-text-muted">
                <Loader2 size={16} className="animate-spin" />
                {t('reading.workspaceLoading')}
              </div>
            )}
            <Button onClick={handleEdit} variant="primary" className="justify-center">
              <Edit2 size={16} />
              {t('reading.edit')}
            </Button>
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center justify-center gap-2 rounded-md border border-border-default px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
            >
              <Copy size={16} />
              {t('reading.copyContent')}
            </button>
            <button
              type="button"
              onClick={handleTogglePin}
              className="flex items-center justify-center gap-2 rounded-md border border-border-default px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
            >
              <Pin size={16} />
              {localNote.is_pinned ? t('reading.unpin') : t('reading.pin')}
            </button>
            <button
              type="button"
              onClick={handleToggleArchive}
              className="flex items-center justify-center gap-2 rounded-md border border-border-default px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
            >
              <Archive size={16} />
              {localNote.is_archived ? t('reading.unarchive') : t('reading.archive')}
            </button>

            {(localNote.parent_id || childVariants.length > 0 || (localNote.variants_count ?? 0) > 0 || isVariantsLoading) && (
              <section className="mt-2 border-t border-border-subtle pt-4" data-testid="reading-variant-panel">
                <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-text-muted">
                  <GitBranch size={13} />
                  {t('reading.variantsTitle')}
                </div>

                {localNote.parent_id && (
                  <button
                    type="button"
                    onClick={() => handleOpenRelatedNote(localNote.parent_id!)}
                    className="mb-2 flex w-full min-w-0 items-center gap-2 rounded-md border border-border-subtle px-3 py-2 text-left text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
                    data-testid="reading-parent-link"
                  >
                    <GitBranch size={14} className="shrink-0 text-accent" />
                    <span className="min-w-0 flex-1 truncate">
                      {localNote.parent_title || t('reading.parentNote')}
                    </span>
                  </button>
                )}

                <div className="space-y-2">
                  {isVariantsLoading && (
                    <div className="rounded-md border border-border-subtle px-3 py-2 text-sm text-text-muted">
                      {t('reading.variantsLoading')}
                    </div>
                  )}
                  {!isVariantsLoading && childVariants.length === 0 && (localNote.variants_count ?? 0) > 0 && (
                    <div className="rounded-md border border-border-subtle px-3 py-2 text-sm text-text-muted">
                      {t('reading.variantsUnavailable')}
                    </div>
                  )}
                  {!isVariantsLoading && childVariants.map((variant) => (
                    <button
                      key={variant.id}
                      type="button"
                      onClick={() => handleOpenRelatedNote(variant.id)}
                      className="flex w-full min-w-0 flex-col rounded-md border border-border-subtle px-3 py-2 text-left transition-colors hover:bg-bg-hover"
                      data-testid={`reading-variant-child-${variant.id}`}
                    >
                      <span className="truncate text-sm text-text-primary">
                        {variant.title || t('reading.untitled')}
                      </span>
                      <span className="mt-0.5 text-xs text-text-muted">
                        {new Date(variant.updated_at).toLocaleDateString(locale)}
                      </span>
                    </button>
                  ))}
                </div>
              </section>
            )}
          </aside>
        </div>
      </article>
      {lightboxIndex !== null && (
        <ImageLightbox
          images={readingImages}
          activeIndex={lightboxIndex}
          onActiveIndexChange={setLightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </Modal>
  )
}
