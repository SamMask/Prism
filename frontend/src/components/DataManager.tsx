import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, X, Save, FolderOpen, Tag, GitMerge } from 'lucide-react'
import { api, Category, Tag as TagType } from '../services/api'
import { Button, IconButton } from './ui'
import { toast } from './ui/Toast'
import { confirm } from './ui/ConfirmDialog'
import { useAppStore } from '../stores/appStore'
import { useTranslation } from '../hooks/useTranslation'
import { getCategoryDisplayName } from '../utils/categoryDisplay'

interface CategoryManagerProps {
  categories: Category[]
  onRefresh: () => void
}

function CategoryManager({ categories, onRefresh }: CategoryManagerProps) {
  const { t } = useTranslation()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editIcon, setEditIcon] = useState('')
  const [newName, setNewName] = useState('')
  const [newIcon, setNewIcon] = useState('📁')
  const [isAdding, setIsAdding] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleCreate = async () => {
    if (!newName.trim()) {
      toast.warning(t('settings.organization.categoryNameRequired'))
      return
    }
    const categoryName = newName.trim()
    setIsLoading(true)
    try {
      await api.createCategory(categoryName, newIcon || '📁')
      toast.success(t('settings.organization.categoryCreated', { name: categoryName }))
      setNewName('')
      setNewIcon('📁')
      setIsAdding(false)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.organization.createFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleUpdate = async (id: number) => {
    if (!editName.trim()) {
      toast.warning(t('settings.organization.categoryNameRequired'))
      return
    }
    setIsLoading(true)
    try {
      await api.updateCategory(id, { name: editName.trim(), icon: editIcon })
      toast.success(t('settings.organization.categoryUpdated'))
      setEditingId(null)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.organization.updateFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (cat: Category) => {
    if (cat.is_default) {
      toast.warning(t('settings.organization.defaultCategoryCannotDelete'))
      return
    }
    const targetCategory = categories.find((candidate) => candidate.is_default)
    if (!targetCategory) {
      toast.error(t('settings.organization.defaultCategoryMissing'))
      return
    }
    if (!await confirm({
      title: t('settings.organization.deleteCategoryTitle'),
      message: t('settings.organization.deleteCategoryMessage', {
        name: getCategoryDisplayName(cat.name, t),
        count: cat.count || 0,
        target: getCategoryDisplayName(targetCategory.name, t),
      }),
      variant: 'danger',
    })) {
      return
    }
    setIsLoading(true)
    try {
      await api.deleteCategory(cat.id, targetCategory.id)
      toast.success(t('settings.organization.categoryDeleted', { name: getCategoryDisplayName(cat.name, t) }))
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.organization.deleteFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const startEdit = (cat: Category) => {
    setEditingId(cat.id)
    setEditName(cat.name)
    setEditIcon(cat.icon || '📁')
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditName('')
    setEditIcon('')
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <FolderOpen size={16} /> {t('settings.organization.categoryManagement')}
        </h3>
        {!isAdding && (
          <Button size="sm" variant="ghost" onClick={() => setIsAdding(true)}>
            <Plus size={14} /> {t('common.add')}
          </Button>
        )}
      </div>

      {isAdding && (
        <div className="flex items-center gap-2 p-2 rounded-lg bg-bg-elevated">
          <input
            type="text"
            value={newIcon}
            onChange={(e) => setNewIcon(e.target.value)}
            className="w-10 px-2 py-1 text-center rounded bg-bg-surface border border-border-default"
            placeholder="📁"
          />
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            className="flex-1 px-3 py-1.5 rounded bg-bg-surface border border-border-default text-sm"
            placeholder={t('settings.organization.categoryNamePlaceholder')}
            autoFocus
          />
          <IconButton size="sm" variant="success" onClick={handleCreate} disabled={isLoading} aria-label={t('common.save')}>
            <Save size={16} />
          </IconButton>
          <IconButton size="sm" onClick={() => setIsAdding(false)} aria-label={t('common.cancel')}>
            <X size={16} />
          </IconButton>
        </div>
      )}

      <div className="space-y-1">
        {categories.map((cat) => {
          const categoryName = getCategoryDisplayName(cat.name, t)
          return (
          <div key={cat.id} className="flex items-center gap-2 p-2 rounded-lg hover:bg-bg-elevated group">
            {editingId === cat.id ? (
              <>
                <input
                  type="text"
                  value={editIcon}
                  onChange={(e) => setEditIcon(e.target.value)}
                  className="w-10 px-2 py-1 text-center rounded bg-bg-surface border border-border-default"
                />
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleUpdate(cat.id)}
                  className="flex-1 px-3 py-1.5 rounded bg-bg-surface border border-border-default text-sm"
                  autoFocus
                />
                <IconButton size="sm" variant="success" onClick={() => handleUpdate(cat.id)} disabled={isLoading} aria-label={t('common.save')}>
                  <Save size={16} />
                </IconButton>
                <IconButton size="sm" onClick={cancelEdit} aria-label={t('common.cancel')}>
                  <X size={16} />
                </IconButton>
              </>
            ) : (
              <>
                <span className="text-lg">{cat.icon || '📁'}</span>
                <span className="min-w-0 flex-1 truncate text-sm text-text-primary">{categoryName}</span>
                <span
                  className="w-12 shrink-0 rounded bg-bg-elevated px-2 py-0.5 text-right text-xs tabular-nums text-text-muted"
                  data-testid="category-count"
                >
                  {cat.count || 0}
                </span>
                <span className="flex w-16 shrink-0 justify-end gap-1" data-testid="category-actions">
                  <IconButton size="sm" onClick={() => startEdit(cat)} className="opacity-0 group-hover:opacity-100" aria-label={t('common.edit')}>
                    <Pencil size={14} />
                  </IconButton>
                  {!cat.is_default ? (
                    <IconButton size="sm" variant="danger-solid" onClick={() => handleDelete(cat)} disabled={isLoading} className="opacity-0 group-hover:opacity-100" aria-label={t('common.delete')}>
                      <Trash2 size={14} />
                    </IconButton>
                  ) : (
                    <span className="h-7 w-7" aria-hidden="true" />
                  )}
                </span>
              </>
            )}
          </div>
        )})}
      </div>
    </div>
  )
}

interface TagManagerProps {
  tags: TagType[]
  onRefresh: () => void
}

function TagManager({ tags, onRefresh }: TagManagerProps) {
  const { t } = useTranslation()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [selectedTags, setSelectedTags] = useState<number[]>([])
  const [mergeTarget, setMergeTarget] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleRename = async (id: number) => {
    if (!editName.trim()) {
      toast.warning(t('settings.organization.tagNameRequired'))
      return
    }
    setIsLoading(true)
    try {
      await api.renameTag(id, editName.trim())
      toast.success(t('settings.organization.tagRenamed'))
      setEditingId(null)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.organization.renameFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (tag: TagType) => {
    if (!await confirm({
      title: t('settings.organization.deleteTagTitle'),
      message: t('settings.organization.deleteTagMessage', { name: tag.name }),
      variant: 'danger',
    })) return
    setIsLoading(true)
    try {
      await api.deleteTag(tag.id)
      toast.success(t('settings.organization.tagDeleted', { name: tag.name }))
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.organization.deleteFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleMerge = async () => {
    if (!mergeTarget || selectedTags.length === 0) {
      toast.warning(t('settings.organization.mergeSelectionRequired'))
      return
    }
    if (selectedTags.includes(mergeTarget)) {
      toast.warning(t('settings.organization.mergeTargetCannotBeSource'))
      return
    }
    setIsLoading(true)
    try {
      const result = await api.mergeTags(selectedTags, mergeTarget)
      toast.success(t('settings.organization.tagsMerged', { count: result.merged_count }))
      setSelectedTags([])
      setMergeTarget(null)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.organization.mergeFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const toggleSelect = (id: number) => {
    if (selectedTags.includes(id)) {
      setSelectedTags(selectedTags.filter((t) => t !== id))
    } else {
      setSelectedTags([...selectedTags, id])
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <Tag size={16} /> {t('settings.organization.tagManagement', { count: tags.length })}
        </h3>
        {selectedTags.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              value={mergeTarget || ''}
              onChange={(e) => setMergeTarget(e.target.value ? Number(e.target.value) : null)}
              className="px-2 py-1 rounded text-xs bg-bg-elevated border border-border-default"
            >
              <option value="">{t('settings.organization.selectMergeTarget')}</option>
              {tags.filter((t) => !selectedTags.includes(t.id)).map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            <Button size="sm" variant="ghost" onClick={handleMerge} disabled={!mergeTarget || isLoading}>
              <GitMerge size={14} /> {t('settings.organization.mergeAction', { count: selectedTags.length })}
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <div
            key={tag.id}
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs
                       transition-colors cursor-pointer
                       ${selectedTags.includes(tag.id)
                         ? 'bg-primary/20 text-primary ring-1 ring-primary/50'
                         : 'bg-bg-elevated text-text-secondary hover:bg-bg-hover'
                       }`}
            onClick={() => toggleSelect(tag.id)}
          >
            {editingId === tag.id ? (
              <>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleRename(tag.id)}
                  onClick={(e) => e.stopPropagation()}
                  className="w-20 px-1 py-0.5 rounded bg-bg-surface border text-xs"
                  autoFocus
                />
                <IconButton size="xs" variant="success" onClick={(e) => { e.stopPropagation(); handleRename(tag.id) }} aria-label={t('common.save')}>
                  <Save size={12} />
                </IconButton>
                <IconButton size="xs" onClick={(e) => { e.stopPropagation(); setEditingId(null) }} aria-label={t('common.cancel')}>
                  <X size={12} />
                </IconButton>
              </>
            ) : (
              <>
                <span>{tag.name}</span>
                <span className="text-text-muted">({tag.count || 0})</span>
                <IconButton size="xs" onClick={(e) => { e.stopPropagation(); setEditingId(tag.id); setEditName(tag.name) }} className="opacity-50 hover:opacity-100" aria-label={t('settings.organization.rename')}>
                  <Pencil size={10} />
                </IconButton>
                <IconButton size="xs" variant="danger-solid" onClick={(e) => { e.stopPropagation(); handleDelete(tag) }} className="opacity-50 hover:opacity-100" aria-label={t('common.delete')}>
                  <Trash2 size={10} />
                </IconButton>
              </>
            )}
          </div>
        ))}
      </div>

      {tags.length === 0 && (
        <p className="text-sm text-text-muted text-center py-4">{t('settings.organization.noTags')}</p>
      )}
    </div>
  )
}

export function DataManager() {
  const { categories, tags, fetchCategories, fetchTags } = useAppStore()

  useEffect(() => {
    fetchCategories()
    fetchTags()
  }, [])

  return (
    <div className="space-y-6">
      <CategoryManager categories={categories} onRefresh={fetchCategories} />
      <div className="border-t border-border-subtle pt-6">
        <TagManager tags={tags} onRefresh={fetchTags} />
      </div>
    </div>
  )
}
