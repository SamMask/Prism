import { useState, useEffect, useRef } from 'react'
import { Moon, Sun, Database, Info, RefreshCw, Trash2, Sparkles, Check, AlertCircle, Loader2, Search, Zap, Image, Download, Upload, FolderOpen } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { toast, ToastContainer } from '../components/ui/Toast'
import { api } from '../services/api'
import { BatchAITagging } from '../components/BatchAITagging'
import { DataManager } from '../components/DataManager'
import { SystemMaintenance } from '../components/SystemMaintenance'
import { useAppStore } from '../stores/appStore'

interface SystemStats {
  notes_count: number
  categories_count: number
  tags_count: number
  images_count: number
  total_size_mb: number
}

interface AIStatus {
  available: boolean
  models: string[]
  vision_ready: boolean
  text_ready: boolean
  error?: string
}

interface SearchStatus {
  available: boolean
  model_name: string
  dimensions: number
  model_loaded: boolean
  total_notes: number
  indexed_notes: number
  index_coverage: string
}

interface OrphanImage {
  filename: string
  size: number
  path: string
}

export function SettingsPage() {
  const { categories } = useAppStore()
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null)
  const [searchStatus, setSearchStatus] = useState<SearchStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isCheckingAI, setIsCheckingAI] = useState(false)
  const [isCheckingSearch, setIsCheckingSearch] = useState(false)
  const [isRebuilding, setIsRebuilding] = useState(false)
  
  // AI Model Selection
  const [selectedVisionModel, setSelectedVisionModel] = useState<string>('')
  const [selectedTextModel, setSelectedTextModel] = useState<string>('')
  
  // Orphan Image Cleanup
  const [orphanImages, setOrphanImages] = useState<OrphanImage[]>([])
  const [orphanTotalSize, setOrphanTotalSize] = useState(0)
  const [isScanning, setIsScanning] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  
  // Original Image Cleanup
  const [originalStats, setOriginalStats] = useState<{count: number, size: number} | null>(null)
  const [isScanningOriginals, setIsScanningOriginals] = useState(false)
  const [isDeletingOriginals, setIsDeletingOriginals] = useState(false)
  
  // Broken Image Paths
  const [brokenPaths, setBrokenPaths] = useState<{total: number, fixable: number} | null>(null)
  const [isScanningBroken, setIsScanningBroken] = useState(false)
  const [isFixingBroken, setIsFixingBroken] = useState(false)

  // Import State
  const [isImporting, setIsImporting] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [importData, setImportData] = useState<unknown>(null)
  const [importMode, setImportMode] = useState<'skip' | 'duplicate'>('skip')
  const fileInputRef = useRef<HTMLInputElement>(null)


  // Load theme preference
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'dark' | 'light' | null
    if (savedTheme) {
      setTheme(savedTheme)
    }
    
    // Load saved AI model preferences
    const savedVisionModel = localStorage.getItem('ai_vision_model')
    const savedTextModel = localStorage.getItem('ai_text_model')
    if (savedVisionModel) setSelectedVisionModel(savedVisionModel)
    if (savedTextModel) setSelectedTextModel(savedTextModel)
  }, [])
  
  // Auto-select default models when AI status is loaded
  useEffect(() => {
    if (aiStatus?.available && aiStatus.models.length > 0) {
      // Set default vision model if not already set
      if (!selectedVisionModel) {
        const visionModels = aiStatus.models.filter(m => 
          m.includes('llava') || m.includes('bakllava') || m.includes('moondream')
        )
        if (visionModels.length > 0) {
          setSelectedVisionModel(visionModels[0])
          localStorage.setItem('ai_vision_model', visionModels[0])
        }
      }
      
      // Set default text model if not already set
      if (!selectedTextModel) {
        const textModels = aiStatus.models.filter(m => 
          !m.includes('llava') && !m.includes('bakllava')
        )
        if (textModels.length > 0) {
          setSelectedTextModel(textModels[0])
          localStorage.setItem('ai_text_model', textModels[0])
        }
      }
    }
  }, [aiStatus, selectedVisionModel, selectedTextModel])

  // Fetch system stats
  const fetchStats = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/test')
      const data = await response.json()
      if (data.status === 'ok') {
        setStats({
          notes_count: data.stats?.notes_count || 0,
          categories_count: data.stats?.categories_count || 0,
          tags_count: data.stats?.tags_count || 0,
          images_count: 0,
          total_size_mb: 0,
        })
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch AI status
  const fetchAIStatus = async () => {
    setIsCheckingAI(true)
    try {
      const status = await api.getAIStatus()
      setAiStatus(status)
    } catch (error: any) {
      setAiStatus({
        available: false,
        models: [],
        vision_ready: false,
        text_ready: false,
        error: error?.message || 'Failed to connect to AI service'
      })
    } finally {
      setIsCheckingAI(false)
    }
  }

  // Fetch Search status
  const fetchSearchStatus = async () => {
    setIsCheckingSearch(true)
    try {
      const status = await api.getSearchStatus()
      setSearchStatus(status)
    } catch (error: any) {
      setSearchStatus(null)
    } finally {
      setIsCheckingSearch(false)
    }
  }

  // Rebuild search index
  const handleRebuildIndex = async () => {
    setIsRebuilding(true)
    toast.info('正在重建搜尋索引...')
    try {
      const result = await api.rebuildSearchIndex()
      toast.success(`索引完成！成功 ${result.success} 筆，失敗 ${result.failed} 筆`)
      fetchSearchStatus()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '重建索引失敗')
    } finally {
      setIsRebuilding(false)
    }
  }

  // Scan for orphan images
  const scanOrphanImages = async () => {
    setIsScanning(true)
    try {
      const result = await api.getOrphanImages()
      setOrphanImages(result.orphan_images)
      setOrphanTotalSize(result.total_size_mb)
      if (result.total_count === 0) {
        toast.success('沒有發現孤兒圖片！')
      } else {
        toast.info(`發現 ${result.total_count} 張孤兒圖片，共 ${result.total_size_mb} MB`)
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '掃描失敗')
    } finally {
      setIsScanning(false)
    }
  }

  // Delete all orphan images
  const deleteAllOrphanImages = async () => {
    if (orphanImages.length === 0) {
      toast.warning('請先掃描孤兒圖片')
      return
    }

    if (!confirm(`確定要刪除 ${orphanImages.length} 張孤兒圖片嗎？此操作無法復原！`)) {
      return
    }

    setIsDeleting(true)
    try {
      const filenames = orphanImages.map(img => img.filename)
      const result = await api.deleteOrphanImages(filenames)
      toast.success(`已刪除 ${result.deleted_count} 張圖片`)
      // Reset state
      setOrphanImages([])
      setOrphanTotalSize(0)
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '刪除失敗')
    } finally {
      setIsDeleting(false)
    }
  }

  // Scan for original images (that have thumbnails)
  const scanOriginalImages = async () => {
    setIsScanningOriginals(true)
    try {
      const result = await api.getOriginalImages()
      setOriginalStats({ count: result.original_count, size: result.original_size_mb })
      if (result.original_count === 0) {
        toast.success('沒有發現可刪除的原圖！')
      } else {
        toast.info(`發現 ${result.original_count} 張原圖，共 ${result.original_size_mb} MB`)
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '掃描失敗')
    } finally {
      setIsScanningOriginals(false)
    }
  }

  // Delete all original images
  const deleteAllOriginals = async () => {
    if (!originalStats || originalStats.count === 0) {
      toast.warning('請先掃描原圖')
      return
    }

    if (!confirm(`確定要刪除 ${originalStats.count} 張原圖嗎？\n\n筆記中的圖片路徑會自動替換為縮圖路徑。此操作無法復原！`)) {
      return
    }

    setIsDeletingOriginals(true)
    try {
      const result = await api.deleteOriginalImages()
      toast.success(`已刪除 ${result.deleted_count} 張原圖，節省 ${result.saved_mb} MB`)
      setOriginalStats(null)
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '刪除失敗')
    } finally {
      setIsDeletingOriginals(false)
    }
  }

  // Scan for broken image paths
  const scanBrokenPaths = async () => {
    setIsScanningBroken(true)
    try {
      const result = await api.getBrokenImages()
      setBrokenPaths({ total: result.total_count, fixable: result.fixable_count })
      if (result.total_count === 0) {
        toast.success('沒有發現失效的圖片路徑！')
      } else {
        toast.info(`發現 ${result.total_count} 個失效路徑，其中 ${result.fixable_count} 個可修復`)
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '掃描失敗')
    } finally {
      setIsScanningBroken(false)
    }
  }

  // Fix broken image paths
  const fixAllBrokenPaths = async () => {
    if (!brokenPaths || brokenPaths.fixable === 0) {
      toast.warning('沒有可修復的失效路徑')
      return
    }

    setIsFixingBroken(true)
    try {
      const result = await api.fixBrokenImages()
      toast.success(`已修復 ${result.fixed_count} 個路徑，更新 ${result.updated_notes} 筆筆記`)
      setBrokenPaths(null)
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '修復失敗')
    } finally {
      setIsFixingBroken(false)
    }
  }

  useEffect(() => {
    fetchStats()
    fetchAIStatus()
    fetchSearchStatus()
  }, [])

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    document.documentElement.classList.toggle('light', newTheme === 'light')
    toast.success(`已切換至${newTheme === 'dark' ? '深色' : '淺色'}主題`)
  }

  // Handle file selection for import
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.json')) {
      toast.error('請選擇 JSON 檔案')
      return
    }

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string)
        if (!data.notes || !Array.isArray(data.notes)) {
          toast.error('無效的匯入檔案格式')
          return
        }
        setImportData(data)
        setShowImportModal(true)
      } catch {
        toast.error('解析 JSON 檔案失敗')
      }
    }
    reader.readAsText(file)
    
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Handle import
  const handleImport = async () => {
    if (!importData) return

    setIsImporting(true)
    try {
      const result = await api.importJSON(importData, importMode)
      
      if (result.skipped > 0 && importMode === 'skip') {
        toast.success(
          `匯入完成：新增 ${result.imported} 筆，略過 ${result.skipped} 筆重複`
        )
      } else {
        toast.success(`成功匯入 ${result.imported} 筆筆記`)
      }
      
      setShowImportModal(false)
      setImportData(null)
      
      // Refresh stats
      fetchStats()
    } catch (error) {
      toast.error('匯入失敗')
    } finally {
      setIsImporting(false)
    }
  }

  return (
    <>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="glass rounded-xl p-6">
          <h1 className="text-2xl font-bold gradient-text mb-2">設定</h1>
          <p className="text-text-secondary">
            管理應用程式偏好設定與資料
          </p>
        </div>

        {/* Category & Tag Management */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <FolderOpen size={20} className="text-primary" />
            分類與標籤管理
          </h2>
          <DataManager />
        </div>

        {/* System Maintenance */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Database size={20} className="text-warning" />
            資料庫維護
          </h2>
          <SystemMaintenance />
        </div>

        {/* AI Status (Phase 3) */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Sparkles size={20} className="text-accent" />
            AI 服務狀態
          </h2>
          
          {isCheckingAI ? (
            <div className="flex items-center gap-2 text-text-muted">
              <Loader2 size={18} className="animate-spin" />
              正在檢查 Ollama 服務...
            </div>
          ) : aiStatus ? (
            <div className="space-y-4">
              {/* Connection Status */}
              <div className="flex items-center gap-3">
                {aiStatus.available ? (
                  <span className="flex items-center gap-2 text-success">
                    <Check size={18} />
                    Ollama 已連線
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-error">
                    <AlertCircle size={18} />
                    Ollama 未連線
                  </span>
                )}
              </div>

              {/* Model Status Row */}
              <div className="flex flex-wrap gap-4">
                <div className="flex items-center gap-2">
                  {aiStatus.vision_ready ? (
                    <span className="flex items-center gap-1.5 text-success text-sm">
                      <Check size={16} />
                      視覺模型
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-warning text-sm">
                      <AlertCircle size={16} />
                      視覺模型未安裝
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {aiStatus.text_ready ? (
                    <span className="flex items-center gap-1.5 text-success text-sm">
                      <Check size={16} />
                      文字模型
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-warning text-sm">
                      <AlertCircle size={16} />
                      文字模型未安裝
                    </span>
                  )}
                </div>
              </div>

              {/* Model List & Selection */}
              {aiStatus.available && aiStatus.models.length > 0 && (
                <div className="space-y-3 pt-3 border-t border-border-subtle">
                  {/* Installed Models */}
                  <div>
                    <p className="text-text-secondary text-sm mb-2">已安裝模型：</p>
                    <div className="flex flex-wrap gap-2">
                      {aiStatus.models.map((model) => (
                        <span
                          key={model}
                          className={`px-2.5 py-1 text-xs rounded-full
                            ${model.includes('llava') || model.includes('bakllava')
                              ? 'bg-accent/10 text-accent border border-accent/30'
                              : 'bg-primary/10 text-primary border border-primary/30'
                            }`}
                        >
                          {model}
                          {(model.includes('llava') || model.includes('bakllava')) && (
                            <span className="ml-1 opacity-60">👁️</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Model Selectors */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Vision Model Selector */}
                    <div>
                      <label className="text-text-secondary text-sm mb-1.5 block">
                        圖片分析模型 (Vision)
                      </label>
                      <select
                        value={selectedVisionModel}
                        onChange={(e) => {
                          setSelectedVisionModel(e.target.value)
                          localStorage.setItem('ai_vision_model', e.target.value)
                          toast.success(`視覺模型已設定為 ${e.target.value}`)
                        }}
                        className="w-full px-3 py-2 rounded-lg
                                   bg-bg-elevated border border-border-default
                                   text-text-primary text-sm
                                   focus:outline-none focus:border-primary"
                      >
                        {aiStatus.models
                          .filter(m => m.includes('llava') || m.includes('bakllava') || m.includes('moondream'))
                          .map((model) => (
                            <option key={model} value={model}>
                              {model}
                            </option>
                          ))}
                        {!aiStatus.models.some(m => m.includes('llava') || m.includes('bakllava') || m.includes('moondream')) && (
                          <option value="" disabled>無可用視覺模型</option>
                        )}
                      </select>
                    </div>

                    {/* Text Model Selector */}
                    <div>
                      <label className="text-text-secondary text-sm mb-1.5 block">
                        文字摘要模型 (Text)
                      </label>
                      <select
                        value={selectedTextModel}
                        onChange={(e) => {
                          setSelectedTextModel(e.target.value)
                          localStorage.setItem('ai_text_model', e.target.value)
                          toast.success(`文字模型已設定為 ${e.target.value}`)
                        }}
                        className="w-full px-3 py-2 rounded-lg
                                   bg-bg-elevated border border-border-default
                                   text-text-primary text-sm
                                   focus:outline-none focus:border-primary"
                      >
                        {aiStatus.models
                          .filter(m => !m.includes('llava') && !m.includes('bakllava'))
                          .map((model) => (
                            <option key={model} value={model}>
                              {model}
                            </option>
                          ))}
                        {!aiStatus.models.some(m => !m.includes('llava') && !m.includes('bakllava')) && (
                          <option value="" disabled>無可用文字模型</option>
                        )}
                      </select>
                    </div>
                  </div>

                  <p className="text-text-muted text-xs">
                    💡 使用 <code className="bg-bg-elevated px-1 rounded">ollama pull 模型名稱</code> 來下載更多模型
                  </p>
                </div>
              )}

              {aiStatus.error && (
                <p className="text-error text-sm">{aiStatus.error}</p>
              )}
            </div>
          ) : (
            <p className="text-text-muted">無法取得 AI 狀態</p>
          )}

          <div className="mt-4 flex justify-end">
            <Button
              onClick={fetchAIStatus}
              variant="ghost"
              className="text-sm"
              disabled={isCheckingAI}
            >
              <RefreshCw size={16} className={isCheckingAI ? 'animate-spin' : ''} />
              重新檢查
            </Button>
          </div>
        </div>

        {/* Batch AI Tagging (Phase 3.1.4) */}
        {aiStatus?.available && (
          <BatchAITagging categories={categories} />
        )}

        {/* Semantic Search (Phase 3.2) */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Search size={20} className="text-primary" />
            語意搜尋
          </h2>
          
          {isCheckingSearch ? (
            <div className="flex items-center gap-2 text-text-muted">
              <Loader2 size={18} className="animate-spin" />
              正在檢查搜尋服務...
            </div>
          ) : searchStatus ? (
            <div className="space-y-4">
              {/* Status */}
              <div className="flex items-center gap-3">
                {searchStatus.available ? (
                  <span className="flex items-center gap-2 text-success">
                    <Check size={18} />
                    模型已安裝 ({searchStatus.model_name})
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-warning">
                    <AlertCircle size={18} />
                    需安裝 sentence-transformers
                    <code className="text-xs bg-bg-elevated px-2 py-0.5 rounded">pip install sentence-transformers</code>
                  </span>
                )}
              </div>

              {/* Index Stats */}
              {searchStatus.available && (
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-bg-elevated rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-primary">
                      {searchStatus.indexed_notes}
                    </div>
                    <div className="text-text-muted text-xs">已索引</div>
                  </div>
                  <div className="bg-bg-elevated rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-text-secondary">
                      {searchStatus.total_notes}
                    </div>
                    <div className="text-text-muted text-xs">總筆記數</div>
                  </div>
                  <div className="bg-bg-elevated rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-accent">
                      {searchStatus.index_coverage}
                    </div>
                    <div className="text-text-muted text-xs">覆蓋率</div>
                  </div>
                </div>
              )}

              {/* Rebuild Button */}
              {searchStatus.available && (
                <div className="flex items-center justify-between pt-2 border-t border-border-subtle">
                  <p className="text-text-muted text-sm">
                    重建索引以更新語意搜尋
                  </p>
                  <Button
                    onClick={handleRebuildIndex}
                    variant="secondary"
                    disabled={isRebuilding}
                    className="flex items-center gap-2"
                  >
                    {isRebuilding ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Zap size={16} />
                    )}
                    {isRebuilding ? '建立中...' : '重建索引'}
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <p className="text-text-muted">語意搜尋服務未啟用</p>
          )}
        </div>

        {/* Appearance */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Sun size={20} className="text-primary" />
            外觀
          </h2>
          
          {/* Dark/Light Mode */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-text-primary">主題模式</p>
              <p className="text-text-muted text-sm">
                選擇深色或淺色主題
              </p>
            </div>
            <Button
              onClick={toggleTheme}
              variant="secondary"
              className="flex items-center gap-2"
            >
              {theme === 'dark' ? <Moon size={18} /> : <Sun size={18} />}
              {theme === 'dark' ? '深色' : '淺色'}
            </Button>
          </div>

          {/* Color Theme */}
          <div className="pt-6 border-t border-border-subtle">
            <div className="mb-3">
              <p className="text-text-primary">主題色彩</p>
              <p className="text-text-muted text-sm">
                選擇你喜歡的配色方案
              </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[
                { id: 'default', name: '專業藍', color: '#3b82f6' },
                { id: 'cyberpunk', name: '賽博龐克', color: '#e879f9' },
                { id: 'eye-care', name: '護眼綠', color: '#34d399' },
                { id: 'elegant', name: '典雅金', color: '#d4a574' },
                { id: 'ocean', name: '海洋青', color: '#14b8a6' },
                { id: 'sunset', name: '夕陽橙', color: '#f97316' },
              ].map((themeOption) => {
                const isSelected = document.documentElement.getAttribute('data-theme') === themeOption.id
                return (
                  <button
                    key={themeOption.id}
                    onClick={() => {
                      document.documentElement.setAttribute('data-theme', themeOption.id)
                      localStorage.setItem('colorTheme', themeOption.id)
                      toast.success(`已切換至「${themeOption.name}」主題`)
                    }}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg border
                      transition-all duration-200
                      ${isSelected
                        ? 'border-primary bg-primary/10'
                        : 'border-border-default hover:border-border-hover hover:bg-bg-elevated'
                      }
                    `}
                  >
                    <div
                      className="w-8 h-8 rounded-full flex-shrink-0"
                      style={{ backgroundColor: themeOption.color }}
                    />
                    <div className="text-left flex-1">
                      <div className={`font-medium ${isSelected ? 'text-primary' : 'text-text-primary'}`}>
                        {themeOption.name}
                      </div>
                    </div>
                    {isSelected && (
                      <Check size={18} className="text-primary flex-shrink-0" />
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Card Open Mode */}
          <div className="pt-6 border-t border-border-subtle">
            <div className="mb-3">
              <p className="text-text-primary">卡片開啟模式</p>
              <p className="text-text-muted text-sm">
                選擇點擊卡片時的預設開啟模式
              </p>
            </div>
            <select
              value={localStorage.getItem('cardOpenMode') || 'reading'}
              onChange={(e) => {
                localStorage.setItem('cardOpenMode', e.target.value)
                const modeName = e.target.value === 'preview' ? '預覽' : e.target.value === 'reading' ? '閱讀' : '編輯'
                toast.success(`已設定為「${modeName}」模式`)
              }}
              className="w-full px-4 py-2 rounded-lg
                         bg-bg-elevated border border-border-default
                         text-text-primary
                         focus:outline-none focus:border-primary
                         transition-colors"
            >
              <option value="preview">預覽模式 (Preview) - 快速瀏覽內容</option>
              <option value="reading">閱讀模式 (Reading) - 沉浸式閱讀</option>
              <option value="edit">編輯模式 (Edit) - 直接編輯</option>
            </select>
          </div>
        </div>

        {/* Database Stats */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Database size={20} className="text-primary" />
            資料庫統計
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-bg-elevated rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-primary">
                {stats?.notes_count ?? '-'}
              </div>
              <div className="text-text-muted text-sm">筆記數</div>
            </div>
            <div className="bg-bg-elevated rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-accent">
                {stats?.categories_count ?? '-'}
              </div>
              <div className="text-text-muted text-sm">分類數</div>
            </div>
            <div className="bg-bg-elevated rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-success">
                {stats?.tags_count ?? '-'}
              </div>
              <div className="text-text-muted text-sm">標籤數</div>
            </div>
            <div className="bg-bg-elevated rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-warning">
                {stats?.images_count ?? '-'}
              </div>
              <div className="text-text-muted text-sm">圖片數</div>
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <Button
              onClick={fetchStats}
              variant="ghost"
              className="text-sm"
              disabled={isLoading}
            >
              <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
              重新整理
            </Button>
          </div>
        </div>

        {/* About */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Info size={20} className="text-primary" />
            關於
          </h2>
          <div className="space-y-2 text-text-secondary">
            <p><strong className="text-text-primary">Prism V2</strong></p>
            <p>版本: 2.0.0-alpha</p>
            <p>前端: Vite + React + TypeScript + Tailwind CSS</p>
            <p>後端: Flask + SQLite</p>
            <p>AI: Ollama (Local LLM) + Sentence Transformers</p>
            <p className="text-text-muted text-sm pt-2">
              本地知識管理系統，所有資料儲存在您的電腦上
            </p>
          </div>
        </div>

        {/* Export / Backup */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Download size={20} className="text-success" />
            匯出備份
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary">匯出 JSON</p>
                <p className="text-text-muted text-sm">
                  匯出所有筆記、分類、標籤為 JSON 格式
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  api.exportJSON()
                  toast.success('開始下載 JSON 備份檔案')
                }}
              >
                下載 JSON
              </Button>
            </div>
            <div className="border-t border-border-subtle pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-text-primary">匯出資料庫</p>
                  <p className="text-text-muted text-sm">
                    匯出完整 SQLite 資料庫檔案
                  </p>
                </div>
                <Button
                  variant="secondary"
                  onClick={() => {
                    api.exportDB()
                    toast.success('開始下載資料庫備份檔案')
                  }}
                >
                  下載 .db
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Import */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Upload size={20} className="text-accent" />
            匯入資料
          </h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-primary">從 JSON 匯入</p>
              <p className="text-text-muted text-sm">
                匯入先前匯出的 JSON 備份檔案
              </p>
            </div>
            <div>
              <input
                type="file"
                ref={fileInputRef}
                accept=".json"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                variant="secondary"
                onClick={() => fileInputRef.current?.click()}
              >
                選擇檔案
              </Button>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="glass rounded-xl p-6 border border-error/30">
          <h2 className="text-lg font-semibold text-error mb-4 flex items-center gap-2">
            <Trash2 size={20} />
            危險區域
          </h2>
          
          {/* Orphan Image Cleanup */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Image size={20} className="text-text-muted" />
                <div>
                  <p className="text-text-primary">清理未使用的圖片</p>
                  <p className="text-text-muted text-sm">
                    掃描並刪除未被任何筆記引用的孤兒圖片
                  </p>
                </div>
              </div>
              <Button
                variant="secondary"
                className="text-primary border-primary/30 hover:bg-primary/10"
                onClick={scanOrphanImages}
                disabled={isScanning}
              >
                {isScanning ? (
                  <>
                    <Loader2 size={16} className="animate-spin mr-1" />
                    掃描中...
                  </>
                ) : (
                  '掃描'
                )}
              </Button>
            </div>

            {/* Scan Results */}
            {orphanImages.length > 0 && (
              <div className="bg-bg-elevated rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-text-primary font-medium">
                      發現 {orphanImages.length} 張孤兒圖片
                    </p>
                    <p className="text-text-muted text-sm">
                      佔用空間：{orphanTotalSize} MB
                    </p>
                  </div>
                  <Button
                    variant="secondary"
                    className="text-error border-error/30 hover:bg-error/10"
                    onClick={deleteAllOrphanImages}
                    disabled={isDeleting}
                  >
                    {isDeleting ? (
                      <>
                        <Loader2 size={16} className="animate-spin mr-1" />
                        刪除中...
                      </>
                    ) : (
                      '全部刪除'
                    )}
                  </Button>
                </div>

                {/* Preview some orphan images */}
                <div className="max-h-32 overflow-y-auto">
                  <div className="flex flex-wrap gap-1">
                    {orphanImages.slice(0, 10).map((img) => (
                      <span
                        key={img.filename}
                        className="text-xs px-2 py-0.5 bg-bg-secondary rounded text-text-muted truncate max-w-[150px]"
                        title={img.filename}
                      >
                        {img.filename}
                      </span>
                    ))}
                    {orphanImages.length > 10 && (
                      <span className="text-xs px-2 py-0.5 text-text-muted">
                        還有 {orphanImages.length - 10} 張...
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Divider */}
            <div className="border-t border-border-subtle my-4" />

            {/* Delete Original Images */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Image size={20} className="text-text-muted" />
                <div>
                  <p className="text-text-primary">刪除原圖（保留縮圖）</p>
                  <p className="text-text-muted text-sm">
                    刪除有縮圖的原圖，筆記中的路徑會自動替換
                  </p>
                </div>
              </div>
              <Button
                variant="secondary"
                className="text-primary border-primary/30 hover:bg-primary/10"
                onClick={scanOriginalImages}
                disabled={isScanningOriginals}
              >
                {isScanningOriginals ? (
                  <>
                    <Loader2 size={16} className="animate-spin mr-1" />
                    掃描中...
                  </>
                ) : (
                  '掃描'
                )}
              </Button>
            </div>

            {/* Original Images Results */}
            {originalStats && originalStats.count > 0 && (
              <div className="bg-bg-elevated rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-text-primary font-medium">
                      發現 {originalStats.count} 張原圖
                    </p>
                    <p className="text-text-muted text-sm">
                      可節省 {originalStats.size} MB 空間
                    </p>
                  </div>
                  <Button
                    variant="secondary"
                    className="text-error border-error/30 hover:bg-error/10"
                    onClick={deleteAllOriginals}
                    disabled={isDeletingOriginals}
                  >
                    {isDeletingOriginals ? (
                      <>
                        <Loader2 size={16} className="animate-spin mr-1" />
                        刪除中...
                      </>
                    ) : (
                      '全部刪除'
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Divider */}
            <div className="border-t border-border-subtle my-4" />

            {/* Fix Broken Image Paths */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertCircle size={20} className="text-warning" />
                <div>
                  <p className="text-text-primary">修復失效圖片路徑</p>
                  <p className="text-text-muted text-sm">
                    掃描並修復指向不存在檔案的圖片引用
                  </p>
                </div>
              </div>
              <Button
                variant="secondary"
                className="text-primary border-primary/30 hover:bg-primary/10"
                onClick={scanBrokenPaths}
                disabled={isScanningBroken}
              >
                {isScanningBroken ? (
                  <>
                    <Loader2 size={16} className="animate-spin mr-1" />
                    掃描中...
                  </>
                ) : (
                  '掃描'
                )}
              </Button>
            </div>

            {/* Broken Paths Results */}
            {brokenPaths && brokenPaths.total > 0 && (
              <div className="bg-bg-elevated rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-text-primary font-medium">
                      發現 {brokenPaths.total} 個失效路徑
                    </p>
                    <p className="text-text-muted text-sm">
                      其中 {brokenPaths.fixable} 個可自動修復
                    </p>
                  </div>
                  {brokenPaths.fixable > 0 && (
                    <Button
                      variant="secondary"
                      className="text-success border-success/30 hover:bg-success/10"
                      onClick={fixAllBrokenPaths}
                      disabled={isFixingBroken}
                    >
                      {isFixingBroken ? (
                        <>
                          <Loader2 size={16} className="animate-spin mr-1" />
                          修復中...
                        </>
                      ) : (
                        '自動修復'
                      )}
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Import Modal */}
      {showImportModal && importData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-bg-elevated rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-text-primary mb-4">
              確認匯入
            </h3>
            
            <p className="text-text-secondary mb-4">
              檔案包含 <strong className="text-text-primary">
                {(importData as { notes?: unknown[] }).notes?.length || 0}
              </strong> 筆筆記
            </p>

            <div className="mb-6">
              <p className="text-sm text-text-muted mb-2">遇到重複筆記時：</p>
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="importMode"
                    value="skip"
                    checked={importMode === 'skip'}
                    onChange={() => setImportMode('skip')}
                    className="accent-primary"
                  />
                  <span className="text-text-secondary">略過（不匯入重複的筆記）</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="importMode"
                    value="duplicate"
                    checked={importMode === 'duplicate'}
                    onChange={() => setImportMode('duplicate')}
                    className="accent-primary"
                  />
                  <span className="text-text-secondary">建立副本（加上 Import 後綴）</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowImportModal(false)
                  setImportData(null)
                }}
              >
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleImport}
                disabled={isImporting}
              >
                {isImporting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    匯入中...
                  </>
                ) : (
                  '開始匯入'
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      <ToastContainer />
    </>
  )
}
