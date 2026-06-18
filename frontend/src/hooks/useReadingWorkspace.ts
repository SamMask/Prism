import { useCallback, useEffect, useState } from 'react'

export const READING_WORKSPACE_STORAGE_KEY = 'prism.readingWorkspace.v1'
export const READING_WORKSPACE_CHANGED_EVENT = 'prism:reading-workspace-changed'

export type ReadingWorkspaceLayout = 'tabs' | 'sidebar'

export interface ReadingWorkspaceState {
  noteIds: number[]
  activeId: number | null
  layout: ReadingWorkspaceLayout
  scrollPositions: Record<string, number>
}

const DEFAULT_READING_WORKSPACE: ReadingWorkspaceState = {
  noteIds: [],
  activeId: null,
  layout: 'tabs',
  scrollPositions: {},
}

function uniqueNoteIds(value: unknown): number[] {
  if (!Array.isArray(value)) return []
  const seen = new Set<number>()
  const ids: number[] = []

  value.forEach((item) => {
    const id = Number(item)
    if (!Number.isInteger(id) || id <= 0 || seen.has(id)) return
    seen.add(id)
    ids.push(id)
  })

  return ids
}

function normalizeLayout(value: unknown): ReadingWorkspaceLayout {
  return value === 'sidebar' ? 'sidebar' : 'tabs'
}

function normalizeScrollPositions(value: unknown, noteIds: number[]): Record<string, number> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}
  const allowedIds = new Set(noteIds.map(String))
  const positions: Record<string, number> = {}

  Object.entries(value as Record<string, unknown>).forEach(([key, rawPosition]) => {
    const position = Number(rawPosition)
    if (!allowedIds.has(key) || !Number.isFinite(position) || position < 0) return
    positions[key] = Math.round(position)
  })

  return positions
}

function normalizeWorkspace(value: unknown): ReadingWorkspaceState {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return DEFAULT_READING_WORKSPACE
  }

  const source = value as Partial<ReadingWorkspaceState>
  const noteIds = uniqueNoteIds(source.noteIds)
  const requestedActiveId = Number(source.activeId)
  const activeId = noteIds.includes(requestedActiveId) ? requestedActiveId : (noteIds[0] ?? null)

  return {
    noteIds,
    activeId,
    layout: normalizeLayout(source.layout),
    scrollPositions: normalizeScrollPositions(source.scrollPositions, noteIds),
  }
}

export function readReadingWorkspace(): ReadingWorkspaceState {
  if (typeof window === 'undefined') return DEFAULT_READING_WORKSPACE

  try {
    return normalizeWorkspace(JSON.parse(window.localStorage.getItem(READING_WORKSPACE_STORAGE_KEY) || '{}'))
  } catch {
    return DEFAULT_READING_WORKSPACE
  }
}

function writeReadingWorkspace(nextState: ReadingWorkspaceState): ReadingWorkspaceState {
  const normalized = normalizeWorkspace(nextState)
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(READING_WORKSPACE_STORAGE_KEY, JSON.stringify(normalized))
    window.dispatchEvent(new CustomEvent(READING_WORKSPACE_CHANGED_EVENT))
  }
  return normalized
}

export function addNoteToReadingWorkspace(noteId: number, options?: { activate?: boolean }): ReadingWorkspaceState {
  const current = readReadingWorkspace()
  const noteIds = current.noteIds.includes(noteId) ? current.noteIds : [...current.noteIds, noteId]
  const activeId = options?.activate || !current.activeId ? noteId : current.activeId
  return writeReadingWorkspace({ ...current, noteIds, activeId })
}

export function isNoteInReadingWorkspace(noteId: number): boolean {
  return readReadingWorkspace().noteIds.includes(noteId)
}

export function useReadingWorkspace() {
  const [workspace, setWorkspace] = useState(readReadingWorkspace)

  const updateWorkspace = useCallback((updater: (current: ReadingWorkspaceState) => ReadingWorkspaceState) => {
    setWorkspace((current) => writeReadingWorkspace(updater(current)))
  }, [])

  useEffect(() => {
    const sync = () => setWorkspace(readReadingWorkspace())
    window.addEventListener(READING_WORKSPACE_CHANGED_EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(READING_WORKSPACE_CHANGED_EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const addNote = useCallback((noteId: number, options?: { activate?: boolean }) => {
    setWorkspace(addNoteToReadingWorkspace(noteId, options))
  }, [])

  const removeNote = useCallback((noteId: number) => {
    updateWorkspace((current) => {
      const noteIds = current.noteIds.filter((id) => id !== noteId)
      const scrollPositions = { ...current.scrollPositions }
      delete scrollPositions[String(noteId)]
      const activeId = current.activeId === noteId ? (noteIds[0] ?? null) : current.activeId
      return { ...current, noteIds, activeId, scrollPositions }
    })
  }, [updateWorkspace])

  const clearWorkspace = useCallback(() => {
    updateWorkspace((current) => ({
      ...current,
      noteIds: [],
      activeId: null,
      scrollPositions: {},
    }))
  }, [updateWorkspace])

  const setActiveNote = useCallback((noteId: number) => {
    updateWorkspace((current) => (
      current.noteIds.includes(noteId)
        ? { ...current, activeId: noteId }
        : current
    ))
  }, [updateWorkspace])

  const setLayout = useCallback((layout: ReadingWorkspaceLayout) => {
    updateWorkspace((current) => ({ ...current, layout }))
  }, [updateWorkspace])

  const saveScrollPosition = useCallback((noteId: number, scrollTop: number) => {
    updateWorkspace((current) => (
      current.noteIds.includes(noteId)
        ? {
          ...current,
          scrollPositions: {
            ...current.scrollPositions,
            [String(noteId)]: Math.max(0, Math.round(scrollTop)),
          },
        }
        : current
    ))
  }, [updateWorkspace])

  const getScrollPosition = useCallback((noteId: number) => (
    workspace.scrollPositions[String(noteId)] ?? 0
  ), [workspace.scrollPositions])

  return {
    workspace,
    addNote,
    removeNote,
    clearWorkspace,
    setActiveNote,
    setLayout,
    saveScrollPosition,
    getScrollPosition,
  }
}
