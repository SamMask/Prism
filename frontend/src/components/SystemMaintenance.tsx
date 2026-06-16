import { useState } from 'react'
import { HardDrive, CheckCircle, AlertTriangle, XCircle, Loader2, Activity } from 'lucide-react'
import { api } from '../services/api'
import { Button } from './ui/Button'
import { toast } from './ui/Toast'
import { useTranslation } from '../hooks/useTranslation'

interface ConsistencyData {
  orphan_note_tags: number
  unused_tags: number
  null_category_id: number
  fk_enabled: boolean
  health: 'healthy' | 'warning' | 'critical'
}

export function SystemMaintenance() {
  const { t } = useTranslation()
  const [isWalRunning, setIsWalRunning] = useState(false)
  const [isCheckRunning, setIsCheckRunning] = useState(false)
  const [walResult, setWalResult] = useState<{ wal_size_before: number; pages_checkpointed: number } | null>(null)
  const [consistencyResult, setConsistencyResult] = useState<ConsistencyData | null>(null)

  const handleWalCheckpoint = async () => {
    setIsWalRunning(true)
    try {
      const result = await api.walCheckpoint()
      setWalResult(result)
      toast.success(t('settings.maintenance.walComplete', { count: result.pages_checkpointed }))
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.maintenance.walFailed'))
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
        toast.success(t('settings.maintenance.consistencyHealthyToast'))
      } else if (result.health === 'warning') {
        toast.warning(t('settings.maintenance.consistencyWarningToast'))
      } else {
        toast.error(t('settings.maintenance.consistencyCriticalToast'))
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.maintenance.checkFailed'))
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
        return t('settings.maintenance.healthHealthy')
      case 'warning':
        return t('settings.maintenance.healthWarning')
      case 'critical':
        return t('settings.maintenance.healthCritical')
      default:
        return t('settings.maintenance.healthUnknown')
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border-subtle bg-bg-elevated/60 p-3 text-xs text-text-muted">
        {t('settings.maintenance.description')}
      </div>

      {/* WAL Checkpoint */}
      <div className="p-4 rounded-lg bg-bg-elevated">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <HardDrive size={18} className="text-primary" />
            <span className="font-medium text-text-primary">{t('settings.maintenance.walTitle')}</span>
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
                {t('settings.maintenance.running')}
              </>
            ) : (
              t('settings.maintenance.run')
            )}
          </Button>
        </div>
        <p className="text-xs text-text-muted mb-2">
          {t('settings.maintenance.walDescription')}
        </p>
        {walResult && (
          <div className="text-xs text-text-secondary bg-bg-surface rounded p-2 mt-2">
            {t('settings.maintenance.walResult', {
              size: (walResult.wal_size_before / 1024).toFixed(1),
              count: walResult.pages_checkpointed,
            })}
          </div>
        )}
      </div>

      {/* Consistency Check */}
      <div className="p-4 rounded-lg bg-bg-elevated">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity size={18} className="text-accent" />
            <span className="font-medium text-text-primary">{t('settings.maintenance.consistencyTitle')}</span>
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
                {t('settings.maintenance.checking')}
              </>
            ) : (
              t('settings.maintenance.check')
            )}
          </Button>
        </div>
        <p className="text-xs text-text-muted mb-2">
          {t('settings.maintenance.consistencyDescription')}
        </p>
        {consistencyResult && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2 text-sm">
              {getHealthIcon(consistencyResult.health)}
              <span className="text-text-primary font-medium">
                {t('settings.maintenance.status', { status: getHealthText(consistencyResult.health) })}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between bg-bg-surface rounded p-2">
                <span className="text-text-muted">{t('settings.maintenance.orphanTagLinks')}</span>
                <span className={consistencyResult.orphan_note_tags > 0 ? 'text-warning' : 'text-success'}>
                  {consistencyResult.orphan_note_tags}
                </span>
              </div>
              <div className="flex justify-between bg-bg-surface rounded p-2">
                <span className="text-text-muted">{t('settings.maintenance.unusedTags')}</span>
                <span className="text-text-secondary">{consistencyResult.unused_tags}</span>
              </div>

              <div className="flex justify-between bg-bg-surface rounded p-2">
                <span className="text-text-muted">{t('settings.maintenance.foreignKeys')}</span>
                <span className={consistencyResult.fk_enabled ? 'text-success' : 'text-warning'}>
                  {consistencyResult.fk_enabled ? t('settings.maintenance.enabled') : t('settings.maintenance.disabled')}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
