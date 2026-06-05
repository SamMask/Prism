
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
  platform: {
    system: string;
    machine: string;
    hostname: string;
    python_version: string;
  };
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

function formatUptime(seconds: number | null): string {
  if (seconds == null) return '-';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}天 ${hours}時 ${mins}分`;
  if (hours > 0) return `${hours}時 ${mins}分`;
  return `${mins}分`;
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
      toast.success('備份下載已開始');
    } catch (error: any) {
      toast.error('備份下載失敗: ' + (error?.message || '未知錯誤'));
    }
  };

  // Handle backup rotation
  const handleRotateBackups = async () => {
    setIsBackingUp(true);
    try {
      const result = await api.rotateBackups(3);
      toast.success(`備份完成！已建立 ${result.new_backup}，保留 ${result.kept_backups.length} 份`);
      if (result.deleted_backups.length > 0) {
        toast.info(`已清理 ${result.deleted_backups.length} 份舊備份`);
      }
      fetchBackups();
    } catch (error: any) {
      toast.error('備份輪換失敗: ' + (error?.response?.data?.message || error?.message || '未知錯誤'));
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleDeleteBackup = async (backup: BackupInfo) => {
    if (!await confirm({ title: '刪除備份', message: `確定要刪除備份「${backup.filename}」嗎？`, variant: 'danger' })) return;
    setDeletingBackup(backup.filename);
    try {
      await api.deleteBackup(backup.filename);
      toast.success('備份已刪除');
      fetchBackups();
    } catch (error: any) {
      toast.error('刪除備份失敗: ' + (error?.response?.data?.message || error?.message || '未知錯誤'));
    } finally {
      setDeletingBackup(null);
    }
  };

  // Handle service restart
  const handleRestart = async () => {
    if (!await confirm({ title: '重啟服務', message: '確定要重啟 Prism 服務嗎？重啟期間將暫時無法使用。', variant: 'warning' })) return;
    setIsRestarting(true);
    try {
      await api.restartService();
      toast.success('服務重啟指令已發送，頁面將在數秒後自動重新載入...');
      // Auto-reload after a delay
      setTimeout(() => window.location.reload(), 5000);
    } catch (error: any) {
      const msg = error?.response?.data?.message || error?.message || '重啟失敗';
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

  return (
    <div className="glass rounded-lg p-5" data-testid="server-dashboard-section">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Server size={20} className="text-cyan-400" />
          伺服器儀表板
        </h2>
        <Button
          onClick={() => { fetchHardware(); fetchVersion(); fetchBackups(); }}
          variant="ghost"
          className="text-sm"
          disabled={isLoading}
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          重新整理
        </Button>
      </div>

      <div className="mb-4 flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3" data-testid="server-local-only-boundary">
        <Shield size={16} className="mt-0.5 shrink-0 text-amber-400" />
        <div className="space-y-1 text-sm">
          <p className="font-medium text-text-primary">Server controls are local-only.</p>
          <p className="text-text-muted">
            `/api/server/*` 仍由後端限制在 localhost / trusted internal access；這裡只呈現既有控制項，不放寬遠端存取。
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
              {hardware?.platform?.system || '-'} / {hardware?.platform?.machine || '-'}
            </span>
            <span className="bg-bg-base rounded px-2 py-0.5">
              Python {hardware?.platform?.python_version || '-'}
            </span>
            {hardware?.platform?.hostname && (
              <span className="bg-bg-base rounded px-2 py-0.5">
                {hardware.platform.hostname}
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
              更新日誌 ({versionInfo.changelog.length} 筆)
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
            <span className="text-text-secondary text-sm font-medium">記憶體</span>
          </div>
          {hardware?.memory ? (
            <ProgressBar
              percent={hardware.memory.percent}
              label={`${hardware.memory.used_mb.toLocaleString()} / ${hardware.memory.total_mb.toLocaleString()} MB`}
              detail={`可用 ${hardware.memory.available_mb.toLocaleString()} MB`}
            />
          ) : (
            <div className="text-text-muted text-sm">無法取得</div>
          )}
        </div>

        {/* Disk */}
        <div className="bg-bg-elevated rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <HardDrive size={16} className="text-purple-400" />
            <span className="text-text-secondary text-sm font-medium">儲存空間</span>
          </div>
          {hardware?.disk ? (
            <ProgressBar
              percent={hardware.disk.percent}
              label={`${hardware.disk.used_gb} / ${hardware.disk.total_gb} GB`}
              detail={`可用 ${hardware.disk.free_gb} GB`}
            />
          ) : (
            <div className="text-text-muted text-sm">無法取得</div>
          )}
        </div>

        {/* CPU Temp (only for Linux/Pi) */}
        <div className="bg-bg-elevated rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Thermometer size={16} className="text-orange-400" />
            <span className="text-text-secondary text-sm font-medium">CPU 溫度</span>
          </div>
          <div className={`text-2xl font-bold ${getTempColor(hardware?.cpu_temp ?? null)}`}>
            {hardware?.cpu_temp != null ? `${hardware.cpu_temp}°C` : 'N/A'}
          </div>
          <div className="text-xs text-text-muted mt-1">
            {hardware?.cpu_temp == null ? '僅支援 Linux / Raspberry Pi' : 
             hardware.cpu_temp < 50 ? '溫度正常' :
             hardware.cpu_temp < 70 ? '溫度偏高' : '⚠️ 溫度過高'}
          </div>
        </div>

        {/* Database & Uptime */}
        <div className="bg-bg-elevated rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Cpu size={16} className="text-cyan-400" />
            <span className="text-text-secondary text-sm font-medium">系統資訊</span>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">資料庫大小</span>
              <span className="text-text-primary font-mono">
                {hardware?.database?.size_mb ?? '-'} MB
              </span>
            </div>
            {hardware?.database?.wal_size_mb != null && hardware.database.wal_size_mb > 0 && (
              <div className="flex justify-between">
                <span className="text-text-muted">WAL 日誌</span>
                <span className="text-text-primary font-mono">
                  {hardware.database.wal_size_mb} MB
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-text-muted">系統運行</span>
              <span className="text-text-primary">
                <Clock size={12} className="inline mr-1" />
                {formatUptime(hardware?.uptime_seconds ?? null)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ============================================================= */}
      {/* Backup Management */}
      {/* ============================================================= */}
      <div className="bg-bg-elevated rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Shield size={16} className="text-emerald-400" />
            <span className="text-text-secondary text-sm font-medium">資料庫備份</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={handleDownloadBackup}
              variant="ghost"
              className="text-xs"
            >
              <Download size={14} />
              一鍵下載
            </Button>
            <Button
              onClick={handleRotateBackups}
              variant="ghost"
              className="text-xs"
              disabled={isBackingUp}
            >
              <RotateCcw size={14} className={isBackingUp ? 'animate-spin' : ''} />
              {isBackingUp ? '備份中...' : '輪換備份'}
            </Button>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-text-muted mb-2">
          <span>輪換備份會保留最近 3 份；一鍵下載不會自動清理</span>
          <button
            onClick={() => { setShowBackups(!showBackups); if (!showBackups) fetchBackups(); }}
            className="text-text-muted hover:text-text-secondary flex items-center gap-1"
          >
            {showBackups ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {backups.length} 份備份 ({backupTotalMb} MB)
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
                  <span>{new Date(backup.created_at).toLocaleDateString()}</span>
                  <button
                    type="button"
                    onClick={() => handleDeleteBackup(backup)}
                    disabled={deletingBackup === backup.filename}
                    className="inline-flex h-7 w-7 items-center justify-center rounded text-red-400 transition-colors hover:bg-red-500/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label={`刪除備份 ${backup.filename}`}
                    title="刪除備份"
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
            尚無備份，點擊「輪換備份」建立第一份
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
            <span className="text-text-secondary text-sm font-medium">系統日誌</span>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={logLevel}
              onChange={(e) => handleLogLevelChange(e.target.value as 'ALL' | 'WARNING' | 'ERROR')}
              className="text-xs bg-bg-base text-text-secondary rounded px-2 py-1 border border-border-subtle"
            >
              <option value="ALL">全部</option>
              <option value="WARNING">⚠️ 警告</option>
              <option value="ERROR">❌ 錯誤</option>
            </select>
            <Button
              onClick={() => { setShowLogs(!showLogs); if (!showLogs) fetchLogs(); }}
              variant="ghost"
              className="text-xs"
            >
              {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              {showLogs ? '收合' : '展開'}
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
                <span className="text-text-muted">載入中...</span>
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
                <span className="text-text-muted">日誌為空或尚未建立</span>
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
                重新載入
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
                <span className="text-text-secondary text-sm font-medium">服務管理</span>
                <p className="text-xs text-text-muted">透過 Systemd 重啟 Prism 服務</p>
              </div>
            </div>
            <Button
              onClick={handleRestart}
              variant="ghost"
              className="text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10"
              disabled={isRestarting}
            >
              <AlertTriangle size={14} />
              {isRestarting ? '重啟中...' : '重啟服務'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
