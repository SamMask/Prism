
import { useState, useEffect, useCallback } from 'react';
import {
  Server,
  Cpu,
  HardDrive,
  MemoryStick,
  Thermometer,
  RefreshCw,
  Download,
  RotateCcw,
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle,
  Power,
  ChevronDown,
  ChevronUp,
  Shield,
  Tag,
  Trash2,
} from 'lucide-react';
import { Button } from '../ui';
import { api } from '../../services/api';
import { toast } from '../ui/Toast';
import { confirm } from '../ui/ConfirmDialog';
import { useTranslation } from '../../hooks/useTranslation';

// ===================================================================
// Types
// ===================================================================

interface HardwareStatus {
  cpu_temp: number | null;
  memory: {
    total_mb: number;
    used_mb: number;
    available_mb: number;
    percent: number;
  } | null;
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  } | null;
  database: {
    size_mb: number;
    wal_size_mb: number;
  } | null;
  data_dir?: string;
  platform: {
    system: string;
    machine: string;
    hostname: string;
    go_version: string;
  } | string;
  service_management?: {
    available: boolean;
    reason: string;
  };
  uptime_seconds: number | null;
}

interface VersionInfo {
  version: string;
  changelog: Array<{
    date: string;
    title: string;
    body: string;
  }>;
  is_frozen: boolean;
  v2_mode: boolean;
  platform: string;
}

interface BackupInfo {
  filename: string;
  size_mb: number;
  created_at: string;
}

// ===================================================================
// Helpers
// ===================================================================

type Translator = (key: string, params?: Record<string, string | number>) => string;

function formatUptime(seconds: number | null, t: Translator): string {
  if (seconds == null) return '-';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return t('settings.serverDashboard.uptimeDays', { days, hours, mins });
  if (hours > 0) return t('settings.serverDashboard.uptimeHours', { hours, mins });
  return t('settings.serverDashboard.uptimeMinutes', { mins });
}

function getProgressColor(percent: number): string {
  if (percent < 60) return 'bg-emerald-500';
  if (percent < 80) return 'bg-amber-500';
  return 'bg-red-500';
}

function getProgressTextColor(percent: number): string {
  if (percent < 60) return 'text-emerald-400';
  if (percent < 80) return 'text-amber-400';
  return 'text-red-400';
}

function getTempColor(temp: number | null): string {
  if (temp == null) return 'text-text-muted';
  if (temp < 50) return 'text-emerald-400';
  if (temp < 70) return 'text-amber-400';
  return 'text-red-400';
}

function getPlatformSystem(platform: HardwareStatus['platform'] | undefined): string {
  if (!platform) return '';
  if (typeof platform === 'string') return platform;
  return platform.system || '';
}

function getPlatformMachine(platform: HardwareStatus['platform'] | undefined): string {
  if (!platform || typeof platform === 'string') return '';
  return platform.machine || '';
}

function getPlatformHostname(platform: HardwareStatus['platform'] | undefined): string {
  if (!platform || typeof platform === 'string') return '';
  return platform.hostname || '';
}

function getPlatformGoVersion(platform: HardwareStatus['platform'] | undefined): string {
  if (!platform || typeof platform === 'string') return '';
  return platform.go_version || '';
}

// ===================================================================
// Progress Bar Sub-component
// ===================================================================

function ProgressBar({ percent, label, detail }: { percent: number; label: string; detail: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-text-secondary">{label}</span>
        <span className={getProgressTextColor(percent)}>{percent}%</span>
      </div>
      <div className="w-full bg-bg-elevated rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${getProgressColor(percent)}`}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      <div className="text-xs text-text-muted mt-1">{detail}</div>
    </div>
  );
}

// ===================================================================
// Main Component
// ===================================================================

