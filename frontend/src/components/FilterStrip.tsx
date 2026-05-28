import { Archive, Hash, Home, Tag } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'

export function FilterStrip() {
  const location = useLocation()
  const navigate = useNavigate()
  const {
    categories,
    tags,
    selectedCategoryId,
    selectedTagId,
    showArchived,
    setSelectedCategory,
    setSelectedTag,
    setShowArchived,
  } = useAppStore()

  const isHomeRoute = location.pathname === '/'
  const isAllActive = isHomeRoute && !selectedCategoryId && !selectedTagId && !showArchived
  const displayTags = tags.slice(0, 12)

  const goHome = () => {
    if (!isHomeRoute) navigate('/')
  }

  const clearFilters = () => {
    if (selectedCategoryId) setSelectedCategory(null)
    if (selectedTagId) setSelectedTag(null)
    if (showArchived) setShowArchived(false)
    goHome()
  }

  const handleArchiveClick = () => {
    const nextArchived = !(isHomeRoute && showArchived)
    setShowArchived(nextArchived)
    goHome()
  }

  const handleCategoryClick = (categoryId: number) => {
    const nextCategoryId = isHomeRoute && selectedCategoryId === categoryId ? null : categoryId
    setSelectedCategory(nextCategoryId)
    goHome()
  }

  const handleTagClick = (tagId: number) => {
    const nextTagId = isHomeRoute && selectedTagId === tagId ? null : tagId
    setSelectedTag(nextTagId)
    goHome()
  }

  const chipBase = 'inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md border px-3 text-[13px] transition-colors'
  const chipIdle = 'border-border-subtle bg-bg-base text-text-secondary hover:border-border-default hover:bg-bg-hover hover:text-text-primary'
  const chipActive = 'border-primary/40 bg-primary/15 text-primary-light'
  const tagActive = 'border-accent/40 bg-accent/15 text-accent'

  return (
    <div
      className="shrink-0 border-b border-border-subtle bg-bg-base px-4 py-2 lg:px-6"
      data-testid="filter-strip"
    >
      <div className="flex items-center gap-2 overflow-x-auto">
        <button
          type="button"
          onClick={clearFilters}
          className={`${chipBase} ${isAllActive ? chipActive : chipIdle}`}
          aria-pressed={isAllActive}
          data-testid="filter-all"
        >
          <Home size={14} />
          <span>全部</span>
        </button>

        <button
          type="button"
          onClick={handleArchiveClick}
          className={`${chipBase} ${showArchived ? chipActive : chipIdle}`}
          aria-pressed={showArchived}
          data-testid="filter-archive"
        >
          <Archive size={14} />
          <span>封存</span>
        </button>

        {categories.length > 0 && (
          <span className="mx-1 h-4 w-px shrink-0 bg-border-subtle" aria-hidden="true" />
        )}

        {categories.map((category) => {
          const isActive = selectedCategoryId === category.id

          return (
            <button
              key={category.id}
              type="button"
              onClick={() => handleCategoryClick(category.id)}
              className={`${chipBase} ${isActive ? chipActive : chipIdle}`}
              aria-pressed={isActive}
              data-testid={`filter-category-${category.id}`}
              title={category.name}
            >
              <span className="text-[14px]" aria-hidden="true">{category.icon || '📁'}</span>
              <span className="max-w-[120px] truncate">{category.name}</span>
              <span className="font-mono text-[11px] text-text-muted">{category.count || 0}</span>
            </button>
          )
        })}

        {displayTags.length > 0 && (
          <span className="mx-1 h-4 w-px shrink-0 bg-border-subtle" aria-hidden="true" />
        )}

        {displayTags.map((tag) => {
          const isActive = selectedTagId === tag.id

          return (
            <button
              key={tag.id}
              type="button"
              onClick={() => handleTagClick(tag.id)}
              className={`${chipBase} ${isActive ? tagActive : chipIdle}`}
              aria-pressed={isActive}
              data-testid={`filter-tag-${tag.id}`}
              title={tag.name}
            >
              <Hash size={14} />
              <span className="max-w-[120px] truncate">{tag.name}</span>
              <span className="font-mono text-[11px] text-text-muted">{tag.count || 0}</span>
            </button>
          )
        })}

        {tags.length > displayTags.length && (
          <span className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md border border-border-subtle bg-bg-base px-3 text-[13px] text-text-muted">
            <Tag size={14} />
            +{tags.length - displayTags.length}
          </span>
        )}
      </div>
    </div>
  )
}
