
import React, { useEffect, useRef, useState } from 'react';
import { Download, Upload, Loader2, RotateCcw, Database } from 'lucide-react';
import { Button, toast } from '../ui';
import { api, type BackupItem } from '../../services/api';
import { useTranslation } from '../../hooks/useTranslation';

interface BackupImportSectionProps {
  onStatsUpdate: () => void;
}

export function BackupImportSection({ onStatsUpdate }: BackupImportSectionProps) {
  const { t } = useTranslation();
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
      toast.error(t('settings.backup.restoreStartFailed'));
      return;
    }
    const healthy = await api.waitForHealthy(40000);
    if (healthy) {
      window.location.reload();
    } else {
      setIsRestarting(false);
      toast.error(t('settings.backup.restoreRestartTimeout'));
    }
  };

  // Handle file selection for import
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.json')) {
      toast.error(t('settings.backup.selectJsonFile'));
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);
        if (!data.notes || !Array.isArray(data.notes)) {
          toast.error(t('settings.backup.invalidImportFile'));
          return;
        }
        setImportData(data);
        setShowImportModal(true);
      } catch {
        toast.error(t('settings.backup.parseJsonFailed'));
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
          t('settings.backup.importSkipped', { imported: result.imported, skipped: result.skipped })
        );
      } else {
        toast.success(t('settings.backup.importSuccess', { count: result.imported }));
      }
      
      setShowImportModal(false);
      setImportData(null);
      
      // Refresh stats
      onStatsUpdate();
    } catch {
      toast.error(t('settings.backup.importFailed'));
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
          {t('settings.backup.exportTitle')}
        </h2>
        <p className="text-text-muted text-sm mb-4">
          {t('settings.backup.exportDescription')}
        </p>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-primary">{t('settings.backup.jsonCopyTitle')}</p>
              <p className="text-text-muted text-sm">
                {t('settings.backup.jsonCopyDescription')}
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                api.exportJSON();
                toast.success(t('settings.backup.jsonDownloadStarted'));
              }}
            >
              {t('settings.backup.downloadJson')}
            </Button>
          </div>
          <div className="border-t border-border-subtle pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary">{t('settings.backup.dbCopyTitle')}</p>
                <p className="text-text-muted text-sm">
                  {t('settings.backup.dbCopyDescription')}
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  api.exportDB();
                  toast.success(t('settings.backup.dbDownloadStarted'));
                }}
              >
                {t('settings.backup.downloadDb')}
              </Button>
            </div>
          </div>
          <div className="border-t border-border-subtle pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary">{t('settings.backup.markdownTitle')}</p>
                <p className="text-text-muted text-sm">
                  {t('settings.backup.markdownDescription')}
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  api.exportMarkdown();
                  toast.success(t('settings.backup.markdownDownloadStarted'));
                }}
              >
                {t('settings.backup.downloadZip')}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Import */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Upload size={20} className="text-accent" />
          {t('settings.backup.importTitle')}
        </h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary">{t('settings.backup.importJsonTitle')}</p>
            <p className="text-text-muted text-sm">
              {t('settings.backup.importJsonDescription')}
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
              {t('settings.backup.chooseFile')}
            </Button>
          </div>
        </div>
      </div>

      {/* Restore from DB backup */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-2 flex items-center gap-2">
          <Database size={20} className="text-warning" />
          {t('settings.backup.restoreTitle')}
        </h2>
        <p className="text-text-muted text-sm mb-4">
          {t('settings.backup.restoreDescriptionPrefix')}
          <strong className="text-text-primary">{t('settings.backup.restoreRestartEmphasis')}</strong>
          {t('settings.backup.restoreDescriptionSuffix')}
        </p>

        {loadingBackups ? (
          <div className="flex items-center gap-2 text-text-muted text-sm">
            <Loader2 size={16} className="animate-spin" />
            {t('settings.backup.loadingRestorePoints')}
          </div>
        ) : backups.length === 0 ? (
          <p className="text-text-muted text-sm">{t('settings.backup.noRestorePoints')}</p>
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
                  {t('settings.backup.restoreAction')}
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
              {t('settings.backup.confirmRestoreTitle')}
            </h3>
            <p className="text-text-secondary mb-2">
              {t('settings.backup.confirmRestoreMessage')}
            </p>
            <p className="text-text-primary text-sm mb-4">
              {restoreTarget.created_at}
              <span className="text-text-muted"> · {restoreTarget.size_mb} MB</span>
            </p>
            <p className="text-text-muted text-sm mb-6">
              {t('settings.backup.confirmRestoreWarning')}
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setRestoreTarget(null)}>
                {t('common.cancel')}
              </Button>
              <Button variant="primary" onClick={handleRestore}>
                {t('settings.backup.confirmRestoreAction')}
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
              {t('settings.backup.restartingTitle')}
            </h3>
            <p className="text-text-muted text-sm">
              {t('settings.backup.restartingDescription')}
            </p>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImportModal && importData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-bg-elevated rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-text-primary mb-4">
              {t('settings.backup.confirmImportTitle')}
            </h3>
            
            <p className="text-text-secondary mb-4">
              {t('settings.backup.fileContainsPrefix')} <strong className="text-text-primary">
                {(importData as { notes?: unknown[] }).notes?.length || 0}
              </strong> {t('settings.backup.fileContainsSuffix')}
            </p>

            <div className="mb-6">
              <p className="text-sm text-text-muted mb-2">{t('settings.backup.duplicateStrategy')}</p>
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
                  <span className="text-text-secondary">{t('settings.backup.skipDuplicates')}</span>
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
                  <span className="text-text-secondary">{t('settings.backup.makeCopies')}</span>
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
                {t('common.cancel')}
              </Button>
              <Button
                variant="primary"
                onClick={handleImport}
                disabled={isImporting}
              >
                {isImporting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    {t('settings.backup.importing')}
                  </>
                ) : (
                  t('settings.backup.startImport')
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
