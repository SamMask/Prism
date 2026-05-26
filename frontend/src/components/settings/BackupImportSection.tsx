
import React, { useRef, useState } from 'react';
import { Download, Upload, Loader2 } from 'lucide-react';
import { Button, toast } from '../ui';
import { api } from '../../services/api';

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
      {/* Export / Backup */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Download size={20} className="text-success" />
          匯出備份
        </h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-primary">匯出 JSON</p>
              <p className="text-text-muted text-sm">
                匯出所有筆記、分類、標籤為 JSON 格式
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                api.exportJSON();
                toast.success('開始下載 JSON 備份檔案');
              }}
            >
              下載 JSON
            </Button>
          </div>
          <div className="border-t border-border-subtle pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary">匯出資料庫</p>
                <p className="text-text-muted text-sm">
                  匯出完整 SQLite 資料庫檔案
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  api.exportDB();
                  toast.success('開始下載資料庫備份檔案');
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
                  每筆記一個 .md 檔（YAML frontmatter + body），跨工具可讀（Obsidian / VSCode）
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
              匯入先前匯出的 JSON 備份檔案
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
