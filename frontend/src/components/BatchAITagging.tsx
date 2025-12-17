/**
 * BatchAITagging - Batch AI Auto-Tagging Component
 * Phase 3.1.4
 */
import { useState, useEffect, useRef } from 'react'
import { Sparkles, Play, Square, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { Button } from './ui/Button'
import { toast } from './ui/Toast'
import { api, Category } from '../services/api'

interface BatchAITaggingProps {
  categories: Category[]
}

type BatchScope = 'all' | 'category' | 'untagged'

interface TaskStatus {
  task_id: string
  status: 'running' | 'completed' | 'stopped' | 'error'
  total: number
  completed: number
  success: number
  failed: number
  progress: number
}

export function BatchAITagging({ categories }: BatchAITaggingProps) {
  const [scope, setScope] = useState<BatchScope>('untagged')
  const [categoryId, setCategoryId] = useState<number | undefined>()
  const [isStarting, setIsStarting] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [status, setStatus] = useState<TaskStatus | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Poll task status
  useEffect(() => {
    if (taskId && status?.status === 'running') {
      pollingRef.current = setInterval(async () => {
        try {
          const newStatus = await api.getBatchStatus(taskId)
          setStatus(newStatus)
          
          if (newStatus.status !== 'running') {
            // Task completed
            if (pollingRef.current) {
              clearInterval(pollingRef.current)
              pollingRef.current = null
            }
            
            if (newStatus.status === 'completed') {
              toast.success(`批次處理完成！成功 ${newStatus.success} 筆，失敗 ${newStatus.failed} 筆`)
            } else if (newStatus.status === 'stopped') {
              toast.info('批次處理已停止')
            }
          }
        } catch (error) {
          console.error('Failed to get batch status:', error)
        }
      }, 2000) // Poll every 2 seconds
    }
    
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [taskId, status?.status])

  // Start batch tagging
  const handleStart = async () => {
    if (scope === 'category' && !categoryId) {
      toast.warning('請選擇分類')
      return
    }
    
    setIsStarting(true)
    try {
      const result = await api.startBatchTag(scope, categoryId)
      
      if (result.task_id) {
        setTaskId(result.task_id)
        setStatus({
          task_id: result.task_id,
          status: 'running',
          total: result.total,
          completed: 0,
          success: 0,
          failed: 0,
          progress: 0
        })
        toast.info(result.message)
      } else {
        toast.info(result.message)
      }
    } catch (error) {
      toast.error('啟動批次處理失敗')
    } finally {
      setIsStarting(false)
    }
  }

  // Stop task
  const handleStop = async () => {
    if (!taskId) return
    
    try {
      await api.stopBatchTask(taskId)
      toast.info('正在停止任務...')
    } catch (error) {
      toast.error('停止任務失敗')
    }
  }

  const isRunning = status?.status === 'running'
  const isCompleted = status?.status === 'completed'
  const isStopped = status?.status === 'stopped'

  return (
    <div className="glass rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-primary 
                        flex items-center justify-center">
          <Sparkles size={20} className="text-white" />
        </div>
        <div>
          <h3 className="font-semibold text-text-primary">批次 AI 標籤</h3>
          <p className="text-sm text-text-muted">自動為筆記生成標籤</p>
        </div>
      </div>

      {/* Scope Selection */}
      {!isRunning && (
        <div className="space-y-3 mb-4">
          <label className="text-sm font-medium text-text-secondary">處理範圍</label>
          <div className="flex gap-2">
            <button
              onClick={() => setScope('untagged')}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors
                ${scope === 'untagged' 
                  ? 'bg-primary text-white' 
                  : 'bg-bg-elevated text-text-secondary hover:bg-bg-hover'}`}
            >
              無標籤筆記
            </button>
            <button
              onClick={() => setScope('category')}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors
                ${scope === 'category' 
                  ? 'bg-primary text-white' 
                  : 'bg-bg-elevated text-text-secondary hover:bg-bg-hover'}`}
            >
              指定分類
            </button>
            <button
              onClick={() => setScope('all')}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors
                ${scope === 'all' 
                  ? 'bg-primary text-white' 
                  : 'bg-bg-elevated text-text-secondary hover:bg-bg-hover'}`}
            >
              全部筆記
            </button>
          </div>

          {scope === 'category' && (
            <select
              value={categoryId || ''}
              onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-3 py-2
                         text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="">選擇分類...</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.icon} {cat.name}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Progress Bar */}
      {status && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-text-secondary">
              {isRunning && <Loader2 size={14} className="inline animate-spin mr-1.5" />}
              {isCompleted && <CheckCircle size={14} className="inline text-success mr-1.5" />}
              {isStopped && <XCircle size={14} className="inline text-warning mr-1.5" />}
              {status.completed} / {status.total}
            </span>
            <span className="text-text-muted">{status.progress}%</span>
          </div>
          
          <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-300 ${
                isCompleted ? 'bg-success' : 
                isStopped ? 'bg-warning' : 
                'bg-gradient-to-r from-primary to-accent'
              }`}
              style={{ width: `${status.progress}%` }}
            />
          </div>

          {(isCompleted || isStopped) && (
            <div className="flex gap-4 mt-2 text-sm">
              <span className="text-success">✓ 成功: {status.success}</span>
              {status.failed > 0 && (
                <span className="text-danger">✗ 失敗: {status.failed}</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {!isRunning ? (
          <Button
            onClick={handleStart}
            variant="primary"
            disabled={isStarting}
            className="flex-1 flex items-center justify-center gap-2"
          >
            {isStarting ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Play size={18} />
            )}
            {isStarting ? '準備中...' : '開始處理'}
          </Button>
        ) : (
          <Button
            onClick={handleStop}
            variant="ghost"
            className="flex-1 flex items-center justify-center gap-2 text-warning"
          >
            <Square size={18} />
            停止
          </Button>
        )}
      </div>

      {/* Warning */}
      {scope === 'all' && !isRunning && (
        <p className="text-xs text-warning mt-3">
          ⚠️ 處理全部筆記可能需要較長時間，建議使用「無標籤筆記」選項
        </p>
      )}
    </div>
  )
}
