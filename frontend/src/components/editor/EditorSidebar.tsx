
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { FolderOpen, Tag as TagIcon, X, Link2, Image, ChevronDown, ChevronRight } from 'lucide-react';
import { IconButton } from '../ui';
import { Tag } from '../../services/api';
import { AttachmentPanel, Attachment } from './AttachmentPanel';
import { ImageManagementPanel } from './ImageManagementPanel';
import { useAppStore } from '../../stores/appStore';

interface EditorSidebarProps {
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

  // Image Management (v1.5.0)
  content: string;
  coverImage: string | undefined;
  onSetCover: (url: string | null) => void;
  onContentChange: (newContent: string) => void;
}

// Tag input with autocomplete dropdown
function TagAutocomplete({
  tagInput,
  onTagInputChange,
  onTagInputKeyDown,
  selectedTags,
  onRemoveTag,
}: {
  tagInput: string;
  onTagInputChange: (value: string) => void;
  onTagInputKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  selectedTags: Tag[];
  onRemoveTag: (id: number) => void;
}) {
  const { tags: allTags } = useAppStore();
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Filter: match input, exclude already-selected tags
  const suggestions = useMemo(() => {
    if (!tagInput.trim()) return [];
    const query = tagInput.toLowerCase();
    const selectedNames = new Set(selectedTags.map((t) => t.name.toLowerCase()));
    return allTags
      .filter((t) => t.name.toLowerCase().includes(query) && !selectedNames.has(t.name.toLowerCase()))
      .slice(0, 8);
  }, [tagInput, allTags, selectedTags]);

  // Show/hide dropdown
  useEffect(() => {
    setShowDropdown(suggestions.length > 0);
    setHighlightIndex(-1);
  }, [suggestions]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectSuggestion = (tagName: string) => {
    // Simulate: set input to tag name, then fire Enter
    onTagInputChange(tagName);
    // Use setTimeout so the state updates before the keydown fires
    setTimeout(() => {
      inputRef.current?.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })
      );
    }, 0);
    setShowDropdown(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (showDropdown && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHighlightIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlightIndex((prev) => Math.max(prev - 1, 0));
        return;
      }
      if (e.key === 'Enter' && highlightIndex >= 0) {
        e.preventDefault();
        selectSuggestion(suggestions[highlightIndex].name);
        return;
      }
      if (e.key === 'Escape') {
        setShowDropdown(false);
        return;
      }
    }
    // Pass through to parent handler (creates new tag on Enter)
    onTagInputKeyDown(e);
  };

  return (
    <div ref={containerRef}>
      <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
        <TagIcon size={14} /> 標籤
      </label>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={tagInput}
          onChange={(e) => onTagInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (suggestions.length > 0) setShowDropdown(true); }}
          placeholder="輸入標籤後按 Enter"
          className="w-full px-3 py-2 rounded-lg
                     bg-bg-elevated border border-border-default
                     text-text-primary text-sm
                     focus:outline-none focus:border-primary"
        />
        {/* Autocomplete dropdown */}
        {showDropdown && (
          <div className="absolute z-50 w-full mt-1 rounded-lg border border-border-default
                          bg-bg-surface shadow-lg overflow-hidden">
            {suggestions.map((tag, i) => (
              <button
                key={tag.id}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selectSuggestion(tag.name)}
                className={`w-full text-left px-3 py-1.5 text-sm flex justify-between items-center
                  ${i === highlightIndex ? 'bg-primary/20 text-text-primary' : 'text-text-secondary hover:bg-bg-hover'}
                `}
              >
                <span>{tag.name}</span>
                <span className="text-xs text-text-muted">{tag.count}</span>
              </button>
            ))}
          </div>
        )}
      </div>
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
  );
}

export function EditorSidebar({
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
  content,
  coverImage,
  onSetCover,
  onContentChange,
}: EditorSidebarProps) {
  const { categories } = useAppStore();
  const [showImagePanel, setShowImagePanel] = useState(false);

  return (
    <div className="max-h-[38vh] w-full flex-shrink-0 space-y-4 overflow-auto border-t border-border-subtle p-4 lg:max-h-none lg:w-72 lg:border-l lg:border-t-0">
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

      {/* Tags with Autocomplete */}
      <TagAutocomplete
        tagInput={tagInput}
        onTagInputChange={onTagInputChange}
        onTagInputKeyDown={onTagInputKeyDown}
        selectedTags={selectedTags}
        onRemoveTag={onRemoveTag}
      />

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
                <IconButton
                  size="xs"
                  variant="danger"
                  onClick={() => onRemoveUrl(index)}
                  className="opacity-0 group-hover:opacity-100"
                  aria-label="移除連結"
                >
                  <X size={12} />
                </IconButton>
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
      </div>

      {/* Image Management (v1.5.0) */}
      <div>
        <button
          onClick={() => setShowImagePanel(!showImagePanel)}
          data-testid="image-management-toggle"
          className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2 w-full hover:text-text-primary transition-colors"
        >
          {showImagePanel ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <Image size={14} />
          🖼️ 圖片管理
        </button>
        {showImagePanel && (
          <ImageManagementPanel
            content={content}
            coverImage={coverImage}
            onSetCover={onSetCover}
            onContentChange={onContentChange}
          />
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
