import { useEffect, useRef, useCallback, useState } from 'react'
import { useAppStore, type ViewMode } from '../stores/appStore'
import { NoteCard } from '../components/NoteCard'
import { NoteEditor } from '../components/NoteEditor'
import { ReadingView } from '../components/ReadingView'
import { ToastContainer, toast } from '../components/ui/Toast'
import { Loader2 } from 'lucide-react'
import { useTranslation } from '../hooks/useTranslation'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Note, api } from '../services/api'

// Sortable NoteCard wrapper
function SortableNoteCard({ note, viewMode }: { note: Note; viewMode: ViewMode }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: note.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 100 : 'auto',
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <NoteCard note={note} viewMode={viewMode} />
    </div>
  )
}

export function HomePage() {
  const { t } = useTranslation()
  const {
    notes,
    isLoading,
    hasMore,
    viewMode,
    isEditorOpen,
    editingNote,
    editorStartsInPreview,
    isReadingOpen,
    readingNote,
    fetchNotes,
    closeEditor,
    closeReading,
    sortBy,
    searchQuery,
    selectedCategoryId,
    selectedTagId,
    showArchived,
    totalNotes,
    categories,
    tags,
  } = useAppStore()

  const [localNotes, setLocalNotes] = useState<Note[]>([])
  const observerRef = useRef<IntersectionObserver | null>(null)
  
  // Settings State
  const [autoLoadMore] = useState(() => localStorage.getItem('autoLoadMore') === 'true')

  // Sync local notes with store
  useEffect(() => {
    setLocalNotes(notes)
  }, [notes])

  useEffect(() => {
    fetchNotes(true)
  }, [fetchNotes])

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement before drag starts
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Handle drag end
  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      const oldIndex = localNotes.findIndex((n) => n.id === active.id)
      const newIndex = localNotes.findIndex((n) => n.id === over.id)

      // Optimistic update
      const newNotes = [...localNotes]
      const [removed] = newNotes.splice(oldIndex, 1)
      newNotes.splice(newIndex, 0, removed)
      setLocalNotes(newNotes)

      // Call API to save order
      try {
        const noteIds = newNotes.map((n) => n.id)
        await api.reorderNotes(noteIds)
        toast.success(t('home.reorderSuccess'))
      } catch {
        // Revert on error
        setLocalNotes(notes)
        toast.error(t('home.reorderFailed'))
      }
    }
  }

  // Infinite scroll using Intersection Observer
  const handleLoadMore = useCallback(() => {
    if (!isLoading && hasMore) {
      fetchNotes()
    }
  }, [isLoading, hasMore, fetchNotes])

  // Callback ref: re-runs whenever the trigger DOM node mounts/unmounts OR
  // when the callback identity changes (autoLoadMore / handleLoadMore).
  // This avoids the race where useEffect observes a still-null ref.
  const setLoadMoreRef = useCallback((node: HTMLDivElement | null) => {
    if (observerRef.current) {
      observerRef.current.disconnect()
      observerRef.current = null
    }

    if (!autoLoadMore || !node) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          handleLoadMore()
        }
      },
      { threshold: 0.1, rootMargin: '200px 0px' }
    )
    observer.observe(node)
    observerRef.current = observer
  }, [autoLoadMore, handleLoadMore])

  // Only enable drag when sortBy is 'custom'
  const isDragEnabled = sortBy === 'custom'
  const activeCategory = categories.find((category) => category.id === selectedCategoryId)
  const activeTag = tags.find((tag) => tag.id === selectedTagId)
  const sectionTitle = searchQuery
    ? t('home.searchResults')
    : showArchived
      ? t('home.archive')
      : activeCategory?.name || (activeTag ? `#${activeTag.name}` : t('home.all'))
  const sectionSub = searchQuery
    ? t('home.searchMeta', { query: searchQuery, count: totalNotes.toLocaleString() })
    : showArchived
      ? t('home.archiveMeta', { count: totalNotes.toLocaleString() })
      : selectedCategoryId
        ? t('home.categoryMeta', { count: totalNotes.toLocaleString() })
        : selectedTagId
          ? t('home.tagMeta', { count: totalNotes.toLocaleString() })
          : t('home.allMeta')
  const emptyStateTitle = searchQuery ? t('home.emptySearchTitle') : t('home.emptyTitle')
  const emptyStateDescription = searchQuery
    ? t('home.emptySearchDescription', { query: searchQuery })
    : t('home.emptyDescription')

  // Render notes grid/list content
  const notesContent = (
    <div
      className={`
        ${viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-[var(--prism-card-gap)]' : ''}
        ${viewMode === 'list' ? 'flex flex-col gap-3' : ''}
        ${viewMode === 'compact' ? 'flex flex-col gap-1.5' : ''}
      `}
      data-testid="notes-grid"
      data-view-mode={viewMode}
    >
      {isDragEnabled ? (
        localNotes.map((note) => (
          <SortableNoteCard key={note.id} note={note} viewMode={viewMode} />
        ))
      ) : (
        localNotes.map((note) => (
          <NoteCard key={note.id} note={note} viewMode={viewMode} />
        ))
      )}
    </div>
  )

  return (
    <>
      <div className="mb-5 flex items-end justify-between gap-4 px-1">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 className="truncate text-3xl font-semibold leading-tight tracking-tight text-text-primary">
              {sectionTitle}
            </h1>
            <p className="text-sm text-text-muted">
              {sectionSub}
            </p>
          </div>
        </div>
      </div>

      {/* Notes Grid/List with optional DnD */}
      {isDragEnabled ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={localNotes.map((n) => n.id)}
            strategy={viewMode === 'grid' ? rectSortingStrategy : verticalListSortingStrategy}
          >
            {notesContent}
          </SortableContext>
        </DndContext>
      ) : (
        notesContent
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-8">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && localNotes.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 rounded-full bg-bg-elevated flex items-center justify-center mb-4">
            <span className="text-3xl">📝</span>
          </div>
          <h3 className="text-lg font-medium text-text-primary mb-2" data-testid="empty-state-title">
            {emptyStateTitle}
          </h3>
          <p className="text-text-secondary" data-testid="empty-state-description">
            {emptyStateDescription}
          </p>
        </div>
      )}

      {/* Infinite Scroll Trigger / Manual Load Button */}
      {hasMore && localNotes.length > 0 && (
        <div
          ref={setLoadMoreRef}
          onClick={handleLoadMore}
          className={`h-20 flex items-center justify-center transition-colors
                     ${!autoLoadMore ? 'cursor-pointer hover:bg-bg-elevated/50 active:bg-bg-elevated rounded-lg' : ''}`}
        >
          {!isLoading && (
            <span className="text-text-muted text-sm flex items-center gap-2">
              {autoLoadMore ? (
                t('home.autoLoadMore')
              ) : (
                t('home.loadMore')
              )}
            </span>
          )}
        </div>
      )}

      {/* End of List */}
      {!hasMore && localNotes.length > 0 && (
        <div className="py-8 text-center text-text-muted text-sm">
          {t('home.loadedAll')}
        </div>
      )}

      {/* Drag hint when custom sort is enabled */}
      {isDragEnabled && localNotes.length > 1 && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-bg-elevated/90 backdrop-blur-sm 
                        border border-border-default rounded-full px-4 py-2 text-sm text-text-secondary
                        shadow-lg z-10">
          {t('home.dragHint')}
        </div>
      )}

      {/* Editor Modal */}
      {isEditorOpen && (
        <NoteEditor note={editingNote} onClose={closeEditor} initialPreview={editorStartsInPreview} />
      )}

      {isReadingOpen && readingNote && (
        <ReadingView note={readingNote} onClose={closeReading} />
      )}

      {/* Toast Notifications */}
      <ToastContainer />
    </>
  )
}
