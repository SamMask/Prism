

import { Loader2, Clipboard, History, Edit3, Eye, Save, X } from 'lucide-react';
import { Button, IconButton } from '../ui';
import { useTranslation } from '../../hooks/useTranslation';

interface EditorToolbarProps {
  // Title
  isEditing: boolean;

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
  const { t } = useTranslation();

  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
      <h2 className="text-lg font-semibold text-text-primary">
        {isEditing ? t('editor.toolbar.editNote') : t('editor.toolbar.newNote')}
      </h2>
      <div className="flex items-center gap-2">
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
          title={hasAIPrompt ? t('editor.toolbar.copyAiPrompt') : t('editor.toolbar.extractImagePrompt')}
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
            title={t('editor.toolbar.historyVersions')}
          >
            {isLoadingHistory ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <History size={16} />
            )}
            {t('editor.toolbar.history')}
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
          title={isPreview ? t('editor.toolbar.editMode') : t('editor.toolbar.previewMode')}
        >
          {isPreview ? <Edit3 size={18} /> : <Eye size={18} />}
        </button>

        {/* Save Button */}
        <Button onClick={onSave} variant="primary" disabled={isSaving}>
          <Save size={16} />
          {isSaving ? t('editor.toolbar.saving') : t('common.save')}
        </Button>

        {/* Close Button */}
        <IconButton onClick={onClose} aria-label={t('editor.toolbar.close')}>
          <X size={18} />
        </IconButton>
      </div>
    </div>
  );
}
