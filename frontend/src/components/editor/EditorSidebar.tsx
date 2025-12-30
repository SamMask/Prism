
import React from 'react';
import { Sparkles, FolderOpen, Tag as TagIcon, X, Link2 } from 'lucide-react';
import { Tag } from '../../services/api';
import { AttachmentPanel, Attachment } from './AttachmentPanel';
import { useAppStore } from '../../stores/appStore';

interface EditorSidebarProps {
  // AI Suggestions
  aiSuggestions: string[];
  aiDescription: string;
  onAddAiTag: (tag: string) => void;

  // Category
  categoryId: number | undefined;
  onChangeCategory: (id: number | undefined) => void;

  // Tags
  tagInput: string;
  onTagInputChange: (value: string) => void;
  onTagInputKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  selectedTags: Tag[];
  onRemoveTag: (id: number) => void;

  // Source URLs
  sourceUrls: string[];
  urlInput: string;
  onUrlInputChange: (value: string) => void;
  onUrlInputKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  onUrlInputBlur: () => void;
  onRemoveUrl: (index: number) => void;

  // Remarks
  remarks: string;
  onChangeRemarks: (value: string) => void;

  // Appearance
  coverPosition: "top" | "center" | "bottom";
  onChangeCoverPosition: (pos: "top" | "center" | "bottom") => void;
  editorLayout: "single" | "dual";
  onChangeEditorLayout: (layout: "single" | "dual") => void;

