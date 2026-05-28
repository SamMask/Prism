import { useEffect } from 'react'
import { Modal } from './ui'
import { Note } from '../services/api'
import { Image, X, History, RotateCcw } from 'lucide-react'
import { EditorToolbar } from './editor/EditorToolbar'
import { EditorSidebar } from './editor/EditorSidebar'
import { EditablePreview } from './editor/EditablePreview'

import { useNoteForm } from '../hooks/editor/useNoteForm'
import { usePasteHandler } from '../hooks/editor/usePasteHandler'
import { useDragDrop } from '../hooks/editor/useDragDrop'
import { useNoteAttachments } from '../hooks/editor/useNoteAttachments'
import { useNoteHistory } from '../hooks/editor/useNoteHistory'
import { usePromptExtraction } from '../hooks/editor/usePromptExtraction'

interface NoteEditorProps {
  note: Note | null
  onClose: () => void
  initialPreview?: boolean
}

export function NoteEditor({ note, onClose, initialPreview = false }: NoteEditorProps) {
  const form = useNoteForm(note, onClose, initialPreview)
  const { handlePaste } = usePasteHandler(form.setContent)
  const { hasAIPrompt, isCheckingPrompt, handleCopyPrompt } = usePromptExtraction(form.content)
  const history = useNoteHistory(note, form.setContent)
  const attachments = useNoteAttachments(note, form.setContent, form.updateOriginalContent)
  const drag = useDragDrop(note?.id, form.setContent, attachments.setAttachments)

  // Load attachments on mount (editing mode only)
  useEffect(() => {
    if (form.isEditing) attachments.loadAttachments()
  }, [form.isEditing, attachments.loadAttachments])

  // Extract images from content for dual-layout gallery
  const galleryImages = (() => {
    const pattern = /!\[.*?\]\((\/static\/uploads\/[^)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/g
    const images: string[] = []
    let m
    while ((m = pattern.exec(form.content || '')) !== null) images.push(m[1] || m[2])
    return images
  })()

  return (
    <>
      <Modal isOpen onClose={form.handleClose} size="full">
        <div className="flex h-[min(86vh,920px)] flex-col overflow-hidden" data-testid="note-editor">

          {/* Toolbar */}
          <EditorToolbar
            isEditing={form.isEditing}
            hasAIPrompt={hasAIPrompt}
            isCheckingPrompt={isCheckingPrompt}
            onCopyPrompt={handleCopyPrompt}
            isLoadingHistory={history.isLoadingHistory}
            onLoadHistory={history.loadHistory}
            isPreview={form.isPreview}
            onTogglePreview={() => form.setIsPreview(!form.isPreview)}
            isSaving={form.isSaving}
            onSave={form.handleSave}
            onClose={form.handleClose}
          />

          {/* Body */}
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">

            {/* Dual-mode image gallery */}
            {form.editorLayout === 'dual' && (
              <div className="hidden w-56 flex-shrink-0 overflow-auto border-r border-border-subtle bg-bg-elevated/30 p-3 lg:block">
                <h4 className="text-sm font-medium text-text-secondary mb-3 flex items-center gap-2">
                  <Image size={14} />
                  圖片預覽
                </h4>
                {galleryImages.length === 0 ? (
                  <div className="text-center text-text-muted text-sm py-8">
                    <Image size={32} className="mx-auto mb-2 opacity-30" />
                    <p>尚無圖片</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {galleryImages.map((src, idx) => (
                      <div key={idx} className="relative group">
                        <img
                          src={src}
                          alt={`圖片 ${idx + 1}`}
                          className="w-full rounded-lg border border-border-subtle cursor-pointer hover:border-primary transition-colors"
                          onClick={() => window.open(src, '_blank')}
                        />
                        <span className="absolute top-2 left-2 bg-black/50 text-white text-xs px-2 py-0.5 rounded">
                          {idx + 1}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Editor / Preview area */}
            <div
              ref={drag.dropZoneRef}
              className={`relative flex min-h-0 flex-1 flex-col overflow-auto px-4 py-5 lg:px-7 lg:py-6 ${
                drag.isDragging ? 'ring-2 ring-primary ring-inset bg-primary/5' : ''
              }`}
              onDragEnter={drag.handleDragEnter}
              onDragOver={drag.handleDragOver}
              onDragLeave={drag.handleDragLeave}
              onDrop={drag.handleDrop}
            >
              {drag.isDragging && (
                <div className="absolute inset-0 flex items-center justify-center bg-bg-surface/80 z-10 pointer-events-none">
                  <div className="text-center">
                    <Image size={48} className="mx-auto text-primary mb-2" />
                    <p className="text-text-primary font-medium">拖放圖片或 .md 檔案至此上傳</p>
                  </div>
                </div>
              )}

              <input
                type="text"
                value={form.title}
                onChange={(e) => form.setTitle(e.target.value)}
                placeholder="標題"
                autoFocus
                className="mb-4 w-full bg-transparent text-2xl font-semibold leading-tight text-text-primary placeholder-text-muted outline-none"
              />

              {form.isPreview ? (
                <div
                  className="min-h-0 flex-1 prose prose-invert max-w-none
                    text-text-primary prose-headings:text-text-primary
                    prose-a:text-primary prose-strong:text-text-primary
                    prose-code:bg-bg-elevated prose-code:px-1 prose-code:rounded
                    prose-img:rounded-lg prose-img:max-h-96"
                >
                  <EditablePreview
                    content={form.content}
                    coverImage={form.coverImage}
                    onContentChange={form.setContent}
                    onSetCover={(url) => form.setCoverImage(url || undefined)}
                  />
                </div>
              ) : (
                <textarea
                  ref={form.textareaRef}
                  value={form.content}
                  onChange={(e) => form.setContent(e.target.value)}
                  onPaste={handlePaste}
                  placeholder="開始輸入內容... (支援 Markdown，可直接貼上或拖曳圖片，Ctrl+B 粗體、Ctrl+I 斜體)"
                  className="min-h-[26rem] flex-1 resize-none border-none bg-transparent font-mono text-sm leading-relaxed text-text-primary outline-none placeholder-text-muted"
                />
              )}
            </div>

            {/* Sidebar */}
            <EditorSidebar
              categoryId={form.categoryId}
              onChangeCategory={form.setCategoryId}
              tagInput={form.tagInput}
              onTagInputChange={form.setTagInput}
              onTagInputKeyDown={form.handleTagKeyDown}
              selectedTags={form.selectedTags}
              onRemoveTag={form.removeTag}
              sourceUrls={form.sourceUrls}
              urlInput={form.urlInput}
              onUrlInputChange={form.setUrlInput}
              onUrlInputKeyDown={(e) => {
                if (e.key === 'Enter' && form.urlInput.trim()) {
                  e.preventDefault()
                  let url = form.urlInput.trim()
                  if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'https://' + url
                  if (!form.sourceUrls.includes(url)) form.setSourceUrls([...form.sourceUrls, url])
                  form.setUrlInput('')
                }
              }}
              onUrlInputBlur={() => {
                if (form.urlInput.trim()) {
                  let url = form.urlInput.trim()
                  if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'https://' + url
                  if (!form.sourceUrls.includes(url)) form.setSourceUrls([...form.sourceUrls, url])
                  form.setUrlInput('')
                }
              }}
              onRemoveUrl={(idx) => form.setSourceUrls(form.sourceUrls.filter((_, i) => i !== idx))}
              remarks={form.remarks}
              onChangeRemarks={form.setRemarks}
              coverPosition={form.coverPosition}
              onChangeCoverPosition={form.setCoverPosition}
              editorLayout={form.editorLayout}
              onChangeEditorLayout={form.setEditorLayout}
              isEditing={form.isEditing}
              attachments={attachments.attachments}
              onLoadAttachment={attachments.handleLoadAttachment}
              onDeleteAttachment={attachments.handleDeleteAttachment}
              onUploadAttachment={attachments.handleAttachmentSelect}
              content={form.content}
              coverImage={form.coverImage}
              onSetCover={(url) => form.setCoverImage(url || undefined)}
              onContentChange={form.setContent}
            />
          </div>
        </div>
      </Modal>

      {/* History modal */}
      {history.showHistory && (
        <Modal isOpen onClose={() => history.setShowHistory(false)} size="md">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                <History size={20} className="text-warning" />
                歷史版本
              </h3>
              <button
                onClick={() => history.setShowHistory(false)}
                className="p-2 rounded-lg text-text-muted hover:bg-bg-hover"
              >
                <X size={18} />
              </button>
            </div>

            {history.historyVersions.length === 0 ? (
              <p className="text-text-muted text-center py-8">沒有歷史版本記錄</p>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {history.historyVersions.map((version) => (
                  <div key={version.id} className="p-4 rounded-lg bg-bg-elevated border border-border-subtle">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-text-primary">{version.diff_summary || '內容變更'}</p>
                        <p className="text-xs text-text-muted mt-1">
                          {new Date(version.created_at).toLocaleString('zh-TW')}
                        </p>
                      </div>
                      <button
                        onClick={() => history.restoreVersion(version.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                      >
                        <RotateCcw size={14} />
                        還原
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Modal>
      )}
    </>
  )
}
