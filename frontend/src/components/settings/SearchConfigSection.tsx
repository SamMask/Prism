

import { Search, Loader2, Check, AlertCircle, Zap } from 'lucide-react';
import { Button } from '../ui';

interface SearchStatus {
  available: boolean;
  model_name: string;
  dimensions: number;
  model_loaded: boolean;
  total_notes: number;
  indexed_notes: number;
  index_coverage: string;
}

interface SearchConfigSectionProps {
  searchStatus: SearchStatus | null;
  isChecking: boolean;
  isRebuilding: boolean;
  onRebuildIndex: () => void;
}

export function SearchConfigSection({
  searchStatus,
  isChecking,
  isRebuilding,
  onRebuildIndex,
}: SearchConfigSectionProps) {
  return (
    <div className="glass rounded-xl p-6">
      <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Search size={20} className="text-primary" />
        語意搜尋
      </h2>
      
      {isChecking ? (
        <div className="flex items-center gap-2 text-text-muted">
          <Loader2 size={18} className="animate-spin" />
          正在檢查搜尋服務...
        </div>
      ) : searchStatus ? (
        <div className="space-y-4">
          {/* Status */}
          <div className="flex items-center gap-3">
            {searchStatus.available ? (
              <span className="flex items-center gap-2 text-success">
                <Check size={18} />
                模型已安裝 ({searchStatus.model_name})
              </span>
            ) : (
              <span className="flex items-center gap-2 text-warning">
                <AlertCircle size={18} />
                需安裝 sentence-transformers
                <code className="text-xs bg-bg-elevated px-2 py-0.5 rounded">pip install sentence-transformers</code>
              </span>
            )}
          </div>

          {/* Index Stats */}
          {searchStatus.available && (
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-bg-elevated rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-primary">
                  {searchStatus.indexed_notes}
                </div>
                <div className="text-text-muted text-xs">已索引</div>
              </div>
              <div className="bg-bg-elevated rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-text-secondary">
                  {searchStatus.total_notes}
                </div>
                <div className="text-text-muted text-xs">總筆記數</div>
              </div>
              <div className="bg-bg-elevated rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-accent">
                  {searchStatus.index_coverage}
                </div>
                <div className="text-text-muted text-xs">覆蓋率</div>
              </div>
            </div>
          )}

          {/* Rebuild Button */}
          {searchStatus.available && (
            <div className="flex items-center justify-between pt-2 border-t border-border-subtle">
              <p className="text-text-muted text-sm">
                重建索引以更新語意搜尋
              </p>
              <Button
                onClick={onRebuildIndex}
                variant="secondary"
                disabled={isRebuilding}
                className="flex items-center gap-2"
              >
                {isRebuilding ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Zap size={16} />
                )}
                {isRebuilding ? '建立中...' : '重建索引'}
              </Button>
            </div>
          )}
        </div>
      ) : (
        <p className="text-text-muted">語意搜尋服務未啟用</p>
      )}
    </div>
  );
}
