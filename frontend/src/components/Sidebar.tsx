import { Link, useLocation } from 'react-router-dom'
import { Home, Sparkles, Settings, FolderOpen, ChevronLeft, ChevronRight, Tag, Hash, ChevronDown, ChevronUp } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'

export function Sidebar() {
  const location = useLocation()
  const { 
    categories, 
    tags,
    fetchCategories, 
    fetchTags,
    selectedCategoryId, 
    selectedTagId,
    setSelectedCategory,
    setSelectedTag 
  } = useAppStore()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [showTags, setShowTags] = useState(true)
  const [showAllTags, setShowAllTags] = useState(false)

  useEffect(() => {
    fetchCategories()
    fetchTags()
  }, [fetchCategories, fetchTags])

  const navItems = [
    { path: '/', icon: Home, label: '首頁' },
    { path: '/prompt-builder', icon: Sparkles, label: 'Prompt Builder' },
    { path: '/settings', icon: Settings, label: '設定' },
  ]

  // Display tags (show all or just first 10)
  const displayTags = showAllTags ? tags : tags.slice(0, 10)
  const hasMoreTags = tags.length > 10

  return (
    <aside
      className={`
        bg-bg-surface border-r border-border-subtle
        flex flex-col transition-all duration-300
        ${isCollapsed ? 'w-16' : 'w-64'}
      `}
    >
      {/* Logo */}
      <div className="p-4 border-b border-border-subtle flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <span className="text-white font-bold text-sm">P</span>
        </div>
        {!isCollapsed && (
          <span className="font-semibold text-lg gradient-text">Prism V2</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto" data-testid="sidebar-nav">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path && !selectedCategoryId && !selectedTagId
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => {
                setSelectedCategory(null)
                setSelectedTag(null)
              }}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg
                transition-colors duration-200
                ${isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                }
              `}
            >
              <item.icon size={20} />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          )
        })}

        {/* Categories Section */}
        {!isCollapsed && categories.length > 0 && (
          <div className="mt-6">
            <h3 className="px-3 py-2 text-xs font-medium text-text-muted uppercase tracking-wider flex items-center gap-2">
              <FolderOpen size={14} />
              分類
            </h3>
            <div className="space-y-1">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(selectedCategoryId === cat.id ? null : cat.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg
                           transition-colors duration-200 text-left
                           ${selectedCategoryId === cat.id
                             ? 'bg-primary/10 text-primary'
                             : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                           }`}
                >
                  <span className="text-lg">{cat.icon || '📁'}</span>
                  <span className="truncate flex-1">{cat.name}</span>
                  <span className="text-xs text-text-muted bg-bg-elevated px-1.5 py-0.5 rounded">
                    {cat.count || 0}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Tags Section */}
        {!isCollapsed && tags.length > 0 && (
          <div className="mt-6">
            <button 
              onClick={() => setShowTags(!showTags)}
              className="w-full px-3 py-2 text-xs font-medium text-text-muted uppercase tracking-wider flex items-center gap-2 hover:text-text-primary transition-colors"
            >
              <Tag size={14} />
              標籤
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
                    onClick={() => setSelectedTag(selectedTagId === tag.id ? null : tag.id)}
                    className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-lg
                             transition-colors duration-200 text-left text-sm
                             ${selectedTagId === tag.id
                               ? 'bg-accent/10 text-accent'
                               : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                             }`}
                  >
                    <Hash size={14} className="flex-shrink-0" />
                    <span className="truncate flex-1">{tag.name}</span>
                    <span className="text-xs text-text-muted bg-bg-elevated px-1.5 py-0.5 rounded">
                      {tag.count || 0}
                    </span>
                  </button>
                ))}
                
                {/* Show more/less button */}
                {hasMoreTags && (
                  <button
                    onClick={() => setShowAllTags(!showAllTags)}
                    className="w-full px-3 py-2 text-xs text-primary hover:text-primary-hover 
                               transition-colors flex items-center justify-center gap-1"
                  >
                    {showAllTags ? (
                      <>
                        <ChevronUp size={14} />
                        收起
                      </>
                    ) : (
                      <>
                        <ChevronDown size={14} />
                        顯示全部 {tags.length} 個標籤
                      </>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </nav>

      {/* Bottom Section */}
      <div className="p-3 border-t border-border-subtle">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg
                     text-text-muted hover:bg-bg-hover hover:text-text-primary
                     transition-colors duration-200"
          title={isCollapsed ? '展開側邊欄' : '收縮側邊欄'}
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          {!isCollapsed && <span>收縮側邊欄</span>}
        </button>
      </div>
    </aside>
  )
}
