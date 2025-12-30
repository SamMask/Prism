import { useState } from 'react'
import { HardDrive, CheckCircle, AlertTriangle, XCircle, Loader2, Activity } from 'lucide-react'
import { api } from '../services/api'
import { Button } from './ui/Button'
import { toast } from './ui/Toast'

interface ConsistencyData {
  orphan_note_tags: number
  unused_tags: number
  type_category_mismatch: number
  null_category_id: number
  fk_enabled: boolean
  health: 'healthy' | 'warning' | 'critical'
}

export function SystemMaintenance() {
  const [isWalRunning, setIsWalRunning] = useState(false)
  const [isCheckRunning, setIsCheckRunning] = useState(false)
  const [walResult, setWalResult] = useState<{ wal_size_before: number; pages_checkpointed: number } | null>(null)
  const [consistencyResult, setConsistencyResult] = useState<ConsistencyData | null>(null)

  const handleWalCheckpoint = async () => {
    setIsWalRunning(true)
    try {
      const result = await api.walCheckpoint()
      setWalResult(result)
      toast.success(`WAL 合併完成，已處理 ${result.pages_checkpointed} 頁`)
    } catch (error: any) {
      toast.error(error?.response?.data?.message || 'WAL Checkpoint 失敗')
    } finally {
      setIsWalRunning(false)
    }
  }

  const handleConsistencyCheck = async () => {
    setIsCheckRunning(true)
    try {
      const result = await api.checkConsistency()
      setConsistencyResult(result)
      if (result.health === 'healthy') {
        toast.success('資料一致性檢查通過！')
      } else if (result.health === 'warning') {
        toast.warning('發現一些小問題，建議檢查')
      } else {
        toast.error('發現嚴重問題，需要處理')
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '檢查失敗')
    } finally {
      setIsCheckRunning(false)
    }
  }

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'healthy':
        return <CheckCircle size={20} className="text-success" />
      case 'warning':
        return <AlertTriangle size={20} className="text-warning" />
      case 'critical':
        return <XCircle size={20} className="text-danger" />
      default:
        return null
    }
  }

  const getHealthText = (health: string) => {
    switch (health) {
      case 'healthy':
        return '健康'
      case 'warning':
        return '警告'
      case 'critical':
        return '危險'
      default:
        return '未知'
    }
  }

  return (
    <div className="space-y-4">
      {/* WAL Checkpoint */}
      <div className="p-4 rounded-lg bg-bg-elevated">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <HardDrive size={18} className="text-primary" />
            <span className="font-medium text-text-primary">WAL Checkpoint</span>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={handleWalCheckpoint}
            disabled={isWalRunning}
          >
            {isWalRunning ? (
              <>
                <Loader2 size={14} className="animate-spin mr-1" />
                執行中...
              </>
            ) : (
              '執行'
            )}
          </Button>
        </div>
        <p className="text-xs text-text-muted mb-2">
          手動將暫存日誌寫入主檔案（僅需在備份 .db 檔前執行，平常由系統自動處理）
        </p>
        {walResult && (
          <div className="text-xs text-text-secondary bg-bg-surface rounded p-2 mt-2">
            ✅ WAL 大小: {(walResult.wal_size_before / 1024).toFixed(1)} KB → 已處理 {walResult.pages_checkpointed} 頁
          </div>
        )}
      </div>

      {/* Consistency Check */}
      <div className="p-4 rounded-lg bg-bg-elevated">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity size={18} className="text-accent" />
            <span className="font-medium text-text-primary">資料一致性檢查</span>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={handleConsistencyCheck}
            disabled={isCheckRunning}
          >
            {isCheckRunning ? (
              <>
                <Loader2 size={14} className="animate-spin mr-1" />
                檢查中...
              </>
            ) : (
              '檢查'
            )}
          </Button>
        </div>
        <p className="text-xs text-text-muted mb-2">
          檢查標籤關聯、分類一致性等資料完整性問題
        </p>
        {consistencyResult && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2 text-sm">
              {getHealthIcon(consistencyResult.health)}
              <span className="text-text-primary font-medium">
                狀態: {getHealthText(consistencyResult.health)}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between bg-bg-surface rounded p-2">
                <span className="text-text-muted">孤兒標籤關聯</span>
                <span className={consistencyResult.orphan_note_tags > 0 ? 'text-warning' : 'text-success'}>
                  {consistencyResult.orphan_note_tags}
                </span>
              </div>
              <div className="flex justify-between bg-bg-surface rounded p-2">
                <span className="text-text-muted">未使用標籤</span>
                <span className="text-text-secondary">{consistencyResult.unused_tags}</span>
              </div>
              <div className="flex justify-between bg-bg-surface rounded p-2">
                <span className="text-text-muted">分類不一致</span>
                <span className={consistencyResult.type_category_mismatch > 0 ? 'text-warning' : 'text-success'}>
                  {consistencyResult.type_category_mismatch}
                </span>
              </div>
              <div className="flex justify-between bg-bg-surface rounded p-2">
                <span className="text-text-muted">FK 狀態</span>
                <span className={consistencyResult.fk_enabled ? 'text-success' : 'text-warning'}>
                  {consistencyResult.fk_enabled ? '啟用' : '停用'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
