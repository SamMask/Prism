import { useState, useEffect } from 'react'
import { Moon, Sun, Database, Info, RefreshCw, Trash2, Sparkles, Check, AlertCircle, Loader2, Search, Zap } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { toast, ToastContainer } from '../components/ui/Toast'
import { api } from '../services/api'
import { BatchAITagging } from '../components/BatchAITagging'
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


  // Load theme preference
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'dark' | 'light' | null
    if (savedTheme) {
      setTheme(savedTheme)
    }
  }, [])

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
            <div className="space-y-3">
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

              {/* Vision Model */}
              <div className="flex items-center gap-3">
                {aiStatus.vision_ready ? (
                  <span className="flex items-center gap-2 text-success">
                    <Check size={18} />
                    視覺模型 (LLaVA) 已就緒
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-warning">
                    <AlertCircle size={18} />
                    視覺模型未安裝
                    <code className="text-xs bg-bg-elevated px-2 py-0.5 rounded">ollama pull llava</code>
                  </span>
                )}
              </div>

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
          <div className="flex items-center justify-between">
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

        {/* Danger Zone */}
        <div className="glass rounded-xl p-6 border border-error/30">
          <h2 className="text-lg font-semibold text-error mb-4 flex items-center gap-2">
            <Trash2 size={20} />
            危險區域
          </h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-primary">清理未使用的圖片</p>
              <p className="text-text-muted text-sm">
                掃描並刪除未被任何筆記引用的圖片
              </p>
            </div>
            <Button
              variant="secondary"
              className="text-error border-error/30 hover:bg-error/10"
              onClick={() => toast.info('此功能即將推出')}
            >
              執行清理
            </Button>
          </div>
        </div>
      </div>
      <ToastContainer />
    </>
  )
}