export function ServerDashboardSection() {
  const { locale, t } = useTranslation();
  const [hardware, setHardware] = useState<HardwareStatus | null>(null);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [backupTotalMb, setBackupTotalMb] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [logLevel, setLogLevel] = useState<'ALL' | 'WARNING' | 'ERROR'>('ALL');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [deletingBackup, setDeletingBackup] = useState<string | null>(null);
  const [isRestarting, setIsRestarting] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [showChangelog, setShowChangelog] = useState(false);
  const [showBackups, setShowBackups] = useState(false);

  // Fetch hardware status
  const fetchHardware = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.getHardwareStatus();
      setHardware(data);
    } catch (error: any) {
      console.error('Failed to fetch hardware status:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch version info
  const fetchVersion = useCallback(async () => {
    try {
      const data = await api.getVersionInfo();
      setVersionInfo(data);
    } catch (error: any) {
      console.error('Failed to fetch version info:', error);
    }
  }, []);

  // Fetch backups
  const fetchBackups = useCallback(async () => {
    try {
      const data = await api.listBackups();
      setBackups(data.backups);
      setBackupTotalMb(data.total_size_mb);
    } catch (error: any) {
      console.error('Failed to fetch backups:', error);
    }
  }, []);

  // Fetch logs
  const fetchLogs = useCallback(async (level?: 'ALL' | 'WARNING' | 'ERROR') => {
    setIsLoadingLogs(true);
    try {
      const data = await api.getServerLogs(100, level || logLevel);
      setLogs(data.lines || []);
    } catch (error: any) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setIsLoadingLogs(false);
    }
  }, [logLevel]);

  // Handle backup download
  const handleDownloadBackup = async () => {
    try {
      await api.downloadBackup();
      toast.success(t('settings.serverDashboard.dbDownloadStarted'));
      await fetchBackups();
    } catch (error: any) {
      toast.error(t('settings.serverDashboard.dbDownloadFailed', { message: error?.message || t('settings.serverDashboard.unknownError') }));
    }
  };

  // Handle backup rotation
  const handleRotateBackups = async () => {
    setIsBackingUp(true);
    try {
      const result = await api.rotateBackups(3);
      toast.success(t('settings.serverDashboard.restorePointCreated', { name: result.new_backup, count: result.kept_backups.length }));
      if (result.deleted_backups.length > 0) {
        toast.info(t('settings.serverDashboard.oldRestorePointsDeleted', { count: result.deleted_backups.length }));
      }
      fetchBackups();
    } catch (error: any) {
      toast.error(t('settings.serverDashboard.createRestorePointFailed', { message: error?.response?.data?.message || error?.message || t('settings.serverDashboard.unknownError') }));
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleDeleteBackup = async (backup: BackupInfo) => {
    if (!await confirm({
      title: t('settings.serverDashboard.deleteRestorePointTitle'),
      message: t('settings.serverDashboard.deleteRestorePointMessage', { name: backup.filename }),
      variant: 'danger',
    })) return;
    setDeletingBackup(backup.filename);
    try {
      await api.deleteBackup(backup.filename);
      toast.success(t('settings.serverDashboard.restorePointDeleted'));
      fetchBackups();
    } catch (error: any) {
      toast.error(t('settings.serverDashboard.deleteRestorePointFailed', { message: error?.response?.data?.message || error?.message || t('settings.serverDashboard.unknownError') }));
    } finally {
      setDeletingBackup(null);
    }
  };

  // Handle service restart
  const handleRestart = async () => {
    if (!await confirm({
      title: t('settings.serverDashboard.restartServiceTitle'),
      message: t('settings.serverDashboard.restartServiceMessage'),
      variant: 'warning',
    })) return;
    setIsRestarting(true);
    try {
      await api.restartService();
      toast.success(t('settings.serverDashboard.restartCommandSent'));
      // Auto-reload after a delay
      setTimeout(() => window.location.reload(), 5000);
    } catch (error: any) {
      const msg = error?.response?.data?.message || error?.message || t('settings.serverDashboard.restartFailed');
      toast.error(msg);
      setIsRestarting(false);
    }
  };

  // Handle log level change
  const handleLogLevelChange = (level: 'ALL' | 'WARNING' | 'ERROR') => {
    setLogLevel(level);
    fetchLogs(level);
  };

  useEffect(() => {
    fetchHardware();
    fetchVersion();
    fetchBackups();
  }, [fetchHardware, fetchVersion, fetchBackups]);

  const canManageService = hardware?.service_management?.available === true;
  const hasCpuTemperature = hardware?.cpu_temp != null;
  const platformSystem = getPlatformSystem(hardware?.platform);
  const platformMachine = getPlatformMachine(hardware?.platform);
  const platformHostname = getPlatformHostname(hardware?.platform);
  const platformGoVersion = getPlatformGoVersion(hardware?.platform);
  const normalizedPlatformSystem = platformSystem.toLowerCase();
  const isWindowsPlatform = normalizedPlatformSystem === 'windows' || normalizedPlatformSystem.startsWith('windows/');
  const showCpuTemperature = hasCpuTemperature && !isWindowsPlatform;

  return (
    <div className="glass rounded-lg p-5" data-testid="server-dashboard-section">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Server size={20} className="text-cyan-400" />
          {t('settings.serverDashboard.title')}
        </h2>
        <Button
          onClick={() => { fetchHardware(); fetchVersion(); fetchBackups(); }}
          variant="ghost"
          className="text-sm"
          disabled={isLoading}
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          {t('settings.serverDashboard.refresh')}
        </Button>
      </div>

      <div className="mb-4 flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3" data-testid="server-local-only-boundary">
        <Shield size={16} className="mt-0.5 shrink-0 text-amber-400" />
        <div className="space-y-1 text-sm">
          <p className="font-medium text-text-primary">{t('settings.serverDashboard.localOnlyTitle')}</p>
          <p className="text-text-muted">
            {t('settings.serverDashboard.localOnlyDescription')}
          </p>
        </div>
      </div>

      {/* ============================================================= */}
      {/* Version & Platform Info */}
      {/* ============================================================= */}
      <div className="bg-bg-elevated rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Tag size={16} className="text-primary" />
            <div>
              <span className="text-text-primary font-medium">Prism </span>
              <span className="text-primary font-mono font-bold">
                v{versionInfo?.version || '-'}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span className="bg-bg-base rounded px-2 py-0.5">
              {platformSystem || '-'} / {platformMachine || '-'}
            </span>
            <span className="bg-bg-base rounded px-2 py-0.5">
              Go {platformGoVersion || '-'}
            </span>
            {platformHostname && (
              <span className="bg-bg-base rounded px-2 py-0.5">
                {platformHostname}
              </span>
            )}
          </div>
        </div>

        {/* Changelog toggle */}
        {versionInfo?.changelog && versionInfo.changelog.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setShowChangelog(!showChangelog)}
              className="text-xs text-text-muted hover:text-text-secondary flex items-center gap-1 transition-colors"
            >
              {showChangelog ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {t('settings.serverDashboard.changelogCount', { count: versionInfo.changelog.length })}
            </button>
            {showChangelog && (
              <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                {versionInfo.changelog.map((entry, i) => (
                  <div key={i} className="text-xs bg-bg-base rounded p-2">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-primary font-mono">{entry.date}</span>
                      <span className="text-text-secondary">{entry.title}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ============================================================= */}
      {/* Hardware Monitoring Grid */}
      {/* ============================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* Memory */}
        <div className="bg-bg-elevated rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <MemoryStick size={16} className="text-blue-400" />
            <span className="text-text-secondary text-sm font-medium">{t('settings.serverDashboard.memory')}</span>
          </div>
          {hardware?.memory ? (
            <ProgressBar
              percent={hardware.memory.percent}
              label={`${hardware.memory.used_mb.toLocaleString(locale)} / ${hardware.memory.total_mb.toLocaleString(locale)} MB`}
              detail={t('settings.serverDashboard.availableMb', { value: hardware.memory.available_mb.toLocaleString(locale) })}
            />
          ) : (
            <div className="text-text-muted text-sm">{t('settings.serverDashboard.unavailable')}</div>
          )}
        </div>

        {/* Disk */}
        <div className="bg-bg-elevated rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <HardDrive size={16} className="text-purple-400" />
            <span className="text-text-secondary text-sm font-medium">{t('settings.serverDashboard.storage')}</span>
          </div>
          {hardware?.disk ? (
            <ProgressBar
              percent={hardware.disk.percent}
              label={`${hardware.disk.used_gb} / ${hardware.disk.total_gb} GB`}
              detail={t('settings.serverDashboard.availableGb', { value: hardware.disk.free_gb })}
            />
          ) : (
            <div className="text-text-muted text-sm">{t('settings.serverDashboard.unavailable')}</div>
          )}
        </div>

        {showCpuTemperature ? (
          <div className="bg-bg-elevated rounded-lg p-4" data-testid="cpu-temperature-card">
            <div className="flex items-center gap-2 mb-3">
              <Thermometer size={16} className="text-orange-400" />
              <span className="text-text-secondary text-sm font-medium">{t('settings.serverDashboard.cpuTemperature')}</span>
            </div>
            <div className={`text-2xl font-bold ${getTempColor(hardware?.cpu_temp ?? null)}`}>
              {hardware?.cpu_temp != null ? `${hardware.cpu_temp}°C` : 'N/A'}
            </div>
            <div className="text-xs text-text-muted mt-1">
              {hardware.cpu_temp! < 50 ? t('settings.serverDashboard.tempNormal') :
               hardware.cpu_temp! < 70 ? t('settings.serverDashboard.tempHigh') : t('settings.serverDashboard.tempCritical')}
            </div>
          </div>
        ) : (
          <div className="bg-bg-elevated rounded-lg p-4" data-testid="data-location-card">
            <div className="flex items-center gap-2 mb-3">
              <FileText size={16} className="text-cyan-400" />
              <span className="text-text-secondary text-sm font-medium">{t('settings.serverDashboard.dataLocation')}</span>
            </div>
            <div className="text-sm font-mono text-text-primary break-all" title={hardware?.data_dir || ''}>
              {hardware?.data_dir || '-'}
            </div>
            <div className="text-xs text-text-muted mt-1">
              {t('settings.serverDashboard.currentDataFolder')}
            </div>
          </div>
        )}

        {/* Database & Uptime */}
        <div className="bg-bg-elevated rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
            {showCpuTemperature ? (
              <Cpu size={16} className="text-cyan-400" />
            ) : (
              <FileText size={16} className="text-cyan-400" />
            )}
            <span className="text-text-secondary text-sm font-medium">
              {showCpuTemperature ? t('settings.serverDashboard.systemInfo') : t('settings.serverDashboard.databaseStatus')}
            </span>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">{t('settings.serverDashboard.databaseSize')}</span>
              <span className="text-text-primary font-mono">
                {hardware?.database?.size_mb ?? '-'} MB
              </span>
            </div>
            {hardware?.database?.wal_size_mb != null && (!showCpuTemperature || hardware.database.wal_size_mb > 0) && (
              <div className="flex justify-between">
                <span className="text-text-muted">{t('settings.serverDashboard.walLog')}</span>
                <span className="text-text-primary font-mono">
                  {hardware.database.wal_size_mb} MB
                </span>
              </div>
            )}
            {showCpuTemperature && (
              <div className="flex justify-between">
                <span className="text-text-muted">{t('settings.serverDashboard.uptime')}</span>
                <span className="text-text-primary">
                  <Clock size={12} className="inline mr-1" />
                  {formatUptime(hardware?.uptime_seconds ?? null, t)}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ============================================================= */}
      {/* Restore Point Management */}
      {/* ============================================================= */}
      <div className="bg-bg-elevated rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Shield size={16} className="text-emerald-400" />
            <span className="text-text-secondary text-sm font-medium">{t('settings.serverDashboard.restorePoints')}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={handleDownloadBackup}
              variant="ghost"
              className="text-xs"
            >
              <Download size={14} />
              {t('settings.serverDashboard.downloadCurrentDb')}
            </Button>
            <Button
              onClick={handleRotateBackups}
              variant="ghost"
              className="text-xs"
              disabled={isBackingUp}
            >
              <RotateCcw size={14} className={isBackingUp ? 'animate-spin' : ''} />
              {isBackingUp ? t('settings.serverDashboard.creating') : t('settings.serverDashboard.createRestorePoint')}
            </Button>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-text-muted mb-2">
          <span>{t('settings.serverDashboard.restorePointDescription')}</span>
          <button
            onClick={() => { setShowBackups(!showBackups); if (!showBackups) fetchBackups(); }}
            className="text-text-muted hover:text-text-secondary flex items-center gap-1"
          >
            {showBackups ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {t('settings.serverDashboard.restorePointCount', { count: backups.length, mb: backupTotalMb })}
          </button>
        </div>

        {showBackups && backups.length > 0 && (
          <div className="space-y-1 mt-2">
            {backups.map((backup, i) => (
              <div key={backup.filename} className="flex items-center justify-between text-xs bg-bg-base rounded p-2">
                <div className="flex items-center gap-2">
                  {i === 0 ? (
                    <CheckCircle size={12} className="text-emerald-400" />
                  ) : (
                    <FileText size={12} className="text-text-muted" />
                  )}
                  <span className="font-mono text-text-secondary">{backup.filename}</span>
                </div>
                <div className="flex items-center gap-3 text-text-muted">
                  <span>{backup.size_mb} MB</span>
                  <span>{new Date(backup.created_at).toLocaleDateString(locale)}</span>
                  <button
                    type="button"
                    onClick={() => handleDeleteBackup(backup)}
                    disabled={deletingBackup === backup.filename}
                    className="inline-flex h-7 w-7 items-center justify-center rounded text-red-400 transition-colors hover:bg-red-500/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label={t('settings.serverDashboard.deleteRestorePointLabel', { name: backup.filename })}
                    title={t('settings.serverDashboard.deleteRestorePointTitle')}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {showBackups && backups.length === 0 && (
          <div className="text-xs text-text-muted text-center py-2">
            {t('settings.serverDashboard.noRestorePoints')}
          </div>
        )}
      </div>

      {/* ============================================================= */}
      {/* Log Viewer */}
      {/* ============================================================= */}
      <div className="bg-bg-elevated rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText size={16} className="text-amber-400" />
            <span className="text-text-secondary text-sm font-medium">{t('settings.serverDashboard.systemLogs')}</span>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={logLevel}
              onChange={(e) => handleLogLevelChange(e.target.value as 'ALL' | 'WARNING' | 'ERROR')}
              className="text-xs bg-bg-base text-text-secondary rounded px-2 py-1 border border-border-subtle"
            >
              <option value="ALL">{t('settings.serverDashboard.logAll')}</option>
              <option value="WARNING">{t('settings.serverDashboard.logWarning')}</option>
              <option value="ERROR">{t('settings.serverDashboard.logError')}</option>
            </select>
            <Button
              onClick={() => { setShowLogs(!showLogs); if (!showLogs) fetchLogs(); }}
              variant="ghost"
              className="text-xs"
            >
              {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              {showLogs ? t('settings.serverDashboard.collapse') : t('settings.serverDashboard.expand')}
            </Button>
          </div>
        </div>

        {showLogs && (
          <>
            <div
              className="bg-bg-base rounded p-3 font-mono text-xs leading-relaxed max-h-64 overflow-y-auto"
              style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}
            >
              {isLoadingLogs ? (
                <span className="text-text-muted">{t('common.loading')}</span>
              ) : logs.length > 0 ? (
                logs.map((line, i) => (
                  <div
                    key={i}
                    className={
                      line.includes('[ERROR]') ? 'text-red-400' :
                      line.includes('[WARNING]') ? 'text-amber-400' :
                      'text-text-muted'
                    }
                  >
                    {line}
                  </div>
                ))
              ) : (
                <span className="text-text-muted">{t('settings.serverDashboard.logsEmpty')}</span>
              )}
            </div>
            <div className="mt-2 flex justify-end">
              <Button
                onClick={() => fetchLogs()}
                variant="ghost"
                className="text-xs"
                disabled={isLoadingLogs}
              >
                <RefreshCw size={12} className={isLoadingLogs ? 'animate-spin' : ''} />
                {t('settings.serverDashboard.reload')}
              </Button>
            </div>
          </>
        )}
      </div>

      {/* ============================================================= */}
      {/* Service Restart (Linux only) */}
      {/* ============================================================= */}
      {canManageService && (
        <div className="bg-bg-elevated rounded-lg p-4 border border-red-500/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Power size={16} className="text-red-400" />
              <div>
                <span className="text-text-secondary text-sm font-medium">{t('settings.serverDashboard.serviceManagement')}</span>
                <p className="text-xs text-text-muted">{t('settings.serverDashboard.serviceManagementDescription')}</p>
              </div>
            </div>
            <Button
              onClick={handleRestart}
              variant="ghost"
              className="text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10"
              disabled={isRestarting}
            >
              <AlertTriangle size={14} />
              {isRestarting ? t('settings.serverDashboard.restarting') : t('settings.serverDashboard.restartService')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
