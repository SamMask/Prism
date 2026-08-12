import { AlertTriangle } from 'lucide-react'
import type { SearchDiagnostics } from '../services/api'
import { useTranslation } from '../hooks/useTranslation'

interface SearchDiagnosticsNoticeProps {
  diagnostics: SearchDiagnostics | null | undefined
  className?: string
}

export function SearchDiagnosticsNotice({ diagnostics, className = '' }: SearchDiagnosticsNoticeProps) {
  const { locale, t } = useTranslation()
  const scan = diagnostics?.attachment_body_scan
  if (!scan?.partial) return null

  const formatNumber = (value: number) => value.toLocaleString(locale)
  const reason = t(`searchDiagnostics.reasons.${scan.reason || 'scan_error'}`)

  return (
    <div
      className={`rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning ${className}`}
      role="status"
      data-testid="search-diagnostics-notice"
    >
      <div className="flex items-start gap-2">
        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
        <div>
          <div className="font-medium">{t('searchDiagnostics.partialTitle')}</div>
          <div className="mt-0.5 text-text-secondary">
            {t('searchDiagnostics.partialDetail', {
              scannedFiles: formatNumber(scan.scanned_files),
              fileLimit: formatNumber(scan.limits.files),
              scannedBytes: formatNumber(scan.scanned_bytes),
              byteLimit: formatNumber(scan.limits.bytes),
              durationLimit: formatNumber(scan.limits.duration_ms),
              reason,
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
