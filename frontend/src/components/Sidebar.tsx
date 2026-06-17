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
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { useTranslation } from '../hooks/useTranslation'
import { getCategoryDisplayName } from '../utils/categoryDisplay'

export function Sidebar() {
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

  useEffect(() => {
    fetchCategories()
    fetchTags()
  }, [fetchCategories, fetchTags])

  // Display tags (show all or just first 10)
  const displayTags = showAllTags ? tags : tags.slice(0, 10)
  const hasMoreTags = tags.length > 10
  const isHomeRoute = location.pathname === '/'

  const clearLibraryFilters = () => {
    setSelectedCategory(null)
    setSelectedTag(null)
    if (showArchived) setShowArchived(false)
  }

  const handleCategoryClick = (categoryId: number) => {
    const nextCategoryId = isHomeRoute && selectedCategoryId === categoryId ? null : categoryId
    setSelectedCategory(nextCategoryId)
    if (!isHomeRoute) navigate('/')
  }

  const handleTagClick = (tagId: number) => {
    const nextTagId = isHomeRoute && selectedTagId === tagId ? null : tagId
    setSelectedTag(nextTagId)
    if (!isHomeRoute) navigate('/')
  }

  const handleArchiveClick = () => {
    setShowArchived(!showArchived)
    if (!isHomeRoute) navigate('/')
  }

  const systemSection = !isCollapsed && (
    <div>
      <h3 className="mb-2 hidden px-2 text-[11px] font-medium uppercase tracking-wider text-text-muted sm:block">
        {t('shell.system')}
      </h3>
      <div className="space-y-1">
        <button
          onClick={handleArchiveClick}
          className={`w-full flex items-center justify-center sm:justify-start gap-2.5 rounded-md px-2.5 py-2 text-left text-[13.5px] transition-colors duration-150
            ${showArchived
              ? 'bg-primary/15 text-primary-light'
              : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
            }`}
        >
          <Archive size={16} />
          <span className="hidden min-w-0 flex-1 truncate sm:block">{t('sidebar.archive')}</span>
        </button>
        <Link
          to="/settings"
          onClick={clearLibraryFilters}
          className={`flex items-center justify-center sm:justify-start gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] transition-colors duration-150
            ${location.pathname === '/settings'
              ? 'bg-primary/15 text-primary-light'
              : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
            }`}
        >
          <Settings size={16} />
          <span className="hidden truncate sm:block">{t('sidebar.settings')}</span>
        </Link>
      </div>
    </div>
  )

  return (
    <aside
      data-testid="app-sidebar"
      className={`
        bg-bg-base border-r border-border-subtle
        flex shrink-0 flex-col transition-all duration-300
        ${isCollapsed ? 'w-16' : 'w-16 sm:w-[var(--prism-sidebar-width)]'}
      `}
    >
      {/* Logo */}
      <div className={`border-b border-border-subtle flex items-center gap-3 ${isCollapsed ? 'px-3.5 py-[18px]' : 'px-[18px] py-[18px]'}`}>
        <div className="w-7 h-7 rounded-md bg-primary text-white flex shrink-0 items-center justify-center">
          <span className="font-semibold text-sm">P</span>
        </div>
        {!isCollapsed && (
          <div className="hidden min-w-0 sm:block">
            <div className="text-[17px] font-semibold leading-tight tracking-tight text-text-primary">Prism</div>
            <div className="mt-0.5 font-mono text-[11px] text-text-muted">v2 · local</div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4" data-testid="sidebar-nav">
        <div className="space-y-6">
          <div>
            {!isCollapsed && (
              <h3 className="mb-2 hidden px-2 text-[11px] font-medium uppercase tracking-wider text-text-muted sm:block">
                {t('shell.navigation')}
              </h3>
            )}
            <div className="space-y-1">
              <Link
                to="/"
                onClick={clearLibraryFilters}
                className={`
                  flex items-center justify-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] sm:justify-start
                  transition-colors duration-150
                  ${isHomeRoute && !selectedCategoryId && !selectedTagId && !showArchived
                    ? 'bg-primary/15 text-primary-light'
                    : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                  }
                `}
              >
                <Home size={16} />
                {!isCollapsed && (
                  <>
                    <span className="hidden min-w-0 flex-1 truncate sm:block">{t('sidebar.all')}</span>
                    <span className="hidden font-mono text-[11px] text-text-muted sm:inline">
                      {categories.reduce((sum, cat) => sum + (cat.count || 0), 0).toLocaleString()}
                    </span>
                  </>
                )}
              </Link>

              <Link
                to="/prompt-builder"
                onClick={clearLibraryFilters}
                className={`
                  flex items-center justify-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] sm:justify-start
                  transition-colors duration-150
                  ${location.pathname === '/prompt-builder'
                    ? 'bg-primary/15 text-primary-light'
                    : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                  }
                `}
              >
                <Sparkles size={16} />
                {!isCollapsed && <span className="hidden truncate sm:block">Prompt Builder</span>}
              </Link>
            </div>
          </div>

        {/* Categories Section */}
        {!isCollapsed && categories.length > 0 && (
          <div>
            <h3 className="mb-2 hidden px-2 text-[11px] font-medium uppercase tracking-wider text-text-muted sm:flex items-center gap-2">
              <FolderOpen size={14} />
              {t('sidebar.categories')}
            </h3>
            <div className="space-y-1">
              {categories.map((cat) => {
                const categoryName = getCategoryDisplayName(cat.name, t)
                return (
                  <button
                    key={cat.id}
                    onClick={() => handleCategoryClick(cat.id)}
                    className={`w-full flex items-center justify-center sm:justify-start gap-2.5 px-2.5 py-2 rounded-md
                             transition-colors duration-150 text-left text-[13.5px]
                             ${selectedCategoryId === cat.id
                               ? 'bg-primary/15 text-primary-light'
                               : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                             }`}
                  >
                    <span className="text-[15px]">{cat.icon || '📁'}</span>
                    <span className="hidden truncate flex-1 sm:block">{categoryName}</span>
                    <span className="hidden font-mono text-[11px] text-text-muted sm:inline">
                      {cat.count || 0}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {systemSection}

        {/* Tags Section */}
        {!isCollapsed && tags.length > 0 && (
          <div>
            <button 
              onClick={() => setShowTags(!showTags)}
              className="w-full mb-2 hidden px-2 text-[11px] font-medium text-text-muted uppercase tracking-wider sm:flex items-center gap-2 hover:text-text-primary transition-colors"
            >
              <Tag size={14} />
              {t('sidebar.tags')}
              <span className="text-text-muted">({tags.length})</span>
              <span className="ml-auto">
                {showTags ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              </span>
            </button>
            {showTags && (
              <div className="space-y-1 mt-1">
                {displayTags.map((tag) => (
                  <button
                    key={tag.id}
                    onClick={() => handleTagClick(tag.id)}
                    className={`w-full flex items-center justify-center sm:justify-start gap-2 px-2.5 py-1.5 rounded-md
                             transition-colors duration-150 text-left text-[13px]
                             ${selectedTagId === tag.id
                               ? 'bg-accent/15 text-accent'
                               : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                             }`}
                  >
                    <Hash size={14} className="flex-shrink-0" />
                    <span className="hidden truncate flex-1 sm:block">{tag.name}</span>
                    <span className="hidden font-mono text-[11px] text-text-muted sm:inline">
                      {tag.count || 0}
                    </span>
                  </button>
                ))}
                
                {/* Show more/less button */}
                {hasMoreTags && (
                  <button
                    onClick={() => setShowAllTags(!showAllTags)}
                    className="hidden w-full px-3 py-2 text-xs text-primary-light hover:text-primary sm:flex
                               transition-colors flex items-center justify-center gap-1"
                  >
                    {showAllTags ? (
                      <>
                        <ChevronUp size={14} />
                        {t('sidebar.showLess')}
                      </>
                    ) : (
                      <>
                        <ChevronDown size={14} />
                        {t('sidebar.showAllTags', { count: tags.length })}
                      </>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
        </div>
      </nav>

      {/* Bottom Section */}
      <div className="p-3 border-t border-border-subtle">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md
                     text-text-muted hover:bg-bg-hover hover:text-text-primary
                     transition-colors duration-150 text-sm"
          title={isCollapsed ? t('sidebar.expand') : t('sidebar.collapse')}
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          {!isCollapsed && <span className="hidden sm:inline">{t('sidebar.collapse')}</span>}
        </button>
      </div>
    </aside>
  )
}
