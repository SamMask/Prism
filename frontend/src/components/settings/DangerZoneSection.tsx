
import { useState } from 'react';
import { Trash2, Image, Loader2, AlertCircle } from 'lucide-react';
import { Button, toast } from '../ui';
import { confirm } from '../ui/ConfirmDialog';
import { api } from '../../services/api';

interface OrphanImage {
  filename: string;
  size: number;
  path: string;
}

export function DangerZoneSection() {
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

  // Scan for orphan images
  const scanOrphanImages = async () => {
    setIsScanning(true);
    try {
      const result = await api.getOrphanImages();
      setOrphanImages(result.orphan_images);
      setOrphanTotalSize(result.total_size_mb);
      if (result.total_count === 0) {
        toast.success('沒有發現孤兒圖片！');
      } else {
        toast.info(`發現 ${result.total_count} 張孤兒圖片，共 ${result.total_size_mb} MB`);
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '掃描失敗');
    } finally {
      setIsScanning(false);
    }
  };

  // Delete all orphan images
  const deleteAllOrphanImages = async () => {
    if (orphanImages.length === 0) {
      toast.warning('請先掃描孤兒圖片');
      return;
    }

    if (!await confirm({ title: '刪除孤兒圖片', message: `確定要刪除 ${orphanImages.length} 張孤兒圖片嗎？此操作無法復原！`, variant: 'danger' })) {
      return;
    }

    setIsDeleting(true);
    try {
      const filenames = orphanImages.map(img => img.filename);
      const result = await api.deleteOrphanImages(filenames);
      toast.success(`已刪除 ${result.deleted_count} 張圖片`);
      // Reset state
      setOrphanImages([]);
      setOrphanTotalSize(0);
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '刪除失敗');
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
        toast.success('沒有發現可刪除的原圖！');
      } else {
        toast.info(`發現 ${result.original_count} 張原圖，共 ${result.original_size_mb} MB`);
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '掃描失敗');
    } finally {
      setIsScanningOriginals(false);
    }
  };

  // Delete all original images
  const deleteAllOriginals = async () => {
    if (!originalStats || originalStats.count === 0) {
      toast.warning('請先掃描原圖');
      return;
    }

    if (!await confirm({ title: '刪除原圖', message: `確定要刪除 ${originalStats.count} 張原圖嗎？\n\n筆記中的圖片路徑會自動替換為縮圖路徑。此操作無法復原！`, variant: 'danger' })) {
      return;
    }

    setIsDeletingOriginals(true);
    try {
      const result = await api.deleteOriginalImages();
      toast.success(`已刪除 ${result.deleted_count} 張原圖，節省 ${result.saved_mb} MB`);
      setOriginalStats(null);
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '刪除失敗');
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
        toast.success('沒有發現失效的圖片路徑！');
      } else {
        toast.info(`發現 ${result.total_count} 個失效路徑，其中 ${result.fixable_count} 個可修復`);
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '掃描失敗');
    } finally {
      setIsScanningBroken(false);
    }
  };

  // Fix broken image paths
  const fixAllBrokenPaths = async () => {
    if (!brokenPaths || brokenPaths.fixable === 0) {
      toast.warning('沒有可修復的失效路徑');
      return;
    }

    setIsFixingBroken(true);
    try {
      const result = await api.fixBrokenImages();
      toast.success(`已修復 ${result.fixed_count} 個路徑，更新 ${result.updated_notes} 筆筆記`);
      setBrokenPaths(null);
    } catch (error: any) {
      toast.error(error?.response?.data?.message || '修復失敗');
    } finally {
      setIsFixingBroken(false);
    }
  };

  return (
    <div className="glass rounded-xl p-6 border border-error/30">
      <h2 className="text-lg font-semibold text-error mb-4 flex items-center gap-2">
        <Trash2 size={20} />
        危險區域
      </h2>
      
      {/* Orphan Image Cleanup */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image size={20} className="text-text-muted" />
            <div>
              <p className="text-text-primary">清理未使用的圖片</p>
              <p className="text-text-muted text-sm">
                掃描並刪除未被任何筆記引用的孤兒圖片
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
                掃描中...
              </>
            ) : (
              '掃描'
            )}
          </Button>
        </div>

        {/* Scan Results */}
        {orphanImages.length > 0 && (
          <div className="bg-bg-elevated rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary font-medium">
                  發現 {orphanImages.length} 張孤兒圖片
                </p>
                <p className="text-text-muted text-sm">
                  佔用空間：{orphanTotalSize} MB
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
                    刪除中...
                  </>
                ) : (
                  '全部刪除'
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
                    還有 {orphanImages.length - 10} 張...
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
              <p className="text-text-primary">刪除原圖（保留縮圖）</p>
              <p className="text-text-muted text-sm">
                刪除有縮圖的原圖，筆記中的路徑會自動替換
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
                掃描中...
              </>
            ) : (
              '掃描'
            )}
          </Button>
        </div>

        {/* Original Images Results */}
        {originalStats && originalStats.count > 0 && (
          <div className="bg-bg-elevated rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary font-medium">
                  發現 {originalStats.count} 張原圖
                </p>
                <p className="text-text-muted text-sm">
                  可節省 {originalStats.size} MB 空間
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
                    刪除中...
                  </>
                ) : (
                  '全部刪除'
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
              <p className="text-text-primary">修復失效圖片路徑</p>
              <p className="text-text-muted text-sm">
                掃描並修復指向不存在檔案的圖片引用
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
                掃描中...
              </>
            ) : (
              '掃描'
            )}
          </Button>
        </div>

        {/* Broken Paths Results */}
        {brokenPaths && brokenPaths.total > 0 && (
          <div className="bg-bg-elevated rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-text-primary font-medium">
                  發現 {brokenPaths.total} 個失效路徑
                </p>
                <p className="text-text-muted text-sm">
                  其中 {brokenPaths.fixable} 個可自動修復
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
                      修復中...
                    </>
                  ) : (
                    '自動修復'
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
