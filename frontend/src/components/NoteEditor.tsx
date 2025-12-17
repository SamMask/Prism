import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { Modal, Button, toast } from './ui'
import { Note, api, Tag } from '../services/api'
import { useAppStore } from '../stores/appStore'
import { Save, X, Image, Tag as TagIcon, FolderOpen, Eye, Edit3, Sparkles, Loader2, Paperclip, FileText, Trash2, Plus } from 'lucide-react'
import { marked } from 'marked'

interface Attachment {
  id: number
  file_path: string
  file_type: string
  title: string
  size_bytes: number
  is_auto_extracted: boolean
  created_at: string
}

interface NoteEditorProps {
  note: Note | null
  onClose: () => void
}

export function NoteEditor({ note, onClose }: NoteEditorProps) {
  const { categories, fetchNotes } = useAppStore()

  // Form State
  const [title, setTitle] = useState(note?.title || '')
  const [content, setContent] = useState(note?.content || '')
  const [categoryId, setCategoryId] = useState<number | undefined>(note?.category_id)
  const [selectedTags, setSelectedTags] = useState<Tag[]>(note?.tags || [])
  const [remarks, setRemarks] = useState(note?.remarks || '')

  // UI State
  const [isPreview, setIsPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [tagInput, setTagInput] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  
  // AI State
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([])
  const [aiDescription, setAiDescription] = useState('')
  
  // Attachment State
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const attachmentInputRef = useRef<HTMLInputElement>(null)

  const isEditing = !!note

  // Render markdown to HTML for preview
  const renderedContent = useMemo(() => {
    if (!content) return ''
    try {
      // Configure marked for security
      marked.setOptions({
        breaks: true,  // Convert \n to <br>
        gfm: true,     // GitHub Flavored Markdown
      })
      return marked(content) as string
    } catch (e) {
      console.error('Markdown parse error:', e)
      return content
    }
  }, [content])

  // Separation threshold (sync with backend)
  const SEPARATION_THRESHOLD = 5000

  // Handle save
  const handleSave = async () => {
    if (!title.trim() && !content.trim()) {
      toast.warning('請輸入標題或內容')
      return
    }

    setIsSaving(true)
    try {
      const payload = {
        title: title.trim() || '無標題',
        content,
        category_id: categoryId,
        remarks,
        tags: selectedTags.map((t) => t.name),
      }

      let savedNoteId: number

      if (isEditing) {
        await api.updateNote(note.id, payload)
        savedNoteId = note.id
        toast.success('筆記已更新')
      } else {
        const result = await api.createNote(payload)
        savedNoteId = result.note_id
        toast.success('筆記已建立')
      }

      // Auto-separate for long content (no prompt)
      if (content.length > SEPARATION_THRESHOLD) {
        try {
          await api.separateContent(savedNoteId)
          // Silent success - no toast needed
        } catch (sepError) {
          console.error('Auto-separation failed:', sepError)
          // Silent failure - content is still saved in full
        }
      }

      fetchNotes(true)
      onClose()
    } catch (error) {
      console.error('Save failed:', error)
      toast.error('儲存失敗，請重試')
    } finally {
      setIsSaving(false)
    }
  }

  // Handle paste image
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (!file) continue

        try {
          toast.info('上傳圖片中...')
          const result = await api.uploadImage(file)
          const markdown = `![image](${result.url})`
          setContent((prev) => prev + '\n' + markdown)
          toast.success('圖片已上傳')
        } catch (error) {
          toast.error('圖片上傳失敗')
        }
      }
    }
  }, [])

  // Handle drag & drop image upload
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const imageFiles = files.filter((f) => f.type.startsWith('image/'))
    const mdFiles = files.filter((f) => 
      f.name.endsWith('.md') || f.name.endsWith('.txt') || f.name.endsWith('.markdown')
    )

    // Upload images
    for (const file of imageFiles) {
      try {
        toast.info('上傳圖片中...')
        const result = await api.uploadImage(file)
        const markdown = `![image](${result.url})`
        setContent((prev) => prev + '\n' + markdown)
        toast.success('圖片已上傳')
      } catch (error) {
        toast.error('圖片上傳失敗')
      }
    }

    // Upload .md files as attachments (only in editing mode)
    if (mdFiles.length > 0 && note?.id) {
      for (const file of mdFiles) {
        try {
          toast.info(`上傳 ${file.name}...`)
          const result = await api.uploadAttachment(note.id, file)
          setAttachments(prev => [...prev, {
            id: result.id,
            file_path: result.file_path,
            file_type: file.name.split('.').pop() || 'md',
            title: result.title,
            size_bytes: result.size_bytes,
            is_auto_extracted: false,
            created_at: new Date().toISOString()
          }])
          toast.success(`附件 "${result.title}" 已上傳`)
        } catch (error: any) {
          toast.error(error?.response?.data?.message || '附件上傳失敗')
        }
      }
    } else if (mdFiles.length > 0) {
      toast.warning('請先儲存筆記後再上傳附件')
    }
  }, [note?.id])

  // Handle tag input
  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault()
      const newTag = { id: Date.now(), name: tagInput.trim() }
      if (!selectedTags.find((t) => t.name.toLowerCase() === newTag.name.toLowerCase())) {
        setSelectedTags([...selectedTags, newTag])
      }
      setTagInput('')
    }
  }

  const removeTag = (tagId: number) => {
    setSelectedTags(selectedTags.filter((t) => t.id !== tagId))
  }

  // Add AI suggested tag
  const addAiTag = (tagName: string) => {
    if (!selectedTags.find((t) => t.name.toLowerCase() === tagName.toLowerCase())) {
      setSelectedTags([...selectedTags, { id: Date.now(), name: tagName }])
    }
    // Remove from suggestions
    setAiSuggestions(aiSuggestions.filter(t => t !== tagName))
  }

  // AI Analysis
  const handleAiAnalyze = async () => {
    // Extract images from content
    const imagePattern = /!\[.*?\]\((.*?)\)/g
    const images: string[] = []
    let match
    while ((match = imagePattern.exec(content)) !== null) {
      images.push(match[1])
    }

    if (images.length === 0 && content.length < 50) {
      toast.warning('請先加入圖片或輸入更多內容')
      return
    }

    setIsAnalyzing(true)
    setAiSuggestions([])
    setAiDescription('')

    try {
      // Check AI status first
      const status = await api.getAIStatus()
      
      if (!status.available) {
        toast.error('Ollama 服務未啟動，請先啟動 Ollama')
        return
      }

      if (images.length > 0 && !status.vision_ready) {
        toast.error('請先安裝視覺模型: ollama pull llava')
        return
      }

      // Analyze first image if available
      if (images.length > 0) {
        toast.info('✨ AI 正在分析圖片...')
        const result = await api.analyzeImageByPath(images[0], { language: 'zh' })
        
        if (result.tags && result.tags.length > 0) {
          setAiSuggestions(result.tags)
          setAiDescription(result.description || '')
          toast.success(`AI 找到 ${result.tags.length} 個建議標籤`)
        } else {
          toast.info('AI 未能識別足夠的特徵')
        }
      } else if (isEditing) {
        // Analyze existing note
        toast.info('✨ AI 正在分析筆記...')
        const result = await api.analyzeNote(note.id)
        
        if (result.suggested_tags && result.suggested_tags.length > 0) {
          setAiSuggestions(result.suggested_tags)
          if (result.summary) {
            setAiDescription(result.summary)
          }
          toast.success(`AI 找到 ${result.suggested_tags.length} 個建議標籤`)
        }
      }
    } catch (error: any) {
      console.error('AI analysis failed:', error)
      toast.error(error?.response?.data?.message || 'AI 分析失敗')
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Load attachments when editing (and auto-load separated content)
  const loadAttachments = useCallback(async () => {
    if (!note?.id) return
    
    try {
      const data = await api.getNoteAttachments(note.id)
      setAttachments(data)
      
      // Auto-load separated content into editor (no API call, just fetch content)
      const autoExtracted = data.find(a => a.is_auto_extracted)
      if (autoExtracted) {
        try {
          // Load content from attachment file directly
          const { content: fullContent } = await api.getAttachmentContent(autoExtracted.id)
          setContent(fullContent)
        } catch (error) {
          console.error('Failed to load attachment content:', error)
          toast.error('無法載入完整內容，目前顯示預覽')
        }
      }
    } catch (error) {
      console.error('Failed to load attachments:', error)
    }
  }, [note?.id])

  // Load attachments on mount for editing mode
  useEffect(() => {
    if (isEditing) {
      loadAttachments()
    }
  }, [isEditing, loadAttachments])

  // Handle attachment file selection
  const handleAttachmentSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0 || !note?.id) return

    for (const file of Array.from(files)) {
      try {
        toast.info(`上傳 ${file.name}...`)
        const result = await api.uploadAttachment(note.id, file)
        setAttachments(prev => [...prev, {
          id: result.id,
          file_path: result.file_path,
          file_type: file.name.split('.').pop() || 'md',
          title: result.title,
          size_bytes: result.size_bytes,
          is_auto_extracted: false,
          created_at: new Date().toISOString()
        }])
        toast.success(`附件 "${result.title}" 已上傳`)
      } catch (error: any) {
        toast.error(error?.response?.data?.message || '附件上傳失敗')
      }
    }
    
    // Reset input
    if (attachmentInputRef.current) {
      attachmentInputRef.current.value = ''
    }
  }

  // Handle delete attachment
  const handleDeleteAttachment = async (attachmentId: number) => {
    if (!confirm('確定要刪除此附件？')) return
    
    try {
      await api.deleteAttachment(attachmentId)
      setAttachments(prev => prev.filter(a => a.id !== attachmentId))
      toast.success('附件已刪除')
    } catch (error) {
      toast.error('刪除附件失敗')
    }
  }

  // Handle load attachment content (click to view)
  const handleLoadAttachment = async (attachmentId: number, isAutoExtracted: boolean) => {
    try {
      const { content: attachmentContent } = await api.getAttachmentContent(attachmentId)
      
      if (isAutoExtracted) {
        // For auto-extracted, load content to editor
        setContent(attachmentContent)
        toast.success('內容已載入')
      } else {
        // For regular attachments, open in new window
        const win = window.open('', '_blank')
        if (win) {
          win.document.write(`
            <html>
              <head>
                <title>附件內容</title>
                <style>
                  body { font-family: monospace; padding: 20px; background: #1a1a2e; color: #e0e0e0; }
                  pre { white-space: pre-wrap; word-wrap: break-word; }
                </style>
              </head>
              <body><pre>${attachmentContent}</pre></body>
            </html>
          `)
          win.document.close()
        }
      }
    } catch (error) {
      toast.error('讀取附件失敗')
    }
  }

  // Ctrl+S to save
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [title, content, categoryId, selectedTags, remarks])

  return (
    <Modal isOpen onClose={onClose} size="xl">
      <div className="flex flex-col h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
          <h2 className="text-lg font-semibold text-text-primary">
            {isEditing ? '編輯筆記' : '新增筆記'}
          </h2>
          <div className="flex items-center gap-2">
            {/* AI Analyze Button */}
            <button
              onClick={handleAiAnalyze}
              disabled={isAnalyzing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                         transition-all duration-200
                         ${isAnalyzing
                           ? 'bg-accent/20 text-accent cursor-wait'
                           : 'bg-accent/10 text-accent hover:bg-accent/20'
                         }`}
              title="AI 智慧分析"
            >
              {isAnalyzing ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Sparkles size={16} />
              )}
              {isAnalyzing ? '分析中...' : 'AI 分析'}
            </button>

            {/* Preview Toggle */}
            <button
              onClick={() => setIsPreview(!isPreview)}
              className={`p-2 rounded-lg transition-colors ${
                isPreview
                  ? 'bg-primary text-white'
                  : 'text-text-muted hover:bg-bg-hover'
              }`}
              title={isPreview ? '編輯模式' : '預覽模式'}
            >
              {isPreview ? <Edit3 size={18} /> : <Eye size={18} />}
            </button>

            {/* Save Button */}
            <Button onClick={handleSave} variant="primary" disabled={isSaving}>
              <Save size={16} />
              {isSaving ? '儲存中...' : '儲存'}
            </Button>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-text-muted hover:bg-bg-hover"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Editor Area */}
          <div 
            className={`flex-1 flex flex-col p-6 overflow-auto relative
                        ${isDragging ? 'ring-2 ring-primary ring-inset bg-primary/5' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {/* Drag Overlay */}
            {isDragging && (
              <div className="absolute inset-0 flex items-center justify-center bg-bg-surface/80 z-10">
                <div className="text-center">
                  <Image size={48} className="mx-auto text-primary mb-2" />
                  <p className="text-text-primary font-medium">拖放圖片至此上傳</p>
                </div>
              </div>
            )}

            {/* Title */}
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="標題"
              className="text-xl font-semibold bg-transparent border-none outline-none
                         text-text-primary placeholder-text-muted mb-4"
            />

            {/* Content */}
            {isPreview ? (
              <div
                className="flex-1 prose prose-invert max-w-none
                           text-text-primary prose-headings:text-text-primary
                           prose-a:text-primary prose-strong:text-text-primary
                           prose-code:bg-bg-elevated prose-code:px-1 prose-code:rounded
                           prose-img:rounded-lg prose-img:max-h-96"
                dangerouslySetInnerHTML={{ __html: renderedContent }}
              />
            ) : (
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onPaste={handlePaste}
                placeholder="開始輸入內容... (支援 Markdown，可直接貼上或拖曳圖片)"
                className="flex-1 bg-transparent border-none outline-none resize-none
                           text-text-primary placeholder-text-muted
                           font-mono text-sm leading-relaxed"
              />
            )}
          </div>

          {/* Sidebar */}
          <div className="w-72 border-l border-border-subtle p-4 space-y-4 overflow-auto">
            {/* AI Suggestions */}
            {(aiSuggestions.length > 0 || aiDescription) && (
              <div className="p-3 rounded-lg bg-accent/5 border border-accent/20">
                <h4 className="flex items-center gap-2 text-sm font-medium text-accent mb-2">
                  <Sparkles size={14} />
                  AI 建議
                </h4>
                
                {aiDescription && (
                  <p className="text-xs text-text-secondary mb-2 leading-relaxed">
                    {aiDescription}
                  </p>
                )}
                
                {aiSuggestions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {aiSuggestions.map((tag, i) => (
                      <button
                        key={i}
                        onClick={() => addAiTag(tag)}
                        className="px-2 py-0.5 text-xs rounded-full
                                   bg-accent/10 text-accent
                                   hover:bg-accent/20 transition-colors"
                        title="點擊添加此標籤"
                      >
                        + {tag}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Category */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                <FolderOpen size={14} /> 分類
              </label>
              <select
                value={categoryId || ''}
                onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-3 py-2 rounded-lg
                           bg-bg-elevated border border-border-default
                           text-text-primary text-sm
                           focus:outline-none focus:border-primary"
              >
                <option value="">選擇分類</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.icon} {cat.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Tags */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                <TagIcon size={14} /> 標籤
              </label>
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                placeholder="輸入標籤後按 Enter"
                className="w-full px-3 py-2 rounded-lg
                           bg-bg-elevated border border-border-default
                           text-text-primary text-sm
                           focus:outline-none focus:border-primary"
              />
              {selectedTags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {selectedTags.map((tag) => (
                    <span
                      key={tag.id}
                      className="inline-flex items-center gap-1 px-2 py-0.5
                                 text-xs rounded-full
                                 bg-primary/10 text-primary-light"
                    >
                      {tag.name}
                      <button
                        onClick={() => removeTag(tag.id)}
                        className="hover:text-danger"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Remarks */}
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                備註
              </label>
              <textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="簡短備註..."
                rows={3}
                className="w-full px-3 py-2 rounded-lg
                           bg-bg-elevated border border-border-default
                           text-text-primary text-sm resize-none
                           focus:outline-none focus:border-primary"
              />
            </div>

            {/* Attachments (Phase 3.4) */}
            {isEditing && (
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                  <Paperclip size={14} /> 附件
                  {attachments.length > 0 && (
                    <span className="text-xs bg-bg-elevated px-1.5 py-0.5 rounded">
                      {attachments.length}
                    </span>
                  )}
                </label>
                
                {/* Attachment List */}
                {attachments.length > 0 && (
                  <div className="space-y-1.5 mb-2">
                    {attachments.map((att) => (
                      <div
                        key={att.id}
                        className={`flex items-center gap-2 px-2 py-1.5 rounded-lg
                                   bg-bg-elevated text-text-secondary text-xs
                                   hover:bg-bg-hover group cursor-pointer
                                   ${att.is_auto_extracted ? 'border-l-2 border-primary' : ''}`}
                        onClick={() => handleLoadAttachment(att.id, att.is_auto_extracted)}
                        title={att.is_auto_extracted ? '點擊還原完整內容' : '點擊查看附件'}
                      >
                        <FileText size={14} className={`flex-shrink-0 ${att.is_auto_extracted ? 'text-accent' : 'text-primary'}`} />
                        <span className="truncate flex-1" title={att.title}>
                          {att.title}
                          {att.is_auto_extracted && <span className="text-accent ml-1">(完整內容)</span>}
                        </span>
                        <span className="text-text-muted">
                          {(att.size_bytes / 1024).toFixed(0)}KB
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation() // Prevent opening file
                            handleDeleteAttachment(att.id)
                          }}
                          className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-danger
                                     transition-opacity"
                          title="刪除附件"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Upload Button */}
                <input
                  ref={attachmentInputRef}
                  type="file"
                  accept=".md,.txt,.markdown"
                  onChange={handleAttachmentSelect}
                  className="hidden"
                />
                <button
                  onClick={() => attachmentInputRef.current?.click()}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2
                             rounded-lg border border-dashed border-border-default
                             text-text-muted text-sm
                             hover:border-primary hover:text-primary
                             transition-colors"
                >
                  <Plus size={14} />
                  新增 .md 附件
                </button>
                <p className="text-xs text-text-muted mt-1.5">
                  支援拖曳 .md 檔案到編輯區
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </Modal>
  )
}
