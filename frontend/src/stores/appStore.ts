import { create } from 'zustand'
import { api, Note, Category, Tag, type BatchDeletePreview, type SearchDiagnostics } from '../services/api'
import { type Locale, readStoredLocale, setLocale as persistLocale } from '../i18n'

export type ViewMode = 'grid' | 'list' | 'compact'
export type SearchWorkspaceFilters = {
  searchQuery: string
  selectedCategoryId: number | null
  selectedTagId: number | null
  sortBy: 'updated' | 'created' | 'custom'
  showArchived: boolean
}

const VIEW_MODE_STORAGE_KEY = 'prism.viewMode'
let notesRequestSequence = 0

function readSavedViewMode(): ViewMode {
  const savedMode = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
  return savedMode === 'grid' || savedMode === 'list' || savedMode === 'compact'
    ? savedMode
    : 'grid'
}

interface AppState {
  // Notes
  notes: Note[]
  isLoading: boolean
  totalNotes: number
  currentPage: number
  hasMore: boolean
  searchDiagnostics: SearchDiagnostics | null
  notesError: string | null
  notesRetryReset: boolean

  // UI State
  locale: Locale
  viewMode: ViewMode
  selectedNoteIds: number[]
  isEditorOpen: boolean
  editingNote: Note | null
  editorStartsInPreview: boolean
  isReadingOpen: boolean
  readingNote: Note | null
  isDeleting: boolean
  isCommandPaletteOpen: boolean

  // Filters
  searchQuery: string
  selectedCategoryId: number | null
  selectedTagId: number | null
  sortBy: 'updated' | 'created' | 'custom'
  showArchived: boolean

  // Data
  categories: Category[]
  tags: Tag[]

  // Actions
  fetchNotes: (reset?: boolean) => Promise<void>
  retryFetchNotes: () => Promise<void>
  fetchCategories: () => Promise<void>
  fetchTags: () => Promise<void>
  setLocale: (locale: Locale) => void
  setViewMode: (mode: ViewMode) => void
  openEditor: (note: Note | null, options?: { preview?: boolean }) => void
  closeEditor: () => void
  openReading: (note: Note) => void
  closeReading: () => void
  openCommandPalette: () => void
  closeCommandPalette: () => void
  toggleCommandPalette: () => void
  setSearchQuery: (query: string) => void
  setSelectedCategory: (id: number | null) => void
  setSelectedTag: (id: number | null) => void
  setSortBy: (sort: 'updated' | 'created' | 'custom') => void
  setShowArchived: (showArchived: boolean) => void
  applySearchWorkspace: (filters: SearchWorkspaceFilters) => void
  toggleNoteSelection: (id: number) => void
  selectAllNotes: () => void
  clearSelection: () => void
  deleteNote: (id: number) => Promise<void>
  deleteSelectedNotes: (preview: BatchDeletePreview) => Promise<BatchDeletePreview>
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial State
  notes: [],
  isLoading: false,
  totalNotes: 0,
  currentPage: 1,
  hasMore: true,
  searchDiagnostics: null,
  notesError: null,
  notesRetryReset: true,

  locale: readStoredLocale(),
  viewMode: readSavedViewMode(),
  selectedNoteIds: [],
  isEditorOpen: false,
  editingNote: null,
  editorStartsInPreview: false,
  isReadingOpen: false,
  readingNote: null,
  isDeleting: false,
  isCommandPaletteOpen: false,

  searchQuery: '',
  selectedCategoryId: null,
  selectedTagId: null,
  sortBy: 'updated',
  showArchived: false,

  categories: [],
  tags: [],

  // Actions
  fetchNotes: async (reset = false) => {
    const requestId = ++notesRequestSequence
    const state = get()
    set({ isLoading: true, notesError: null })

    try {
      const page = reset ? 1 : state.currentPage
      
      // Build params
      const params: Record<string, any> = {
        page,
        per_page: 20,
        sort: state.sortBy,
      }
      
      if (state.searchQuery) {
        params.search = state.searchQuery
      }
      
      if (state.selectedCategoryId) {
        params.category_id = state.selectedCategoryId
      }
      
      // Include archived if viewing archive
      if (state.showArchived) {
        params.archived = true
      }
      
      // Tag filtering - use tag ID
      if (state.selectedTagId) {
        params.tags = String(state.selectedTagId)
      }
      
      const response = await api.getNotes(params)

      if (requestId !== notesRequestSequence) return

      set({
        notes: reset ? response.notes : [...get().notes, ...response.notes],
        totalNotes: response.total,
        currentPage: page + 1,
        hasMore: response.notes.length === 20,
        searchDiagnostics: response.searchDiagnostics ?? null,
        isLoading: false,
        notesRetryReset: false,
      })
    } catch (error) {
      if (requestId !== notesRequestSequence) return
      console.error('Failed to fetch notes:', error)
      set({
        isLoading: false,
        notesError: 'fetch_failed',
        notesRetryReset: reset,
        ...(reset ? {
          notes: [],
          totalNotes: 0,
          hasMore: false,
          searchDiagnostics: null,
        } : {}),
      })
    }
  },

