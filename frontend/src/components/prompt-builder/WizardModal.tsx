/**
 * WizardModal - guided inspiration wizard
 * Helps users generate prompts through guided fields
 */
import { X, Sparkles, Shuffle } from 'lucide-react';
import { WizardOptions } from '../../hooks/usePromptBuilder';
import { useTranslation } from '../../hooks/useTranslation';

interface WizardModalProps {
  isOpen: boolean;
  onClose: () => void;
  wizardForm: {
    subject: string;
    action: string;
    environment: string;
    details: string;
  };
  wizardOptions: WizardOptions;
  wizardAppend: boolean;
  onUpdateField: (field: string, value: string) => void;
  onRandomizeField: (field: keyof WizardOptions) => void;
  onConfirm: () => void;
  onSetAppend: (value: boolean) => void;
}

export function WizardModal({
  isOpen,
  onClose,
  wizardForm,
  wizardOptions,
  wizardAppend,
  onUpdateField,
  onRandomizeField,
  onConfirm,
  onSetAppend,
}: WizardModalProps) {
  const { t } = useTranslation();

  if (!isOpen) return null;

  // Wizard Preview
  const wizardPreview = [
    wizardForm.subject,
    wizardForm.action,
    wizardForm.environment,
    wizardForm.details,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="glass rounded-2xl w-full max-w-2xl overflow-hidden border border-primary/30"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle bg-gradient-to-r from-primary/20 to-accent/20">
          <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <Sparkles size={20} className="text-primary" />
            {t('promptBuilder.wizard.title')}
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-secondary hover:text-text-primary"
            aria-label={t('common.close')}
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Subject */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-text-secondary flex items-center gap-2">
                <span>👤</span> {t('promptBuilder.wizard.subject')}
              </label>
              <button
                onClick={() => onRandomizeField('subject')}
                className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-primary"
                title={t('promptBuilder.wizard.random')}
              >
                <Shuffle size={16} />
              </button>
            </div>
            <input
              type="text"
              value={wizardForm.subject}
              onChange={(e) => onUpdateField('subject', e.target.value)}
              placeholder={wizardOptions.subject?.placeholder || t('promptBuilder.wizard.subjectPlaceholder')}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Action */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-text-secondary flex items-center gap-2">
                <span>🎬</span> {t('promptBuilder.wizard.action')}
              </label>
              <button
                onClick={() => onRandomizeField('action')}
                className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-primary"
                title={t('promptBuilder.wizard.random')}
              >
                <Shuffle size={16} />
              </button>
            </div>
            <input
              type="text"
              value={wizardForm.action}
              onChange={(e) => onUpdateField('action', e.target.value)}
              placeholder={wizardOptions.action?.placeholder || t('promptBuilder.wizard.actionPlaceholder')}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Environment */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-text-secondary flex items-center gap-2">
                <span>🌍</span> {t('promptBuilder.wizard.environment')}
              </label>
              <button
                onClick={() => onRandomizeField('environment')}
                className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-primary"
                title={t('promptBuilder.wizard.random')}
              >
                <Shuffle size={16} />
              </button>
            </div>
            <input
              type="text"
              value={wizardForm.environment}
              onChange={(e) => onUpdateField('environment', e.target.value)}
              placeholder={wizardOptions.environment?.placeholder || t('promptBuilder.wizard.environmentPlaceholder')}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Details */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-text-secondary flex items-center gap-2">
                <span>✨</span> {t('promptBuilder.wizard.details')}
              </label>
              <button
                onClick={() => onRandomizeField('details')}
                className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-primary"
                title={t('promptBuilder.wizard.random')}
              >
                <Shuffle size={16} />
              </button>
            </div>
            <input
              type="text"
              value={wizardForm.details}
              onChange={(e) => onUpdateField('details', e.target.value)}
              placeholder={wizardOptions.details?.placeholder || t('promptBuilder.wizard.detailsPlaceholder')}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Preview */}
          <div className="mt-6 p-4 bg-bg-elevated/70 rounded-xl border border-border-subtle">
            <p className="text-xs text-primary font-medium mb-2">📝 {t('promptBuilder.wizard.preview')}</p>
            <p className="text-sm text-text-primary leading-relaxed">
              {wizardPreview || t('promptBuilder.wizard.emptyPreview')}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border-subtle bg-bg-elevated/50">
          <label className="flex items-center gap-2 mb-4 text-sm text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={wizardAppend}
              onChange={(e) => onSetAppend(e.target.checked)}
              className="w-4 h-4 rounded border-border-subtle text-primary focus:ring-primary"
            />
            {t('promptBuilder.wizard.append')}
          </label>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-2.5 bg-bg-elevated hover:bg-border-subtle text-text-primary text-sm font-medium rounded-lg transition-colors"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 py-2.5 bg-gradient-to-r from-primary to-accent hover:opacity-90 text-white text-sm font-medium rounded-lg transition-opacity flex items-center justify-center gap-2"
            >
              <span>✓</span>
              {t('promptBuilder.wizard.confirm')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
