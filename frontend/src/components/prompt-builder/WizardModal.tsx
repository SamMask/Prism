/**
 * WizardModal - 靈感引導 Wizard
 * Helps users generate prompts through guided fields
 */
import { X, Sparkles, Shuffle } from 'lucide-react';
import { WizardOptions } from '../../hooks/usePromptBuilder';

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
            靈感引導 Wizard
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-secondary hover:text-text-primary"
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
                <span>👤</span> 主體 (Subject / Who)
              </label>
              <button
                onClick={() => onRandomizeField('subject')}
                className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-primary"
                title="隨機靈感"
              >
                <Shuffle size={16} />
              </button>
            </div>
            <input
              type="text"
              value={wizardForm.subject}
              onChange={(e) => onUpdateField('subject', e.target.value)}
              placeholder={wizardOptions.subject?.placeholder || "一隻穿著太空服的橘貓..."}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Action */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-text-secondary flex items-center gap-2">
                <span>🎬</span> 動作與姿態 (Action & Pose / What)
              </label>
              <button
                onClick={() => onRandomizeField('action')}
                className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-primary"
                title="隨機靈感"
              >
                <Shuffle size={16} />
              </button>
            </div>
            <input
              type="text"
              value={wizardForm.action}
              onChange={(e) => onUpdateField('action', e.target.value)}
              placeholder={wizardOptions.action?.placeholder || "漂浮在半空中、正在喝咖啡..."}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Environment */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-text-secondary flex items-center gap-2">
                <span>🌍</span> 環境與背景 (Environment / Where)
              </label>
              <button
                onClick={() => onRandomizeField('environment')}
                className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-primary"
                title="隨機靈感"
              >
                <Shuffle size={16} />
              </button>
            </div>
            <input
              type="text"
              value={wizardForm.environment}
              onChange={(e) => onUpdateField('environment', e.target.value)}
              placeholder={wizardOptions.environment?.placeholder || "充滿霓虹燈的東京街道..."}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Details */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-text-secondary flex items-center gap-2">
                <span>✨</span> 細節與特徵 (Details & Features)
              </label>
              <button
                onClick={() => onRandomizeField('details')}
                className="p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-primary"
                title="隨機靈感"
              >
                <Shuffle size={16} />
              </button>
            </div>
            <input
              type="text"
              value={wizardForm.details}
              onChange={(e) => onUpdateField('details', e.target.value)}
              placeholder={wizardOptions.details?.placeholder || "衣服上有破損、眼神堅毅..."}
              className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/50"
            />
          </div>

          {/* Preview */}
          <div className="mt-6 p-4 bg-bg-elevated/70 rounded-xl border border-border-subtle">
            <p className="text-xs text-primary font-medium mb-2">📝 組合預覽</p>
            <p className="text-sm text-text-primary leading-relaxed">
              {wizardPreview || "(填寫上方欄位後將自動組合顯示...)"}
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
            追加到現有描述後方（而非覆蓋）
          </label>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-2.5 bg-bg-elevated hover:bg-border-subtle text-text-primary text-sm font-medium rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 py-2.5 bg-gradient-to-r from-primary to-accent hover:opacity-90 text-white text-sm font-medium rounded-lg transition-opacity flex items-center justify-center gap-2"
            >
              <span>✓</span>
              確認並填入
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
