import {
  Archive,
  FileText,
  Home,
  Moon,
  Plus,
  Search,
  Settings,
  Sparkles,
  Sun,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Note, api } from '../services/api'
import { useAppStore } from '../stores/appStore'
import { toast } from './ui/Toast'
import { useTranslation } from '../hooks/useTranslation'

const SERVER_SEARCH_MIN_CHARS = 3
const SERVER_SEARCH_LIMIT = 8
const SERVER_SEARCH_DEBOUNCE_MS = 250

type CommandGroup = 'navigation' | 'results' | 'recent' | 'actions'

interface CommandItem {
  id: string
  group: CommandGroup
  title: string
  subtitle: string
  keywords: string
  icon: typeof Search
  action: () => void | Promise<void>
}

function formatNoteDate(value: string, locale: string, fallback: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return date.toLocaleDateString(locale)
}

function getNotePreview(note: Note, fallback: string) {
  const content = (note.content_preview ?? note.content)
    ?.replace(/!\[.*?\]\(.*?\)/g, '')
    .replace(/\[.*?\]\(.*?\)/g, '')
    .replace(/#{1,6}\s/g, '')
    .trim()

  return content ? content.slice(0, 72) : fallback
}

function getServerSearchTerm(query: string): string {
  const trimmed = query.trim()
  if (trimmed.startsWith('?')) return trimmed.slice(1).trim()
  return trimmed.length >= SERVER_SEARCH_MIN_CHARS ? trimmed : ''
}

export function CommandPalette() {
  const navigate = useNavigate()
  const { locale, t } = useTranslation()
  const inputRef = useRef<HTMLInputElement>(null)
  const {
    notes,
    openEditor,
    setSelectedCategory,
    setSelectedTag,
    setShowArchived,
    showArchived,
    isCommandPaletteOpen: isOpen,
    closeCommandPalette,
    toggleCommandPalette,
  } = useAppStore()

  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const [serverSearchNotes, setServerSearchNotes] = useState<Note[]>([])
  const [serverSearchTotal, setServerSearchTotal] = useState(0)
  const [isServerSearchLoading, setIsServerSearchLoading] = useState(false)
  const [serverSearchFailed, setServerSearchFailed] = useState(false)
  const serverSearchTerm = useMemo(() => getServerSearchTerm(query), [query])

  const closePalette = () => {
    closeCommandPalette()
    setQuery('')
    setActiveIndex(0)
  }

  const goHome = () => {
    setSelectedCategory(null)
    setSelectedTag(null)
    if (showArchived) setShowArchived(false)
    navigate('/')
  }

  const openNewNote = () => {
    navigate('/')
    openEditor(null)
  }

  const toggleTheme = () => {
    const currentTheme = (localStorage.getItem('theme') as 'dark' | 'light') || 'light'
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark'
    localStorage.setItem('theme', nextTheme)
    document.documentElement.classList.toggle('light', nextTheme === 'light')
    toast.success(t('commandPalette.themeChanged', {
      theme: t(nextTheme === 'dark' ? 'commandPalette.themeDark' : 'commandPalette.themeLight'),
    }))
  }

  const openNoteFromPalette = useCallback(async (note: Note) => {
    navigate('/')
    try {
      const noteForEditor = note.content_truncated ? await api.getNote(note.id) : note
      openEditor(noteForEditor)
    } catch {
      toast.error(t('reading.loadFailed'))
    }
  }, [navigate, openEditor, t])

  const recentNotes = useMemo(() => {
    return [...notes]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 6)
  }, [notes])

  const commands = useMemo<CommandItem[]>(() => {
    const navigation: CommandItem[] = [
      {
        id: 'nav-home',
        group: 'navigation',
        title: t('commandPalette.commands.allNotes.title'),
        subtitle: t('commandPalette.commands.allNotes.subtitle'),
        keywords: t('commandPalette.commands.allNotes.keywords'),
        icon: Home,
        action: goHome,
      },
      {
        id: 'nav-prompt-builder',
        group: 'navigation',
        title: 'Prompt Builder',
        subtitle: t('commandPalette.commands.promptBuilder.subtitle'),
        keywords: t('commandPalette.commands.promptBuilder.keywords'),
        icon: Sparkles,
        action: () => navigate('/prompt-builder'),
      },
      {
        id: 'nav-settings',
        group: 'navigation',
        title: t('commandPalette.commands.settings.title'),
        subtitle: t('commandPalette.commands.settings.subtitle'),
        keywords: t('commandPalette.commands.settings.keywords'),
        icon: Settings,
        action: () => navigate('/settings'),
      },
      {
        id: 'nav-archive',
        group: 'navigation',
        title: t('commandPalette.commands.archive.title'),
        subtitle: t('commandPalette.commands.archive.subtitle'),
        keywords: t('commandPalette.commands.archive.keywords'),
        icon: Archive,
        action: () => {
          setSelectedCategory(null)
          setSelectedTag(null)
          setShowArchived(true)
          navigate('/')
        },
      },
    ]

    const noteCommands = recentNotes.map((note) => ({
      id: `note-${note.id}`,
      group: 'recent' as const,
      title: note.title || t('commandPalette.untitled'),
      subtitle: `${formatNoteDate(note.updated_at, locale, t('commandPalette.unknownTime'))} · ${getNotePreview(note, t('commandPalette.noPreview'))}`,
      keywords: `${note.title || ''} ${note.content || ''} ${note.category_name || note.type || ''} ${note.tags?.map((tag) => tag.name).join(' ') || ''}`,
      icon: FileText,
      action: () => openNoteFromPalette(note),
    }))

    const serverResultCommands = serverSearchNotes.map((note) => ({
      id: `search-note-${note.id}`,
      group: 'results' as const,
      title: note.title || t('commandPalette.untitled'),
      subtitle: `${formatNoteDate(note.updated_at, locale, t('commandPalette.unknownTime'))} · ${getNotePreview(note, t('commandPalette.noPreview'))}`,
      keywords: `${note.title || ''} ${note.content || ''} ${note.content_preview || ''} ${note.category_name || note.type || ''} ${note.tags?.map((tag) => tag.name).join(' ') || ''}`,
      icon: Search,
      action: () => openNoteFromPalette(note),
    }))

    const actions: CommandItem[] = [
      {
        id: 'action-new-note',
        group: 'actions',
        title: t('commandPalette.commands.newNote.title'),
        subtitle: t('commandPalette.commands.newNote.subtitle'),
        keywords: t('commandPalette.commands.newNote.keywords'),
        icon: Plus,
        action: openNewNote,
      },
      {
        id: 'action-toggle-theme',
        group: 'actions',
        title: t('commandPalette.commands.toggleTheme.title'),
        subtitle: t('commandPalette.commands.toggleTheme.subtitle'),
        keywords: t('commandPalette.commands.toggleTheme.keywords'),
        icon: ((localStorage.getItem('theme') || 'light') === 'dark' ? Sun : Moon),
        action: toggleTheme,
      },
      {
        id: 'action-settings',
        group: 'actions',
        title: t('commandPalette.commands.appearance.title'),
        subtitle: t('commandPalette.commands.appearance.subtitle'),
        keywords: t('commandPalette.commands.appearance.keywords'),
        icon: Settings,
        action: () => navigate('/settings'),
      },
    ]

    return [...navigation, ...serverResultCommands, ...noteCommands, ...actions]
  }, [
    navigate,
    locale,
    openEditor,
    openNoteFromPalette,
    recentNotes,
    serverSearchNotes,
    setSelectedCategory,
    setSelectedTag,
    setShowArchived,
    showArchived,
    t,
  ])

  const filteredCommands = useMemo(() => {
    const normalizedQuery = (serverSearchTerm || query.trim()).toLowerCase()
    if (!normalizedQuery) return commands
    return commands
      .map((item, index) => {
        const title = item.title.toLowerCase()
        const keywords = item.keywords.toLowerCase()
        const subtitle = item.subtitle.toLowerCase()
        const score = title.includes(normalizedQuery)
          ? 0
          : keywords.includes(normalizedQuery)
            ? 1
            : subtitle.includes(normalizedQuery)
              ? 2
              : -1

        return { item, index, score }
      })
      .filter((entry) => entry.score >= 0)
      .sort((a, b) => a.score - b.score || a.index - b.index)
      .map((entry) => entry.item)
  }, [commands, query, serverSearchTerm])

  const groupedCommands = useMemo(() => {
    return filteredCommands.reduce<Record<CommandGroup, CommandItem[]>>((acc, item) => {
      acc[item.group].push(item)
      return acc
    }, { navigation: [], results: [], recent: [], actions: [] })
  }, [filteredCommands])

  useEffect(() => {
    if (!isOpen || !serverSearchTerm) {
      setServerSearchNotes([])
      setServerSearchTotal(0)
      setIsServerSearchLoading(false)
      setServerSearchFailed(false)
      return
    }

    let isCurrent = true
    setIsServerSearchLoading(true)
    setServerSearchFailed(false)

    const timer = window.setTimeout(() => {
      api.getNotes({
        search: serverSearchTerm,
        per_page: SERVER_SEARCH_LIMIT,
        include_archived: true,
        sort: 'updated',
      })
        .then((response) => {
          if (!isCurrent) return
          setServerSearchNotes(response.notes)
          setServerSearchTotal(response.total)
        })
        .catch(() => {
          if (!isCurrent) return
          setServerSearchNotes([])
          setServerSearchTotal(0)
          setServerSearchFailed(true)
        })
        .finally(() => {
          if (isCurrent) setIsServerSearchLoading(false)
        })
    }, SERVER_SEARCH_DEBOUNCE_MS)

    return () => {
      isCurrent = false
      window.clearTimeout(timer)
    }
  }, [isOpen, serverSearchTerm])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const isPaletteShortcut = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k'
      if (isPaletteShortcut) {
        event.preventDefault()
        toggleCommandPalette()
        return
      }

      if (event.key === 'Escape' && isOpen) {
        event.preventDefault()
        closePalette()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, toggleCommandPalette])

  useEffect(() => {
    if (!isOpen) return
    const timer = window.setTimeout(() => inputRef.current?.focus(), 0)
    return () => window.clearTimeout(timer)
  }, [isOpen])

  useEffect(() => {
    setActiveIndex(0)
  }, [query])

  const runCommand = async (item: CommandItem) => {
    await item.action()
    closePalette()
  }

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (filteredCommands.length === 0) return
      setActiveIndex((index) => Math.min(index + 1, filteredCommands.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (filteredCommands.length === 0) return
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter' && filteredCommands[activeIndex]) {
      event.preventDefault()
      void runCommand(filteredCommands[activeIndex])
    }
  }

  if (!isOpen) return null

  let flatIndex = -1

  return (
    <div className="fixed inset-0 z-50 bg-black/45 px-3 py-20 backdrop-blur-sm sm:px-6" role="dialog" aria-modal="true">
      <button
        type="button"
        className="absolute inset-0 h-full w-full cursor-default"
        aria-label={t('commandPalette.close')}
        onClick={closePalette}
      />

      <div className="relative mx-auto flex max-h-[min(680px,calc(100vh-7rem))] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-border-default bg-bg-surface shadow-2xl shadow-black/40">
        <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-3">
          <Search size={18} className="shrink-0 text-text-muted" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder={t('commandPalette.placeholder')}
            className="h-9 min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
            data-testid="command-palette-input"
          />
          <kbd className="hidden rounded border border-border-default px-1.5 py-0.5 font-mono text-[11px] text-text-muted sm:inline">
            Esc
          </kbd>
        </div>

        <div className="overflow-y-auto p-2" data-testid="command-palette-list">
          {serverSearchTerm && (
            <div className="mb-1 rounded-md border border-border-subtle bg-bg-elevated/45 px-3 py-2 text-xs text-text-muted" data-testid="command-palette-server-search-status">
              {isServerSearchLoading
                ? t('commandPalette.serverSearch.searching', { query: serverSearchTerm })
                : serverSearchFailed
                  ? t('commandPalette.serverSearch.failed')
                  : serverSearchNotes.length === 0
                    ? t('commandPalette.serverSearch.empty', { query: serverSearchTerm })
                    : t('commandPalette.serverSearch.count', { query: serverSearchTerm, count: serverSearchTotal })}
            </div>
          )}
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm text-text-muted">
              {t('commandPalette.empty')}
            </div>
          ) : (
            (Object.keys(groupedCommands) as CommandGroup[]).map((group) => {
              const items = groupedCommands[group]
              if (items.length === 0) return null

              return (
                <div key={group} className="py-1">
                  <div className="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wider text-text-muted">
                    {t(`commandPalette.groups.${group}`)}
                  </div>
                  <div className="space-y-1">
                    {items.map((item) => {
                      flatIndex += 1
                      const itemIndex = flatIndex
                      const Icon = item.icon
                      const isActive = itemIndex === activeIndex

                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => { void runCommand(item) }}
                          onMouseEnter={() => setActiveIndex(itemIndex)}
                          className={`flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors ${
                            isActive
                              ? 'bg-primary/15 text-text-primary'
                              : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                          }`}
                          data-testid={`command-item-${item.id}`}
                        >
                          <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${
                            isActive ? 'bg-primary/20 text-primary-light' : 'bg-bg-elevated text-text-muted'
                          }`}>
                            <Icon size={16} />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium">{item.title}</span>
                            <span className="mt-0.5 block truncate text-xs text-text-muted">{item.subtitle}</span>
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
