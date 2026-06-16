
import { useState } from 'react';
import { Trash2, Image, Loader2, AlertCircle } from 'lucide-react';
import { Button, toast } from '../ui';
import { confirm } from '../ui/ConfirmDialog';
import { api } from '../../services/api';
import { useTranslation } from '../../hooks/useTranslation';

interface OrphanImage {
  filename: string;
  size: number;
  path: string;
}

const orphanImageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'];

function countOrphanImageGroups(images: OrphanImage[]): number {
  const filenames = new Set(images.map((image) => image.filename.toLowerCase()));
  const companionThumbCount = images.filter((image) => {
    const match = image.filename.toLowerCase().match(/^(.*)_thumb\.[^.]+$/);
    if (!match) {
      return false;
    }
    return orphanImageExtensions.some((extension) => filenames.has(`${match[1]}${extension}`));
  }).length;
  return images.length - companionThumbCount;
}

export function DangerZoneSection() {
  const { t } = useTranslation();
  // Orphan Image Cleanup
  const [orphanImages, setOrphanImages] = useState<OrphanImage[]>([]);
  const [orphanTotalSize, setOrphanTotalSize] = useState(0);
  const [isScanning, setIsScanning] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Original Image Cleanup
  const [originalStats, setOriginalStats] = useState<{count: number, size: number} | null>(null);
  const [isScanningOriginals, setIsScanningOriginals] = useState(false);
  const [isDeletingOriginals, setIsDeletingOriginals] = useState(false);
  
  // Broken Image Paths
  const [brokenPaths, setBrokenPaths] = useState<{total: number, fixable: number} | null>(null);
  const [isScanningBroken, setIsScanningBroken] = useState(false); // Added missing state
  const [isFixingBroken, setIsFixingBroken] = useState(false); // Added missing state
  const orphanFileCount = orphanImages.length;
  const orphanGroupCount = countOrphanImageGroups(orphanImages);

  // Scan for orphan images
  const scanOrphanImages = async () => {
    setIsScanning(true);
    try {
      const result = await api.getOrphanImages();
      setOrphanImages(result.orphan_images);
      setOrphanTotalSize(result.total_size_mb);
      if (result.total_count === 0) {
        toast.success(t('settings.dangerZone.noOrphanImages'));
      } else {
        const groupCount = countOrphanImageGroups(result.orphan_images);
        toast.info(t('settings.dangerZone.orphanImagesFoundToast', {
          groups: groupCount,
          files: result.total_count,
          size: result.total_size_mb,
        }));
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.dangerZone.scanFailed'));
    } finally {
      setIsScanning(false);
    }
  };

  // Delete all orphan images
  const deleteAllOrphanImages = async () => {
    if (orphanImages.length === 0) {
      toast.warning(t('settings.dangerZone.scanOrphanFirst'));
      return;
    }

    if (!await confirm({
      title: t('settings.dangerZone.deleteOrphanTitle'),
      message: t('settings.dangerZone.deleteOrphanMessage', { groups: orphanGroupCount, files: orphanFileCount }),
      variant: 'danger',
    })) {
      return;
    }

    setIsDeleting(true);
    try {
      const filenames = orphanImages.map(img => img.filename);
      const result = await api.deleteOrphanImages(filenames);
      toast.success(t('settings.dangerZone.deletedImages', { count: result.deleted_count }));
      // Reset state
      setOrphanImages([]);
      setOrphanTotalSize(0);
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.dangerZone.deleteFailed'));
    } finally {
      setIsDeleting(false);
    }
  };

  // Scan for original images (that have thumbnails)
  const scanOriginalImages = async () => {
    setIsScanningOriginals(true);
    try {
      const result = await api.getOriginalImages();
      setOriginalStats({ count: result.original_count, size: result.original_size_mb });
      if (result.original_count === 0) {
        toast.success(t('settings.dangerZone.noOriginalImages'));
      } else {
        toast.info(t('settings.dangerZone.originalImagesFoundToast', {
          count: result.original_count,
          size: result.original_size_mb,
        }));
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.dangerZone.scanFailed'));
    } finally {
      setIsScanningOriginals(false);
    }
  };

  // Delete all original images
  const deleteAllOriginals = async () => {
    if (!originalStats || originalStats.count === 0) {
      toast.warning(t('settings.dangerZone.scanOriginalFirst'));
      return;
    }

    if (!await confirm({
      title: t('settings.dangerZone.deleteOriginalTitle'),
      message: t('settings.dangerZone.deleteOriginalMessage', { count: originalStats.count }),
      variant: 'danger',
    })) {
      return;
    }

    setIsDeletingOriginals(true);
    try {
      const result = await api.deleteOriginalImages();
      toast.success(t('settings.dangerZone.deletedOriginals', {
        count: result.deleted_count,
        size: result.saved_mb,
      }));
      setOriginalStats(null);
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.dangerZone.deleteFailed'));
    } finally {
      setIsDeletingOriginals(false);
    }
  };

  // Scan for broken image paths
  const scanBrokenPaths = async () => {
    setIsScanningBroken(true);
    try {
      const result = await api.getBrokenImages();
      setBrokenPaths({ total: result.total_count, fixable: result.fixable_count });
      if (result.total_count === 0) {
        toast.success(t('settings.dangerZone.noBrokenPaths'));
      } else {
        toast.info(t('settings.dangerZone.brokenPathsFoundToast', {
          total: result.total_count,
          fixable: result.fixable_count,
        }));
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.dangerZone.scanFailed'));
    } finally {
      setIsScanningBroken(false);
    }
  };

  // Fix broken image paths
  const fixAllBrokenPaths = async () => {
    if (!brokenPaths || brokenPaths.fixable === 0) {
      toast.warning(t('settings.dangerZone.noFixablePaths'));
      return;
    }

    setIsFixingBroken(true);
    try {
      const result = await api.fixBrokenImages();
      toast.success(t('settings.dangerZone.fixedBrokenPaths', {
        fixed: result.fixed_count,
        notes: result.updated_notes,
      }));
      setBrokenPaths(null);
    } catch (error: any) {
      toast.error(error?.response?.data?.message || t('settings.dangerZone.fixFailed'));
    } finally {
      setIsFixingBroken(false);
    }
  };

  return (
    <div className="glass rounded-xl p-6 border border-error/30">
      <h2 className="text-lg font-semibold text-error mb-4 flex items-center gap-2">
        <Trash2 size={20} />
        {t('settings.dangerZone.title')}
      </h2>
      
      {/* Orphan Image Cleanup */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image size={20} className="text-text-muted" />
            <div>
              <p className="text-text-primary">{t('settings.dangerZone.orphanTitle')}</p>
              <p className="text-text-muted text-sm">
                {t('settings.dangerZone.orphanDescription')}
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            className="text-primary border-primary/30 hover:bg-primary/10"
            onClick={scanOrphanImages}
            disabled={isScanning}
          >
            {isScanning ? (
              <>
                <Loader2 size={16} className="animate-spin mr-1" />
                {t('settings.dangerZone.scanning')}
              </>
            ) : (
              t('settings.dangerZone.scan')
            )}
          </Button>
        </div>

        {/* Scan Results */}
        {orphanImages.length > 0 && (
          <div className="bg-bg-elevated rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary font-medium">
                  {t('settings.dangerZone.orphanImagesFound', { groups: orphanGroupCount })}
                </p>
                <p className="text-text-muted text-sm">
                  {t('settings.dangerZone.fileSizeSummary', { files: orphanFileCount, size: orphanTotalSize })}
                </p>
              </div>
              <Button
                variant="secondary"
                className="text-error border-error/30 hover:bg-error/10"
                onClick={deleteAllOrphanImages}
                disabled={isDeleting}
              >
                {isDeleting ? (
                  <>
                    <Loader2 size={16} className="animate-spin mr-1" />
                    {t('settings.dangerZone.deleting')}
                  </>
                ) : (
                  t('settings.dangerZone.deleteAll')
                )}
              </Button>
            </div>

            {/* Preview some orphan images */}
            <div className="max-h-32 overflow-y-auto">
              <div className="flex flex-wrap gap-1">
                {orphanImages.slice(0, 10).map((img) => (
                  <span
                    key={img.filename}
                    className="text-xs px-2 py-0.5 bg-bg-secondary rounded text-text-muted truncate max-w-[150px]"
                    title={img.filename}
                  >
                    {img.filename}
                  </span>
                ))}
                {orphanImages.length > 10 && (
                  <span className="text-xs px-2 py-0.5 text-text-muted">
                    {t('settings.dangerZone.moreFiles', { count: orphanImages.length - 10 })}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Divider */}
        <div className="border-t border-border-subtle my-4" />

        {/* Delete Original Images */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image size={20} className="text-text-muted" />
            <div>
              <p className="text-text-primary">{t('settings.dangerZone.originalTitle')}</p>
              <p className="text-text-muted text-sm">
                {t('settings.dangerZone.originalDescription')}
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            className="text-primary border-primary/30 hover:bg-primary/10"
            onClick={scanOriginalImages}
            disabled={isScanningOriginals}
          >
            {isScanningOriginals ? (
              <>
                <Loader2 size={16} className="animate-spin mr-1" />
                {t('settings.dangerZone.scanning')}
              </>
            ) : (
              t('settings.dangerZone.scan')
            )}
          </Button>
        </div>

        {/* Original Images Results */}
        {originalStats && originalStats.count > 0 && (
          <div className="bg-bg-elevated rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary font-medium">
                  {t('settings.dangerZone.originalImagesFound', { count: originalStats.count })}
                </p>
                <p className="text-text-muted text-sm">
                  {t('settings.dangerZone.saveSpaceSummary', { size: originalStats.size })}
                </p>
              </div>
              <Button
                variant="secondary"
                className="text-error border-error/30 hover:bg-error/10"
                onClick={deleteAllOriginals}
                disabled={isDeletingOriginals}
              >
                {isDeletingOriginals ? (
                  <>
                    <Loader2 size={16} className="animate-spin mr-1" />
                    {t('settings.dangerZone.deleting')}
                  </>
                ) : (
                  t('settings.dangerZone.deleteAll')
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Divider */}
        <div className="border-t border-border-subtle my-4" />

        {/* Fix Broken Image Paths */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle size={20} className="text-warning" />
            <div>
              <p className="text-text-primary">{t('settings.dangerZone.brokenTitle')}</p>
              <p className="text-text-muted text-sm">
                {t('settings.dangerZone.brokenDescription')}
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            className="text-primary border-primary/30 hover:bg-primary/10"
            onClick={scanBrokenPaths}
            disabled={isScanningBroken}
          >
            {isScanningBroken ? (
              <>
                <Loader2 size={16} className="animate-spin mr-1" />
                {t('settings.dangerZone.scanning')}
              </>
            ) : (
              t('settings.dangerZone.scan')
            )}
          </Button>
        </div>

        {/* Broken Paths Results */}
        {brokenPaths && brokenPaths.total > 0 && (
          <div className="bg-bg-elevated rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary font-medium">
                  {t('settings.dangerZone.brokenPathsFound', { count: brokenPaths.total })}
                </p>
                <p className="text-text-muted text-sm">
                  {t('settings.dangerZone.fixableSummary', { count: brokenPaths.fixable })}
                </p>
              </div>
              {brokenPaths.fixable > 0 && (
                <Button
                  variant="secondary"
                  className="text-success border-success/30 hover:bg-success/10"
                  onClick={fixAllBrokenPaths}
                  disabled={isFixingBroken}
                >
                  {isFixingBroken ? (
                    <>
                      <Loader2 size={16} className="animate-spin mr-1" />
                      {t('settings.dangerZone.fixing')}
                    </>
                  ) : (
                    t('settings.dangerZone.autoFix')
                  )}
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