  retryFetchNotes: () => get().fetchNotes(get().notesRetryReset),

  fetchCategories: async () => {
    try {
      const categories = await api.getCategories()
      set({ categories })
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    }
  },

  fetchTags: async () => {
    try {
      const tags = await api.getTags()
      set({ tags })
    } catch (error) {
      console.error('Failed to fetch tags:', error)
    }
  },

  setLocale: (locale) => {
    persistLocale(locale)
    set({ locale })
  },

  setViewMode: (mode) => {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode)
    set({ viewMode: mode })
  },

  openEditor: (note, options) => set({
    isEditorOpen: true,
    editingNote: note,
    editorStartsInPreview: !!options?.preview,
    isReadingOpen: false,
    readingNote: null,
  }),

  closeEditor: () => set({ isEditorOpen: false, editingNote: null, editorStartsInPreview: false }),

  openReading: (note) => set({ isReadingOpen: true, readingNote: note }),

  closeReading: () => set({ isReadingOpen: false, readingNote: null }),

  openCommandPalette: () => set({ isCommandPaletteOpen: true }),

  closeCommandPalette: () => set({ isCommandPaletteOpen: false }),

  toggleCommandPalette: () => set((state) => ({ isCommandPaletteOpen: !state.isCommandPaletteOpen })),

  setSearchQuery: (query) => {
    set({ searchQuery: query, currentPage: 1, selectedNoteIds: [] })
    get().fetchNotes(true)
  },

  setSelectedCategory: (id) => {
    set({ selectedCategoryId: id, selectedTagId: null, showArchived: false, currentPage: 1, selectedNoteIds: [] })
    get().fetchNotes(true)
  },

  setSelectedTag: (id) => {
    set({ selectedTagId: id, selectedCategoryId: null, showArchived: false, currentPage: 1, selectedNoteIds: [] })
    get().fetchNotes(true)
  },

  setSortBy: (sort) => {
    set({ sortBy: sort, currentPage: 1, selectedNoteIds: [] })
    get().fetchNotes(true)
  },

  setShowArchived: (showArchived) => {
    set({ showArchived, selectedCategoryId: null, selectedTagId: null, currentPage: 1, selectedNoteIds: [] })
    get().fetchNotes(true)
  },

  applySearchWorkspace: (filters) => {
    set({
      searchQuery: filters.searchQuery,
      selectedCategoryId: filters.selectedCategoryId,
      selectedTagId: filters.selectedTagId,
      sortBy: filters.sortBy,
      showArchived: filters.showArchived,
      currentPage: 1,
      selectedNoteIds: [],
    })
    get().fetchNotes(true)
  },

  toggleNoteSelection: (id) => {
    const selected = get().selectedNoteIds
    if (selected.includes(id)) {
      set({ selectedNoteIds: selected.filter((i) => i !== id) })
    } else {
      set({ selectedNoteIds: [...selected, id] })
    }
  },

  selectAllNotes: () => {
    const allIds = get().notes.map(n => n.id)
    set({ selectedNoteIds: allIds })
  },

  clearSelection: () => set({ selectedNoteIds: [] }),

  deleteNote: async (id) => {
    set({ isDeleting: true })
    try {
      await api.deleteNote(id)
      set(state => ({
        notes: state.notes.filter(n => n.id !== id),
        totalNotes: state.totalNotes - 1,
        isDeleting: false,
      }))
    } catch (error) {
      console.error('Failed to delete note:', error)
      set({ isDeleting: false })
      throw error
    }
  },

  deleteSelectedNotes: async (preview) => {
    const { selectedNoteIds } = get()
    if (selectedNoteIds.length === 0) {
      return preview
    }

    set({ isDeleting: true })
    try {
      await api.batchDeleteNotes(selectedNoteIds)
      
      set(state => ({
        notes: state.notes.filter(n => !selectedNoteIds.includes(n.id)),
        totalNotes: Math.max(0, state.totalNotes - preview.deletable_count),
        selectedNoteIds: [],
        isDeleting: false,
      }))
      return preview
    } catch (error) {
      console.error('Failed to delete notes:', error)
      set({ isDeleting: false })
      throw error
    }
  },
}))
