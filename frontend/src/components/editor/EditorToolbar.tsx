

import { Loader2, Sparkles, Clipboard, History, Edit3, Eye, Save, X } from 'lucide-react';
import { Button } from '../ui/Button';

interface EditorToolbarProps {
  // Title
  isEditing: boolean;

  // AI Analyze
  isAnalyzing: boolean;
  onAiAnalyze: () => void;

  // Prompt Extraction
  hasAIPrompt: boolean;
  isCheckingPrompt: boolean;
  onCopyPrompt: () => void;

  // History
  isLoadingHistory: boolean;
  onLoadHistory: () => void;

  // View Mode
  isPreview: boolean;
  onTogglePreview: () => void;

  // Save/Close
  isSaving: boolean;
  onSave: () => void;
  onClose: () => void;
}

export function EditorToolbar({
  isEditing,
  isAnalyzing,
  onAiAnalyze,
  hasAIPrompt,
  isCheckingPrompt,
  onCopyPrompt,
  isLoadingHistory,
  onLoadHistory,
  isPreview,
  onTogglePreview,
  isSaving,
  onSave,
  onClose,
}: EditorToolbarProps) {
  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
      <h2 className="text-lg font-semibold text-text-primary">
        {isEditing ? "編輯筆記" : "新增筆記"}
      </h2>
      <div className="flex items-center gap-2">
        {/* AI Analyze Button */}
        <button
          onClick={onAiAnalyze}
          disabled={isAnalyzing}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                     transition-all duration-200
                     ${
                       isAnalyzing
                         ? "bg-accent/20 text-accent cursor-wait"
                         : "bg-accent/10 text-accent hover:bg-accent/20"
                     }`}
          title="AI 智慧分析"
        >
          {isAnalyzing ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Sparkles size={16} />
          )}
          {isAnalyzing ? "分析中..." : "AI 分析"}
        </button>

        {/* Extract Prompt Button */}
        <button
          onClick={onCopyPrompt}
          disabled={isCheckingPrompt}
          className={`p-2 rounded-lg transition-all duration-200 relative
                     ${
                       hasAIPrompt
                         ? "bg-success/20 text-success hover:bg-success/30 shadow-lg shadow-success/20"
                         : isCheckingPrompt
                           ? "bg-bg-elevated text-text-muted cursor-wait"
                           : "bg-bg-elevated text-text-muted hover:text-text-primary hover:bg-bg-hover"
                     }`}
          title={hasAIPrompt ? "複製 AI 提示詞" : "提取圖片提示詞"}
        >
          {isCheckingPrompt ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Clipboard size={16} />
          )}
          {hasAIPrompt && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-success rounded-full animate-pulse" />
          )}
        </button>

        {/* History Button (only for existing notes) */}
        {isEditing && (
          <button
            onClick={onLoadHistory}
            disabled={isLoadingHistory}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                       transition-all duration-200
                       ${
                         isLoadingHistory
                           ? "bg-warning/20 text-warning cursor-wait"
                           : "bg-warning/10 text-warning hover:bg-warning/20"
                       }`}
            title="歷史版本"
          >
            {isLoadingHistory ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <History size={16} />
            )}
            歷史
          </button>
        )}

        {/* Preview Toggle */}
        <button
          onClick={onTogglePreview}
          className={`p-2 rounded-lg transition-colors ${
            isPreview
              ? "bg-primary text-white"
              : "text-text-muted hover:bg-bg-hover"
          }`}
          title={isPreview ? "編輯模式" : "預覽模式"}
        >
          {isPreview ? <Edit3 size={18} /> : <Eye size={18} />}
        </button>

        {/* Save Button */}
        <Button onClick={onSave} variant="primary" disabled={isSaving}>
          <Save size={16} />
          {isSaving ? "儲存中..." : "儲存"}
        </Button>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="p-2 rounded-lg text-text-muted hover:bg-bg-hover"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
