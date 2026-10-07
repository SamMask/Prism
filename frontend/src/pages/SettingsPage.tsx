
import { ReactNode, useState, useEffect } from 'react';
import { Database, FolderOpen, Image, Info, Palette, Shield, Wrench, ArchiveRestore } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { DataManager } from '../components/DataManager';
import { SystemMaintenance } from '../components/SystemMaintenance';
import { useAppStore } from '../stores/appStore';
import { AppearanceSection } from '../components/settings/AppearanceSection';
import { ImageSaveModeSetting } from '../components/settings/ImageSaveModeSetting';
import { BackupImportSection } from '../components/settings/BackupImportSection';
import { DangerZoneSection } from '../components/settings/DangerZoneSection';
import { SystemStatsSection } from '../components/settings/SystemStatsSection';
import { SecuritySection } from '../components/settings/SecuritySection';
import { ServerDashboardSection } from '../components/settings/ServerDashboardSection';
import { useTranslation } from '../hooks/useTranslation';

interface SystemStats {
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
  { id: 'backup', label: '資料與復原', labelKey: 'settings.tabs.backup', icon: <ArchiveRestore size={16} /> },
  { id: 'maintenance', label: '維護與健康', labelKey: 'settings.tabs.maintenance', icon: <Wrench size={16} /> },
  { id: 'access', label: '存取與系統', labelKey: 'settings.tabs.access', icon: <Shield size={16} /> },
  { id: 'about', label: '關於', labelKey: 'settings.tabs.about', icon: <Info size={16} /> },
];

const SETTINGS_TAB_IDS = SETTINGS_TABS.map((tab) => tab.id);

// Alternate ?tab= values that map to a current tab id; current ids stay valid as-is.
const SETTINGS_TAB_ALIASES: Record<string, SettingsTab> = { data: 'backup' };

function isSettingsTab(value: string | null): value is SettingsTab {
  return SETTINGS_TAB_IDS.includes(value as SettingsTab);
}

function resolveSettingsTab(value: string | null): SettingsTab {
  const normalized = value ? SETTINGS_TAB_ALIASES[value] ?? value : null;
  return isSettingsTab(normalized) ? normalized : 'appearance';
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
  const { categories, appVersion } = useAppStore();
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const tabParam = searchParams.get('tab');
  const activeTab: SettingsTab = resolveSettingsTab(tabParam);

  const setActiveTab = (tab: SettingsTab) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('tab', tab);
    setSearchParams(nextParams, { replace: true });
  };

  // Fetch system stats
  const fetchStats = async () => {
    setIsLoading(true);
    try {
      const [response, testResponse] = await Promise.all([
        fetch('/api/system/stats'),
        fetch('/api/test'),
      ]);
      const body = await response.json();
      const test = await testResponse.json();
      if (body.status === 'success') {
        const db = body.data?.database;
        const uploads = body.data?.uploads;
        setStats({
          // Same definition as Sidebar / Header / Footer: archived notes are not part of the Library total.
          notes_count: (db?.notes_count || 0) - (db?.archived_count || 0),
          categories_count: test.stats?.categories_count || 0,
          tags_count: db?.tags_count || 0,
          images_count: uploads?.files || 0,
          total_size_mb: uploads?.size_mb || 0,
        });
      }
      // Reuse this /api/test response instead of requesting it again for the shared Library total.
      if (typeof test.stats?.library_count === 'number') useAppStore.setState({ libraryTotal: test.stats.library_count });
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
              <SectionPanel title={t('settings.maintenance.imagesStorage.title')} icon={<Image size={20} className="text-primary" />} testId="settings-images-storage">
                <p className="mb-4 text-sm text-text-muted">{t('settings.maintenance.imagesStorage.description')}</p>
                <div className="space-y-5">
                  <ImageSaveModeSetting />
                  <DangerZoneSection />
                </div>
              </SectionPanel>
              <SystemStatsSection
                stats={stats}
                isLoading={isLoading}
                onRefresh={fetchStats}
              />
              <details className="glass rounded-lg" data-testid="maintenance-advanced">
                <summary className="cursor-pointer px-5 py-4 font-medium text-text-primary">
                  {t('settings.maintenance.advancedTitle')}
                </summary>
                <div className="border-t border-border-subtle p-5">
                  <p className="mb-4 text-sm text-text-muted">{t('settings.maintenance.advancedDescription')}</p>
                  <ServerDashboardSection />
                </div>
              </details>
            </>
          )}

          {activeTab === 'access' && (
            <>
              <SecuritySection />
            </>
          )}

          {activeTab === 'about' && (
            <SectionPanel title={t('settings.about.title')} icon={<Info size={20} className="text-primary" />} testId="settings-about">
              <div className="space-y-2 text-text-secondary">
                <p><strong className="text-text-primary">Prism</strong></p>
                {appVersion && <p>{t('settings.about.version', { version: appVersion })}</p>}
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

    </>
  );
}
