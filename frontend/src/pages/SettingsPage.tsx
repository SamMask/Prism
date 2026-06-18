
import { ReactNode, useState, useEffect } from 'react';
import { Database, FolderOpen, Info, Palette, Shield, Wrench, ArchiveRestore } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { ToastContainer } from '../components/ui/Toast';
import { DataManager } from '../components/DataManager';
import { SystemMaintenance } from '../components/SystemMaintenance';
import { useAppStore } from '../stores/appStore';
import { AppearanceSection } from '../components/settings/AppearanceSection';
import { BackupImportSection } from '../components/settings/BackupImportSection';
import { DangerZoneSection } from '../components/settings/DangerZoneSection';
import { SystemStatsSection } from '../components/settings/SystemStatsSection';
import { SecuritySection } from '../components/settings/SecuritySection';
import { ServerDashboardSection } from '../components/settings/ServerDashboardSection';
import { useTranslation } from '../hooks/useTranslation';

interface SystemStats {
  version?: string;
  notes_count: number;
  categories_count: number;
  tags_count: number;
  images_count: number;
  total_size_mb: number;
}

type SettingsTab = 'appearance' | 'organization' | 'backup' | 'maintenance' | 'access' | 'about';

interface SettingsTabConfig {
  id: SettingsTab;
  label: string;
  labelKey: string;
  icon: ReactNode;
}

const SETTINGS_TABS: SettingsTabConfig[] = [
  { id: 'appearance', label: '外觀', labelKey: 'settings.tabs.appearance', icon: <Palette size={16} /> },
  { id: 'organization', label: '組織', labelKey: 'settings.tabs.organization', icon: <FolderOpen size={16} /> },
  { id: 'backup', label: '備份與還原', labelKey: 'settings.tabs.backup', icon: <ArchiveRestore size={16} /> },
  { id: 'maintenance', label: '維護與健康', labelKey: 'settings.tabs.maintenance', icon: <Wrench size={16} /> },
  { id: 'access', label: '存取與系統', labelKey: 'settings.tabs.access', icon: <Shield size={16} /> },
  { id: 'about', label: '關於', labelKey: 'settings.tabs.about', icon: <Info size={16} /> },
];

const SETTINGS_TAB_IDS = SETTINGS_TABS.map((tab) => tab.id);

function isSettingsTab(value: string | null): value is SettingsTab {
  return SETTINGS_TAB_IDS.includes(value as SettingsTab);
}

function SectionPanel({
  title,
  icon,
  children,
  testId,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  testId?: string;
}) {
  return (
    <section className="glass rounded-lg p-5" data-testid={testId}>
      <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        {icon}
        {title}
      </h2>
      {children}
    </section>
  );
}

export function SettingsPage() {
  const { categories } = useAppStore();
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const tabParam = searchParams.get('tab');
  const activeTab: SettingsTab = isSettingsTab(tabParam) ? tabParam : 'appearance';

  const setActiveTab = (tab: SettingsTab) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('tab', tab);
    setSearchParams(nextParams, { replace: true });
  };

  // Fetch system stats
  const fetchStats = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/test');
      const data = await response.json();
      if (data.status === 'ok') {
        setStats({
          version: data.version,
          notes_count: data.stats?.notes_count || 0,
          categories_count: data.stats?.categories_count || 0,
          tags_count: data.stats?.tags_count || 0,
          images_count: 0,
          total_size_mb: 0,
        });
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <>
      <div className="mx-auto max-w-5xl space-y-5" data-testid="settings-page">
        {/* Header */}
        <div className="glass rounded-lg p-5">
          <h1 className="text-2xl font-bold gradient-text mb-2">{t('settings.title')}</h1>
          <p className="text-text-secondary">
            {t('settings.subtitle')}
          </p>
        </div>

        <div className="flex gap-2 overflow-x-auto border-b border-border-subtle pb-2" role="tablist" aria-label={t('settings.title')} data-testid="settings-tabs">
          {SETTINGS_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              data-testid={`settings-tab-${tab.id}`}
              className={`flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'bg-bg-elevated text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              }`}
            >
              {tab.icon}
              {t(tab.labelKey)}
            </button>
          ))}
        </div>

        <div className="space-y-5" data-testid={`settings-panel-${activeTab}`}>
          {activeTab === 'appearance' && (
            <AppearanceSection categories={categories} />
          )}

          {activeTab === 'organization' && (
            <SectionPanel title={t('settings.organization.title')} icon={<FolderOpen size={20} className="text-primary" />} testId="settings-organization-taxonomy">
              <DataManager />
            </SectionPanel>
          )}

          {activeTab === 'backup' && (
            <BackupImportSection onStatsUpdate={fetchStats} />
          )}

          {activeTab === 'maintenance' && (
            <>
              <SectionPanel title={t('settings.maintenance.title')} icon={<Database size={20} className="text-warning" />} testId="settings-maintenance-health">
                <SystemMaintenance />
              </SectionPanel>
              <SystemStatsSection
                stats={stats}
                isLoading={isLoading}
                onRefresh={fetchStats}
              />
              {/* 「部署安全邊界」「端口設定」「版本更新」暫時隱藏：封裝成 .exe 視窗程式後對使用者無用，
                  在 Pi 上也僅資訊性。元件檔仍保留於 components/settings（PortConfigSection / UpdateSection）。
                  隱藏理由與復原方式見 docs/TODO.md「設定精簡（hidden sections）」。 */}
              <ServerDashboardSection />
            </>
          )}

          {activeTab === 'access' && (
            <>
              <SecuritySection />
              <DangerZoneSection />
            </>
          )}

          {activeTab === 'about' && (
            <SectionPanel title={t('settings.about.title')} icon={<Info size={20} className="text-primary" />} testId="settings-about">
              <div className="space-y-2 text-text-secondary">
                <p><strong className="text-text-primary">Prism</strong></p>
                <p>{t('settings.about.version', { version: stats?.version || '2.5' })}</p>
                <p>{t('settings.about.frontend')}</p>
                <p>{t('settings.about.backend')}</p>
                <p className="text-text-muted text-sm pt-2">
                  {t('settings.about.summary')}
                </p>
                <p className="text-text-muted text-sm">
                  {t('settings.about.data')}
                </p>
              </div>
            </SectionPanel>
          )}
        </div>
      </div>

      <ToastContainer />
    </>
  );
}
