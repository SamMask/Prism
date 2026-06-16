
import { useState, useMemo } from 'react';
import { Image, CheckSquare, Square, Trash2, Star, X, Copy, XCircle } from 'lucide-react';
import { api } from '../../services/api';
import { toast } from '../ui/Toast';
import { confirm } from '../ui/ConfirmDialog';
import { extractImageReferences, removeImageReferences } from './imageReferences';
import { useTranslation } from '../../hooks/useTranslation';

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
  const { t } = useTranslation();
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  const images = useMemo(() => extractImageReferences(content), [content]);

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
    toast.success(t('editor.imagePanel.copiedSyntax'));
  };

  const handleRemoveFromContent = (urls: string[]) => {
    onContentChange(removeImageReferences(content, urls));
    // Clear cover if it was one of the removed images
    if (coverImage && urls.includes(coverImage)) {
      onSetCover(null);
    }
    setSelectedImages(new Set());
    toast.success(t('editor.imagePanel.removedReferences', { count: urls.length }));
  };

  const handleDeleteFiles = async (urls: string[]) => {
    if (!await confirm({
      title: t('editor.imagePanel.deleteTitle'),
      message: t('editor.imagePanel.deleteMessage', { count: urls.length }),
      variant: 'danger',
    })) return;

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
      toast.success(t('editor.imagePanel.deletedFiles', {
        success: successCount,
        failed: failCount > 0 ? t('editor.imagePanel.failedSuffix', { count: failCount }) : '',
      }));
    } else {
      toast.error(t('editor.imagePanel.deleteFailed'));
    }
  };

  if (images.length === 0) {
    return (
      <div className="text-center py-6" data-testid="image-management-empty">
        <Image size={32} className="mx-auto mb-2 text-text-muted opacity-30" />
        <p className="text-sm text-text-muted">{t('editor.imagePanel.empty')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="image-management-panel">
      {/* Toolbar */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          onClick={selectedImages.size === images.length ? clearSelection : selectAll}
          className="flex items-center gap-1 px-2 py-1 text-xs rounded-md
                   bg-bg-elevated text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
        >
          {selectedImages.size === images.length ? <XCircle size={12} /> : <CheckSquare size={12} />}
          {selectedImages.size === images.length ? t('editor.imagePanel.deselectAll') : t('editor.imagePanel.selectAll')}
        </button>

        {selectedImages.size > 0 && (
          <>
            <button
              onClick={() => handleRemoveFromContent(Array.from(selectedImages))}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded-md
                       bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20 transition-colors"
            >
              <X size={12} />
              {t('editor.imagePanel.removeReferences', { count: selectedImages.size })}
            </button>
            <button
              onClick={() => handleDeleteFiles(Array.from(selectedImages))}
              disabled={isDeleting}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded-md
                       bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 size={12} />
              {isDeleting ? t('editor.imagePanel.deleting') : t('editor.imagePanel.deleteFiles', { count: selectedImages.size })}
            </button>
          </>
        )}
      </div>

      {/* Image count */}
      <p className="text-xs text-text-muted">
        {t('editor.imagePanel.countSummary', { count: images.length })}
        {selectedImages.size > 0 ? t('editor.imagePanel.selectedSuffix', { count: selectedImages.size }) : ''}
      </p>

      {/* Image Grid */}
      <div className="grid grid-cols-2 gap-2">
        {images.map((src, index) => {
          const isSelected = selectedImages.has(src);
          const isCover = coverImage === src;

          return (
            <div
              key={index}
              data-testid={`managed-image-${index}`}
              className={`relative group rounded-lg overflow-hidden border transition-all cursor-pointer
                        ${isSelected ? 'border-primary ring-1 ring-primary' : 'border-border-subtle hover:border-border-hover'}
                        ${isCover ? 'ring-2 ring-yellow-500' : ''}`}
            >
              {/* Image */}
              <img
                src={src}
                alt={t('editor.imagePanel.imageAlt', { index: index + 1 })}
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
                  {t('editor.imagePanel.cover')}
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
                  title={isCover ? t('editor.imagePanel.unsetCover') : t('editor.imagePanel.setCover')}
                >
                  <Star size={12} fill={isCover ? 'currentColor' : 'none'} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleCopySyntax(src); }}
                  className="p-1 rounded text-white/70 hover:text-white text-xs transition-colors"
                  title={t('editor.imagePanel.copySyntax')}
                >
                  <Copy size={12} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleRemoveFromContent([src]); }}
                  data-testid={`remove-image-reference-${index}`}
                  className="p-1 rounded text-white/70 hover:text-yellow-400 text-xs transition-colors"
                  title={t('editor.imagePanel.removeReference')}
                >
                  <X size={12} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteFiles([src]); }}
                  className="p-1 rounded text-white/70 hover:text-red-400 text-xs transition-colors"
                  title={t('editor.imagePanel.deleteFile')}
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
