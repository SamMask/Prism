import { Search, Plus, LayoutGrid, List, AlignJustify, X, ArrowUpDown, Trash2, CheckSquare, Square, Command, BookOpen } from 'lucide-react'
import { useState, useCallback, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { Button, IconButton } from './ui'
import { toast } from './ui/Toast'
import { confirm } from './ui/ConfirmDialog'
import { useTranslation } from '../hooks/useTranslation'
import { getCategoryDisplayName } from '../utils/categoryDisplay'
import { useReadingWorkspace } from '../hooks/useReadingWorkspace'
import { api } from '../services/api'

export function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { workspace } = useReadingWorkspace()
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
    openReading,
  } = useAppStore()

  const [inputValue, setInputValue] = useState(searchQuery)
  const [showSortMenu, setShowSortMenu] = useState(false)
  const [isOpeningReadingWorkspace, setIsOpeningReadingWorkspace] = useState(false)

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

    if (await confirm({
      title: t('header.batchDeleteTitle'),
      message: t('header.batchDeleteMessage', { count: selectedNoteIds.length }),
      variant: 'danger',
    })) {
      try {
        await deleteSelectedNotes()
        toast.success(t('header.batchDeleteSuccess', { count: selectedNoteIds.length }))
      } catch {
        toast.error(t('header.deleteFailed'))
      }
    }
  }

  const handleOpenReadingWorkspace = async () => {
    const noteId = workspace.activeId ?? workspace.noteIds[0]
    if (!noteId) return

    setIsOpeningReadingWorkspace(true)
    try {
      const note = await api.getNote(noteId)
      if (location.pathname !== '/') navigate('/')
      openReading(note)
    } catch {
      toast.error(t('reading.workspaceLoadFailed'))
    } finally {
      setIsOpeningReadingWorkspace(false)
    }
  }

  // Sort options matching backend
  const sortOptions = [
    { value: 'updated' as const, label: t('header.sortUpdated') },
    { value: 'created' as const, label: t('header.sortCreated') },
    { value: 'custom' as const, label: t('header.sortCustom') },
  ]
  const viewOptions = [
    { value: 'grid' as const, label: t('header.viewGrid'), icon: LayoutGrid },
    { value: 'list' as const, label: t('header.viewList'), icon: List },
    { value: 'compact' as const, label: t('header.viewCompact'), icon: AlignJustify },
  ]

  const isSelectionMode = selectedNoteIds.length > 0
  const isHomeRoute = location.pathname === '/'
  const activeCategory = categories.find((category) => category.id === selectedCategoryId)
  const activeCategoryName = getCategoryDisplayName(activeCategory, t)
  const activeTag = tags.find((tag) => tag.id === selectedTagId)
  const pageTitle = location.pathname === '/prompt-builder'
    ? 'Prompt Builder'
    : location.pathname === '/settings'
      ? t('header.settings')
      : showArchived
      ? t('header.archive')
        : activeCategoryName || (activeTag ? `#${activeTag.name}` : t('header.all'))
  const pageMeta = isHomeRoute
    ? t('header.homeMeta', { count: totalNotes.toLocaleString() })
    : location.pathname === '/prompt-builder'
      ? t('header.promptBuilderMeta')
      : t('header.settingsMeta')

  return (
    <header className="h-[60px] shrink-0 bg-bg-base border-b border-border-subtle px-4 lg:px-6 flex items-center gap-3" data-testid="header">
      {isSelectionMode ? (
        // Selection Mode Header
        <>
          <div className="flex items-center gap-3">
            <IconButton onClick={clearSelection} aria-label={t('header.cancelSelection')}>
              <X size={20} />
            </IconButton>
            <span className="text-text-primary font-medium">
              {t('header.selectedCount', { count: selectedNoteIds.length })}
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
            {t('header.selectAll')}
          </button>

          <Button
            onClick={handleDeleteSelected}
            variant="secondary"
            className="text-danger border-danger/30 hover:bg-danger/10"
            disabled={isDeleting}
          >
            <Trash2 size={18} />
            {t('common.delete')}
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
                  placeholder={t('header.searchPlaceholder')}
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
          <div className="flex items-center gap-0.5 p-1 rounded-md bg-bg-elevated" aria-label={t('header.viewMode')}>
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
            aria-label={t('header.commandPalette')}
            title={t('header.commandPalette')}
          >
            <Command size={16} />
            <span className="font-mono text-xs">Ctrl K</span>
          </button>

          {workspace.noteIds.length > 0 && (
            <button
              type="button"
              onClick={handleOpenReadingWorkspace}
              disabled={isOpeningReadingWorkspace}
              className="inline-flex shrink-0 items-center gap-2 rounded-md bg-bg-elevated px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary disabled:cursor-wait disabled:opacity-60"
              data-testid="header-open-reading-workspace"
              aria-label={t('header.openReadingWorkspace', { count: workspace.noteIds.length })}
              title={t('header.openReadingWorkspace', { count: workspace.noteIds.length })}
            >
              <BookOpen size={16} />
              <span className="hidden xl:inline">{t('header.readingWorkspace')}</span>
              <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-xs text-primary-light">
                {workspace.noteIds.length}
              </span>
            </button>
          )}

          {/* New Note Button */}
          <Button onClick={() => openEditor(null)} variant="primary" size="sm" className="shrink-0" data-testid="add-note-button">
            <Plus size={18} />
            <span className="hidden sm:inline">{t('header.addNote')}</span>
          </Button>
        </>
      )}
    </header>
  )
}
