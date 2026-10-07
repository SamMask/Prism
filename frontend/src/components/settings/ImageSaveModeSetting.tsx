import { useState } from 'react';
import { toast } from '../ui';
import { useTranslation } from '../../hooks/useTranslation';

export function ImageSaveModeSetting() {
  const { t } = useTranslation();
  const [mode, setMode] = useState(() => localStorage.getItem('imageSaveMode') || 'both');

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-text-primary">{t('settings.appearance.imageSaveMode.title')}</p>
        <p className="text-text-muted text-sm">
          {t('settings.appearance.imageSaveMode.description')}
        </p>
      </div>
      <select
        value={mode}
        onChange={(e) => {
          setMode(e.target.value);
          localStorage.setItem('imageSaveMode', e.target.value);
          const modeKey = e.target.value === 'both'
            ? 'settings.appearance.imageSaveMode.bothLabel'
            : 'settings.appearance.imageSaveMode.thumbnailOnlyLabel';
          toast.success(t('settings.appearance.imageSaveMode.changed', { mode: t(modeKey) }));
        }}
        className="px-4 py-2 rounded-lg
                   bg-bg-elevated border border-border-default
                   text-text-primary
                   focus:outline-none focus:border-primary
                   transition-colors"
        data-testid="image-save-mode-select"
      >
        <option value="both">{t('settings.appearance.imageSaveMode.both')}</option>
        <option value="thumbnail_only">{t('settings.appearance.imageSaveMode.thumbnailOnly')}</option>
      </select>
    </div>
  );
}
