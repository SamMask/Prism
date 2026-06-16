

import { Database, RefreshCw } from 'lucide-react';
import { Button } from '../ui';
import { useTranslation } from '../../hooks/useTranslation';

interface SystemStats {
  notes_count: number;
  categories_count: number;
  tags_count: number;
  images_count: number;
  total_size_mb: number;
}

interface SystemStatsSectionProps {
  stats: SystemStats | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export function SystemStatsSection({ stats, isLoading, onRefresh }: SystemStatsSectionProps) {
  const { t } = useTranslation();

  return (
    <div className="glass rounded-xl p-6">
      <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Database size={20} className="text-primary" />
        {t('settings.systemStats.title')}
      </h2>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-bg-elevated rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-primary">
            {stats?.notes_count ?? '-'}
          </div>
          <div className="text-text-muted text-sm">{t('settings.systemStats.notes')}</div>
        </div>
        <div className="bg-bg-elevated rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-accent">
            {stats?.categories_count ?? '-'}
          </div>
          <div className="text-text-muted text-sm">{t('settings.systemStats.categories')}</div>
        </div>
        <div className="bg-bg-elevated rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-success">
            {stats?.tags_count ?? '-'}
          </div>
          <div className="text-text-muted text-sm">{t('settings.systemStats.tags')}</div>
        </div>
        <div className="bg-bg-elevated rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-warning">
            {stats?.images_count ?? '-'}
          </div>
          <div className="text-text-muted text-sm">{t('settings.systemStats.images')}</div>
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <Button
          onClick={onRefresh}
          variant="ghost"
          className="text-sm"
          disabled={isLoading}
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          {t('settings.systemStats.refresh')}
        </Button>
      </div>
    </div>
  );
}
