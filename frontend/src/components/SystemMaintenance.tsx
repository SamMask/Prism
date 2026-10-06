import { useEffect, useState } from 'react'
import { HardDrive, CheckCircle, AlertTriangle, XCircle, Loader2, Activity, Search, RefreshCw, FileText } from 'lucide-react'
import {
  api,
  type InlineSeparatedNotesReport,
  type InlineSkipReason,
  type SearchIntegrityResponse,
} from '../services/api'
import { Button } from './ui/Button'
import { confirm } from './ui/ConfirmDialog'
import { toast } from './ui/Toast'
import { useTranslation } from '../hooks/useTranslation'

interface ConsistencyData {
  orphan_note_tags: number
  unused_tags: number
  null_category_id: number
  fk_enabled: boolean
  foreign_key_violations_total: number
  foreign_key_violations_by_table: Record<string, number>
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
              <div className="flex justify-between bg-bg-surface rounded p-2">
                <span className="text-text-muted">{t('settings.maintenance.foreignKeyViolations')}</span>
                <span className={consistencyResult.foreign_key_violations_total > 0 ? 'text-danger' : 'text-success'}>
                  {consistencyResult.foreign_key_violations_total}
                </span>
              </div>
            </div>
            {consistencyResult.foreign_key_violations_total > 0 && (
              <div className="rounded bg-danger/10 p-2 text-xs text-danger" role="status">
                {t('settings.maintenance.foreignKeyViolationTables', {
                  tables: Object.entries(consistencyResult.foreign_key_violations_by_table)
                    .sort(([left], [right]) => left.localeCompare(right))
                    .map(([table, count]) => `${table}: ${count}`)
                    .join(', '),
                })}
              </div>
            )}
          </div>
        )}
      </div>

      <InlineSeparatedNotesCard />

      <details className="rounded-lg border border-border-subtle bg-bg-elevated/50" data-testid="maintenance-advanced-diagnostics">
        <summary className="cursor-pointer px-4 py-3 font-medium text-text-primary">
          {t('settings.maintenance.advancedTitle')}
        </summary>
        <div className="space-y-4 border-t border-border-subtle p-4">
          <p className="text-xs text-text-muted">{t('settings.maintenance.advancedDescription')}</p>

          {/* WAL Checkpoint */}
          <div className="rounded-lg bg-bg-elevated p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HardDrive size={18} className="text-primary" />
                <span className="font-medium text-text-primary">{t('settings.maintenance.walTitle')}</span>
              </div>
              <Button size="sm" variant="secondary" onClick={handleWalCheckpoint} disabled={isWalRunning}>
                {isWalRunning ? (
                  <>
                    <Loader2 size={14} className="mr-1 animate-spin" />
                    {t('settings.maintenance.running')}
                  </>
                ) : t('settings.maintenance.run')}
              </Button>
            </div>
            <p className="mb-2 text-xs text-text-muted">{t('settings.maintenance.walDescription')}</p>
            {walResult && (
              <div className="mt-2 rounded bg-bg-surface p-2 text-xs text-text-secondary">
                {t('settings.maintenance.walResult', {
                  size: (walResult.wal_size_before / 1024).toFixed(1),
                  count: walResult.pages_checkpointed,
                })}
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
      </details>
    </div>
  )
}

const INLINE_LIST_LIMIT = 20

type InlineErrorKind = 'rejected' | 'nothingChanged' | 'unknown'

interface InlineErrorState {
  kind: InlineErrorKind
  message: string
}

// A 4xx or a 500 that says notes_changed: 0 proves nothing changed; anything else (no
// response, proxy errors, a 5xx without the flag) leaves the outcome unknown.
function inlineError(error: unknown): InlineErrorState {
  const response = (error as { response?: { status?: number; data?: { message?: string; notes_changed?: number } } })
    ?.response
  const message = response?.data?.message || ''
  if (response?.status && response.status >= 400 && response.status < 500) return { kind: 'rejected', message }
  if (response?.status === 500 && response.data?.notes_changed === 0) return { kind: 'nothingChanged', message }
  return { kind: 'unknown', message }
}

