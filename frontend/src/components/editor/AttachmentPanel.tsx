import React from "react";
import { Paperclip, FileText, Trash2, Plus } from "lucide-react";


export interface Attachment {
  id: number;
  file_path: string;
  file_type: string;
  title: string;
  size_bytes: number;
  is_auto_extracted: boolean;
  created_at: string;
}

interface AttachmentPanelProps {
  attachments: Attachment[];
  onLoadAttachment: (id: number, isAutoExtracted: boolean) => void;
  onDeleteAttachment: (id: number) => void;
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function AttachmentPanel({
  attachments,
  onLoadAttachment,
  onDeleteAttachment,
  onUpload,
}: AttachmentPanelProps) {
  const attachmentInputRef = React.useRef<HTMLInputElement>(null);

  // Wrapper to clean up input after selection (if needed by parent, handled here)
  const handleUploadWrapper = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpload(e);
    if (attachmentInputRef.current) {
      attachmentInputRef.current.value = "";
    }
  };

  return (
    <div data-testid="attachment-panel">
      <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
        <Paperclip size={14} /> 附件
        {attachments.length > 0 && (
          <span className="text-xs bg-bg-elevated px-1.5 py-0.5 rounded">
            {attachments.length}
          </span>
        )}
      </label>

      {/* Attachment List */}
      {attachments.length > 0 && (
        <div className="space-y-1.5 mb-2">
          {attachments.map((att) => (
            <div
              key={att.id}
              data-testid={`attachment-item-${att.id}`}
              className={`flex items-center gap-2 px-2 py-1.5 rounded-lg
                         bg-bg-elevated text-text-secondary text-xs
                         hover:bg-bg-hover group cursor-pointer
                         ${
                           att.is_auto_extracted
                             ? "border-l-2 border-primary"
                             : ""
                         }`}
              onClick={() => onLoadAttachment(att.id, att.is_auto_extracted)}
              title={
                att.is_auto_extracted ? "點擊還原完整內容" : "點擊查看附件"
              }
            >
              <FileText
                size={14}
                className={`flex-shrink-0 ${
                  att.is_auto_extracted ? "text-accent" : "text-primary"
                }`}
              />
              <span className="truncate flex-1" title={att.title}>
                {att.title}
                {att.is_auto_extracted && (
                  <span className="text-accent ml-1">(完整內容)</span>
                )}
              </span>
              <span className="text-text-muted">
                {(att.size_bytes / 1024).toFixed(0)}KB
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation(); // Prevent opening file
                  onDeleteAttachment(att.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-danger
                           transition-opacity"
                title="刪除附件"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload Button */}
      <input
        ref={attachmentInputRef}
        type="file"
        accept=".md,.txt,.markdown"
        onChange={handleUploadWrapper}
        className="hidden"
      />
      <button
        onClick={() => attachmentInputRef.current?.click()}
        data-testid="attachment-upload-button"
        className="w-full flex items-center justify-center gap-2 px-3 py-2
                   rounded-lg border border-dashed border-border-default
                   text-text-muted text-sm
                   hover:border-primary hover:text-primary
                   transition-colors"
      >
        <Plus size={14} />
        新增 .md 附件
      </button>
    </div>
  );
}
