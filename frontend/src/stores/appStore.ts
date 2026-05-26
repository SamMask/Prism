import { create } from 'zustand'
import { api, Note, Category, Tag } from '../services/api'

interface AppState {
  // Notes
  notes: Note[]
  isLoading: boolean
  totalNotes: number
  currentPage: number
  hasMore: boolean

  // UI State
  viewMode: 'grid' | 'list'
  selectedNoteIds: number[]
  isEditorOpen: boolean
  editingNote: Note | null
  isDeleting: boolean

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
  fetchCategories: () => Promise<void>
  fetchTags: () => Promise<void>
  setViewMode: (mode: 'grid' | 'list') => void
  openEditor: (note: Note | null) => void
  closeEditor: () => void
  setSearchQuery: (query: string) => void
  setSelectedCategory: (id: number | null) => void
  setSelectedTag: (id: number | null) => void
  setSortBy: (sort: 'updated' | 'created' | 'custom') => void
  setShowArchived: (showArchived: boolean) => void
  toggleNoteSelection: (id: number) => void
  selectAllNotes: () => void
  clearSelection: () => void
  deleteNote: (id: number) => Promise<void>
  deleteSelectedNotes: () => Promise<void>
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial State
  notes: [],
  isLoading: false,
  totalNotes: 0,
  currentPage: 1,
  hasMore: true,

  viewMode: 'grid',
  selectedNoteIds: [],
  isEditorOpen: false,
  editingNote: null,
  isDeleting: false,

  searchQuery: '',
  selectedCategoryId: null,
  selectedTagId: null,
  sortBy: 'updated',
  showArchived: false,

  categories: [],
  tags: [],

  // Actions
  fetchNotes: async (reset = false) => {
    const state = get()
    if (state.isLoading) return

    set({ isLoading: true })

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

      set({
        notes: reset ? response.notes : [...state.notes, ...response.notes],
        totalNotes: response.total,
        currentPage: page + 1,
        hasMore: response.notes.length === 20,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to fetch notes:', error)
      set({ isLoading: false })
    }
  },

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

  setViewMode: (mode) => set({ viewMode: mode }),

  openEditor: (note) => set({ isEditorOpen: true, editingNote: note }),

  closeEditor: () => set({ isEditorOpen: false, editingNote: null }),

  setSearchQuery: (query) => {
    set({ searchQuery: query, currentPage: 1 })
    get().fetchNotes(true)
  },

  setSelectedCategory: (id) => {
    set({ selectedCategoryId: id, selectedTagId: null, currentPage: 1 })
    get().fetchNotes(true)
  },

  setSelectedTag: (id) => {
    set({ selectedTagId: id, selectedCategoryId: null, currentPage: 1 })
    get().fetchNotes(true)
  },

  setSortBy: (sort) => {
    set({ sortBy: sort, currentPage: 1 })
    get().fetchNotes(true)
  },

  setShowArchived: (showArchived) => {
    set({ showArchived, selectedCategoryId: null, selectedTagId: null, currentPage: 1 })
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

  deleteSelectedNotes: async () => {
    const { selectedNoteIds } = get()
    if (selectedNoteIds.length === 0) return

    set({ isDeleting: true })
    try {
      for (const id of selectedNoteIds) {
        await api.deleteNote(id)
      }
      
      set(state => ({
        notes: state.notes.filter(n => !selectedNoteIds.includes(n.id)),
        totalNotes: state.totalNotes - selectedNoteIds.length,
        selectedNoteIds: [],
        isDeleting: false,
      }))
    } catch (error) {
      console.error('Failed to delete notes:', error)
      set({ isDeleting: false })
      throw error
    }
  },
}))
