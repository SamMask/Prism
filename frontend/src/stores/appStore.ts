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
const NOTES_PAGE_SIZE = 20
let notesRequestSequence = 0
let libraryTotalRequestSequence = 0

function notesParams(state: SearchWorkspaceFilters, page: number) {
  const params: Record<string, any> = { page, per_page: NOTES_PAGE_SIZE, sort: state.sortBy }
  if (state.searchQuery) params.search = state.searchQuery
  if (state.selectedCategoryId) params.category_id = state.selectedCategoryId
  // Include archived if viewing archive
  if (state.showArchived) params.archived = true
  // Tag filtering - use tag ID
  if (state.selectedTagId) params.tags = String(state.selectedTagId)
  return params
}

function readSavedViewMode(): ViewMode {
  const savedMode = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
  return savedMode === 'grid' || savedMode === 'list' || savedMode === 'compact'
    ? savedMode
    : window.matchMedia('(max-width: 639px)').matches ? 'list' : 'grid'
}

interface AppState {
  // Notes
  notes: Note[]
  isLoading: boolean
  totalNotes: number // size of the current list result (search / filter aware)
  libraryTotal: number | null // whole Library, archived excluded; the one total shown by Sidebar/Header/Footer
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
  appVersion: string | null

  // Actions
  fetchNotes: (reset?: boolean) => Promise<void>
  refreshLoadedNotes: () => Promise<void>
  retryFetchNotes: () => Promise<void>
  fetchCategories: () => Promise<void>
  fetchTags: () => Promise<void>
  fetchAppVersion: () => Promise<void>
  fetchLibraryTotal: () => Promise<void>
  setLocale: (locale: Locale) => void
  setViewMode: (mode: ViewMode) => void
  openEditor: (note: Note | null, options?: { preview?: boolean; inPlace?: boolean }) => void
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
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void
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
  libraryTotal: null,
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
  sidebarCollapsed: false,
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),

  categories: [],
  tags: [],
  appVersion: null,

  // Actions
  fetchNotes: async (reset = false) => {
    const requestId = ++notesRequestSequence
    const state = get()
    set({ isLoading: true, notesError: null })

    try {
      const page = reset ? 1 : state.currentPage
      const response = await api.getNotes(notesParams(state, page))

      if (requestId !== notesRequestSequence) return

      set({
        notes: reset ? response.notes : [...get().notes, ...response.notes],
        totalNotes: response.total,
        currentPage: page + 1,
        hasMore: response.notes.length === NOTES_PAGE_SIZE,
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

  // After a mutation: re-fetch the pages already loaded and swap them in at once, so the list keeps
  // its depth and scroll position while the server still decides order (pinned first, sort) and
  // which notes match the current filters (PRISM-OPT-32).
  refreshLoadedNotes: async () => {
    const requestId = ++notesRequestSequence
    const state = get()
    const loadedPages = Math.max(1, state.currentPage - 1)
    set({ isLoading: true, notesError: null })

    try {
      const responses = await Promise.all(
        Array.from({ length: loadedPages }, (_, index) => api.getNotes(notesParams(state, index + 1))),
      )

      if (requestId !== notesRequestSequence) return

      // Pages are separate reads; a note that shifted across a page boundary is kept once.
      const seen = new Set<number>()
      const notes = responses.flatMap((response) => response.notes)
        .filter((note) => !seen.has(note.id) && !!seen.add(note.id))
      const last = responses[responses.length - 1]
      set({
        notes,
        totalNotes: last.total,
        currentPage: loadedPages + 1,
        hasMore: last.notes.length === NOTES_PAGE_SIZE,
        searchDiagnostics: last.searchDiagnostics ?? null,
        isLoading: false,
        notesRetryReset: false,
      })
    } catch (error) {
      if (requestId !== notesRequestSequence) return
      console.error('Failed to refresh notes:', error)
      // Keep the list on screen; Retry falls back to a fresh first page.
      set({ isLoading: false, notesError: 'fetch_failed', notesRetryReset: true })
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

  // The runtime version (Go prismVersion()) is the single source; UI never hardcodes it.
  fetchAppVersion: async () => {
    const requestId = ++libraryTotalRequestSequence
    try {
      const response = await fetch('/api/test')
      const data = await response.json()
      if (typeof data.version === 'string' && data.version) set({ appVersion: data.version })
      if (requestId === libraryTotalRequestSequence && typeof data.stats?.library_count === 'number') set({ libraryTotal: data.stats.library_count })
    } catch (error) {
      console.error('Failed to fetch app version:', error)
    }
  },

  // Library total = notes that are not archived (uncategorized included), independent of search / filters.
  // Only mutations that change it call this (create, variant, archive toggle, delete, import); the
  // newest request wins so an older response can't overwrite a newer total.
  fetchLibraryTotal: async () => {
    const requestId = ++libraryTotalRequestSequence
    try {
      const response = await fetch('/api/test')
      const data = await response.json()
      if (requestId === libraryTotalRequestSequence && typeof data.stats?.library_count === 'number') set({ libraryTotal: data.stats.library_count })
    } catch (error) {
      console.error('Failed to fetch library total:', error)
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

  openEditor: (note, options) => {
    // The open form belongs to the note it was loaded from (it doesn't remount); only its own
    // create -> edit switch may rebind it. Other callers must wait until it closes (PRISM-OPT-59).
    if (get().isEditorOpen && !options?.inPlace) return
    set({
      isEditorOpen: true,
      editingNote: note,
      editorStartsInPreview: !!options?.preview,
      isReadingOpen: false,
      readingNote: null,
    })
  },

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
        libraryTotal: state.libraryTotal === null ? null : Math.max(0, state.libraryTotal - 1),
        isDeleting: false,
      }))
      void get().fetchLibraryTotal()
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
      void get().fetchLibraryTotal()
      return preview
    } catch (error) {
      console.error('Failed to delete notes:', error)
      set({ isDeleting: false })
      throw error
    }
  },
}))
