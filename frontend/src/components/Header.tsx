import { Search, Plus, LayoutGrid, List, AlignJustify, X, ArrowUpDown, Trash2, CheckSquare, Square, Command } from 'lucide-react'
import { useState, useCallback, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { Button, IconButton } from './ui'
import { toast } from './ui/Toast'
import { confirm } from './ui/ConfirmDialog'

export function Header() {
  const location = useLocation()
  const {
    searchQuery,
    setSearchQuery,
    viewMode,
    setViewMode,
    openEditor,
    selectedNoteIds,
    selectAllNotes,
    clearSelection,
    deleteSelectedNotes,
    isDeleting,
    sortBy,
    setSortBy,
    notes,
    categories,
    tags,
    selectedCategoryId,
    selectedTagId,
    showArchived,
    totalNotes,
    openCommandPalette,
  } = useAppStore()

  const [inputValue, setInputValue] = useState(searchQuery)
  const [showSortMenu, setShowSortMenu] = useState(false)

  // Sync input with store when searchQuery changes externally
  useEffect(() => {
    setInputValue(searchQuery)
  }, [searchQuery])

  // Handle search change - auto-search when cleared
  const handleSearchChange = useCallback((value: string) => {
    setInputValue(value)
    if (value === '' && searchQuery !== '') {
      setSearchQuery('')
    }
  }, [searchQuery, setSearchQuery])

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(inputValue)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearchSubmit(e as any)
    }
  }

  const handleClearSearch = () => {
    setInputValue('')
    setSearchQuery('')
  }

  const handleDeleteSelected = async () => {
    if (selectedNoteIds.length === 0) return

    if (await confirm({ title: '批次刪除', message: `確定要刪除 ${selectedNoteIds.length} 個筆記嗎？此操作無法復原。`, variant: 'danger' })) {
      try {
        await deleteSelectedNotes()
        toast.success(`已刪除 ${selectedNoteIds.length} 個筆記`)
      } catch {
        toast.error('刪除失敗')
      }
    }
  }

  // Sort options matching backend
  const sortOptions = [
    { value: 'updated' as const, label: '更新時間 (新→舊)' },
    { value: 'created' as const, label: '建立時間 (新→舊)' },
    { value: 'custom' as const, label: '自訂順序' },
  ]
  const viewOptions = [
    { value: 'grid' as const, label: '網格', icon: LayoutGrid },
    { value: 'list' as const, label: '列表', icon: List },
    { value: 'compact' as const, label: '精簡列表', icon: AlignJustify },
  ]

  const isSelectionMode = selectedNoteIds.length > 0
  const isHomeRoute = location.pathname === '/'
  const activeCategory = categories.find((category) => category.id === selectedCategoryId)
  const activeTag = tags.find((tag) => tag.id === selectedTagId)
  const pageTitle = location.pathname === '/prompt-builder'
    ? 'Prompt Builder'
    : location.pathname === '/settings'
      ? '設定'
      : showArchived
        ? '封存'
        : activeCategory?.name || (activeTag ? `#${activeTag.name}` : '全部')
  const pageMeta = isHomeRoute
    ? `${totalNotes.toLocaleString()} 筆內容`
    : location.pathname === '/prompt-builder'
      ? '結構化提示工具'
      : '系統與資料維護'

  return (
    <header className="h-[60px] shrink-0 bg-bg-base border-b border-border-subtle px-4 lg:px-6 flex items-center gap-3" data-testid="header">
      {isSelectionMode ? (
        // Selection Mode Header
        <>
          <div className="flex items-center gap-3">
            <IconButton onClick={clearSelection} aria-label="取消選取">
              <X size={20} />
            </IconButton>
            <span className="text-text-primary font-medium">
              已選擇 {selectedNoteIds.length} 項
            </span>
          </div>

          <div className="flex-1" />

          <button
            onClick={() => {
              if (selectedNoteIds.length === notes.length) {
                clearSelection()
              } else {
                selectAllNotes()
              }
            }}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
          >
            {selectedNoteIds.length === notes.length ? (
              <CheckSquare size={18} />
            ) : (
              <Square size={18} />
            )}
            全選
          </button>

          <Button
            onClick={handleDeleteSelected}
            variant="secondary"
            className="text-danger border-danger/30 hover:bg-danger/10"
            disabled={isDeleting}
          >
            <Trash2 size={18} />
            刪除
          </Button>
        </>
      ) : (
        // Normal Header
        <>
          <div className="min-w-0 flex items-center gap-2 pr-2">
            <div className="min-w-0">
              <div className="truncate text-[16px] font-semibold tracking-tight text-text-primary">
                {pageTitle}
              </div>
              <div className="hidden sm:block truncate text-[11px] text-text-muted">
                {pageMeta}
              </div>
            </div>
          </div>

          <div className="flex-1" />

          {/* Search Bar */}
          <form onSubmit={handleSearchSubmit} className="hidden md:block w-[min(36vw,440px)] relative" data-testid="search-form">
            <div className="relative flex items-center gap-2">
              {/* Search Input */}
              <div className="relative flex-1">
                <Search
                  size={18}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
                />
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="搜尋筆記... (按 Enter)"
                  data-testid="search-input"
                  className="w-full pl-10 pr-10 py-2 rounded-md text-sm
                             bg-bg-elevated border border-border-default
                             text-text-primary placeholder-text-muted
                             focus:outline-none focus:ring-1 focus:border-primary focus:ring-primary/50
                             transition-colors duration-200"
                />
                {inputValue && (
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted
                               hover:text-text-primary transition-colors"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            </div>
          </form>

          {/* Sort Dropdown */}
          {isHomeRoute && (
          <div className="relative hidden sm:block">
            <button
              onClick={() => setShowSortMenu(!showSortMenu)}
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-bg-elevated
                         text-text-secondary hover:bg-bg-hover hover:text-text-primary transition-colors text-sm"
            >
              <ArrowUpDown size={16} />
              <span className="text-sm hidden sm:inline">
                {sortOptions.find(o => o.value === sortBy)?.label.split(' ')[0]}
              </span>
            </button>

            {showSortMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowSortMenu(false)}
                />
                <div className="absolute right-0 top-full mt-2 w-56 bg-bg-surface border border-border-default rounded-lg shadow-xl z-20 py-1">
                  {sortOptions.map(option => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setSortBy(option.value)
                        setShowSortMenu(false)
                      }}
                      className={`w-full flex items-center justify-between px-4 py-2.5 text-sm
                                 ${sortBy === option.value ? 'text-primary bg-primary/5' : 'text-text-secondary'}
                                 hover:bg-bg-hover transition-colors`}
                    >
                      <span>{option.label}</span>
                      {sortBy === option.value && (
                        <span className="text-primary">✓</span>
                      )}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
          )}

          {/* View Mode Toggle */}
          {isHomeRoute && (
          <div className="flex items-center gap-0.5 p-1 rounded-md bg-bg-elevated" aria-label="顯示模式">
            {viewOptions.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => setViewMode(value)}
                className={`p-1.5 rounded transition-colors duration-150 ${
                  viewMode === value
                    ? 'bg-primary/20 text-primary-light'
                    : 'text-text-muted hover:text-text-primary'
                }`}
                title={label}
                aria-label={label}
                aria-pressed={viewMode === value}
                data-testid={`view-mode-${value}`}
              >
                <Icon size={18} />
              </button>
            ))}
          </div>
          )}

          {/* Command Palette Button */}
          <button
            type="button"
            onClick={openCommandPalette}
            className="hidden items-center gap-2 rounded-md bg-bg-elevated px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary lg:flex"
            data-testid="command-palette-button"
            aria-label="開啟命令面板"
            title="開啟命令面板"
          >
            <Command size={16} />
            <span className="font-mono text-xs">Ctrl K</span>
          </button>

          {/* New Note Button */}
          <Button onClick={() => openEditor(null)} variant="primary" size="sm" className="shrink-0" data-testid="add-note-button">
            <Plus size={18} />
            <span className="hidden sm:inline">新增</span>
          </Button>
        </>
      )}
    </header>
  )
}
