import { Search, Plus, LayoutGrid, List, X, ArrowUpDown, Trash2, CheckSquare, Square } from 'lucide-react'
import { useState, useCallback, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Button, IconButton } from './ui'
import { toast } from './ui/Toast'
import { confirm } from './ui/ConfirmDialog'

export function Header() {
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

  const isSelectionMode = selectedNoteIds.length > 0

  return (
    <header className="h-16 bg-bg-surface border-b border-border-subtle px-6 flex items-center gap-4" data-testid="header">
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
          {/* Search Bar */}
          <form onSubmit={handleSearchSubmit} className="flex-1 max-w-xl relative" data-testid="search-form">
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
                  className="w-full pl-10 pr-10 py-2.5 rounded-lg
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
          <div className="relative">
            <button
              onClick={() => setShowSortMenu(!showSortMenu)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-elevated
                         text-text-secondary hover:text-text-primary transition-colors"
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

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-bg-elevated">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-md transition-colors duration-200 ${
                viewMode === 'grid'
                  ? 'bg-primary text-white'
                  : 'text-text-muted hover:text-text-primary'
              }`}
              title="Grid View"
            >
              <LayoutGrid size={18} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-md transition-colors duration-200 ${
                viewMode === 'list'
                  ? 'bg-primary text-white'
                  : 'text-text-muted hover:text-text-primary'
              }`}
              title="List View"
            >
              <List size={18} />
            </button>
          </div>

          {/* New Note Button */}
          <Button onClick={() => openEditor(null)} variant="primary" data-testid="add-note-button">
            <Plus size={18} />
            <span>新增筆記</span>
          </Button>
        </>
      )}
    </header>
  )
}
