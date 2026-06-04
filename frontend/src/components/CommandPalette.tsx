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
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Note } from '../services/api'
import { useAppStore } from '../stores/appStore'
import { toast } from './ui/Toast'

type CommandGroup = '導覽' | '最近筆記' | '動作'

interface CommandItem {
  id: string
  group: CommandGroup
  title: string
  subtitle: string
  keywords: string
  icon: typeof Search
  action: () => void
}

function formatNoteDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未知時間'
  return date.toLocaleDateString('zh-TW')
}

function getNotePreview(note: Note) {
  const content = note.content
    ?.replace(/!\[.*?\]\(.*?\)/g, '')
    .replace(/\[.*?\]\(.*?\)/g, '')
    .replace(/#{1,6}\s/g, '')
    .trim()

  return content ? content.slice(0, 72) : '沒有內容預覽'
}

export function CommandPalette() {
  const navigate = useNavigate()
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
    const currentTheme = (localStorage.getItem('theme') as 'dark' | 'light') || 'dark'
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark'
    localStorage.setItem('theme', nextTheme)
    document.documentElement.classList.toggle('light', nextTheme === 'light')
    toast.success(`已切換至${nextTheme === 'dark' ? '深色' : '淺色'}主題`)
  }

  const recentNotes = useMemo(() => {
    return [...notes]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 6)
  }, [notes])

  const commands = useMemo<CommandItem[]>(() => {
    const navigation: CommandItem[] = [
      {
        id: 'nav-home',
        group: '導覽',
        title: '全部筆記',
        subtitle: '回到 Home 並清除分類、標籤與封存篩選',
        keywords: 'home all notes library 首頁 全部 筆記',
        icon: Home,
        action: goHome,
      },
      {
        id: 'nav-prompt-builder',
        group: '導覽',
        title: 'Prompt Builder',
        subtitle: '開啟結構化提示工具',
        keywords: 'prompt builder 提示 工具',
        icon: Sparkles,
        action: () => navigate('/prompt-builder'),
      },
      {
        id: 'nav-settings',
        group: '導覽',
        title: '設定',
        subtitle: '開啟系統、外觀與資料維護',
        keywords: 'settings preferences options 設定 外觀 資料 維護',
        icon: Settings,
        action: () => navigate('/settings'),
      },
      {
        id: 'nav-archive',
        group: '導覽',
        title: '封存筆記',
        subtitle: '回到 Home 並顯示封存內容',
        keywords: 'archive archived 封存',
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
      group: '最近筆記' as const,
      title: note.title || '無標題',
      subtitle: `${formatNoteDate(note.updated_at)} · ${getNotePreview(note)}`,
      keywords: `${note.title || ''} ${note.content || ''} ${note.category_name || note.type || ''} ${note.tags?.map((tag) => tag.name).join(' ') || ''}`,
      icon: FileText,
      action: () => {
        navigate('/')
        openEditor(note)
      },
    }))

    const actions: CommandItem[] = [
      {
        id: 'action-new-note',
        group: '動作',
        title: '新增筆記',
        subtitle: '開啟既有新增筆記編輯器，不直接寫入資料庫',
        keywords: 'new create note add 新增 筆記',
        icon: Plus,
        action: openNewNote,
      },
      {
        id: 'action-toggle-theme',
        group: '動作',
        title: '切換明暗主題',
        subtitle: '套用現有 localStorage 主題設定',
        keywords: 'theme dark light appearance 主題 深色 淺色 外觀',
        icon: ((localStorage.getItem('theme') || 'dark') === 'dark' ? Sun : Moon),
        action: toggleTheme,
      },
      {
        id: 'action-settings',
        group: '動作',
        title: '外觀設定',
        subtitle: '前往 Settings 調整主題色彩與顯示密度',
        keywords: 'appearance color view mode 外觀 主題色彩 顯示模式',
        icon: Settings,
        action: () => navigate('/settings'),
      },
    ]

    return [...navigation, ...noteCommands, ...actions]
  }, [
    navigate,
    openEditor,
    recentNotes,
    setSelectedCategory,
    setSelectedTag,
    setShowArchived,
    showArchived,
  ])

  const filteredCommands = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
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
  }, [commands, query])

  const groupedCommands = useMemo(() => {
    return filteredCommands.reduce<Record<CommandGroup, CommandItem[]>>((acc, item) => {
      acc[item.group].push(item)
      return acc
    }, { 導覽: [], 最近筆記: [], 動作: [] })
  }, [filteredCommands])

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

  const runCommand = (item: CommandItem) => {
    item.action()
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
      runCommand(filteredCommands[activeIndex])
    }
  }

  if (!isOpen) return null

  let flatIndex = -1

  return (
    <div className="fixed inset-0 z-50 bg-black/45 px-3 py-20 backdrop-blur-sm sm:px-6" role="dialog" aria-modal="true">
      <button
        type="button"
        className="absolute inset-0 h-full w-full cursor-default"
        aria-label="關閉命令面板"
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
            placeholder="搜尋命令、最近筆記、設定..."
            className="h-9 min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
            data-testid="command-palette-input"
          />
          <kbd className="hidden rounded border border-border-default px-1.5 py-0.5 font-mono text-[11px] text-text-muted sm:inline">
            Esc
          </kbd>
        </div>

        <div className="overflow-y-auto p-2" data-testid="command-palette-list">
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm text-text-muted">
              找不到符合的命令
            </div>
          ) : (
            (Object.keys(groupedCommands) as CommandGroup[]).map((group) => {
              const items = groupedCommands[group]
              if (items.length === 0) return null

              return (
                <div key={group} className="py-1">
                  <div className="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wider text-text-muted">
                    {group}
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
                          onClick={() => runCommand(item)}
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
