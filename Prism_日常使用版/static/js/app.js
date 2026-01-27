/**
 * Local Insight v1.0
 * Main Application Entry Point (ES Modules)
 * 
 * 此檔案為模組化重構後的主入口。
 * 使用方式: <script type="module" src="/static/js/app.js"></script>
 */

import { useNotes } from './composables/useNotes.js?v=1.0';
import { useTags } from './composables/useTags.js?v=1.0';
import { useEditor } from './composables/useEditor.js?v=1.0';
import { useSettings } from './composables/useSettings.js?v=1.0';
import { provideI18n } from './composables/useI18n.js?v=1.0';

const { createApp, watch, onMounted, ref, computed } = Vue;

const app = createApp({
    setup() {
        // v0.8.9: 使用 provide/inject 模式，t() 會自動注入到所有 composables
        const i18nComposable = provideI18n();
        const t = i18nComposable.t;

        // Composables (不再需要傳遞 t，使用 inject 自動取得)
        const notesComposable = useNotes();
        const tagsComposable = useTags();
        const settingsComposable = useSettings();
        // useEditor needs quickAddDefaultType, newNoteDefaultType, imageSaveMode, cardOpenMode callbacks
        const editorComposable = useEditor(
            () => settingsComposable.quickAddDefaultType.value,
            () => settingsComposable.newNoteDefaultType.value,
            () => settingsComposable.imageSaveMode.value,
            () => settingsComposable.cardOpenMode.value
        );

        // UI State
        const langDropdownOpen = ref(false);
        const mobileSidebarOpen = ref(false);  // Mobile sidebar toggle (v0.8.9)

        // Callbacks for cross-composable communication
        const refreshNotes = () => notesComposable.fetchNotes(1, false);
        const refreshTags = () => tagsComposable.fetchTags();

        // Wrappers to sync tags after batch operations (v0.9.0)
        const handleBatchAddTag = async (tagName) => {
            await notesComposable.batch_addTag(tagName);
            await refreshTags();
        };

        const handleDeleteSelected = async () => {
            await notesComposable.deleteSelectedNotes();
            await refreshTags();
        };

        const getTypeColor = (type) => {
            const map = {
                '提示詞': 'bg-yellow-500',
                '筆記': 'bg-blue-500',
                '教學': 'bg-green-500',
                '資料': 'bg-purple-500',
                '靈感': 'bg-pink-500'
            };
            return map[type] || 'bg-gray-500';
        };

        // Watch for filter changes
        let isInitialLoadComplete = false;
        
        watch(
            [
                notesComposable.selectedType,
                notesComposable.selectedTags,
                notesComposable.tagFilterMode,
                notesComposable.debouncedSearchKeyword
            ],
            () => {
                if (isInitialLoadComplete) {
                    notesComposable.fetchNotes(1, false);
                }
            },
            { deep: true }
        );

        // Watch categories changes and sync to types
        watch(
            settingsComposable.categories,
            (newCategories) => {
                notesComposable.syncTypesFromCategories(newCategories);
            },
            { deep: true }
        );

        // Computed properties
        const recommendedTags = computed(() => {
            // Sort tags by usage count descending (v0.9.0)
            return [...tagsComposable.tags.value]
                .sort((a, b) => (b.count || 0) - (a.count || 0))
                .slice(0, 8);
        });

        // Lifecycle
        onMounted(async () => {
            // Keyboard shortcuts
            window.addEventListener('keydown', (e) => {
                // Ctrl+A to select all in selection mode
                if (notesComposable.isSelectionMode.value && (e.ctrlKey || e.metaKey) && e.key === 'a') {
                    e.preventDefault();
                    notesComposable.selectAllNotes();
                }
                // ESC to cancel selection mode
                if (notesComposable.isSelectionMode.value && e.key === 'Escape') {
                    e.preventDefault();
                    notesComposable.toggleSelectionMode();
                }
            });
            
            // Infinite scroll (respects autoLoadMore setting)
            let scrollTimeout = null;
            window.addEventListener('scroll', () => {
                // 只有在 autoLoadMore 開啟時才自動載入
                if (!settingsComposable.autoLoadMore.value) return;
                
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    const scrollY = window.scrollY;
                    const windowHeight = window.innerHeight;
                    const docHeight = document.documentElement.scrollHeight;
                    
                    // 當滾動到距離底部 300px 時載入更多
                    if (scrollY + windowHeight >= docHeight - 300) {
                        if (notesComposable.hasMore.value && 
                            !notesComposable.notesLoading.value && 
                            !notesComposable.loadingMore.value) {
                            notesComposable.loadMoreNotes();
                        }
                    }
                }, 100);  // 100ms debounce
            });

            // Load initial data
            await settingsComposable.catLoadList();
            // 同步 categories 到 types
            notesComposable.syncTypesFromCategories(settingsComposable.categories.value);
            await tagsComposable.fetchTags();
            await notesComposable.fetchNotes();
            
            isInitialLoadComplete = true;
        });

        // Return all composable properties for template access
        return {
            // Notes
            ...notesComposable,
            // Override batch actions (v0.9.0)
            batch_addTag: handleBatchAddTag,
            deleteSelectedNotes: handleDeleteSelected,
            
            // Helper
            getTypeColor,
            
            // Tags
            tags: tagsComposable.tags,
            recommendedTags, // v0.9.0
            tagsLoading: tagsComposable.tagsLoading,
            tagsError: tagsComposable.tagsError,
            fetchTags: tagsComposable.fetchTags,
            tagContextMenu: tagsComposable.tagContextMenu,
            openTagContextMenu: tagsComposable.openTagContextMenu,
            tagRenameModal: tagsComposable.tagRenameModal,
            openTagRenameModal: tagsComposable.openTagRenameModal,
            confirmRenameTag: () => tagsComposable.confirmRenameTag(refreshNotes),
            tagMergeModal: tagsComposable.tagMergeModal,
            openTagMergeModal: tagsComposable.openTagMergeModal,
            confirmMergeTag: () => tagsComposable.confirmMergeTag((targetId) => {
                // 選中目標標籤來顯示合併後的結果
                notesComposable.selectedTags.value = [targetId];
                refreshNotes();
            }),
            deleteTag: () => tagsComposable.deleteTag(() => {
                // 清除標籤過濾器，因為被刪除的標籤已不存在
                notesComposable.selectedTags.value = [];
                refreshNotes();
            }),
            closeTagModals: tagsComposable.closeTagModals,
            
            // Editor
            isEditing: editorComposable.isEditing,
            isQuickAddOpen: editorComposable.isQuickAddOpen, // v0.9.0
            isPromptMode: editorComposable.isPromptMode,
            activeTab: editorComposable.activeTab,
            isContentPreview: editorComposable.isContentPreview,
            isReadingMode: editorComposable.isReadingMode,  // v1.1
            isSaving: editorComposable.isSaving,
            isDeleting: editorComposable.isDeleting,
            isDuplicating: editorComposable.isDuplicating,
            isUploading: editorComposable.isUploading,
            isRestoring: editorComposable.isRestoring,
            currentNote: editorComposable.currentNote,
            newTagInput: editorComposable.newTagInput,
            openEditor: editorComposable.openEditor,
            openQuickAdd: editorComposable.openQuickAdd, // v0.9.0
            closeEditor: editorComposable.closeEditor,
            saveNote: () => editorComposable.saveNote(() => {
                refreshNotes();
                refreshTags();
            }),
            deleteNote: () => editorComposable.deleteNote(() => {
                refreshNotes();
                refreshTags();
            }),
            duplicateNote: () => editorComposable.duplicateNote(refreshNotes),
            addUrl: editorComposable.addUrl,
            removeUrl: editorComposable.removeUrl,
            addTag: editorComposable.addTag,
            removeTag: editorComposable.removeTag,
            toggleTag: editorComposable.toggleTag,
            isTagSelected: editorComposable.isTagSelected,
            handleUpload: editorComposable.handleUpload,
            handlePasteInEditor: editorComposable.handlePasteInEditor,
            noteHistory: editorComposable.noteHistory,
            historyLoading: editorComposable.historyLoading,
            loadNoteHistory: editorComposable.loadNoteHistory,
            restoreVersion: editorComposable.restoreVersion,
            clearNoteHistory: editorComposable.clearNoteHistory,
            markedContent: editorComposable.markedContent,
            hasUnsavedChanges: editorComposable.hasUnsavedChanges,
            
            // Images (v0.8.2)
            contentImages: editorComposable.contentImages,
            deleteImageFromContent: editorComposable.deleteImageFromContent,
            copyImageSyntax: editorComposable.copyImageSyntax,
            exportImages: editorComposable.exportImages,
            isDeletingImage: editorComposable.isDeletingImage,
            
            // Settings (camelCase)
            isSettingsOpen: settingsComposable.isSettingsOpen,
            isExporting: settingsComposable.isExporting,
            exportJSON: settingsComposable.exportJSON,
            exportDB: settingsComposable.exportDB,
            importFileInput: settingsComposable.importFileInput,
            isImporting: settingsComposable.isImporting,
            triggerImportFile: settingsComposable.triggerImportFile,
            handleImportFile: settingsComposable.handleImportFile,
            categories: settingsComposable.categories,
            categoriesLoading: settingsComposable.categoriesLoading,
            catLoadList: settingsComposable.catLoadList,
            catCreate: settingsComposable.catCreate,
            catEditingId: settingsComposable.catEditingId,
            catStartEdit: settingsComposable.catStartEdit,
            catCancelEdit: settingsComposable.catCancelEdit,
            catSaveEdit: settingsComposable.catSaveEdit,
            catDelete: settingsComposable.catDelete,
            catForm: settingsComposable.catForm,
            catEditMode: settingsComposable.catEditMode,
            closeSettings: settingsComposable.closeSettings,
            
            // User Preferences
            autoLoadMore: settingsComposable.autoLoadMore,
            quickAddDefaultType: settingsComposable.quickAddDefaultType,
            setQuickAddDefault: (type) => { settingsComposable.quickAddDefaultType.value = type; }, // v0.9.0
            newNoteDefaultType: settingsComposable.newNoteDefaultType,
            setNewNoteDefault: (type) => { settingsComposable.newNoteDefaultType.value = type; },
            imageSaveMode: settingsComposable.imageSaveMode,
            cardOpenMode: settingsComposable.cardOpenMode,
            colorTheme: settingsComposable.colorTheme,
            availableThemes: settingsComposable.availableThemes,
            
            // Orphan Image Cleanup (v0.8)
            orphanImages: settingsComposable.orphanImages,
            orphanImagesLoading: settingsComposable.orphanImagesLoading,
            orphanTotalSize: settingsComposable.orphanTotalSize,
            orphanDeleting: settingsComposable.orphanDeleting,
            loadOrphanImages: settingsComposable.loadOrphanImages,
            deleteOrphanImages: settingsComposable.deleteOrphanImages,
            deleteAllOrphanImages: settingsComposable.deleteAllOrphanImages,
            
            // Original Images Cleanup (v0.8.9)
            originalImagesStats: settingsComposable.originalImagesStats,
            originalImagesLoading: settingsComposable.originalImagesLoading,
            originalImagesDeleting: settingsComposable.originalImagesDeleting,
            loadOriginalImagesStats: settingsComposable.loadOriginalImagesStats,
            deleteAllOriginals: settingsComposable.deleteAllOriginals,
            handleDeleteAllOriginals: settingsComposable.handleDeleteAllOriginals,
            
            // Broken Images Fix (v0.8.9)
            brokenImagesStats: settingsComposable.brokenImagesStats,
            brokenImagesLoading: settingsComposable.brokenImagesLoading,
            brokenImagesFixing: settingsComposable.brokenImagesFixing,
            loadBrokenImages: settingsComposable.loadBrokenImages,
            handleFixBrokenImages: settingsComposable.handleFixBrokenImages,

            // Database VACUUM (v0.8.9)
            vacuumLoading: settingsComposable.vacuumLoading,
            vacuumResult: settingsComposable.vacuumResult,
            vacuumDatabase: settingsComposable.vacuumDatabase,
            clearingHistory: settingsComposable.clearingHistory,
            clearHistory: settingsComposable.clearHistory,
            
            // WAL Checkpoint (v1.2)
            walCheckpointing: settingsComposable.walCheckpointing,
            walCheckpointResult: settingsComposable.walCheckpointResult,
            walCheckpoint: settingsComposable.walCheckpoint,
            
            // Startup Preference (v1.1)
            startupAutoOpen: settingsComposable.startupAutoOpen,
            toggleAutoOpenBrowser: settingsComposable.toggleAutoOpenBrowser,

            // i18n (v0.8.8)
            t: i18nComposable.t,
            currentLocale: i18nComposable.currentLocale,
            availableLocales: i18nComposable.availableLocales,
            setLocale: i18nComposable.setLocale,
            getLocaleName: i18nComposable.getLocaleName,
            langDropdownOpen,
            mobileSidebarOpen,

            // Legacy compatibility (for template)
            openPromptWindow: () => editorComposable.openEditor(null, 'prompt'),
            extractFirstImage: (content) => {
                if (!content) return null;
                const match = content.match(/!\[.*?\]\((.*?)\)/);
                return match ? match[1] : null;
            },
            
            // Utility functions for callbacks
            refreshNotes
        };
    }
});

app.directive('click-outside', {
    mounted(el, binding) {
        el.clickOutsideEvent = function(event) {
            if (!(el === event.target || el.contains(event.target))) {
                binding.value(event);
            }
        };
        // Delay binding to avoid catching the triggering click
        setTimeout(() => {
            document.body.addEventListener('click', el.clickOutsideEvent);
        }, 0);
    },
    unmounted(el) {
        document.body.removeEventListener('click', el.clickOutsideEvent);
    },
});

app.mount('#app');

console.log('[Local Insight] App mounted with ES Modules architecture');
