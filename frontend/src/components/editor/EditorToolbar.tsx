

import { Check, Copy, ListPlus, Loader2, History, Edit3, Eye, Save, X } from 'lucide-react';
import { Button, IconButton } from '../ui';
import { useTranslation } from '../../hooks/useTranslation';

interface EditorToolbarProps {
  // Title
  isEditing: boolean;

  // Reading list
  canAddToReadingWorkspace: boolean;
  isInReadingWorkspace: boolean;
  onAddToReadingWorkspace: () => void;

  // History
  isLoadingHistory: boolean;
  onLoadHistory: () => void;

  // Copy
  onCopyContent: () => void;

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
  canAddToReadingWorkspace,
  isInReadingWorkspace,
  onAddToReadingWorkspace,
  isLoadingHistory,
  onLoadHistory,
  onCopyContent,
  isPreview,
  onTogglePreview,
  isSaving,
  onSave,
  onClose,
}: EditorToolbarProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
      <h2 className="text-lg font-semibold text-text-primary">
        {isEditing ? t('editor.toolbar.editNote') : t('editor.toolbar.newNote')}
      </h2>
      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        {canAddToReadingWorkspace && (
          <button
            onClick={onAddToReadingWorkspace}
            className={`relative rounded-lg p-2 transition-all duration-200 ${
              isInReadingWorkspace
                ? 'bg-success/20 text-success hover:bg-success/30'
                : 'bg-bg-elevated text-text-muted hover:bg-bg-hover hover:text-text-primary'
            }`}
            title={isInReadingWorkspace ? t('noteCard.inReadingWorkspace') : t('noteCard.addToReadingWorkspace')}
            aria-label={isInReadingWorkspace ? t('noteCard.inReadingWorkspace') : t('noteCard.addToReadingWorkspace')}
            aria-pressed={isInReadingWorkspace}
            data-testid="editor-add-reading-workspace"
          >
            {isInReadingWorkspace ? <Check size={16} /> : <ListPlus size={16} />}
          </button>
        )}

        {/* History Button (only for existing notes) */}
        {isEditing && (
          <button
            onClick={onLoadHistory}
            disabled={isLoadingHistory}
            className={`flex items-center gap-1.5 p-2 sm:px-3 sm:py-1.5 rounded-lg text-sm
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
            <span className="hidden sm:inline">{t('editor.toolbar.history')}</span>
          </button>
        )}

        {/* Copy current content */}
        <button
          type="button"
          onClick={onCopyContent}
          className="p-2 rounded-lg text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
          title={t('noteCard.copyContent')}
          aria-label={t('noteCard.copyContent')}
          data-testid="editor-copy-content"
        >
          <Copy size={18} />
        </button>

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
        <Button
          onClick={onSave}
          variant="primary"
          disabled={isSaving}
          aria-label={isSaving ? t('editor.toolbar.saving') : t('common.save')}
          title={isSaving ? t('editor.toolbar.saving') : t('common.save')}
        >
          <Save size={16} />
          <span className="hidden sm:inline">
            {isSaving ? t('editor.toolbar.saving') : t('common.save')}
          </span>
        </Button>

        {/* Close Button */}
        <IconButton onClick={onClose} aria-label={t('editor.toolbar.close')}>
          <X size={18} />
        </IconButton>
      </div>
    </div>
  );
}
