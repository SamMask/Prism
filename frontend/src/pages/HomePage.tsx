import { useEffect, useRef, useCallback, useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { NoteCard } from '../components/NoteCard'
import { NoteEditor } from '../components/NoteEditor'
import { ToastContainer, toast } from '../components/ui/Toast'
import { Loader2 } from 'lucide-react'
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
function SortableNoteCard({ note, viewMode }: { note: Note; viewMode: 'grid' | 'list' }) {
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
  const {
    notes,
    isLoading,
    hasMore,
    viewMode,
    isEditorOpen,
    editingNote,
    fetchNotes,
    closeEditor,
    sortBy,
  } = useAppStore()

  const [localNotes, setLocalNotes] = useState<Note[]>([])
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  
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
        toast.success('排序已更新')
      } catch {
        // Revert on error
        setLocalNotes(notes)
        toast.error('排序更新失敗')
      }
    }
  }

  // Infinite scroll using Intersection Observer
  const handleLoadMore = useCallback(() => {
    if (!isLoading && hasMore) {
      fetchNotes()
    }
  }, [isLoading, hasMore, fetchNotes])

  useEffect(() => {
    if (observerRef.current) {
      observerRef.current.disconnect()
    }

    // Only set up observer if auto load more is enabled
    if (autoLoadMore) {
      observerRef.current = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            handleLoadMore()
          }
        },
        { threshold: 0.1 }
      )

      if (loadMoreRef.current) {
        observerRef.current.observe(loadMoreRef.current)
      }
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [handleLoadMore, autoLoadMore])

  // Only enable drag when sortBy is 'custom'
  const isDragEnabled = sortBy === 'custom'

  // Render notes grid/list content
  const notesContent = (
    <div
      className={`
        ${viewMode === 'grid'
          ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'
          : 'flex flex-col gap-3'
        }
      `}
      data-testid="notes-grid"
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
          <h3 className="text-lg font-medium text-text-primary mb-2">
            還沒有任何筆記
          </h3>
          <p className="text-text-secondary">
            點擊上方「新增筆記」按鈕開始創作
          </p>
        </div>
      )}

      {/* Infinite Scroll Trigger / Manual Load Button */}
      {hasMore && localNotes.length > 0 && (
        <div 
          ref={loadMoreRef} 
          onClick={handleLoadMore}
          className={`h-20 flex items-center justify-center transition-colors
                     ${!autoLoadMore ? 'cursor-pointer hover:bg-bg-elevated/50 active:bg-bg-elevated rounded-lg' : ''}`}
        >
          {!isLoading && (
            <span className="text-text-muted text-sm flex items-center gap-2">
              {autoLoadMore ? (
                '滾動載入更多...'
              ) : (
                '點擊載入更多'
              )}
            </span>
          )}
        </div>
      )}

      {/* End of List */}
      {!hasMore && localNotes.length > 0 && (
        <div className="py-8 text-center text-text-muted text-sm">
          已載入所有筆記
        </div>
      )}

      {/* Drag hint when custom sort is enabled */}
      {isDragEnabled && localNotes.length > 1 && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-bg-elevated/90 backdrop-blur-sm 
                        border border-border-default rounded-full px-4 py-2 text-sm text-text-secondary
                        shadow-lg z-10">
          💡 拖曳卡片可調整順序
        </div>
      )}

      {/* Editor Modal */}
      {isEditorOpen && (
        <NoteEditor note={editingNote} onClose={closeEditor} />
      )}

      {/* Toast Notifications */}
      <ToastContainer />
    </>
  )
}
