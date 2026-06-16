import { useState, useEffect } from 'react';
import { ShieldCheck, Loader2, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import { toast } from '../ui/Toast';
import { IconButton } from '../ui';
import { useTranslation } from '../../hooks/useTranslation';

export function SecuritySection() {
  const { t } = useTranslation();
  const [enabled, setEnabled] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = async () => {
    setIsLoading(true);
    try {
      setEnabled(await api.getCsrfProtection());
      setLoaded(true);
    } catch (error) {
      console.error('Failed to load CSRF setting:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggle = async () => {
    const next = !enabled;
    setIsSaving(true);
    try {
      const saved = await api.setCsrfProtection(next);
      setEnabled(saved);
      toast.success(t(saved ? 'settings.security.enabledToast' : 'settings.security.disabledToast'));
    } catch (error) {
      toast.error(t('settings.security.saveFailed'));
    } finally {
      setIsSaving(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="glass rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <ShieldCheck size={20} className="text-primary" />
          {t('settings.security.title')}
        </h2>
        <IconButton onClick={load} disabled={isLoading} aria-label={t('settings.security.reload')}>
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
        </IconButton>
      </div>

      {isLoading && !loaded ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 size={24} className="animate-spin text-text-muted" />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="pr-4">
              <label className="text-sm font-medium text-text-secondary">
                {t('settings.security.verifyOrigin')}
              </label>
              <p className="text-xs text-text-muted">
                {t('settings.security.description')}
              </p>
            </div>
            <button
              onClick={toggle}
              disabled={isSaving}
              role="switch"
              aria-checked={enabled}
              data-testid="csrf-toggle"
              className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
                enabled ? 'bg-primary' : 'bg-bg-active'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {!enabled && (
            <div className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs text-warning">
              {t('settings.security.disabledWarning')}
            </div>
          )}

          <p className="text-xs text-text-muted">
            {t('settings.security.restartNotRequired')}
          </p>
        </div>
      )}
    </div>
  );
}
