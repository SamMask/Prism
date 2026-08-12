import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Archive,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  FolderOpen,
  Hash,
  Home,
  Settings,
  Sparkles,
  Tag,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { useTranslation } from '../hooks/useTranslation'
import { getCategoryDisplayName } from '../utils/categoryDisplay'

interface SidebarProps {
  isMobileOpen: boolean
  onMobileClose: () => void
}

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export function Sidebar({ isMobileOpen, onMobileClose }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const {
    categories,
    tags,
    fetchCategories,
    fetchTags,
    selectedCategoryId,
    selectedTagId,
    showArchived,
    setSelectedCategory,
    setSelectedTag,
    setShowArchived,
  } = useAppStore()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [showTags, setShowTags] = useState(true)
  const [showAllTags, setShowAllTags] = useState(false)
  const drawerRef = useRef<HTMLElement>(null)

  useEffect(() => {
    fetchCategories()
    fetchTags()
  }, [fetchCategories, fetchTags])

  useEffect(() => {
    if (!isMobileOpen) return

    const previouslyFocused = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const drawer = drawerRef.current
    const focusFirstControl = window.requestAnimationFrame(() => {
      drawer?.querySelector<HTMLElement>(focusableSelector)?.focus()
    })

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onMobileClose()
        return
      }
      if (event.key !== 'Tab' || !drawer) return

      const controls = Array.from(drawer.querySelectorAll<HTMLElement>(focusableSelector))
      if (controls.length === 0) return
      const first = controls[0]
      const last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      window.cancelAnimationFrame(focusFirstControl)
      document.removeEventListener('keydown', handleKeyDown)
      previouslyFocused?.focus()
    }
  }, [isMobileOpen, onMobileClose])

  const displayTags = showAllTags ? tags : tags.slice(0, 10)
  const hasMoreTags = tags.length > 10
  const isHomeRoute = location.pathname === '/'
  const desktopCollapsedClass = isCollapsed ? 'md:hidden' : ''

  const clearLibraryFilters = () => {
    setSelectedCategory(null)
    setSelectedTag(null)
    if (showArchived) setShowArchived(false)
    onMobileClose()
  }

  const handleCategoryClick = (categoryId: number) => {
    const nextCategoryId = isHomeRoute && selectedCategoryId === categoryId ? null : categoryId
    setSelectedCategory(nextCategoryId)
    if (!isHomeRoute) navigate('/')
    onMobileClose()
  }

  const handleTagClick = (tagId: number) => {
    const nextTagId = isHomeRoute && selectedTagId === tagId ? null : tagId
    setSelectedTag(nextTagId)
    if (!isHomeRoute) navigate('/')
    onMobileClose()
  }

  const handleArchiveClick = () => {
    setShowArchived(!showArchived)
    if (!isHomeRoute) navigate('/')
    onMobileClose()
  }

  return (
    <>
      {isMobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/45 md:hidden"
          onClick={onMobileClose}
          aria-label={t('sidebar.closeNavigation')}
          data-testid="mobile-navigation-backdrop"
        />
      )}
      <aside
        ref={drawerRef}
        data-testid="app-sidebar"
        data-mobile-navigation-drawer="true"
        role={isMobileOpen ? 'dialog' : undefined}
        aria-modal={isMobileOpen ? true : undefined}
        aria-label={t('shell.navigation')}
        className={`${isMobileOpen ? 'flex translate-x-0' : 'hidden -translate-x-full'}
          fixed inset-y-0 left-0 z-50 w-[min(18rem,85vw)] flex-col border-r border-border-subtle bg-bg-base
          shadow-2xl transition-transform duration-200 md:static md:z-auto md:flex md:translate-x-0 md:shadow-none
          ${isCollapsed ? 'md:w-16' : 'md:w-[var(--prism-sidebar-width)]'}`}
      >
        <div className={`flex items-center gap-3 border-b border-border-subtle px-[18px] py-[18px] ${isCollapsed ? 'md:px-3.5' : 'md:px-[18px]'}`}>
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-white">
            <span className="text-sm font-semibold">P</span>
          </div>
          <div className={`min-w-0 flex-1 ${desktopCollapsedClass}`}>
            <div className="text-[17px] font-semibold leading-tight tracking-tight text-text-primary">Prism</div>
            <div className="mt-0.5 font-mono text-[11px] text-text-muted">V2.6.1</div>
          </div>
          <button
            type="button"
            onClick={onMobileClose}
            className="rounded-md p-2 text-text-muted hover:bg-bg-hover hover:text-text-primary md:hidden"
            aria-label={t('sidebar.closeNavigation')}
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4" data-testid="sidebar-nav">
          <div className="space-y-6">
            <div>
              <h3 className={`mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-text-muted ${desktopCollapsedClass}`}>
                {t('shell.navigation')}
              </h3>
              <div className="space-y-1">
                <Link
                  to="/"
                  onClick={clearLibraryFilters}
                  aria-label={t('sidebar.all')}
                  className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] transition-colors duration-150
                    ${isCollapsed ? 'md:justify-center' : 'md:justify-start'}
                    ${isHomeRoute && !selectedCategoryId && !selectedTagId && !showArchived
                      ? 'bg-primary/15 text-primary-light'
                      : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'}`}
                >
                  <Home size={16} />
                  <span className={`min-w-0 flex-1 truncate ${desktopCollapsedClass}`}>{t('sidebar.all')}</span>
                  <span className={`font-mono text-[11px] text-text-muted ${desktopCollapsedClass}`}>
                    {categories.reduce((sum, category) => sum + (category.count || 0), 0).toLocaleString()}
                  </span>
                </Link>
                <Link
                  to="/prompt-builder"
                  onClick={clearLibraryFilters}
                  aria-label="Prompt Builder"
                  className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] transition-colors duration-150
                    ${isCollapsed ? 'md:justify-center' : 'md:justify-start'}
                    ${location.pathname === '/prompt-builder'
                      ? 'bg-primary/15 text-primary-light'
                      : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'}`}
                >
                  <Sparkles size={16} />
                  <span className={`truncate ${desktopCollapsedClass}`}>Prompt Builder</span>
                </Link>
              </div>
            </div>

            {categories.length > 0 && (
              <div className={desktopCollapsedClass}>
                <h3 className="mb-2 flex items-center gap-2 px-2 text-[11px] font-medium uppercase tracking-wider text-text-muted">
                  <FolderOpen size={14} />
                  {t('sidebar.categories')}
                </h3>
                <div className="space-y-1">
                  {categories.map((category) => {
                    const categoryName = getCategoryDisplayName(category, t)
                    return (
                      <button
                        key={category.id}
                        type="button"
                        onClick={() => handleCategoryClick(category.id)}
                        aria-label={categoryName}
                        className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13.5px] transition-colors duration-150
                          ${selectedCategoryId === category.id
                            ? 'bg-primary/15 text-primary-light'
                            : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'}`}
                      >
                        <span className="text-[15px]">{category.icon || '📁'}</span>
                        <span className="min-w-0 flex-1 truncate">{categoryName}</span>
                        <span className="font-mono text-[11px] text-text-muted">{category.count || 0}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            <div className={desktopCollapsedClass}>
              <h3 className="mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-text-muted">{t('shell.system')}</h3>
              <div className="space-y-1">
                <button
                  type="button"
                  onClick={handleArchiveClick}
                  aria-label={t('sidebar.archive')}
                  className={`flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13.5px] transition-colors duration-150
                    ${showArchived
                      ? 'bg-primary/15 text-primary-light'
                      : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'}`}
                >
                  <Archive size={16} />
                  <span className="min-w-0 flex-1 truncate">{t('sidebar.archive')}</span>
                </button>
                <Link
                  to="/settings"
                  onClick={clearLibraryFilters}
                  aria-label={t('sidebar.settings')}
                  className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] transition-colors duration-150
                    ${location.pathname === '/settings'
                      ? 'bg-primary/15 text-primary-light'
                      : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'}`}
                >
                  <Settings size={16} />
                  <span className="truncate">{t('sidebar.settings')}</span>
                </Link>
              </div>
            </div>

            {tags.length > 0 && (
              <div className={desktopCollapsedClass}>
                <button
                  type="button"
                  onClick={() => setShowTags(!showTags)}
                  className="mb-2 flex w-full items-center gap-2 px-2 text-[11px] font-medium uppercase tracking-wider text-text-muted transition-colors hover:text-text-primary"
                  aria-expanded={showTags}
                >
                  <Tag size={14} />
                  {t('sidebar.tags')}
                  <span className="text-text-muted">({tags.length})</span>
                  <span className="ml-auto">{showTags ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</span>
                </button>
                {showTags && (
                  <div className="mt-1 space-y-1">
                    {displayTags.map((tag) => (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => handleTagClick(tag.id)}
                        aria-label={`#${tag.name}`}
                        className={`flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-[13px] transition-colors duration-150
                          ${selectedTagId === tag.id
                            ? 'bg-accent/15 text-accent'
                            : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'}`}
                      >
                        <Hash size={14} className="shrink-0" />
                        <span className="min-w-0 flex-1 truncate">{tag.name}</span>
                        <span className="font-mono text-[11px] text-text-muted">{tag.count || 0}</span>
                      </button>
                    ))}
                    {hasMoreTags && (
                      <button
                        type="button"
                        onClick={() => setShowAllTags(!showAllTags)}
                        className="flex w-full items-center justify-center gap-1 px-3 py-2 text-xs text-primary-light transition-colors hover:text-primary"
                      >
                        {showAllTags ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        {showAllTags ? t('sidebar.showLess') : t('sidebar.showAllTags', { count: tags.length })}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </nav>

        <div className="hidden border-t border-border-subtle p-3 md:block">
          <button
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="flex w-full items-center justify-center gap-2 rounded-md px-3 py-2 text-sm text-text-muted transition-colors duration-150 hover:bg-bg-hover hover:text-text-primary"
            title={isCollapsed ? t('sidebar.expand') : t('sidebar.collapse')}
            aria-label={isCollapsed ? t('sidebar.expand') : t('sidebar.collapse')}
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            {!isCollapsed && <span>{t('sidebar.collapse')}</span>}
          </button>
        </div>
      </aside>
    </>
  )
}