function InlineList({
  title,
  items,
  testId,
}: {
  title: string
  items: Array<{ key: string; label: string; detail?: string }>
  testId: string
}) {
  const { t } = useTranslation()
  if (items.length === 0) return null
  return (
    <details className="rounded bg-bg-surface p-2 text-xs" data-testid={testId}>
      <summary className="cursor-pointer font-medium text-text-primary">
        {title} ({items.length})
      </summary>
      <ul className="mt-2 max-h-64 space-y-1 overflow-y-auto">
        {items.slice(0, INLINE_LIST_LIMIT).map((item) => (
          <li key={item.key} className="min-w-0">
            <div className="break-words text-text-secondary">{item.label}</div>
            {item.detail && <div className="break-all font-mono text-[11px] text-text-muted">{item.detail}</div>}
          </li>
        ))}
        {items.length > INLINE_LIST_LIMIT && (
          <li className="text-text-muted">
            {t('settings.maintenance.inlineNotes.more', { count: items.length - INLINE_LIST_LIMIT })}
          </li>
        )}
      </ul>
    </details>
  )
}

function InlineSeparatedNotesCard() {
  const { t } = useTranslation()
  const [report, setReport] = useState<InlineSeparatedNotesReport | null>(null)
  const [phase, setPhase] = useState<'idle' | 'checking' | 'merging'>('idle')
  const [error, setError] = useState<InlineErrorState | null>(null)
  const busy = phase !== 'idle'
  const reasonLabel = (reason: InlineSkipReason | '') =>
    reason ? t(`settings.maintenance.inlineNotes.reasons.${reason}`) : ''

  const runCheck = async () => {
    setPhase('checking')
    setError(null)
    try {
      setReport(await api.inlineSeparatedNotes(true))
    } catch (err) {
      const state = inlineError(err)
      setError(state)
      toast.error(state.message || t('settings.maintenance.inlineNotes.checkFailed'))
    } finally {
      setPhase('idle')
    }
  }

  const runMerge = async () => {
    if (!report) return
    const accepted = await confirm({
      title: t('settings.maintenance.inlineNotes.confirmTitle'),
      message: t('settings.maintenance.inlineNotes.confirmMessage', {
        merge: report.counts.merge,
        history: report.counts.history,
      }),
      confirmText: t('settings.maintenance.inlineNotes.confirmAction'),
      variant: 'warning',
    })
    if (!accepted) return
    setPhase('merging')
    setError(null)
    try {
      const result = await api.inlineSeparatedNotes(false)
      setReport(result)
      const done = result.counts.merged + result.counts.historied
      const failed = result.counts.failed + result.counts.move_failed
      if (result.aborted || failed > 0 || result.audit_error) {
        toast.warning(t('settings.maintenance.inlineNotes.partial', { done, failed }))
      } else {
        toast.success(t('settings.maintenance.inlineNotes.success', { count: done }))
      }
    } catch (err) {
      setError(inlineError(err))
      toast.error(t('settings.maintenance.inlineNotes.mergeFailed'))
    } finally {
      setPhase('idle')
    }
  }

  const counts = report?.counts
  const missing = counts ? counts.skipped_by_reason.missing_file + counts.skipped_by_reason.dangling_row : 0
  const nothingToDo = counts ? counts.actionable === 0 && counts.skipped === 0 && counts.orphan_files === 0 : false
  const executed = report !== null && !report.dry_run
  const partial =
    executed && counts !== undefined && (report.aborted || counts.failed + counts.move_failed > 0 || report.audit_error !== '')
  const noteLabel = (item: { note_id: number; title: string }) => `#${item.note_id} ${item.title}`

  return (
    <div className="rounded-lg bg-bg-elevated p-4" data-testid="inline-notes-card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <FileText size={18} className="shrink-0 text-accent" />
          <span className="font-medium text-text-primary">{t('settings.maintenance.inlineNotes.title')}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={runCheck} disabled={busy} data-testid="inline-notes-check">
            {phase === 'checking' ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            {phase === 'checking'
              ? t('settings.maintenance.inlineNotes.checking')
              : t('settings.maintenance.inlineNotes.check')}
          </Button>
          {report?.dry_run && counts && counts.actionable > 0 && (
            <Button size="sm" variant="primary" onClick={runMerge} disabled={busy} data-testid="inline-notes-merge">
              {phase === 'merging' ? <Loader2 size={14} className="animate-spin" /> : null}
              {phase === 'merging'
                ? t('settings.maintenance.inlineNotes.merging')
                : t('settings.maintenance.inlineNotes.merge', { count: counts.actionable })}
            </Button>
          )}
        </div>
      </div>
      <p className="mb-2 text-xs text-text-muted">{t('settings.maintenance.inlineNotes.description')}</p>

      {error && (
        <div className="mt-2 rounded bg-danger/10 p-2 text-xs text-danger" role="alert" data-testid="inline-notes-error">
          {error.kind === 'unknown'
            ? t('settings.maintenance.inlineNotes.resultUnknown')
            : error.kind === 'nothingChanged'
              ? t('settings.maintenance.inlineNotes.failedNothingChanged', { message: error.message })
              : t('settings.maintenance.inlineNotes.rejected', { message: error.message })}
        </div>
      )}

      {report && counts && (
        <div className="mt-3 space-y-2">
          {!executed && (
            <div className="rounded bg-bg-surface p-2 text-sm text-text-primary" role="status" data-testid="inline-notes-summary">
              {nothingToDo
                ? t('settings.maintenance.inlineNotes.nothingToDo')
                : t('settings.maintenance.inlineNotes.summary', {
                    merge: counts.merge,
                    history: counts.history,
                    missing,
                    other: counts.skipped - missing,
                  })}
            </div>
          )}
          {executed && (
            <div
              className={`space-y-1 rounded p-2 text-xs ${partial ? 'bg-warning/10 text-warning' : 'bg-success/10 text-success'}`}
              role="status"
              data-testid="inline-notes-result"
            >
              <div className="text-sm font-medium">
                {partial
                  ? t('settings.maintenance.inlineNotes.partial', {
                      done: counts.merged + counts.historied,
                      failed: counts.failed + counts.move_failed,
                    })
                  : t('settings.maintenance.inlineNotes.success', { count: counts.merged + counts.historied })}
              </div>
              {report.aborted && <div>{t('settings.maintenance.inlineNotes.aborted')}</div>}
              {report.audit_error && (
                <div className="break-all">
                  {t('settings.maintenance.inlineNotes.auditError', { message: report.audit_error })}
                </div>
              )}
              {report.restore_point && (
                <div className="break-all font-mono">
                  {t('settings.maintenance.inlineNotes.restorePoint', { path: report.restore_point })}
                </div>
              )}
              {report.quarantine_dir && (
                <div className="break-all font-mono">
                  {t('settings.maintenance.inlineNotes.quarantineDir', { path: report.quarantine_dir })}
                </div>
              )}
            </div>
          )}
          {!executed && (
            <>
              <InlineList
                title={t('settings.maintenance.inlineNotes.listMerge')}
                testId="inline-notes-merge-list"
                items={report.merge.map((item) => ({ key: `m${item.attachment_id}`, label: noteLabel(item), detail: item.file_path }))}
              />
              <InlineList
                title={t('settings.maintenance.inlineNotes.listHistory')}
                testId="inline-notes-history-list"
                items={report.history.map((item) => ({ key: `h${item.attachment_id}`, label: noteLabel(item), detail: item.file_path }))}
              />
            </>
          )}
          <InlineList
            title={t('settings.maintenance.inlineNotes.listResults')}
            testId="inline-notes-results"
            items={report.results.map((item) => ({
              key: `r${item.attachment_id}`,
              label: `${noteLabel(item)} · ${t(`settings.maintenance.inlineNotes.status.${item.status}`)}${
                item.reason ? ` · ${reasonLabel(item.reason)}` : ''
              }`,
              detail: item.move_error
                ? t('settings.maintenance.inlineNotes.moveFailed', { message: item.move_error })
                : item.error || item.moved_to || undefined,
            }))}
          />
          <InlineList
            title={t('settings.maintenance.inlineNotes.listSkipped')}
            testId="inline-notes-skipped"
            items={report.skipped.map((item) => ({
              key: `s${item.attachment_id}`,
              label: `${noteLabel(item)} · ${reasonLabel(item.reason)}`,
              detail: item.file_path,
            }))}
          />
          <InlineList
            title={t('settings.maintenance.inlineNotes.listOrphans')}
            testId="inline-notes-orphans"
            items={report.orphan_files.map((item) => ({ key: item.file_path, label: item.file_path }))}
          />
          <InlineList
            title={t('settings.maintenance.inlineNotes.listShared')}
            testId="inline-notes-shared"
            items={report.shared_files.map((item, index) => ({
              key: `${item.file_path}-${index}`,
              label: item.note_ids.map((id) => `#${id}`).join(', '),
              detail: item.file_path,
            }))}
          />
          <InlineList
            title={t('settings.maintenance.inlineNotes.listUnverified')}
            testId="inline-notes-unverified"
            items={report.unverified_rows.map((item) => ({ key: `u${item.attachment_id}`, label: `#${item.note_id}`, detail: item.file_path }))}
          />
          {(counts.skipped > 0 || counts.orphan_files > 0) && (
            <p className="text-xs text-text-muted">{t('settings.maintenance.inlineNotes.manualHint')}</p>
          )}
        </div>
      )}
    </div>
  )
}
