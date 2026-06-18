import { Note, api } from '../services/api'
import { useAppStore, type ViewMode } from '../stores/appStore'
import { Pin, MoreHorizontal, Edit2, Trash2, Copy, Archive, Check, GitBranch, Download, BookOpen } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { IconButton } from './ui'
import { toast } from './ui/Toast'
import { confirm } from './ui/ConfirmDialog'
import { useTranslation } from '../hooks/useTranslation'
import { getCategoryDisplayName } from '../utils/categoryDisplay'

interface NoteCardProps {
  note: Note
  viewMode: ViewMode
}

export function NoteCard({ note, viewMode }: NoteCardProps) {
  const { openEditor, openReading, selectedNoteIds, toggleNoteSelection, deleteNote } = useAppStore()
  const { locale, t } = useTranslation()
  const [showMenu, setShowMenu] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const isSelected = selectedNoteIds.includes(note.id)
  const isSelectionMode = selectedNoteIds.length > 0

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false)
      }
    }
    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showMenu])

  // Extract first image from content for cover
  const extractFirstImage = (content: string): string | null => {
    const match = content.match(/!\[.*?\]\((.*?)\)/)
    return match ? match[1] : null
  }

  const coverImage = note.cover_image || extractFirstImage(note.content)
  const parentTitle = note.parent_title?.trim()
  const variantCount = note.variants_count ?? 0
  const lineageLabel = parentTitle ? t('noteCard.lineageFrom', { title: parentTitle }) : ''
  const categoryName = getCategoryDisplayName(note.category_name || note.type, t)

  // Truncate content for preview
  const getPreview = (content: string, maxLength = 120): string => {
    // Remove markdown images and links
    const clean = content
      .replace(/!\[.*?\]\(.*?\)/g, '')
      .replace(/\[.*?\]\(.*?\)/g, '')
      .replace(/#{1,6}\s/g, '')
      .trim()
    return clean.length > maxLength ? clean.slice(0, maxLength) + '...' : clean
  }

  // Handle card click
  const handleClick = () => {
    if (isSelectionMode) {
      toggleNoteSelection(note.id)
    } else {
      const cardOpenMode = localStorage.getItem('cardOpenMode') === 'edit' ? 'edit' : 'preview'
      if (cardOpenMode === 'edit') {
        openEditor(note)
      } else {
        openEditor(note, { preview: true })
      }
    }
  }

  // Handle long press / ctrl+click for selection
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault()
    toggleNoteSelection(note.id)
  }

  // Handle delete
  const handleDelete = async () => {
    if (!await confirm({
      title: t('noteCard.deleteTitle'),
      message: t('noteCard.deleteMessage'),
      variant: 'danger',
    })) return
    
    setIsDeleting(true)
    try {
      await deleteNote(note.id)
      toast.success(t('noteCard.deleted'))
    } catch {
      toast.error(t('noteCard.deleteFailed'))
    } finally {
      setIsDeleting(false)
      setShowMenu(false)
    }
  }

  // Handle copy content
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(note.content)
      toast.success(t('noteCard.copied'))
    } catch {
      toast.error(t('noteCard.copyFailed'))
    }
    setShowMenu(false)
  }

  // Phase 3.7: Handle create variant
  const handleCreateVariant = async () => {
    try {
      const result = await api.duplicateNote(note.id, { as_variant: true })
      toast.success(t('noteCard.variantCreated', { id: result.note_id }))
      // Refresh notes list
      const { fetchNotes } = useAppStore.getState()
      fetchNotes(true)
    } catch {
      toast.error(t('noteCard.variantFailed'))
    }
    setShowMenu(false)
  }

  // Handle toggle pin
  const handleTogglePin = async () => {
    try {
      const result = await api.togglePin(note.id)
      toast.success(result.is_pinned ? t('noteCard.pinned') : t('noteCard.unpinned'))
      // Refresh notes list
      const { fetchNotes } = useAppStore.getState()
      fetchNotes(true)
    } catch {
      toast.error(t('noteCard.togglePinFailed'))
    }
    setShowMenu(false)
  }

  // Handle export images
  const handleExportImages = async () => {
    // Extract image URLs from content
    const imagePattern = /\/static\/uploads\/[^\s\)"\]']+/g
    const matches: string[] = note.content?.match(imagePattern) || []
    
    // Add cover image if exists
    if (note.cover_image) {
      matches.unshift(note.cover_image)
    }
    
    // Remove duplicates
    const uniqueImages = [...new Set(matches)]
    
    if (uniqueImages.length === 0) {
      toast.warning(t('noteCard.noImagesToExport'))
      setShowMenu(false)
      return
    }
    
    try {
      await api.exportImages(uniqueImages, note.title || t('noteCard.untitled'))
      toast.success(t('noteCard.exportedImages', { count: uniqueImages.length }))
    } catch {
      toast.error(t('noteCard.exportImagesFailed'))
    }
    setShowMenu(false)
  }

  // Handle toggle archive
  const handleToggleArchive = async () => {
    try {
      const result = await api.toggleArchive(note.id)
      toast.success(result.is_archived ? t('noteCard.archived') : t('noteCard.unarchived'))
      // Refresh notes list
      const { fetchNotes } = useAppStore.getState()
      fetchNotes(true)
    } catch {
      toast.error(t('noteCard.toggleArchiveFailed'))
    }
    setShowMenu(false)
  }

  const handleOpenReading = () => {
    openReading(note)
    setShowMenu(false)
  }

  const handleOpenVariants = () => {
    openReading(note)
    setShowMenu(false)
  }

  if (viewMode === 'compact') {
    return (
      <div
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        data-testid={`note-card-${note.id}`}
        className={`
          group flex min-h-[48px] items-center gap-3 rounded-md px-3 py-2 cursor-pointer
          bg-bg-surface border border-border-subtle
          hover:border-border-default hover:bg-bg-elevated
          transition-colors duration-150
          ${isSelected ? 'ring-2 ring-primary bg-primary/5' : ''}
        `}
      >
        {isSelectionMode && (
          <div className={`w-4 h-4 rounded border-2 flex shrink-0 items-center justify-center
                          ${isSelected ? 'bg-primary border-primary' : 'border-border-default'}`}>
            {isSelected && <Check size={12} className="text-white" />}
          </div>
        )}

        <div className="flex min-w-0 flex-1 items-center gap-2">
          {note.is_pinned && <Pin size={13} className="shrink-0 text-warning" />}
          <h3 className="truncate text-sm font-medium text-text-primary">
            {note.title || t('noteCard.untitled')}
          </h3>
          {parentTitle && (
            <span className="hidden shrink-0 items-center gap-1 text-xs text-accent sm:inline-flex" title={lineageLabel}>
              <GitBranch size={12} />
              <span className="max-w-[120px] truncate">{parentTitle}</span>
            </span>
          )}
          {variantCount > 0 && (
            <span
              className="hidden shrink-0 items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary-light sm:inline-flex"
              data-testid={`note-card-variants-count-${note.id}`}
            >
              <GitBranch size={12} />
              {t('noteCard.variantCount', { count: variantCount })}
            </span>
          )}
          <span className="hidden min-w-0 flex-1 truncate text-xs text-text-muted md:block">
            {getPreview(note.content, 96)}
          </span>
        </div>

        <div className="hidden shrink-0 items-center gap-2 text-xs text-text-muted sm:flex">
          <span className="max-w-[140px] truncate">{categoryName}</span>
          <span>{t('noteCard.wordCount', { count: note.content?.length?.toLocaleString() || 0 })}</span>
          <span>{new Date(note.updated_at).toLocaleDateString(locale)}</span>
        </div>
      </div>
    )
  }

  if (viewMode === 'list') {
    return (
      <div
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        data-testid={`note-card-${note.id}`}
        className={`
          flex items-center gap-4 p-[var(--prism-card-padding)] rounded-xl cursor-pointer
          bg-bg-surface border border-border-subtle
          hover:border-border-default hover:bg-bg-elevated
          transition-all duration-200
          ${isSelected ? 'ring-2 ring-primary bg-primary/5' : ''}
        `}
      >
        {/* Selection Checkbox */}
        {isSelectionMode && (
          <div className={`w-5 h-5 rounded border-2 flex items-center justify-center
                          ${isSelected ? 'bg-primary border-primary' : 'border-border-default'}`}>
            {isSelected && <Check size={14} className="text-white" />}
          </div>
        )}

        {/* Thumbnail */}
        {coverImage && (
          <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
            <img
              src={coverImage}
              alt=""
              className="w-full h-full object-cover"
            />
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {note.is_pinned && <Pin size={14} className="text-warning" />}
            <h3 className="font-medium text-text-primary truncate">
              {note.title || t('noteCard.untitled')}
            </h3>
          </div>
          <p className="text-sm text-text-secondary mt-1 line-clamp-1">
            {getPreview(note.content, 80)}
          </p>
          {parentTitle && (
            <div className="mt-1 flex items-center gap-1.5 text-xs text-accent" title={lineageLabel}>
              <GitBranch size={12} />
              <span className="truncate">{lineageLabel}</span>
            </div>
          )}
          {variantCount > 0 && (
            <div
              className="mt-1 flex items-center gap-1.5 text-xs text-primary-light"
              data-testid={`note-card-variants-count-${note.id}`}
            >
              <GitBranch size={12} />
              <span className="truncate">{t('noteCard.variantCount', { count: variantCount })}</span>
            </div>
          )}
        </div>

        {/* Meta */}
        <div className="text-xs text-text-muted">
          {new Date(note.updated_at).toLocaleDateString(locale)}
        </div>
      </div>
    )
  }

  // Grid View
  return (
    <div
      onClick={handleClick}
      onContextMenu={handleContextMenu}
      data-testid={`note-card-${note.id}`}
      className={`
        group relative rounded-xl cursor-pointer
        bg-bg-surface border border-border-subtle
        hover:border-border-default hover:shadow-lg hover:shadow-black/20
        transition-all duration-300
        ${isSelected ? 'ring-2 ring-primary bg-primary/5' : ''}
      `}
    >
      {/* Selection Checkbox (top-left) */}
      <div 
        className={`absolute top-2 left-2 z-10 w-6 h-6 rounded border-2 flex items-center justify-center
                    transition-all duration-200
                    ${isSelectionMode || isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}
                    ${isSelected ? 'bg-primary border-primary' : 'bg-bg-surface/80 border-border-default hover:border-primary'}`}
        onClick={(e) => {
          e.stopPropagation()
          toggleNoteSelection(note.id)
        }}
      >
        {isSelected && <Check size={14} className="text-white" />}
      </div>

      {/* Cover Image */}
      {coverImage && (
        <div className="aspect-video overflow-hidden bg-bg-elevated rounded-t-xl">
          <img
            src={coverImage}
            alt=""
            className={`
              w-full h-full object-cover
              group-hover:scale-105 transition-transform duration-500
            `}
            style={{ objectPosition: note.cover_position || 'center' }}
          />
        </div>
      )}

      {/* Content */}
      <div className="p-[var(--prism-card-padding)]">
        {/* Title */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {note.is_pinned && (
              <Pin size={14} className="text-warning flex-shrink-0" />
            )}
            <h3 className="font-medium text-text-primary truncate">
              {note.title || t('noteCard.untitled')}
            </h3>
          </div>

          {/* Actions Menu */}
          <IconButton
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              setShowMenu(!showMenu)
            }}
            className="opacity-0 group-hover:opacity-100"
            aria-label={t('noteCard.moreActions')}
          >
            <MoreHorizontal size={16} />
          </IconButton>
        </div>

        {/* Preview */}
        <p className="text-sm text-text-secondary mt-2 line-clamp-2">
          {getPreview(note.content)}
        </p>

        {/* Tags */}
        {note.tags && note.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {note.tags.slice(0, 3).map((tag) => (
              <span
                key={tag.id}
                className="px-2 py-0.5 text-xs rounded-full
                           bg-primary/10 text-primary-light"
              >
                {tag.name}
              </span>
            ))}
            {note.tags.length > 3 && (
              <span className="px-2 py-0.5 text-xs text-text-muted">
                +{note.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Parent Lineage Badge (Phase 3.7) */}
        {parentTitle && (
          <div className="flex items-center gap-1.5 mt-2 text-xs text-accent">
            <GitBranch size={12} />
            <span className="truncate" title={lineageLabel}>
              {t('noteCard.lineageFrom', { title: parentTitle.substring(0, 20) })}
              {parentTitle.length > 20 ? '...' : ''}
            </span>
          </div>
        )}
        {variantCount > 0 && (
          <div
            className="flex items-center gap-1.5 mt-2 text-xs text-primary-light"
            data-testid={`note-card-variants-count-${note.id}`}
          >
            <GitBranch size={12} />
            <span className="truncate">
              {t('noteCard.variantCount', { count: variantCount })}
            </span>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border-subtle">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">
              {categoryName}
            </span>
            <span className="text-xs text-text-muted">
              {t('noteCard.wordCount', { count: note.content?.length?.toLocaleString() || 0 })}
            </span>
          </div>
          <span className="text-xs text-text-muted">
            {new Date(note.updated_at).toLocaleDateString(locale)}
          </span>
        </div>
      </div>

      {/* Dropdown Menu */}
      {showMenu && (
        <div
          ref={menuRef}
          onClick={(e) => e.stopPropagation()}
          className="absolute top-2 right-2 z-20
                     bg-bg-elevated border border-border-default rounded-lg
                     shadow-xl shadow-black/30 py-1 min-w-[140px]"
        >
          <button
            onClick={handleOpenReading}
            className="w-full flex items-center gap-2 px-3 py-2
                       text-sm text-text-secondary
                       hover:bg-bg-hover hover:text-text-primary"
          >
            <BookOpen size={14} /> {t('noteCard.openReading')}
          </button>
          <button 
            onClick={() => {
              openEditor(note)
              setShowMenu(false)
            }}
            className="w-full flex items-center gap-2 px-3 py-2
                       text-sm text-text-secondary
                       hover:bg-bg-hover hover:text-text-primary"
          >
            <Edit2 size={14} /> {t('common.edit')}
          </button>
          <button 
            onClick={handleTogglePin}
            className={`w-full flex items-center gap-2 px-3 py-2
                       text-sm ${note.is_pinned ? 'text-warning' : 'text-text-secondary'}
                       hover:bg-bg-hover hover:text-text-primary`}
          >
            <Pin size={14} /> {note.is_pinned ? t('noteCard.unpin') : t('noteCard.pin')}
          </button>
          <button 
            onClick={handleCopy}
            className="w-full flex items-center gap-2 px-3 py-2
                       text-sm text-text-secondary
                       hover:bg-bg-hover hover:text-text-primary"
          >
            <Copy size={14} /> {t('noteCard.copyContent')}
          </button>
          <button 
            onClick={handleCreateVariant}
            className="w-full flex items-center gap-2 px-3 py-2
                       text-sm text-text-secondary
                       hover:bg-bg-hover hover:text-text-primary"
          >
            <GitBranch size={14} /> {t('noteCard.createVariant')}
          </button>
          {variantCount > 0 && (
            <button
              onClick={handleOpenVariants}
              className="w-full flex items-center gap-2 px-3 py-2
                         text-sm text-text-secondary
                         hover:bg-bg-hover hover:text-text-primary"
            >
              <GitBranch size={14} /> {t('noteCard.viewVariants')}
            </button>
          )}
          <button 
            onClick={handleToggleArchive}
            className={`w-full flex items-center gap-2 px-3 py-2
                       text-sm ${note.is_archived ? 'text-warning' : 'text-text-secondary'}
                       hover:bg-bg-hover hover:text-text-primary`}
          >
            <Archive size={14} /> {note.is_archived ? t('noteCard.unarchive') : t('noteCard.archive')}
          </button>
          <button 
            onClick={handleExportImages}
            className="w-full flex items-center gap-2 px-3 py-2
                       text-sm text-text-secondary
                       hover:bg-bg-hover hover:text-text-primary"
          >
            <Download size={14} /> {t('noteCard.exportImages')}
          </button>
          <div className="border-t border-border-subtle my-1" />
          <button 
            onClick={handleDelete}
            disabled={isDeleting}
            className="w-full flex items-center gap-2 px-3 py-2
                       text-sm text-danger
                       hover:bg-danger/10 disabled:opacity-50"
          >
            <Trash2 size={14} /> {isDeleting ? t('noteCard.deleting') : t('common.delete')}
          </button>
        </div>
      )}
    </div>
  )
}
