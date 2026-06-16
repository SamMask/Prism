import { marked } from 'marked'
import { Archive, Copy, Edit2, GitBranch, Pin, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Note, api } from '../services/api'
import { useAppStore } from '../stores/appStore'
import { Modal, Button } from './ui'
import { toast } from './ui/Toast'
import { useTranslation } from '../hooks/useTranslation'

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

export function ReadingView({ note, onClose }: ReadingViewProps) {
  const { openEditor, fetchNotes } = useAppStore()
  const { locale, t } = useTranslation()
  const [localNote, setLocalNote] = useState(note)
  const coverImage = localNote.cover_image || extractFirstImage(localNote.content || '')
  const renderedContent = useMemo(() => renderMarkdown(localNote.content || '', t('reading.emptyContent')), [localNote.content, t])
  const updatedAt = new Date(localNote.updated_at).toLocaleString(locale)

  useEffect(() => {
    let isMounted = true
    api.getNote(note.id)
      .then((detail) => {
        if (isMounted) setLocalNote(detail)
      })
      .catch(() => {
        toast.error(t('reading.loadFailed'))
      })

    return () => {
      isMounted = false
    }
  }, [note.id])

  const handleEdit = () => {
    onClose()
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

  return (
    <Modal isOpen onClose={onClose} size="full">
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
              <span>{localNote.category_name || localNote.type || t('reading.uncategorized')}</span>
              <span>·</span>
              <span>{updatedAt}</span>
              {localNote.parent_title && (
                <>
                  <span>·</span>
                  <span className="inline-flex items-center gap-1 text-accent">
                    <GitBranch size={12} />
                    {localNote.parent_title}
                  </span>
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
            onClick={onClose}
            className="rounded-md p-2 text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
            aria-label={t('reading.closePanel')}
          >
            <X size={20} />
          </button>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_220px]">
          <div className="overflow-y-auto px-5 py-5 lg:px-8 lg:py-7">
            {coverImage && (
              <img
                src={coverImage}
                alt=""
                className="mb-6 max-h-[360px] w-full rounded-lg border border-border-subtle object-cover"
                style={{ objectPosition: localNote.cover_position || 'center' }}
              />
            )}
            <div
              className="prose prose-invert max-w-none text-text-primary prose-headings:text-text-primary prose-a:text-primary prose-strong:text-text-primary prose-code:rounded prose-code:bg-bg-elevated prose-code:px-1 prose-img:rounded-lg"
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
          </aside>
        </div>
      </article>
    </Modal>
  )
}
