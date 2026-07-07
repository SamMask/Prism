import { useEffect, useRef, useCallback, useState } from 'react'
import { useAppStore, type SearchWorkspaceFilters, type ViewMode } from '../stores/appStore'
import { NoteCard } from '../components/NoteCard'
import { NoteEditor } from '../components/NoteEditor'
import { ReadingView } from '../components/ReadingView'
import { ToastContainer, toast } from '../components/ui/Toast'
import { Bookmark, Clock, Loader2, Search, Trash2, X } from 'lucide-react'
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
import { getCategoryDisplayName } from '../utils/categoryDisplay'

const RECENT_SEARCHES_STORAGE_KEY = 'prism.recentSearches'
const MAX_RECENT_SEARCHES = 5
const SAVED_SEARCH_WORKSPACES_STORAGE_KEY = 'prism.savedSearchWorkspaces.v1'
const MAX_SAVED_SEARCH_WORKSPACES = 8

type SavedSearchWorkspace = SearchWorkspaceFilters & {
  id: string
  label: string
  createdAt: string
}

function isSortBy(value: unknown): value is SearchWorkspaceFilters['sortBy'] {
  return value === 'updated' || value === 'created' || value === 'custom'
}

function readSavedSearchWorkspaces(): SavedSearchWorkspace[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(SAVED_SEARCH_WORKSPACES_STORAGE_KEY) || '[]')
    if (!Array.isArray(parsed)) return []

    return parsed
      .filter((item): item is SavedSearchWorkspace => (
        item
        && typeof item.id === 'string'
        && typeof item.label === 'string'
        && typeof item.searchQuery === 'string'
        && (typeof item.selectedCategoryId === 'number' || item.selectedCategoryId === null)
        && (typeof item.selectedTagId === 'number' || item.selectedTagId === null)
        && typeof item.showArchived === 'boolean'
        && isSortBy(item.sortBy)
        && typeof item.createdAt === 'string'
      ))
      .slice(0, MAX_SAVED_SEARCH_WORKSPACES)
  } catch {
    return []
  }
}

function writeSavedSearchWorkspaces(workspaces: SavedSearchWorkspace[]): void {
  localStorage.setItem(SAVED_SEARCH_WORKSPACES_STORAGE_KEY, JSON.stringify(workspaces))
}

function sameSearchWorkspace(a: SearchWorkspaceFilters, b: SearchWorkspaceFilters): boolean {
  return a.searchQuery.trim().toLowerCase() === b.searchQuery.trim().toLowerCase()
    && a.selectedCategoryId === b.selectedCategoryId
    && a.selectedTagId === b.selectedTagId
    && a.sortBy === b.sortBy
    && a.showArchived === b.showArchived
}

function readRecentSearches(): string[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECENT_SEARCHES_STORAGE_KEY) || '[]')
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === 'string' && item.trim() !== '').slice(0, MAX_RECENT_SEARCHES)
      : []
  } catch {
    return []
  }
}

