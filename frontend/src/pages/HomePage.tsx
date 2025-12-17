import { useEffect, useRef, useCallback } from 'react'
import { useAppStore } from '../stores/appStore'
import { NoteCard } from '../components/NoteCard'
import { NoteEditor } from '../components/NoteEditor'
import { ToastContainer } from '../components/ui/Toast'
import { Loader2 } from 'lucide-react'

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
  } = useAppStore()

  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    fetchNotes(true)
  }, [fetchNotes])

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

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [handleLoadMore])

  return (
    <>
      {/* Notes Grid/List */}
      <div
        className={`
          ${viewMode === 'grid'
            ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'
            : 'flex flex-col gap-3'
          }
        `}
        data-testid="notes-grid"
      >
        {notes.map((note) => (
          <NoteCard key={note.id} note={note} viewMode={viewMode} />
        ))}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-8">
          <Loader2 size={24} className="animate-spin text-primary" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && notes.length === 0 && (
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

      {/* Infinite Scroll Trigger */}
      {hasMore && notes.length > 0 && (
        <div ref={loadMoreRef} className="h-20 flex items-center justify-center">
          {!isLoading && (
            <span className="text-text-muted text-sm">滾動載入更多...</span>
          )}
        </div>
      )}

      {/* End of List */}
      {!hasMore && notes.length > 0 && (
        <div className="py-8 text-center text-text-muted text-sm">
          已載入所有筆記
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
