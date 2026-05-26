
import { useState, useEffect } from 'react';
import { Wifi, Save, Loader2, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import { toast } from '../ui/Toast';
import { IconButton } from '../ui';

interface PortConfig {
  preferred_port: number;
  fallback_enabled: boolean;
  fallback_range: number;
  current_port: number;
}

export function PortConfigSection() {
  const [config, setConfig] = useState<PortConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Local edit state
  const [preferredPort, setPreferredPort] = useState(8080);
  const [fallbackEnabled, setFallbackEnabled] = useState(true);
  const [fallbackRange, setFallbackRange] = useState(10);

  const loadConfig = async () => {
    setIsLoading(true);
    try {
      const data = await api.getPortConfig();
      setConfig(data);
      setPreferredPort(data.preferred_port);
      setFallbackEnabled(data.fallback_enabled);
      setFallbackRange(data.fallback_range);
    } catch (error) {
      console.error('Failed to load port config:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const saveConfig = async () => {
    if (preferredPort < 1024 || preferredPort > 65535) {
      toast.error('端口範圍必須在 1024-65535 之間');
      return;
    }
    if (fallbackRange < 1 || fallbackRange > 100) {
      toast.error('備用範圍必須在 1-100 之間');
      return;
    }

    setIsSaving(true);
    try {
      await api.savePortConfig({
        preferred_port: preferredPort,
        fallback_enabled: fallbackEnabled,
        fallback_range: fallbackRange,
      });
      toast.success('端口設定已儲存，重啟後生效');
      loadConfig();
    } catch (error) {
      toast.error('儲存失敗');
    } finally {
      setIsSaving(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  return (
    <div className="glass rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <Wifi size={20} className="text-primary" />
          端口設定
        </h2>
        <IconButton onClick={loadConfig} disabled={isLoading} aria-label="重新載入">
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
        </IconButton>
      </div>

      {isLoading && !config ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 size={24} className="animate-spin text-text-muted" />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Current Port */}
          {config && (
            <div className="p-3 rounded-lg bg-success/5 border border-success/20">
              <p className="text-sm text-success">
                目前使用端口: <strong>{config.current_port}</strong>
              </p>
            </div>
          )}

          {/* Preferred Port */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">
              偏好端口
            </label>
            <input
              type="number"
              value={preferredPort}
              onChange={(e) => setPreferredPort(Number(e.target.value))}
              min={1024}
              max={65535}
              className="w-full px-3 py-2 rounded-lg bg-bg-elevated border border-border-default
                       text-text-primary text-sm focus:outline-none focus:border-primary"
            />
            <p className="text-xs text-text-muted mt-1">
              應用程式啟動時會優先嘗試此端口 (1024-65535)
            </p>
          </div>

          {/* Fallback Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-text-secondary">
                啟用自動備用
              </label>
              <p className="text-xs text-text-muted">
                當偏好端口不可用時，自動嘗試其他端口
              </p>
            </div>
            <button
              onClick={() => setFallbackEnabled(!fallbackEnabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                fallbackEnabled ? 'bg-primary' : 'bg-bg-active'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  fallbackEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Fallback Range */}
          {fallbackEnabled && (
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                備用範圍
              </label>
              <input
                type="number"
                value={fallbackRange}
                onChange={(e) => setFallbackRange(Number(e.target.value))}
                min={1}
                max={100}
                className="w-full px-3 py-2 rounded-lg bg-bg-elevated border border-border-default
                         text-text-primary text-sm focus:outline-none focus:border-primary"
              />
              <p className="text-xs text-text-muted mt-1">
                從偏好端口開始，最多嘗試 {fallbackRange} 個端口
                (範圍: {preferredPort} ~ {preferredPort + fallbackRange - 1})
              </p>
            </div>
          )}

          {/* Save Button */}
          <button
            onClick={saveConfig}
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white
                     text-sm font-medium hover:bg-primary/90 transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Save size={16} />
            )}
            {isSaving ? '儲存中...' : '儲存設定'}
          </button>

          <p className="text-xs text-text-muted">
            💡 端口設定變更需要重新啟動應用程式才會生效。Windows 更新後某些端口可能暫時無法使用，
            建議開啟自動備用功能。
          </p>
        </div>
      )}
    </div>
  );
}