  // Attachments
  isEditing: boolean;
  attachments: Attachment[];
  onLoadAttachment: (id: number, isAutoExtracted: boolean) => void;
  onDeleteAttachment: (id: number) => void;
  onUploadAttachment: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function EditorSidebar({
  aiSuggestions,
  aiDescription,
  onAddAiTag,
  categoryId,
  onChangeCategory,
  tagInput,
  onTagInputChange,
  onTagInputKeyDown,
  selectedTags,
  onRemoveTag,
  sourceUrls,
  urlInput,
  onUrlInputChange,
  onUrlInputKeyDown,
  onUrlInputBlur,
  onRemoveUrl,
  remarks,
  onChangeRemarks,
  coverPosition,
  onChangeCoverPosition,
  editorLayout,
  onChangeEditorLayout,
  isEditing,
  attachments,
  onLoadAttachment,
  onDeleteAttachment,
  onUploadAttachment,
}: EditorSidebarProps) {
  const { categories } = useAppStore();

  return (
    <div className="w-64 flex-shrink-0 border-l border-border-subtle p-4 space-y-4 overflow-auto">
      {/* AI Suggestions */}
      {(aiSuggestions.length > 0 || aiDescription) && (
        <div className="p-3 rounded-lg bg-accent/5 border border-accent/20">
          <h4 className="flex items-center gap-2 text-sm font-medium text-accent mb-2">
            <Sparkles size={14} />
            AI 建議
          </h4>

          {aiDescription && (
            <p className="text-xs text-text-secondary mb-2 leading-relaxed">
              {aiDescription}
            </p>
          )}

          {aiSuggestions.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {aiSuggestions.map((tag, i) => (
                <button
                  key={i}
                  onClick={() => onAddAiTag(tag)}
                  className="px-2 py-0.5 text-xs rounded-full
                             bg-accent/10 text-accent
                             hover:bg-accent/20 transition-colors"
                  title="點擊添加此標籤"
                >
                  + {tag}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Category */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
          <FolderOpen size={14} /> 分類
        </label>
        <select
          value={categoryId || ""}
          onChange={(e) =>
            onChangeCategory(
              e.target.value ? Number(e.target.value) : undefined
            )
          }
          className="w-full px-3 py-2 rounded-lg
                     bg-bg-elevated border border-border-default
                     text-text-primary text-sm
                     focus:outline-none focus:border-primary"
        >
          <option value="">選擇分類</option>
          {categories.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.icon} {cat.name}
            </option>
          ))}
        </select>
      </div>

      {/* Tags */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
          <TagIcon size={14} /> 標籤
        </label>
        <input
          type="text"
          value={tagInput}
          onChange={(e) => onTagInputChange(e.target.value)}
          onKeyDown={onTagInputKeyDown}
          placeholder="輸入標籤後按 Enter"
          className="w-full px-3 py-2 rounded-lg
                     bg-bg-elevated border border-border-default
                     text-text-primary text-sm
                     focus:outline-none focus:border-primary"
        />
        {selectedTags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {selectedTags.map((tag) => (
              <span
                key={tag.id}
                className="inline-flex items-center gap-1 px-2 py-0.5
                           text-xs rounded-full
                           bg-primary/10 text-primary-light"
              >
                {tag.name}
                <button
                  onClick={() => onRemoveTag(tag.id)}
                  className="hover:text-danger"
                >
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Source URLs */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
          <Link2 size={14} /> 來源連結
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={urlInput}
            onChange={(e) => onUrlInputChange(e.target.value)}
            onKeyDown={onUrlInputKeyDown}
            onBlur={onUrlInputBlur}
            placeholder="輸入 URL 後按 Enter"
            className="flex-1 px-3 py-2 rounded-lg
                       bg-bg-elevated border border-border-default
                       text-text-primary text-sm
                       focus:outline-none focus:border-primary"
          />
        </div>
        {sourceUrls.length > 0 && (
          <div className="mt-2 space-y-1.5">
            {sourceUrls.map((url, index) => (
              <div
                key={index}
                className="flex items-center gap-2 p-2 rounded-lg bg-bg-elevated group"
              >
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 text-xs text-primary truncate hover:underline"
                >
                  {url}
                </a>
                <button
                  onClick={() => onRemoveUrl(index)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-danger/10 text-text-muted hover:text-danger"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Remarks */}
      <div>
        <label className="text-sm font-medium text-text-secondary mb-2 block">
          備註
        </label>
        <textarea
          value={remarks}
          onChange={(e) => onChangeRemarks(e.target.value)}
          placeholder="簡短備註..."
          rows={3}
          className="w-full px-3 py-2 rounded-lg
                     bg-bg-elevated border border-border-default
                     text-text-primary text-sm resize-none
                     focus:outline-none focus:border-primary"
        />
      </div>

      {/* Cover Position */}
      <div>
        <label className="text-sm font-medium text-text-secondary mb-2 block">
          封面位置
        </label>
        <div className="flex gap-2">
          {([
            { value: "top", label: "頂部" },
            { value: "center", label: "中間" },
            { value: "bottom", label: "底部" },
          ] as const).map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onChangeCoverPosition(option.value)}
              className={`flex-1 px-3 py-1.5 rounded-lg text-sm transition-colors
                         ${coverPosition === option.value
                           ? "bg-primary text-white"
                           : "bg-bg-elevated text-text-secondary hover:bg-bg-hover"
                         }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Editor Layout */}
      <div>
        <label className="text-sm font-medium text-text-secondary mb-2 block">
          編輯版面
        </label>
        <div className="flex gap-2">
          {([
            { value: "single", label: "單欄" },
            { value: "dual", label: "雙欄" },
          ] as const).map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onChangeEditorLayout(option.value)}
              className={`flex-1 px-3 py-1.5 rounded-lg text-sm transition-colors
                         ${editorLayout === option.value
                           ? "bg-primary text-white"
                           : "bg-bg-elevated text-text-secondary hover:bg-bg-hover"
                         }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {editorLayout === "dual" && (
          <p className="text-xs text-text-muted mt-1.5">
            圖片會顯示在左側，編輯區在右側
          </p>
        )}
      </div>

      {/* Attachments */}
      {isEditing && (
        <AttachmentPanel
          attachments={attachments}
          onLoadAttachment={onLoadAttachment}
          onDeleteAttachment={onDeleteAttachment}
          onUpload={onUploadAttachment}
        />
      )}
    </div>
  );
}
