/**
 * useSettings Composable
 * 分類管理、資料匯出、用戶偏好設定
 * v0.8.9: 使用 inject 取得 i18n
 */

import { api } from "../api.js";
import { injectT } from "./useI18n.js";

export function useSettings() {
  const { ref, computed, watch } = Vue;
  const t = injectT(); // v0.8.9: 自動注入翻譯函數

  // Modal State
  const isSettingsOpen = ref(false);
  const isExporting = ref(false);

  // Categories State
  const categories = ref([]);
  const categoriesLoading = ref(false);
  const catEditingId = ref(null);
  const catForm = ref({ name: "", icon: "📁" });
  const catEditMode = computed(() => catEditingId.value !== null);

  // User Preferences (存儲在 localStorage)
  const STORAGE_KEY = "localInsightSettings";

  // 從 localStorage 讀取設定
  const loadSettings = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  };

  // 保存設定到 localStorage
  const saveSettings = (settings) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {
      console.error("Failed to save settings:", e);
    }
  };

  // 自動載入更多卡片 (預設開啟)
  const savedSettings = loadSettings();
  const autoLoadMore = ref(savedSettings.autoLoadMore !== false); // 預設 true

  // 快速新增預設分類 (v0.8.8)
  const quickAddDefaultType = ref(
    savedSettings.quickAddDefaultType || "提示詞"
  );

  // 新增卡片預設分類 (v0.9.0: 綁定到分類星星按鈕)
  const newNoteDefaultType = ref(savedSettings.newNoteDefaultType || "筆記");

  // 圖片保存模式 (v0.8.9): 'both' 或 'thumbnail_only'
  const imageSaveMode = ref(savedSettings.imageSaveMode || "both");

  // 卡片預設開啟模式 (v1.1.1): 'preview' / 'reading' / 'edit'
  const cardOpenMode = ref(savedSettings.cardOpenMode || "reading");

  // 品牌主題色 (v0.8.9): 'default' / 'cyberpunk' / 'eye-care' / 'elegant' / 'ocean' / 'sunset'
  const colorTheme = ref(savedSettings.colorTheme || "default");
  const availableThemes = [
    {
      id: "default",
      name: "專業藍",
      nameEn: "Professional Blue",
      color: "#3b82f6",
    },
    {
      id: "cyberpunk",
      name: "賽博龐克",
      nameEn: "Cyberpunk",
      color: "#e879f9",
    },
    { id: "eye-care", name: "護眼綠", nameEn: "Eye Care", color: "#34d399" },
    { id: "elegant", name: "典雅金", nameEn: "Elegant Gold", color: "#d4a574" },
    { id: "ocean", name: "海洋青", nameEn: "Ocean Teal", color: "#14b8a6" },
    { id: "sunset", name: "夕陽橙", nameEn: "Sunset Orange", color: "#f97316" },
  ];

  // 應用主題到 document
  const applyTheme = (theme) => {
    console.log("[Theme] Applying theme:", theme);
    document.documentElement.setAttribute("data-theme", theme);
    // 強制刷新樣式
    document.documentElement.style.setProperty("--current-theme", theme);
  };

  // 初始化時立即應用主題 (確保在 DOM ready 後)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () =>
      applyTheme(colorTheme.value)
    );
  } else {
    applyTheme(colorTheme.value);
  }

  // 監聽設定變化並自動保存
  watch(autoLoadMore, (newVal) => {
    const current = loadSettings();
    saveSettings({ ...current, autoLoadMore: newVal });
  });

  watch(quickAddDefaultType, (newVal) => {
    const current = loadSettings();
    saveSettings({ ...current, quickAddDefaultType: newVal });
  });

  watch(newNoteDefaultType, (newVal) => {
    const current = loadSettings();
    saveSettings({ ...current, newNoteDefaultType: newVal });
  });

  watch(imageSaveMode, (newVal) => {
    const current = loadSettings();
    saveSettings({ ...current, imageSaveMode: newVal });
  });

  watch(colorTheme, (newVal) => {
    const current = loadSettings();
    saveSettings({ ...current, colorTheme: newVal });
    applyTheme(newVal);
  });

  watch(cardOpenMode, (newVal) => {
    const current = loadSettings();
    saveSettings({ ...current, cardOpenMode: newVal });
  });

  // Orphan Image Cleanup (v0.8)
  const orphanImages = ref([]);
  const orphanImagesLoading = ref(false);
  const orphanTotalSize = ref(0);
  const orphanDeleting = ref(false);

  const loadOrphanImages = async () => {
    orphanImagesLoading.value = true;
    try {
      const result = await api.getOrphanImages();
      if (result.status === "success") {
        orphanImages.value = result.data.orphan_images || [];
        orphanTotalSize.value = result.data.total_size_mb || 0;
      }
    } catch (error) {
      console.error("Load orphan images error:", error);
    } finally {
      orphanImagesLoading.value = false;
    }
  };

  const deleteOrphanImages = async (filenames) => {
    if (!filenames || filenames.length === 0) return;

    orphanDeleting.value = true;
    try {
      const result = await api.deleteOrphanImages(filenames);
      if (result.status === "success") {
        // 從列表中移除已刪除的圖片
        orphanImages.value = orphanImages.value.filter(
          (img) => !filenames.includes(img.filename)
        );
        return result.data.deleted_count;
      }
    } catch (error) {
      console.error("Delete orphan images error:", error);
      throw error;
    } finally {
      orphanDeleting.value = false;
    }
  };

  const deleteAllOrphanImages = async () => {
    const filenames = orphanImages.value.map((img) => img.filename);
    return await deleteOrphanImages(filenames);
  };

  // Original Images Cleanup (v0.8.9)
  const originalImagesStats = ref({
    original_count: 0,
    original_size_mb: 0,
    thumbnail_count: 0,
  });
  const originalImagesLoading = ref(false);
  const originalImagesDeleting = ref(false);

  const loadOriginalImagesStats = async () => {
    originalImagesLoading.value = true;
    try {
      const result = await api.getOriginalImages();
      if (result.status === "success") {
        originalImagesStats.value = result.data;
      }
    } catch (error) {
      console.error("Load original images error:", error);
    } finally {
      originalImagesLoading.value = false;
    }
  };

  const deleteAllOriginals = async () => {
    originalImagesDeleting.value = true;
    try {
      const result = await api.deleteAllOriginals();
      if (result.status === "success") {
        // 清除統計數據
        originalImagesStats.value = {
          original_count: 0,
          original_size_mb: 0,
          thumbnail_count: originalImagesStats.value.thumbnail_count,
        };
        return result.data;
      }
    } catch (error) {
      console.error("Delete all originals error:", error);
      throw error;
    } finally {
      originalImagesDeleting.value = false;
    }
  };

  const handleDeleteAllOriginals = async () => {
    const confirmMsg = t
      ? t(
          "originalImages.confirmDelete",
          "確定要刪除所有原圖嗎？此操作無法復原，但筆記中的圖片路徑會自動改為縮圖。"
        )
      : "確定要刪除所有原圖嗎？";
    if (!confirm(confirmMsg)) return;

    try {
      const data = await deleteAllOriginals();
      if (data) {
        const successMsg = t
          ? t("originalImages.deleted", "已刪除 {count} 個原圖，釋放 {size} MB")
              .replace("{count}", data.deleted_count)
              .replace("{size}", data.saved_mb)
          : `已刪除 ${data.deleted_count} 個原圖，釋放 ${data.saved_mb} MB`;
        alert(successMsg);
      }
    } catch (error) {
      alert("刪除失敗: " + error.message);
    }
  };

  // Broken Images Fix (v0.8.9)
  const brokenImagesStats = ref({
    total_count: 0,
    broken_paths: [],
  });
  const brokenImagesLoading = ref(false);
  const brokenImagesFixing = ref(false);

  const loadBrokenImages = async () => {
    brokenImagesLoading.value = true;
    try {
      const result = await api.getBrokenImages();
      if (result.status === "success") {
        brokenImagesStats.value = result.data;
      }
    } catch (error) {
      console.error("Load broken images error:", error);
    } finally {
      brokenImagesLoading.value = false;
    }
  };

  const fixBrokenImages = async () => {
    brokenImagesFixing.value = true;
    try {
      const result = await api.fixBrokenImages();
      if (result.status === "success") {
        brokenImagesStats.value = { total_count: 0, broken_paths: [] };
        return result.data;
      }
    } catch (error) {
      console.error("Fix broken images error:", error);
      throw error;
    } finally {
      brokenImagesFixing.value = false;
    }
  };

  const handleFixBrokenImages = async (onSuccess) => {
    const confirmMsg = t
      ? t("brokenImages.confirmFix", "確定要修正所有失效的圖片路徑嗎？")
      : "確定要修正所有失效的圖片路徑嗎？";
    if (!confirm(confirmMsg)) return;

    try {
      const data = await fixBrokenImages();
      if (data) {
        const successMsg = t
          ? t(
              "brokenImages.fixed",
              "已修正 {count} 個圖片路徑，更新了 {notes} 則筆記"
            )
              .replace("{count}", data.fixed_count)
              .replace("{notes}", data.updated_notes)
          : `已修正 ${data.fixed_count} 個圖片路徑，更新了 ${data.updated_notes} 則筆記`;
        alert(successMsg);

        // 刷新筆記列表
        if (onSuccess && typeof onSuccess === "function") {
          onSuccess();
        }
      }
    } catch (error) {
      alert("修正失敗: " + error.message);
    }
  };

  // Database VACUUM (v0.8.9)
  const vacuumLoading = ref(false);
  const vacuumResult = ref(null);

  const vacuumDatabase = async () => {
    if (
      !confirm(
        t(
          "settings.vacuumConfirm",
          "確定要整理資料庫嗎？這可能需要幾秒鐘時間。"
        )
      )
    ) {
      return;
    }

    vacuumLoading.value = true;
    vacuumResult.value = null;
    try {
      const response = await fetch("/api/system/vacuum", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const result = await response.json();
      if (result.status === "success") {
        vacuumResult.value = result.data;
        const msg =
          t("settings.vacuumSuccess", "資料庫整理完成！") +
          ` ${result.data.size_before_mb} MB → ${result.data.size_after_mb} MB` +
          ` (${t("settings.freed", "釋放")} ${result.data.freed_mb} MB)`;
        console.log("[VACUUM]", msg);
      } else {
        alert("整理失敗: " + result.message);
      }
    } catch (error) {
      alert("整理失敗: " + error.message);
    } finally {
      vacuumLoading.value = false;
    }
  };

  // WAL Checkpoint (v1.2)
  const walCheckpointing = ref(false);
  const walCheckpointResult = ref(null);

  const walCheckpoint = async () => {
    walCheckpointing.value = true;
    walCheckpointResult.value = null;
    try {
      const response = await fetch("/api/system/wal-checkpoint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const result = await response.json();
      if (result.status === "success") {
        walCheckpointResult.value = result.data;
        console.log("[WAL Checkpoint]", result.data.message);
      } else {
        alert(
          t("settings.walCheckpointFailed", "WAL 合併失敗") +
            ": " +
            result.message
        );
      }
    } catch (error) {
      alert(
        t("settings.walCheckpointFailed", "WAL 合併失敗") + ": " + error.message
      );
    } finally {
      walCheckpointing.value = false;
    }
  };

  // Startup Preference (v1.1)
  const startupAutoOpen = ref(null);

  const loadStartupPreference = async () => {
    try {
      const response = await fetch("/api/system/startup-preference");
      const result = await response.json();
      if (result.status === "success") {
        startupAutoOpen.value = result.data.auto_open_browser;
      }
    } catch (error) {
      console.error("Load startup preference error:", error);
    }
  };

  const toggleAutoOpenBrowser = async () => {
    try {
      const newValue = !startupAutoOpen.value;
      const response = await fetch("/api/system/startup-preference", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_open_browser: newValue }),
      });
      const result = await response.json();
      if (result.status === "success") {
        startupAutoOpen.value = newValue;
      }
    } catch (error) {
      console.error("Toggle startup preference error:", error);
      alert("設定失敗: " + error.message);
    }
  };

  // 初始載入啟動偏好
  loadStartupPreference();

  // Port Configuration (v1.5.0)
  const portConfig = ref({
    preferred_port: 5000,
    fallback_enabled: true,
    fallback_range: 20,
    current_port: null
  });
  const portConfigLoading = ref(false);
  const portConfigSaving = ref(false);

  const loadPortConfig = async () => {
    portConfigLoading.value = true;
    try {
      const response = await fetch('/api/system/port-config');
      const result = await response.json();
      if (result.status === 'success') {
        portConfig.value = result.data;
      }
    } catch (error) {
      console.error('Load port config error:', error);
    } finally {
      portConfigLoading.value = false;
    }
  };

  const savePortConfig = async () => {
    portConfigSaving.value = true;
    try {
      const response = await fetch('/api/system/port-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferred_port: portConfig.value.preferred_port,
          fallback_enabled: portConfig.value.fallback_enabled,
          fallback_range: portConfig.value.fallback_range
        })
      });
      const result = await response.json();
      if (result.status === 'success') {
        alert(result.message || t('settings.portConfigSaved', '端口設定已儲存，下次啟動時生效'));
      } else {
        alert(t('settings.portConfigFailed', '儲存失敗') + ': ' + result.message);
      }
    } catch (error) {
      console.error('Save port config error:', error);
      alert(t('settings.portConfigFailed', '儲存失敗') + ': ' + error.message);
    } finally {
      portConfigSaving.value = false;
    }
  };

  // 初始載入端口設定
  loadPortConfig();

  // Clear History (v1.1)
  const clearingHistory = ref(false);

  const clearHistory = async () => {
    if (
      !confirm(
        t(
          "settings.clearHistoryConfirm",
          "確定要清空所有歷史版本嗎？此操作無法復原。"
        )
      )
    ) {
      return;
    }

    clearingHistory.value = true;
    try {
      const response = await fetch("/api/system/clear-history", {
        method: "POST",
      });
      const result = await response.json();

      if (result.status === "success") {
        const count = result.data.deleted_count;
        alert(
          t("settings.clearHistorySuccess", `已清空 ${count} 個歷史版本記錄`)
        );
      } else {
        alert("清空失敗: " + result.message);
      }
    } catch (error) {
      console.error("Clear history error:", error);
      alert("清空失敗: " + error.message);
    } finally {
      clearingHistory.value = false;
    }
  };

  // Load Categories
  const catLoadList = async () => {
    categoriesLoading.value = true;
    try {
      const result = await api.getCategories();
      if (result.status === "success") {
        categories.value = result.data || [];
      }
    } catch (error) {
      console.error("Load categories error:", error);
    } finally {
      categoriesLoading.value = false;
    }
  };

  // Create Category
  const catCreate = async () => {
    const name = catForm.value.name.trim();
    if (!name) {
      alert(t("messages.enterCategoryName"));
      return;
    }

    try {
      const result = await api.createCategory({
        name: name,
        icon: catForm.value.icon || "📁",
      });

      if (result.status === "success") {
        await catLoadList();
        catForm.value = { name: "", icon: "📁" };
      }
    } catch (error) {
      console.error("Create category error:", error);
      alert(error.message || t("messages.addCategoryFailed"));
    }
  };

  // Start Edit Category
  const catStartEdit = (category) => {
    catEditingId.value = category.id;
    catForm.value = { name: category.name, icon: category.icon || "📁" };
  };

  // Cancel Edit
  const catCancelEdit = () => {
    catEditingId.value = null;
    catForm.value = { name: "", icon: "📁" };
  };

  // Save Edit
  const catSaveEdit = async () => {
    const id = catEditingId.value;
    const name = catForm.value.name.trim();
    if (!name) {
      alert(t("messages.categoryNameEmpty"));
      return;
    }

    try {
      const result = await api.updateCategory(id, {
        name: name,
        icon: catForm.value.icon || "📁",
      });

      if (result.status === "success") {
        await catLoadList();
        catCancelEdit();
      }
    } catch (error) {
      console.error("Update category error:", error);
      alert(error.message || t("messages.updateCategoryFailed"));
    }
  };

  // Delete Category
  const catDelete = async (categoryId) => {
    const category = categories.value.find((c) => c.id === categoryId);
    if (!category) return;

    if (category.is_default) {
      alert(t("messages.cannotDeleteDefault"));
      return;
    }

    const noteCount = category.count || 0;

    // 如果沒有筆記，直接刪除
    if (noteCount === 0) {
      if (
        !confirm(
          t(
            "messages.confirmDeleteCategory",
            `確定要刪除分類「${category.name}」嗎？`
          ).replace("{name}", category.name)
        )
      ) {
        return;
      }

      try {
        const result = await api.deleteCategory(categoryId);
        if (result.status === "success") {
          await catLoadList();
        }
      } catch (error) {
        console.error("Delete category error:", error);
        alert(error.message || t("messages.deleteCategoryFailed"));
      }
      return;
    }

    // 有筆記時，讓用戶選擇目標分類
    const otherCategories = categories.value.filter((c) => c.id !== categoryId);
    if (otherCategories.length === 0) {
      alert(t("messages.noOtherCategories"));
      return;
    }

    // 建立選項清單
    const optionsList = otherCategories
      .map((c, i) => `${i + 1}. ${c.icon} ${c.name}`)
      .join("\n");
    const userInput = prompt(
      `分類「${category.name}」包含 ${noteCount} 則筆記。\n\n` +
        `請輸入要將筆記移動到的分類編號：\n\n${optionsList}`,
      "1"
    );

    if (userInput === null) return; // 用戶取消

    const selectedIndex = parseInt(userInput) - 1;
    if (
      isNaN(selectedIndex) ||
      selectedIndex < 0 ||
      selectedIndex >= otherCategories.length
    ) {
      alert(t("messages.invalidSelection"));
      return;
    }

    const targetCategory = otherCategories[selectedIndex].name;

    if (
      !confirm(
        `確定要刪除分類「${category.name}」？\n\n` +
          `${noteCount} 則筆記將會移動到「${targetCategory}」分類。`
      )
    ) {
      return;
    }

    try {
      const result = await api.deleteCategory(categoryId, targetCategory);

      if (result.status === "success") {
        await catLoadList();
      }
    } catch (error) {
      console.error("Delete category error:", error);
      alert(error.message || t("messages.deleteCategoryFailed"));
    }
  };

  // Export Functions
  const exportJSON = () => {
    isExporting.value = true;
    try {
      window.location.href = api.getExportJsonUrl();
    } finally {
      setTimeout(() => {
        isExporting.value = false;
      }, 1000);
    }
  };

  const exportDB = () => {
    isExporting.value = true;
    try {
      window.location.href = api.getExportDbUrl();
    } finally {
      setTimeout(() => {
        isExporting.value = false;
      }, 1000);
    }
  };

  // Import Functions (v1.1)
  const importFileInput = ref(null);
  const isImporting = ref(false);

  const triggerImportFile = () => {
    if (importFileInput.value) {
      importFileInput.value.click();
    }
  };

  const handleImportFile = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const fileCount = files.length;
    const mdFiles = Array.from(files).filter((f) => f.name.endsWith(".md"));

    if (mdFiles.length === 0) {
      alert(t ? t("messages.noMdFiles", "未找到 .md 檔案") : "未找到 .md 檔案");
      return;
    }

    // 提示批量匯入
    if (fileCount > 1) {
      const confirmMsg = t
        ? t(
            "messages.confirmBatchImport",
            `即將匯入 ${mdFiles.length} 個 Markdown 檔案，是否繼續？`
          )
        : `即將匯入 ${mdFiles.length} 個 Markdown 檔案，是否繼續？`;
      if (!confirm(confirmMsg)) {
        event.target.value = "";
        return;
      }
    }

    isImporting.value = true;
    let successCount = 0;
    let failCount = 0;
    const errors = [];

    try {
      // 批量處理檔案
      for (const file of mdFiles) {
        try {
          const formData = new FormData();
          formData.append("file", file);

          const response = await fetch("/api/notes/import/md", {
            method: "POST",
            body: formData,
          });

          const result = await response.json();

          if (result.status === "success") {
            successCount++;
          } else {
            failCount++;
            errors.push(`${file.name}: ${result.message}`);
          }
        } catch (error) {
          failCount++;
          errors.push(`${file.name}: ${error.message}`);
        }
      }

      // 顯示結果
      if (failCount === 0) {
        const successMsg =
          fileCount === 1
            ? t
              ? t("messages.importSuccess", "匯入成功！")
              : "匯入成功！"
            : `成功匯入 ${successCount} 個檔案！`;
        alert(successMsg);

        // 重新載入筆記列表
        if (window.location.pathname === "/") {
          window.location.reload();
        }
      } else {
        const summary = `成功: ${successCount}, 失敗: ${failCount}\n\n失敗詳情:\n${errors.join(
          "\n"
        )}`;
        alert(summary);

        // 如果有成功的，仍然重新載入
        if (successCount > 0 && window.location.pathname === "/") {
          window.location.reload();
        }
      }
    } catch (error) {
      console.error("Import error:", error);
      alert(
        t
          ? t("messages.importFailed", "匯入失敗")
          : "匯入失敗: " + error.message
      );
    } finally {
      isImporting.value = false;
      // 清空 file input
      if (event.target) {
        event.target.value = "";
      }
    }
  };

  // Close Settings
  const closeSettings = () => {
    isSettingsOpen.value = false;
    catCancelEdit();
  };

  return {
    // Modal
    isSettingsOpen,
    closeSettings,

    // Export
    isExporting,
    exportJSON,
    exportDB,

    // Import (v1.1)
    importFileInput,
    isImporting,
    triggerImportFile,
    handleImportFile,

    // Categories (camelCase)
    categories,
    categoriesLoading,
    catLoadList,
    catCreate,
    catEditingId,
    catStartEdit,
    catCancelEdit,
    catSaveEdit,
    catDelete,
    catForm,
    catEditMode,

    // User Preferences
    autoLoadMore,
    quickAddDefaultType,
    newNoteDefaultType,
    imageSaveMode,
    cardOpenMode,
    colorTheme,
    availableThemes,

    // Orphan Image Cleanup (v0.8)
    orphanImages,
    orphanImagesLoading,
    orphanTotalSize,
    orphanDeleting,
    loadOrphanImages,
    deleteOrphanImages,
    deleteAllOrphanImages,

    // Original Images Cleanup (v0.8.9)
    originalImagesStats,
    originalImagesLoading,
    originalImagesDeleting,
    loadOriginalImagesStats,
    deleteAllOriginals,
    handleDeleteAllOriginals,

    // Broken Images Fix (v0.8.9)
    brokenImagesStats,
    brokenImagesLoading,
    brokenImagesFixing,
    loadBrokenImages,
    fixBrokenImages,
    handleFixBrokenImages,

    // Database VACUUM (v0.8.9)
    vacuumLoading,
    vacuumResult,
    vacuumDatabase,

    // WAL Checkpoint (v1.2)
    walCheckpointing,
    walCheckpointResult,
    walCheckpoint,

    // Clear History (v1.1)
    clearingHistory,
    clearHistory,

    // Startup Preference (v1.1)
    startupAutoOpen,
    toggleAutoOpenBrowser,
    loadStartupPreference,

    // Port Configuration (v1.5.0)
    portConfig,
    portConfigLoading,
    portConfigSaving,
    loadPortConfig,
    savePortConfig,
  };
}
