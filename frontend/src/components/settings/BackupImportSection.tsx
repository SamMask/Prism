
import React, { useEffect, useRef, useState } from 'react';
import { Download, Upload, Loader2, RotateCcw, Database } from 'lucide-react';
import { Button, toast } from '../ui';
import { api, type BackupItem } from '../../services/api';

interface BackupImportSectionProps {
  onStatsUpdate: () => void;
}

export function BackupImportSection({ onStatsUpdate }: BackupImportSectionProps) {
  // Import State
  const [isImporting, setIsImporting] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importData, setImportData] = useState<unknown>(null);
  const [importMode, setImportMode] = useState<'skip' | 'duplicate'>('skip');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Restore-from-backup state
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [loadingBackups, setLoadingBackups] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<BackupItem | null>(null);
  const [isRestarting, setIsRestarting] = useState(false);

  const loadBackups = async () => {
    setLoadingBackups(true);
    try {
      const res = await api.listBackups();
      setBackups(res.backups || []);
    } catch {
      // Server-management API is localhost-only; silently show an empty list off-box.
      setBackups([]);
    } finally {
      setLoadingBackups(false);
    }
  };

  useEffect(() => {
    loadBackups();
  }, []);

  // Confirm → stage restore → server restarts → poll until it is back → reload.
  const handleRestore = async () => {
    if (!restoreTarget) return;
    const filename = restoreTarget.filename;
    setRestoreTarget(null);
    setIsRestarting(true);
    try {
      await api.restoreBackup(filename);
    } catch {
      setIsRestarting(false);
      toast.error('還原啟動失敗，資料庫未變更');
      return;
    }
    const healthy = await api.waitForHealthy(40000);
    if (healthy) {
      window.location.reload();
    } else {
      setIsRestarting(false);
      toast.error('等待程式重新啟動逾時，請手動重新開啟 Prism');
    }
  };

  // Handle file selection for import
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.json')) {
      toast.error('請選擇 JSON 檔案');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);
        if (!data.notes || !Array.isArray(data.notes)) {
          toast.error('無效的匯入檔案格式');
          return;
        }
        setImportData(data);
        setShowImportModal(true);
      } catch {
        toast.error('解析 JSON 檔案失敗');
      }
    };
    reader.readAsText(file);
    
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle import
  const handleImport = async () => {
    if (!importData) return;

    setIsImporting(true);
    try {
      const result = await api.importJSON(importData, importMode);
      
      if (result.skipped > 0 && importMode === 'skip') {
        toast.success(
          `匯入完成：新增 ${result.imported} 筆，略過 ${result.skipped} 筆重複`
        );
      } else {
        toast.success(`成功匯入 ${result.imported} 筆筆記`);
      }
      
      setShowImportModal(false);
      setImportData(null);
      
      // Refresh stats
      onStatsUpdate();
    } catch (error) {
      toast.error('匯入失敗');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <>
      {/* Export Copies */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Download size={20} className="text-success" />
          匯出副本
        </h2>
        <p className="text-text-muted text-sm mb-4">
          下載一份可自行保存或帶到其他工具使用的資料副本；這不會建立 Prism 內建還原點。
        </p>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-primary">下載 JSON 副本</p>
              <p className="text-text-muted text-sm">
                下載所有筆記、分類、標籤，之後可用「匯入資料」帶回 Prism
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                api.exportJSON();
                toast.success('開始下載 JSON 副本');
              }}
            >
              下載 JSON
            </Button>
          </div>
          <div className="border-t border-border-subtle pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary">下載資料庫副本</p>
                <p className="text-text-muted text-sm">
                  下載完整 SQLite .db 檔，適合離線保存或人工檢查
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  api.exportDB();
                  toast.success('開始下載資料庫副本');
                }}
              >
                下載 .db
              </Button>
            </div>
          </div>
          <div className="border-t border-border-subtle pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary">匯出 Markdown</p>
                <p className="text-text-muted text-sm">
                  每筆記一個 .md 檔，並把本機圖片打包到 zip 內（Obsidian / VSCode 可讀）
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  api.exportMarkdown();
                  toast.success('開始下載 Markdown zip');
                }}
              >
                下載 .zip
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Import */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Upload size={20} className="text-accent" />
          匯入資料
        </h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary">從 JSON 匯入</p>
            <p className="text-text-muted text-sm">
              匯入先前下載的 JSON 副本；這會新增或建立副本，不會覆蓋整個資料庫
            </p>
          </div>
          <div>
            <input
              type="file"
              ref={fileInputRef}
              accept=".json"
              onChange={handleFileSelect}
              className="hidden"
            />
            <Button
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
            >
              選擇檔案
            </Button>
          </div>
        </div>
      </div>

      {/* Restore from DB backup */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-2 flex items-center gap-2">
          <Database size={20} className="text-warning" />
          還原資料庫
        </h2>
        <p className="text-text-muted text-sm mb-4">
          選一個 Prism 內建還原點。點「還原」後，Prism 會<strong className="text-text-primary">自動關閉並重新開啟</strong>，
          用你選的還原點覆蓋目前資料庫。還原前會先把目前資料庫另存一份。
        </p>

        {loadingBackups ? (
          <div className="flex items-center gap-2 text-text-muted text-sm">
            <Loader2 size={16} className="animate-spin" />
            讀取還原點清單…
          </div>
        ) : backups.length === 0 ? (
          <p className="text-text-muted text-sm">目前沒有可還原的 Prism 內建還原點。</p>
        ) : (
          <div className="space-y-2">
            {backups.map((b) => (
              <div
                key={b.filename}
                className="flex items-center justify-between border border-border-subtle rounded-lg px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="text-text-primary text-sm truncate">{b.created_at}</p>
                  <p className="text-text-muted text-xs truncate">
                    {b.filename} · {b.size_mb} MB
                  </p>
                </div>
                <Button
                  variant="secondary"
                  onClick={() => setRestoreTarget(b)}
                  disabled={isRestarting}
                >
                  <RotateCcw size={16} />
                  還原
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Restore confirm modal */}
      {restoreTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-bg-elevated rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Database size={20} className="text-warning" />
              確認還原資料庫
            </h3>
            <p className="text-text-secondary mb-2">
              將用這個 Prism 內建還原點覆蓋目前的資料庫：
            </p>
            <p className="text-text-primary text-sm mb-4">
              {restoreTarget.created_at}
              <span className="text-text-muted"> · {restoreTarget.size_mb} MB</span>
            </p>
            <p className="text-text-muted text-sm mb-6">
              點「確認還原」後 Prism 會自動重新開啟，畫面會短暫中斷幾秒，回來後就是還原好的內容。
              目前的資料庫會先自動備份一份。
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setRestoreTarget(null)}>
                取消
              </Button>
              <Button variant="primary" onClick={handleRestore}>
                確認還原
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Restarting overlay */}
      {isRestarting && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-bg-elevated rounded-xl p-8 max-w-sm w-full mx-4 shadow-2xl text-center">
            <Loader2 size={32} className="animate-spin text-accent mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              正在重新啟動 Prism…
            </h3>
            <p className="text-text-muted text-sm">
              正在用備份還原資料庫，程式重新開啟後會自動回到這個畫面，請稍候。
            </p>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImportModal && importData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-bg-elevated rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-text-primary mb-4">
              確認匯入
            </h3>
            
            <p className="text-text-secondary mb-4">
              檔案包含 <strong className="text-text-primary">
                {(importData as { notes?: unknown[] }).notes?.length || 0}
              </strong> 筆筆記
            </p>

            <div className="mb-6">
              <p className="text-sm text-text-muted mb-2">遇到重複筆記時：</p>
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="importMode"
                    value="skip"
                    checked={importMode === 'skip'}
                    onChange={() => setImportMode('skip')}
                    className="accent-primary"
                  />
                  <span className="text-text-secondary">略過（不匯入重複的筆記）</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="importMode"
                    value="duplicate"
                    checked={importMode === 'duplicate'}
                    onChange={() => setImportMode('duplicate')}
                    className="accent-primary"
                  />
                  <span className="text-text-secondary">建立副本（加上 Import 後綴）</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowImportModal(false);
                  setImportData(null);
                }}
              >
                取消
              </Button>
              <Button
                variant="primary"
                onClick={handleImport}
                disabled={isImporting}
              >
                {isImporting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    匯入中...
                  </>
                ) : (
                  '開始匯入'
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
