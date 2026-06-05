
import { ReactNode, useState, useEffect } from 'react';
import { Database, FolderOpen, Info, Palette, Rocket, Search, ShieldAlert } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { ToastContainer } from '../components/ui/Toast';
import { DataManager } from '../components/DataManager';
import { SystemMaintenance } from '../components/SystemMaintenance';
import { useAppStore } from '../stores/appStore';
import { AppearanceSection } from '../components/settings/AppearanceSection';
import { BackupImportSection } from '../components/settings/BackupImportSection';
import { DangerZoneSection } from '../components/settings/DangerZoneSection';
import { SystemStatsSection } from '../components/settings/SystemStatsSection';
import { PortConfigSection } from '../components/settings/PortConfigSection';
import { UpdateSection } from '../components/settings/UpdateSection';
import { ServerDashboardSection } from '../components/settings/ServerDashboardSection';

interface SystemStats {
  version?: string;
  notes_count: number;
  categories_count: number;
  tags_count: number;
  images_count: number;
  total_size_mb: number;
}

type SettingsTab = 'appearance' | 'data' | 'search' | 'deploy' | 'about';

interface SettingsTabConfig {
  id: SettingsTab;
  label: string;
  icon: ReactNode;
}

const SETTINGS_TABS: SettingsTabConfig[] = [
  { id: 'appearance', label: '外觀', icon: <Palette size={16} /> },
  { id: 'data', label: '資料', icon: <Database size={16} /> },
  { id: 'search', label: '搜尋', icon: <Search size={16} /> },
  { id: 'deploy', label: '部署', icon: <Rocket size={16} /> },
  { id: 'about', label: '關於', icon: <Info size={16} /> },
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
          <h1 className="text-2xl font-bold gradient-text mb-2">設定</h1>
          <p className="text-text-secondary">
            管理應用程式偏好設定與資料
          </p>
        </div>

        <div className="flex gap-2 overflow-x-auto border-b border-border-subtle pb-2" role="tablist" aria-label="設定分類" data-testid="settings-tabs">
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
              {tab.label}
            </button>
          ))}
        </div>

        <div className="space-y-5" data-testid={`settings-panel-${activeTab}`}>
          {activeTab === 'appearance' && (
            <AppearanceSection categories={categories} />
          )}

          {activeTab === 'data' && (
            <>
              <SectionPanel title="資料庫維護（進階）" icon={<Database size={20} className="text-warning" />} testId="settings-data-maintenance">
                <SystemMaintenance />
              </SectionPanel>
              <SystemStatsSection
                stats={stats}
                isLoading={isLoading}
                onRefresh={fetchStats}
              />
              <BackupImportSection onStatsUpdate={fetchStats} />
              <DangerZoneSection />
            </>
          )}

          {activeTab === 'search' && (
            <SectionPanel title="分類與標籤管理" icon={<FolderOpen size={20} className="text-primary" />} testId="settings-search-taxonomy">
              <DataManager />
            </SectionPanel>
          )}

          {activeTab === 'deploy' && (
            <>
              <SectionPanel title="部署安全邊界" icon={<ShieldAlert size={20} className="text-amber-400" />} testId="settings-deploy-safety">
                <div className="space-y-2 text-sm text-text-secondary">
                  <p>伺服器控制端點維持 localhost-only，這個頁面只重排既有控制項。</p>
                  <p className="text-text-muted">遠端使用仍應透過 trusted LAN、VPN、SSH tunnel 或受保護的 reverse proxy。</p>
                </div>
              </SectionPanel>
              <PortConfigSection />
              <UpdateSection />
              <ServerDashboardSection />
            </>
          )}

          {activeTab === 'about' && (
            <SectionPanel title="關於" icon={<Info size={20} className="text-primary" />} testId="settings-about">
              <div className="space-y-2 text-text-secondary">
                <p><strong className="text-text-primary">Prism</strong></p>
                <p>版本: {stats?.version || '2.4.9'}</p>
                <p>前端: Vite + React + TypeScript + Tailwind CSS</p>
                <p>後端: Flask + SQLite (FTS5)</p>
                <p className="text-text-muted text-sm pt-2">
                  本地優先的知識管理系統；目前穩定使用路徑是 Source / Dev mode 與 Raspberry Pi 部署。
                </p>
                <p className="text-text-muted text-sm">
                  使用者資料保存在 `knowledge.db`、`static/uploads` 與 `docs/attachments`；本機更新程式時不應覆蓋這些資料目錄。
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
