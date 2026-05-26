
import { useState, useMemo } from 'react';
import { Image, CheckSquare, Square, Trash2, Star, X, Copy, XCircle } from 'lucide-react';
import { api } from '../../services/api';
import { toast } from '../ui/Toast';
import { confirm } from '../ui/ConfirmDialog';
import { removeImageReferences } from './imageReferences';

interface ImageManagementPanelProps {
  content: string;
  coverImage: string | undefined;
  onSetCover: (url: string | null) => void;
  onContentChange: (newContent: string) => void;
}

export function ImageManagementPanel({
  content,
  coverImage,
  onSetCover,
  onContentChange,
}: ImageManagementPanelProps) {
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  // Extract all images from content
  const images = useMemo(() => {
    const pattern = /!\[.*?\]\(([^)]+)\)/g;
    const found: string[] = [];
    let match;
    while ((match = pattern.exec(content)) !== null) {
      if (!found.includes(match[1])) {
        found.push(match[1]);
      }
    }
    return found;
  }, [content]);

  const toggleSelect = (url: string) => {
    setSelectedImages(prev => {
      const next = new Set(prev);
      if (next.has(url)) {
        next.delete(url);
      } else {
        next.add(url);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedImages(new Set(images));
  };

  const clearSelection = () => {
    setSelectedImages(new Set());
  };

  const handleSetCover = (url: string) => {
    if (coverImage === url) {
      onSetCover(null);
    } else {
      onSetCover(url);
    }
  };

  const handleCopySyntax = (url: string) => {
    navigator.clipboard.writeText(`![image](${url})`);
    toast.success('已複製圖片語法');
  };

  const handleRemoveFromContent = (urls: string[]) => {
    onContentChange(removeImageReferences(content, urls));
    // Clear cover if it was one of the removed images
    if (coverImage && urls.includes(coverImage)) {
      onSetCover(null);
    }
    setSelectedImages(new Set());
    toast.success(`已從內容移除 ${urls.length} 張圖片引用`);
  };

  const handleDeleteFiles = async (urls: string[]) => {
    if (!await confirm({ title: '刪除圖片', message: `確定要刪除 ${urls.length} 個圖片檔案嗎？此操作無法還原。`, variant: 'danger' })) return;

    setIsDeleting(true);
    let successCount = 0;
    let failCount = 0;

    for (const url of urls) {
      try {
        await api.deleteImage(url);
        successCount++;
      } catch {
        failCount++;
      }
    }

    // Also remove from content
    handleRemoveFromContent(urls);

    setIsDeleting(false);
    if (successCount > 0) {
      toast.success(`已刪除 ${successCount} 個檔案${failCount > 0 ? `，${failCount} 個失敗` : ''}`);
    } else {
      toast.error('刪除失敗');
    }
  };

  if (images.length === 0) {
    return (
      <div className="text-center py-6">
        <Image size={32} className="mx-auto mb-2 text-text-muted opacity-30" />
        <p className="text-sm text-text-muted">此筆記尚無圖片</p>
        <p className="text-xs text-text-muted mt-1">在內容中加入圖片後會顯示在此</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          onClick={selectedImages.size === images.length ? clearSelection : selectAll}
          className="flex items-center gap-1 px-2 py-1 text-xs rounded-md
                   bg-bg-elevated text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
        >
          {selectedImages.size === images.length ? <XCircle size={12} /> : <CheckSquare size={12} />}
          {selectedImages.size === images.length ? '取消全選' : '全選'}
        </button>

        {selectedImages.size > 0 && (
          <>
            <button
              onClick={() => handleRemoveFromContent(Array.from(selectedImages))}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded-md
                       bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20 transition-colors"
            >
              <X size={12} />
              移除引用 ({selectedImages.size})
            </button>
            <button
              onClick={() => handleDeleteFiles(Array.from(selectedImages))}
              disabled={isDeleting}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded-md
                       bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 size={12} />
              {isDeleting ? '刪除中...' : `刪除檔案 (${selectedImages.size})`}
            </button>
          </>
        )}
      </div>

      {/* Image count */}
      <p className="text-xs text-text-muted">
        共 {images.length} 張圖片{selectedImages.size > 0 ? `，已選 ${selectedImages.size} 張` : ''}
      </p>

      {/* Image Grid */}
      <div className="grid grid-cols-2 gap-2">
        {images.map((src, index) => {
          const isSelected = selectedImages.has(src);
          const isCover = coverImage === src;

          return (
            <div
              key={index}
              className={`relative group rounded-lg overflow-hidden border transition-all cursor-pointer
                        ${isSelected ? 'border-primary ring-1 ring-primary' : 'border-border-subtle hover:border-border-hover'}
                        ${isCover ? 'ring-2 ring-yellow-500' : ''}`}
            >
              {/* Image */}
              <img
                src={src}
                alt={`圖片 ${index + 1}`}
                className="w-full h-20 object-cover"
                onClick={() => window.open(src, '_blank')}
              />

              {/* Selection checkbox */}
              <button
                onClick={(e) => { e.stopPropagation(); toggleSelect(src); }}
                className="absolute top-1 left-1 p-0.5 rounded bg-black/50 text-white hover:bg-black/70 transition-colors"
              >
                {isSelected ? <CheckSquare size={14} className="text-primary" /> : <Square size={14} />}
              </button>

              {/* Cover badge */}
              {isCover && (
                <span className="absolute top-1 right-1 px-1.5 py-0.5 text-[10px] font-medium rounded
                             bg-yellow-500 text-black">
                  封面
                </span>
              )}

              {/* Hover actions */}
              <div className="absolute bottom-0 left-0 right-0 p-1 bg-gradient-to-t from-black/80 to-transparent
                            opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                <button
                  onClick={(e) => { e.stopPropagation(); handleSetCover(src); }}
                  className={`p-1 rounded text-xs transition-colors ${
                    isCover ? 'text-yellow-400 hover:text-yellow-300' : 'text-white/70 hover:text-yellow-400'
                  }`}
                  title={isCover ? '取消封面' : '設為封面'}
                >
                  <Star size={12} fill={isCover ? 'currentColor' : 'none'} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleCopySyntax(src); }}
                  className="p-1 rounded text-white/70 hover:text-white text-xs transition-colors"
                  title="複製語法"
                >
                  <Copy size={12} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleRemoveFromContent([src]); }}
                  className="p-1 rounded text-white/70 hover:text-yellow-400 text-xs transition-colors"
                  title="移除引用"
                >
                  <X size={12} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteFiles([src]); }}
                  className="p-1 rounded text-white/70 hover:text-red-400 text-xs transition-colors"
                  title="刪除檔案"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
