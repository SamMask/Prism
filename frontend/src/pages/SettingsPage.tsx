
import { useState, useEffect } from 'react';
import { Database, FolderOpen, Info } from 'lucide-react';
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
  notes_count: number;
  categories_count: number;
  tags_count: number;
  images_count: number;
  total_size_mb: number;
}

export function SettingsPage() {
  const { categories } = useAppStore();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch system stats
  const fetchStats = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/test');
      const data = await response.json();
      if (data.status === 'ok') {
        setStats({
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
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="glass rounded-xl p-6">
          <h1 className="text-2xl font-bold gradient-text mb-2">設定</h1>
          <p className="text-text-secondary">
            管理應用程式偏好設定與資料
          </p>
        </div>

        {/* Category & Tag Management */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <FolderOpen size={20} className="text-primary" />
            分類與標籤管理
          </h2>
          <DataManager />
        </div>

        {/* System Maintenance (DB Vacuum/Optimize) */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Database size={20} className="text-warning" />
            資料庫維護
          </h2>
          <SystemMaintenance />
        </div>

        {/* Appearance */}
        <AppearanceSection categories={categories} />

        {/* Port Configuration (v1.5.0) */}
        <PortConfigSection />

        {/* Database Stats */}
        <SystemStatsSection
          stats={stats}
          isLoading={isLoading}
          onRefresh={fetchStats}
        />

        {/* Update Check (v2.1.0 - Task 7.1) */}
        <UpdateSection />

        {/* Server Dashboard (v2.1.2 - Phase 8.2) */}
        <ServerDashboardSection />

        {/* About */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Info size={20} className="text-primary" />
            關於
          </h2>
          <div className="space-y-2 text-text-secondary">
            <p><strong className="text-text-primary">Prism</strong></p>
            <p>版本: 2.0.0-alpha</p>
            <p>前端: Vite + React + TypeScript + Tailwind CSS</p>
            <p>後端: Flask + SQLite (FTS5)</p>
            <p className="text-text-muted text-sm pt-2">
              本地知識管理系統，所有資料儲存在您的電腦上
            </p>
          </div>
        </div>

        {/* Backup & Import */}
        <BackupImportSection onStatsUpdate={fetchStats} />

        {/* Danger Zone */}
        <DangerZoneSection />
      </div>

      <ToastContainer />
    </>
  );
}