function writeRecentSearches(query: string): string[] {
  const trimmed = query.trim()
  if (!trimmed) return readRecentSearches()
  const nextSearches = [trimmed, ...readRecentSearches().filter((item) => item.toLowerCase() !== trimmed.toLowerCase())].slice(0, MAX_RECENT_SEARCHES)
  localStorage.setItem(RECENT_SEARCHES_STORAGE_KEY, JSON.stringify(nextSearches))
  return nextSearches
}

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
    setSearchQuery,
    setSelectedCategory,
    setSelectedTag,
    setShowArchived,
    showArchived,
    applySearchWorkspace,
    totalNotes,
    categories,
    tags,
  } = useAppStore()

  const [localNotes, setLocalNotes] = useState<Note[]>([])
  const [mobileSearchValue, setMobileSearchValue] = useState(searchQuery)
  const [recentSearches, setRecentSearches] = useState<string[]>(() => readRecentSearches())
  const [savedSearchWorkspaces, setSavedSearchWorkspaces] = useState<SavedSearchWorkspace[]>(() => readSavedSearchWorkspaces())
  const observerRef = useRef<IntersectionObserver | null>(null)
  
  // Settings State
  const [autoLoadMore] = useState(() => localStorage.getItem('autoLoadMore') !== 'false')

  // Sync local notes with store
  useEffect(() => {
    setLocalNotes(notes)
  }, [notes])

  useEffect(() => {
    fetchNotes(true)
  }, [fetchNotes])

  useEffect(() => {
    setMobileSearchValue(searchQuery)
    if (searchQuery.trim()) {
      setRecentSearches(writeRecentSearches(searchQuery))
    }
  }, [searchQuery])

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
  const activeCategoryName = getCategoryDisplayName(activeCategory, t)
  const activeTag = tags.find((tag) => tag.id === selectedTagId)
  const hasActiveFilter = !!selectedCategoryId || !!selectedTagId || showArchived
  const currentSearchWorkspaceFilters: SearchWorkspaceFilters = {
    searchQuery: searchQuery.trim(),
    selectedCategoryId,
    selectedTagId,
    sortBy,
    showArchived,
  }
  const currentSearchWorkspaceLabel = [
    searchQuery.trim() || activeCategoryName || (activeTag ? `#${activeTag.name}` : showArchived ? t('home.archive') : t('home.all')),
    sortBy !== 'updated' ? t(`home.savedSearch.sort.${sortBy}`) : '',
  ].filter(Boolean).join(' · ')
  const hasSavedCurrentSearchWorkspace = savedSearchWorkspaces.some((workspace) => (
    sameSearchWorkspace(workspace, currentSearchWorkspaceFilters)
  ))
  const sectionTitle = searchQuery
    ? t('home.searchResults')
    : showArchived
      ? t('home.archive')
      : activeCategoryName || (activeTag ? `#${activeTag.name}` : t('home.all'))
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

  const clearSearch = () => setSearchQuery('')
  const clearSearchAndFilters = () => {
    setSearchQuery('')
    if (selectedCategoryId) setSelectedCategory(null)
    if (selectedTagId) setSelectedTag(null)
    if (showArchived) setShowArchived(false)
  }
  const submitMobileSearch = (event: React.FormEvent) => {
    event.preventDefault()
    setSearchQuery(mobileSearchValue.trim())
  }
  const runRecentSearch = (query: string) => {
    setMobileSearchValue(query)
    setSearchQuery(query)
  }
  function saveCurrentSearchWorkspace() {
    const workspace: SavedSearchWorkspace = {
      ...currentSearchWorkspaceFilters,
      id: `${Date.now()}`,
      label: currentSearchWorkspaceLabel,
      createdAt: new Date().toISOString(),
    }
    const nextWorkspaces = [
      workspace,
      ...savedSearchWorkspaces.filter((item) => !sameSearchWorkspace(item, workspace)),
    ].slice(0, MAX_SAVED_SEARCH_WORKSPACES)
    writeSavedSearchWorkspaces(nextWorkspaces)
    setSavedSearchWorkspaces(nextWorkspaces)
    toast.success(t('home.savedSearch.saved', { label: workspace.label }))
  }
  const applySavedSearchWorkspace = (workspace: SavedSearchWorkspace) => {
    applySearchWorkspace({
      searchQuery: workspace.searchQuery,
      selectedCategoryId: workspace.selectedCategoryId,
      selectedTagId: workspace.selectedTagId,
      sortBy: workspace.sortBy,
      showArchived: workspace.showArchived,
    })
    toast.success(t('home.savedSearch.restored', { label: workspace.label }))
  }
  const deleteSavedSearchWorkspace = (id: string) => {
    const nextWorkspaces = savedSearchWorkspaces.filter((workspace) => workspace.id !== id)
    writeSavedSearchWorkspaces(nextWorkspaces)
    setSavedSearchWorkspaces(nextWorkspaces)
    toast.success(t('home.savedSearch.removed'))
  }

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
      <form
        onSubmit={submitMobileSearch}
        className="mb-4 md:hidden"
        data-testid="mobile-search-form"
      >
        <label className="sr-only" htmlFor="mobile-search-input">{t('common.search')}</label>
        <div className="relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            id="mobile-search-input"
            type="text"
            value={mobileSearchValue}
            onChange={(event) => setMobileSearchValue(event.target.value)}
            placeholder={t('header.searchPlaceholder')}
            className="h-10 w-full rounded-md border border-border-default bg-bg-elevated pl-10 pr-10 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/50"
            data-testid="mobile-search-input"
          />
          {mobileSearchValue && (
            <button
              type="button"
              onClick={() => {
                setMobileSearchValue('')
                if (searchQuery) clearSearch()
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
              aria-label={t('home.clearSearch')}
            >
              <X size={16} />
            </button>
          )}
        </div>
      </form>

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

      <div
        className="mb-4 rounded-md border border-border-subtle bg-bg-elevated/55 px-3 py-3"
        data-testid="saved-search-workspace-bar"
      >
        <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
          <Bookmark size={14} className="text-primary" />
          <span className="font-medium text-text-primary">{t('home.savedSearch.title')}</span>
          <button
            type="button"
            onClick={saveCurrentSearchWorkspace}
            disabled={hasSavedCurrentSearchWorkspace}
            className="ml-auto rounded-md border border-border-default bg-bg-base px-2.5 py-1.5 text-xs text-text-primary hover:bg-bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="save-search-workspace"
          >
            {hasSavedCurrentSearchWorkspace ? t('home.savedSearch.alreadySaved') : t('home.savedSearch.save')}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {savedSearchWorkspaces.length === 0 ? (
            <span className="text-xs text-text-muted">{t('home.savedSearch.empty')}</span>
          ) : (
            savedSearchWorkspaces.map((workspace) => (
              <span key={workspace.id} className="inline-flex h-8 items-center gap-1 rounded-md border border-border-subtle bg-bg-base text-xs text-text-secondary">
                <button
                  type="button"
                  onClick={() => applySavedSearchWorkspace(workspace)}
                  className="h-full px-2.5 hover:text-text-primary"
                  data-testid={`saved-search-workspace-${workspace.id}`}
                  title={t('home.savedSearch.restore', { label: workspace.label })}
                >
                  {workspace.label}
                </button>
                <button
                  type="button"
                  onClick={() => deleteSavedSearchWorkspace(workspace.id)}
                  className="h-full rounded-r-md px-2 text-text-muted hover:bg-danger/10 hover:text-danger"
                  data-testid={`delete-saved-search-workspace-${workspace.id}`}
                  aria-label={t('home.savedSearch.delete', { label: workspace.label })}
                  title={t('home.savedSearch.delete', { label: workspace.label })}
                >
                  <Trash2 size={13} />
                </button>
              </span>
            ))
          )}
        </div>
      </div>

      {searchQuery && (
        <div className="mb-4 rounded-md border border-border-subtle bg-bg-elevated/70 px-3 py-3" data-testid="search-context-bar">
          <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
            <Search size={14} className="text-primary" />
            <span className="font-medium text-text-primary">{t('home.searchScopeTitle')}</span>
            <span>{t('home.searchScopeHint')}</span>
            {hasActiveFilter && <span className="text-warning">{t('home.searchFilteredHint')}</span>}
            <button type="button" onClick={clearSearch} className="ml-auto text-primary hover:text-primary-light">
              {t('home.clearSearch')}
            </button>
          </div>
          {recentSearches.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 text-xs text-text-muted">
                <Clock size={13} />
                {t('home.recentSearches')}
              </span>
              {recentSearches.map((query) => (
                <button
                  key={query}
                  type="button"
                  onClick={() => runRecentSearch(query)}
                  className="h-7 rounded-md border border-border-subtle bg-bg-base px-2 text-xs text-text-secondary hover:border-border-default hover:bg-bg-hover hover:text-text-primary"
                >
                  {query}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

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
          {searchQuery && (
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <button
                type="button"
                onClick={clearSearch}
                className="rounded-md border border-border-default bg-bg-elevated px-3 py-2 text-sm text-text-primary hover:bg-bg-hover"
              >
                {t('home.clearSearch')}
              </button>
              {hasActiveFilter && (
                <button
                  type="button"
                  onClick={clearSearchAndFilters}
                  className="rounded-md border border-primary/40 bg-primary/15 px-3 py-2 text-sm text-primary-light hover:bg-primary/20"
                >
                  {t('home.clearSearchAndFilters')}
                </button>
              )}
            </div>
          )}
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
