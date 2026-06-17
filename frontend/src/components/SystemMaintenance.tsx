import { useEffect, useState } from 'react'
import { HardDrive, CheckCircle, AlertTriangle, XCircle, Loader2, Activity, Search, RefreshCw } from 'lucide-react'
import { api, type SearchIntegrityResponse } from '../services/api'
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
  const [isSearchCheckRunning, setIsSearchCheckRunning] = useState(false)
  const [isSearchRebuildRunning, setIsSearchRebuildRunning] = useState(false)
  const [walResult, setWalResult] = useState<{ wal_size_before: number; pages_checkpointed: number } | null>(null)
  const [consistencyResult, setConsistencyResult] = useState<ConsistencyData | null>(null)
  const [searchIntegrity, setSearchIntegrity] = useState<SearchIntegrityResponse | null>(null)

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

  const handleSearchIntegrityCheck = async () => {
    setIsSearchCheckRunning(true)
    try {
      const result = await api.getSearchIntegrity()
      setSearchIntegrity(result)
      if (result.status === 'ok') {
        toast.success(t('settings.maintenance.searchHealthyToast'))
      } else {
        toast.warning(t('settings.maintenance.searchNeedsRebuildToast'))
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.maintenance.searchCheckFailed'))
    } finally {
      setIsSearchCheckRunning(false)
    }
  }

  const handleSearchRebuild = async () => {
    setIsSearchRebuildRunning(true)
    try {
      const result = await api.rebuildSearchIndex()
      toast.success(t('settings.maintenance.searchRebuildComplete', { count: result.fts_rows }))
      await handleSearchIntegrityCheck()
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.maintenance.searchRebuildFailed'))
    } finally {
      setIsSearchRebuildRunning(false)
    }
  }

  useEffect(() => {
    handleConsistencyCheck()
    handleSearchIntegrityCheck()
  }, [])

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

  const overviewHealth = consistencyResult?.health === 'critical' || searchIntegrity?.status === 'needs_rebuild'
    ? 'warning'
    : consistencyResult?.health || (searchIntegrity ? 'healthy' : 'unknown')

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border-subtle bg-bg-elevated/60 p-3 text-xs text-text-muted">
        {t('settings.maintenance.description')}
      </div>

      <div className="rounded-lg bg-bg-elevated p-4" data-testid="maintenance-health-overview">
        <div className="mb-3 flex items-center gap-2">
          {getHealthIcon(overviewHealth)}
          <span className="font-medium text-text-primary">{t('settings.maintenance.overviewTitle')}</span>
        </div>
        <div className="grid gap-2 text-xs sm:grid-cols-3">
          <div className="rounded bg-bg-surface p-2">
            <div className="text-text-muted">{t('settings.maintenance.overviewData')}</div>
            <div className="mt-1 font-medium text-text-primary">
              {consistencyResult ? getHealthText(consistencyResult.health) : t('settings.maintenance.healthUnknown')}
            </div>
          </div>
          <div className="rounded bg-bg-surface p-2">
            <div className="text-text-muted">{t('settings.maintenance.overviewSearch')}</div>
            <div className={`mt-1 font-medium ${searchIntegrity?.status === 'needs_rebuild' ? 'text-warning' : 'text-text-primary'}`}>
              {searchIntegrity ? t(`settings.maintenance.searchStatus.${searchIntegrity.status}`) : t('settings.maintenance.healthUnknown')}
            </div>
          </div>
          <div className="rounded bg-bg-surface p-2">
            <div className="text-text-muted">{t('settings.maintenance.overviewWal')}</div>
            <div className="mt-1 font-medium text-text-primary">
              {walResult ? t('settings.maintenance.walPagesShort', { count: walResult.pages_checkpointed }) : t('settings.maintenance.manualOnly')}
            </div>
          </div>
        </div>
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

      <div className="rounded-lg bg-bg-elevated p-4" data-testid="search-integrity-card">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Search size={18} className="text-primary" />
            <span className="font-medium text-text-primary">{t('settings.maintenance.searchIntegrityTitle')}</span>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button size="sm" variant="secondary" onClick={handleSearchIntegrityCheck} disabled={isSearchCheckRunning || isSearchRebuildRunning}>
              {isSearchCheckRunning ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              {t('settings.maintenance.check')}
            </Button>
            <Button size="sm" variant="secondary" onClick={handleSearchRebuild} disabled={isSearchRebuildRunning || isSearchCheckRunning}>
              {isSearchRebuildRunning ? <Loader2 size={14} className="animate-spin" /> : null}
              {t('settings.maintenance.searchRebuild')}
            </Button>
          </div>
        </div>
        <p className="mb-2 text-xs text-text-muted">
          {t('settings.maintenance.searchIntegrityDescription')}
        </p>
        {searchIntegrity && (
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            <div className="rounded bg-bg-surface p-2">
              <span className="text-text-muted">{t('settings.maintenance.searchStatusLabel')}</span>
              <div className={searchIntegrity.status === 'ok' ? 'font-medium text-success' : 'font-medium text-warning'}>
                {t(`settings.maintenance.searchStatus.${searchIntegrity.status}`)}
              </div>
            </div>
            <div className="rounded bg-bg-surface p-2">
              <span className="text-text-muted">{t('settings.maintenance.searchNotesCount')}</span>
              <div className="font-medium text-text-primary">{searchIntegrity.notes_count}</div>
            </div>
            <div className="rounded bg-bg-surface p-2">
              <span className="text-text-muted">{t('settings.maintenance.searchFtsRows')}</span>
              <div className="font-medium text-text-primary">{searchIntegrity.fts_rows}</div>
            </div>
            <div className="rounded bg-bg-surface p-2">
              <span className="text-text-muted">{t('settings.maintenance.searchMismatch')}</span>
              <div className={searchIntegrity.missing_fts_rows || searchIntegrity.orphan_fts_rows ? 'font-medium text-warning' : 'font-medium text-success'}>
                {searchIntegrity.missing_fts_rows + searchIntegrity.orphan_fts_rows}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
