
import { useState, useEffect } from 'react';
import { Database, FolderOpen, Info } from 'lucide-react';
import { toast, ToastContainer } from '../components/ui/Toast';
import { api } from '../services/api';
import { BatchAITagging } from '../components/BatchAITagging';
import { DataManager } from '../components/DataManager';
import { SystemMaintenance } from '../components/SystemMaintenance';
import { useAppStore } from '../stores/appStore';
import { AIConfigSection } from '../components/settings/AIConfigSection';
import { SearchConfigSection } from '../components/settings/SearchConfigSection';
import { AppearanceSection } from '../components/settings/AppearanceSection';
import { BackupImportSection } from '../components/settings/BackupImportSection';
import { DangerZoneSection } from '../components/settings/DangerZoneSection';
import { SystemStatsSection } from '../components/settings/SystemStatsSection';

interface SystemStats {
  notes_count: number;
  categories_count: number;
  tags_count: number;
  images_count: number;
  total_size_mb: number;
}

interface AIStatus {
  available: boolean;
  models: string[];
  vision_ready: boolean;
  text_ready: boolean;
  error?: string;
}

interface SearchStatus {
  available: boolean;
  model_name: string;
  dimensions: number;
  model_loaded: boolean;
  total_notes: number;
  indexed_notes: number;
  index_coverage: string;
}

export function SettingsPage() {
  const { categories } = useAppStore();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [searchStatus, setSearchStatus] = useState<SearchStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingAI, setIsCheckingAI] = useState(false);
  const [isCheckingSearch, setIsCheckingSearch] = useState(false);
  const [isRebuilding, setIsRebuilding] = useState(false);

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

  // Fetch AI status
  const fetchAIStatus = async () => {
    setIsCheckingAI(true);
    try {
      const status = await api.getAIStatus();
      setAiStatus(status);
    } catch (error: any) {
      setAiStatus({
        available: false,
        models: [],
        vision_ready: false,
        text_ready: false,
        error: error?.message || 'Failed to connect to AI service'
      });
    } finally {
      setIsCheckingAI(false);
    }
  };

  // Fetch Search status
  const fetchSearchStatus = async () => {
    setIsCheckingSearch(true);
    try {
      const status = await api.getSearchStatus();
      setSearchStatus(status);
    } catch (error: any) {
      setSearchStatus(null);
    } finally {
      setIsCheckingSearch(false);
    }
  };

  // Rebuild search index
  const handleRebuildIndex = async () => {
    setIsRebuilding(true);
    toast.info('正在重建搜尋索引...');
    try {
      const result = await api.rebuildSearchIndex();
      toast.success(`索引完成！成功 ${result.success} 筆，失敗 ${result.failed} 筆`);
      fetchSearchStatus();
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '重建索引失敗');
    } finally {
      setIsRebuilding(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchAIStatus();
    fetchSearchStatus();
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

        {/* AI Status (Phase 3) */}
        <AIConfigSection
          aiStatus={aiStatus}
          isChecking={isCheckingAI}
          onRefresh={fetchAIStatus}
        />

        {/* Batch AI Tagging (Phase 3.1.4) */}
        {aiStatus?.available && (
          <BatchAITagging categories={categories} />
        )}

        {/* Semantic Search (Phase 3.2) */}
        <SearchConfigSection
          searchStatus={searchStatus}
          isChecking={isCheckingSearch}
          isRebuilding={isRebuilding}
          onRebuildIndex={handleRebuildIndex}
        />

        {/* Appearance */}
        <AppearanceSection categories={categories} />

        {/* Database Stats */}
        <SystemStatsSection
          stats={stats}
          isLoading={isLoading}
          onRefresh={fetchStats}
        />

        {/* About */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Info size={20} className="text-primary" />
            關於
          </h2>
          <div className="space-y-2 text-text-secondary">
            <p><strong className="text-text-primary">Prism V2</strong></p>
            <p>版本: 2.0.0-alpha</p>
            <p>前端: Vite + React + TypeScript + Tailwind CSS</p>
            <p>後端: Flask + SQLite</p>
            <p>AI: Ollama (Local LLM) + Sentence Transformers</p>
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
