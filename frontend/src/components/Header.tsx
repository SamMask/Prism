import { Search, Plus, LayoutGrid, List, X, ArrowUpDown, Trash2, CheckSquare, Square, Brain, Loader2 } from 'lucide-react'
import { useState, useCallback, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Button } from './ui/Button'
import { toast } from './ui/Toast'
import { api } from '../services/api'

interface SemanticResult {
  id: number
  title: string
  content_preview: string
  similarity: number
  category: string
  category_icon: string
  tags: string[]
}

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
  
  // Semantic Search State
  const [isSemanticMode, setIsSemanticMode] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [semanticResults, setSemanticResults] = useState<SemanticResult[]>([])
  const [showSemanticResults, setShowSemanticResults] = useState(false)

  // Sync input with store when searchQuery changes externally
  useEffect(() => {
    setInputValue(searchQuery)
  }, [searchQuery])

  // Handle search change - auto-search when cleared
  const handleSearchChange = useCallback((value: string) => {
    setInputValue(value)
    if (value === '' && searchQuery !== '') {
      setSearchQuery('')
      setSemanticResults([])
      setShowSemanticResults(false)
    }
  }, [searchQuery, setSearchQuery])

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (isSemanticMode && inputValue.trim()) {
      // Semantic Search
      setIsSearching(true)
      try {
        const response = await api.semanticSearch(inputValue.trim())
        setSemanticResults(response.data || [])
        setShowSemanticResults(true)
        if (response.data.length === 0) {
          toast.info('未找到相似的筆記')
        }
      } catch (error: any) {
        if (error?.response?.data?.message?.includes('not installed')) {
          toast.error('請先安裝 sentence-transformers')
        } else if (error?.response?.data?.message?.includes('No indexed')) {
          toast.warning('請先到設定頁面重建搜尋索引')
        } else {
          toast.error('語意搜尋失敗')
        }
      } finally {
        setIsSearching(false)
      }
    } else {
      // Normal search
      setSearchQuery(inputValue)
      setShowSemanticResults(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearchSubmit(e as any)
    }
    if (e.key === 'Escape') {
      setShowSemanticResults(false)
    }
  }

  const handleClearSearch = () => {
    setInputValue('')
    setSearchQuery('')
    setSemanticResults([])
    setShowSemanticResults(false)
  }

  const handleSemanticResultClick = (noteId: number) => {
    // Find note in store or open editor
    const note = notes.find(n => n.id === noteId)
    if (note) {
      openEditor(note)
    } else {
      // Note not in current view, need to fetch
      toast.info('正在載入筆記...')
      api.getNote(noteId).then(fetchedNote => {
        openEditor(fetchedNote)
      }).catch(() => {
        toast.error('無法載入筆記')
      })
    }
    setShowSemanticResults(false)
  }

  const handleDeleteSelected = async () => {
    if (selectedNoteIds.length === 0) return
    
    if (confirm(`確定要刪除 ${selectedNoteIds.length} 個筆記嗎？此操作無法復原。`)) {
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
            <button
              onClick={clearSelection}
              className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-hover transition-colors"
            >
              <X size={20} />
            </button>
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
              {/* Semantic Mode Toggle */}
              <button
                type="button"
                onClick={() => {
                  setIsSemanticMode(!isSemanticMode)
                  if (!isSemanticMode) {
                    toast.info('🧠 語意搜尋已啟用')
                  }
                }}
                className={`p-2.5 rounded-lg transition-all duration-200 flex-shrink-0 ${
                  isSemanticMode
                    ? 'bg-accent text-white shadow-lg shadow-accent/30'
                    : 'bg-bg-elevated text-text-muted hover:text-text-primary'
                }`}
                title={isSemanticMode ? '語意搜尋 (點擊關閉)' : '啟用語意搜尋'}
              >
                <Brain size={18} />
              </button>
              
              {/* Search Input */}
              <div className="relative flex-1">
                {isSearching ? (
                  <Loader2
                    size={18}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-accent animate-spin"
                  />
                ) : (
                  <Search
                    size={18}
                    className={`absolute left-3 top-1/2 -translate-y-1/2 ${
                      isSemanticMode ? 'text-accent' : 'text-text-muted'
                    }`}
                  />
                )}
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onFocus={() => {
                    if (semanticResults.length > 0) setShowSemanticResults(true)
                  }}
                  placeholder={isSemanticMode ? '語意搜尋... (按 Enter)' : '搜尋筆記... (按 Enter)'}
                  data-testid="search-input"
                  className={`w-full pl-10 pr-10 py-2.5 rounded-lg
                             bg-bg-elevated border 
                             text-text-primary placeholder-text-muted
                             focus:outline-none focus:ring-1 transition-colors duration-200
                             ${isSemanticMode 
                               ? 'border-accent/50 focus:border-accent focus:ring-accent/50' 
                               : 'border-border-default focus:border-primary focus:ring-primary/50'
                             }`}
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

            {/* Semantic Search Results Dropdown */}
            {showSemanticResults && semanticResults.length > 0 && (
              <>
                <div 
                  className="fixed inset-0 z-10" 
                  onClick={() => setShowSemanticResults(false)}
                />
                <div className="absolute left-0 right-0 top-full mt-2 bg-bg-surface border border-border-default rounded-xl shadow-2xl z-20 overflow-hidden max-h-[60vh] overflow-y-auto">
                  <div className="px-4 py-2 border-b border-border-subtle bg-bg-elevated/50">
                    <span className="text-xs text-text-muted">
                      🧠 語意相似度搜尋結果 ({semanticResults.length})
                    </span>
                  </div>
                  {semanticResults.map((result) => (
                    <button
                      key={result.id}
                      onClick={() => handleSemanticResultClick(result.id)}
                      className="w-full text-left px-4 py-3 hover:bg-bg-hover border-b border-border-subtle last:border-0 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-text-primary truncate flex-1">
                          {result.category_icon} {result.title}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ml-2 ${
                          result.similarity > 0.7 
                            ? 'bg-success/20 text-success' 
                            : result.similarity > 0.5 
                              ? 'bg-warning/20 text-warning'
                              : 'bg-bg-elevated text-text-muted'
                        }`}>
                          {(result.similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-sm text-text-secondary line-clamp-2">
                        {result.content_preview}
                      </p>
                      {result.tags.length > 0 && (
                        <div className="flex gap-1 mt-1.5">
                          {result.tags.slice(0, 3).map((tag, i) => (
                            <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </>
            )}
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
