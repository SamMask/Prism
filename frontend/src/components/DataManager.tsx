import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, X, Save, FolderOpen, Tag, GitMerge } from 'lucide-react'
import { api, Category, Tag as TagType } from '../services/api'
import { Button, IconButton } from './ui'
import { toast } from './ui/Toast'
import { confirm } from './ui/ConfirmDialog'
import { useAppStore } from '../stores/appStore'

interface CategoryManagerProps {
  categories: Category[]
  onRefresh: () => void
}

function CategoryManager({ categories, onRefresh }: CategoryManagerProps) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editIcon, setEditIcon] = useState('')
  const [newName, setNewName] = useState('')
  const [newIcon, setNewIcon] = useState('📁')
  const [isAdding, setIsAdding] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleCreate = async () => {
    if (!newName.trim()) {
      toast.warning('請輸入分類名稱')
      return
    }
    setIsLoading(true)
    try {
      await api.createCategory(newName.trim(), newIcon || '📁')
      toast.success(`分類 "${newName}" 已建立`)
      setNewName('')
      setNewIcon('📁')
      setIsAdding(false)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '建立失敗')
    } finally {
      setIsLoading(false)
    }
  }

  const handleUpdate = async (id: number) => {
    if (!editName.trim()) {
      toast.warning('請輸入分類名稱')
      return
    }
    setIsLoading(true)
    try {
      await api.updateCategory(id, { name: editName.trim(), icon: editIcon })
      toast.success('分類已更新')
      setEditingId(null)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '更新失敗')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (cat: Category) => {
    if (cat.is_default) {
      toast.warning('無法刪除預設分類')
      return
    }
    const targetCategory = categories.find((candidate) => candidate.is_default)
    if (!await confirm({ title: '刪除分類', message: `確定要刪除分類「${cat.name}」嗎？\n其中的 ${cat.count || 0} 篇筆記將移至「筆記」分類。`, variant: 'danger' })) {
      return
    }
    if (!targetCategory) {
      toast.error('找不到預設分類，無法遷移筆記')
      return
    }
    setIsLoading(true)
    try {
      await api.deleteCategory(cat.id, targetCategory.id)
      toast.success(`分類 "${cat.name}" 已刪除`)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '刪除失敗')
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
          <FolderOpen size={16} /> 分類管理
        </h3>
        {!isAdding && (
          <Button size="sm" variant="ghost" onClick={() => setIsAdding(true)}>
            <Plus size={14} /> 新增
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
            placeholder="分類名稱"
            autoFocus
          />
          <IconButton size="sm" variant="success" onClick={handleCreate} disabled={isLoading} aria-label="儲存">
            <Save size={16} />
          </IconButton>
          <IconButton size="sm" onClick={() => setIsAdding(false)} aria-label="取消">
            <X size={16} />
          </IconButton>
        </div>
      )}

      <div className="space-y-1">
        {categories.map((cat) => (
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
                <IconButton size="sm" variant="success" onClick={() => handleUpdate(cat.id)} disabled={isLoading} aria-label="儲存">
                  <Save size={16} />
                </IconButton>
                <IconButton size="sm" onClick={cancelEdit} aria-label="取消">
                  <X size={16} />
                </IconButton>
              </>
            ) : (
              <>
                <span className="text-lg">{cat.icon || '📁'}</span>
                <span className="min-w-0 flex-1 truncate text-sm text-text-primary">{cat.name}</span>
                <span
                  className="w-12 shrink-0 rounded bg-bg-elevated px-2 py-0.5 text-right text-xs tabular-nums text-text-muted"
                  data-testid="category-count"
                >
                  {cat.count || 0}
                </span>
                <span className="flex w-16 shrink-0 justify-end gap-1" data-testid="category-actions">
                  <IconButton size="sm" onClick={() => startEdit(cat)} className="opacity-0 group-hover:opacity-100" aria-label="編輯">
                    <Pencil size={14} />
                  </IconButton>
                  {!cat.is_default ? (
                    <IconButton size="sm" variant="danger-solid" onClick={() => handleDelete(cat)} disabled={isLoading} className="opacity-0 group-hover:opacity-100" aria-label="刪除">
                      <Trash2 size={14} />
                    </IconButton>
                  ) : (
                    <span className="h-7 w-7" aria-hidden="true" />
                  )}
                </span>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

interface TagManagerProps {
  tags: TagType[]
  onRefresh: () => void
}

function TagManager({ tags, onRefresh }: TagManagerProps) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [selectedTags, setSelectedTags] = useState<number[]>([])
  const [mergeTarget, setMergeTarget] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleRename = async (id: number) => {
    if (!editName.trim()) {
      toast.warning('請輸入標籤名稱')
      return
    }
    setIsLoading(true)
    try {
      await api.renameTag(id, editName.trim())
      toast.success('標籤已重命名')
      setEditingId(null)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '重命名失敗')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (tag: TagType) => {
    if (!await confirm({ title: '刪除標籤', message: `確定要刪除標籤「${tag.name}」嗎？`, variant: 'danger' })) return
    setIsLoading(true)
    try {
      await api.deleteTag(tag.id)
      toast.success(`標籤 "${tag.name}" 已刪除`)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '刪除失敗')
    } finally {
      setIsLoading(false)
    }
  }

  const handleMerge = async () => {
    if (!mergeTarget || selectedTags.length === 0) {
      toast.warning('請選擇要合併的標籤和目標標籤')
      return
    }
    if (selectedTags.includes(mergeTarget)) {
      toast.warning('目標標籤不能被合併')
      return
    }
    setIsLoading(true)
    try {
      const result = await api.mergeTags(selectedTags, mergeTarget)
      toast.success(`已合併 ${result.merged_count} 個標籤`)
      setSelectedTags([])
      setMergeTarget(null)
      onRefresh()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '合併失敗')
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
          <Tag size={16} /> 標籤管理 ({tags.length})
        </h3>
        {selectedTags.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              value={mergeTarget || ''}
              onChange={(e) => setMergeTarget(e.target.value ? Number(e.target.value) : null)}
              className="px-2 py-1 rounded text-xs bg-bg-elevated border border-border-default"
            >
              <option value="">選擇目標標籤</option>
              {tags.filter((t) => !selectedTags.includes(t.id)).map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            <Button size="sm" variant="ghost" onClick={handleMerge} disabled={!mergeTarget || isLoading}>
              <GitMerge size={14} /> 合併 ({selectedTags.length})
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
                <IconButton size="xs" variant="success" onClick={(e) => { e.stopPropagation(); handleRename(tag.id) }} aria-label="儲存">
                  <Save size={12} />
                </IconButton>
                <IconButton size="xs" onClick={(e) => { e.stopPropagation(); setEditingId(null) }} aria-label="取消">
                  <X size={12} />
                </IconButton>
              </>
            ) : (
              <>
                <span>{tag.name}</span>
                <span className="text-text-muted">({tag.count || 0})</span>
                <IconButton size="xs" onClick={(e) => { e.stopPropagation(); setEditingId(tag.id); setEditName(tag.name) }} className="opacity-50 hover:opacity-100" aria-label="重新命名">
                  <Pencil size={10} />
                </IconButton>
                <IconButton size="xs" variant="danger-solid" onClick={(e) => { e.stopPropagation(); handleDelete(tag) }} className="opacity-50 hover:opacity-100" aria-label="刪除">
                  <Trash2 size={10} />
                </IconButton>
              </>
            )}
          </div>
        ))}
      </div>

      {tags.length === 0 && (
        <p className="text-sm text-text-muted text-center py-4">尚無標籤</p>
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
