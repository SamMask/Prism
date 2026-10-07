import { useRef, useState } from 'react'
import { MoreHorizontal, FolderInput, Tags, Download } from 'lucide-react'
import { useAppStore } from '../stores/appStore'
import { api } from '../services/api'
import { Button, Input, Modal } from './ui'
import { toast } from './ui/Toast'
import { useTranslation } from '../hooks/useTranslation'
import { getCategoryOptionLabel } from '../utils/categoryDisplay'

type Dialog = 'category' | 'tags' | null

// Splits on ASCII and CJK separators, drops blanks and repeats.
const parseTags = (raw: string) =>
  Array.from(new Set(raw.split(/[,，、\n]/).map((tag) => tag.trim()).filter(Boolean)))

// "More" menu of the multi-select toolbar: batch category, batch tags, export selected.
export function SelectionActions() {
  const { t } = useTranslation()
  const { selectedNoteIds, categories, tags, clearSelection, refreshLoadedNotes, fetchCategories, fetchTags } = useAppStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const [dialog, setDialog] = useState<Dialog>(null)
  const [busy, setBusy] = useState(false)
  const [categoryId, setCategoryId] = useState('')
  const [tagText, setTagText] = useState('')
  const [tagMode, setTagMode] = useState<'append' | 'replace'>('append')
  const menuRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  const closeMenu = () => {
    setMenuOpen(false)
    if (menuRef.current?.contains(document.activeElement)) buttonRef.current?.focus()
  }

  const openDialog = (next: Exclude<Dialog, null>) => {
    setMenuOpen(false)
    setCategoryId('')
    setTagText('')
    setTagMode('append')
    setDialog(next)
  }

  // After a batch write: leave selection mode, re-read the loaded pages in place, refresh sidebar counts.
  const finish = () => {
    setDialog(null)
    clearSelection()
    void refreshLoadedNotes()
    void fetchCategories()
    void fetchTags()
  }

  const applyCategory = async () => {
    if (!categoryId) return
    setBusy(true)
    try {
      const result = await api.batchUpdateCategory(selectedNoteIds, Number(categoryId))
      toast.success(t('header.batchCategorySuccess', { count: result.updated_count }))
      finish()
    } catch {
      toast.error(t('header.batchCategoryFailed'))
    } finally {
      setBusy(false)
    }
  }

  const applyTags = async () => {
    const names = parseTags(tagText)
    if (names.length === 0) return
    setBusy(true)
    try {
      const result = await api.batchUpdateTags(selectedNoteIds, names, tagMode)
      toast.success(t('header.batchTagsSuccess', { count: result.affected_notes }))
      finish()
    } catch {
      toast.error(t('header.batchTagsFailed'))
    } finally {
      setBusy(false)
    }
  }

  const exportSelected = async () => {
    setMenuOpen(false)
    try {
      await api.exportNotesBatch(selectedNoteIds)
      toast.success(t('header.exportSelectedSuccess', { count: selectedNoteIds.length }))
    } catch {
      toast.error(t('header.exportSelectedFailed'))
    }
  }

  const itemClass = 'flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary'

  return (
    <>
      <div className="relative shrink-0" ref={menuRef}>
        <button
          ref={buttonRef}
          type="button"
          className="rounded-lg p-2 text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={t('header.moreActions')}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          data-testid="selection-more-menu"
        >
          <MoreHorizontal size={20} />
        </button>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div
              role="menu"
              aria-label={t('header.moreActions')}
              onKeyDown={(e) => { if (e.key === 'Escape') closeMenu() }}
              className="fixed right-3 top-[68px] z-20 w-60 max-w-[calc(100vw-1.5rem)] rounded-lg border border-border-default bg-bg-surface py-1 shadow-xl sm:absolute sm:right-0 sm:top-full sm:mt-2"
            >
              <button role="menuitem" autoFocus className={itemClass} onClick={() => openDialog('category')} data-testid="selection-change-category">
                <FolderInput size={16} />{t('header.changeCategory')}
              </button>
              <button role="menuitem" className={itemClass} onClick={() => openDialog('tags')} data-testid="selection-edit-tags">
                <Tags size={16} />{t('header.editTags')}
              </button>
              <button role="menuitem" className={itemClass} onClick={exportSelected} data-testid="selection-export">
                <Download size={16} />{t('header.exportSelected')}
              </button>
            </div>
          </>
        )}
      </div>

      <Modal isOpen={dialog === 'category'} onClose={() => setDialog(null)} title={t('header.batchCategoryTitle', { count: selectedNoteIds.length })} size="sm">
        <div className="space-y-4 p-6">
          <label className="block space-y-1.5">
            <span className="block text-sm font-medium text-text-secondary">{t('header.batchCategoryLabel')}</span>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              data-testid="batch-category-select"
              className="w-full rounded-lg border border-border-default bg-bg-elevated px-3 py-2.5 text-text-primary focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/50"
            >
              <option value="">{t('header.batchCategoryPlaceholder')}</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>{getCategoryOptionLabel(category, t)}</option>
              ))}
            </select>
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDialog(null)}>{t('common.cancel')}</Button>
            <Button onClick={applyCategory} disabled={!categoryId || busy} data-testid="batch-category-apply">{t('header.batchApply')}</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={dialog === 'tags'} onClose={() => setDialog(null)} title={t('header.batchTagsTitle', { count: selectedNoteIds.length })} size="sm">
        <form
          className="space-y-4 p-6"
          onSubmit={(e) => { e.preventDefault(); void applyTags() }}
        >
          <Input
            id="batch-tags-input"
            label={t('header.batchTagsLabel')}
            value={tagText}
            onChange={(e) => setTagText(e.target.value)}
            placeholder={t('header.batchTagsPlaceholder')}
            list="batch-tags-suggestions"
            data-testid="batch-tags-input"
          />
          <datalist id="batch-tags-suggestions">
            {tags.map((tag) => <option key={tag.id} value={tag.name} />)}
          </datalist>
          <fieldset className="space-y-2 text-sm text-text-secondary">
            <label className="flex items-center gap-2">
              <input type="radio" name="batch-tag-mode" checked={tagMode === 'append'} onChange={() => setTagMode('append')} data-testid="batch-tags-mode-append" />
              {t('header.batchTagsAppend')}
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="batch-tag-mode" checked={tagMode === 'replace'} onChange={() => setTagMode('replace')} data-testid="batch-tags-mode-replace" />
              {t('header.batchTagsReplace')}
            </label>
            {tagMode === 'replace' && <p className="text-xs text-warning">{t('header.batchTagsReplaceHint')}</p>}
          </fieldset>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setDialog(null)}>{t('common.cancel')}</Button>
            <Button type="submit" disabled={parseTags(tagText).length === 0 || busy} data-testid="batch-tags-apply">{t('header.batchApply')}</Button>
          </div>
        </form>
      </Modal>
    </>
  )
}
