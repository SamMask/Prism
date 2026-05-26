
import { useState } from 'react';
import { RefreshCw, Download, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../../services/api';

interface UpdateInfo {
  current_version: string;
  latest_version: string | null;
  has_update: boolean;
  release_url: string;
  release_notes: string;
  message?: string;
  error?: string;
}

export function UpdateSection() {
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  const checkUpdate = async () => {
    setIsChecking(true);
    try {
      const data = await api.checkUpdate();
      setUpdateInfo(data);
    } catch {
      setUpdateInfo({
        current_version: '未知',
        latest_version: null,
        has_update: false,
        release_url: '',
        release_notes: '',
        error: '無法連接更新伺服器',
      });
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="glass rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <RefreshCw size={20} className="text-primary" />
          版本更新
        </h2>
      </div>

      <div className="space-y-4">
        {/* Current version */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-secondary">目前版本</span>
          <span className="font-mono text-text-primary">
            {updateInfo?.current_version ?? '—'}
          </span>
        </div>

        {/* Latest version (after check) */}
        {updateInfo?.latest_version && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-secondary">最新版本</span>
            <span className="font-mono text-text-primary">{updateInfo.latest_version}</span>
          </div>
        )}

        {/* Status banner */}
        {updateInfo && (
          <div className={`p-3 rounded-lg text-sm flex items-start gap-2 ${
            updateInfo.error
              ? 'bg-red-500/10 border border-red-500/20 text-red-400'
              : updateInfo.has_update
              ? 'bg-amber-500/10 border border-amber-500/20 text-amber-400'
              : 'bg-success/10 border border-success/20 text-success'
          }`}>
            {updateInfo.error ? (
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
            ) : updateInfo.has_update ? (
              <Download size={16} className="mt-0.5 shrink-0" />
            ) : (
              <CheckCircle size={16} className="mt-0.5 shrink-0" />
            )}
            <div>
              {updateInfo.error
                ? updateInfo.error
                : updateInfo.message
                ? updateInfo.message
                : updateInfo.has_update
                ? `發現新版本 v${updateInfo.latest_version}！`
                : '已是最新版本'}
              {updateInfo.release_notes && (
                <p className="mt-1 text-xs opacity-80 whitespace-pre-line line-clamp-3">
                  {updateInfo.release_notes}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Download link */}
        {updateInfo?.has_update && updateInfo.release_url && (
          <a
            href={updateInfo.release_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white
                       text-sm font-medium hover:bg-primary/90 transition-colors w-fit"
          >
            <Download size={16} />
            前往下載頁面
          </a>
        )}

        {/* Check button */}
        <button
          onClick={checkUpdate}
          disabled={isChecking}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border-default
                     text-text-secondary text-sm hover:bg-bg-hover transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isChecking ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <RefreshCw size={16} />
          )}
          {isChecking ? '檢查中...' : '檢查更新'}
        </button>
      </div>
    </div>
  );
}
