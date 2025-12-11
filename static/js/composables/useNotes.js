/**
 * useNotes Composable
 * 筆記列表、搜尋、過濾、分頁、批量操作
 * v0.8.9: 使用 inject 取得 i18n
 */

import { api } from '../api.js';
import { debounce, extractFirstImage, getThumbUrl } from '../utils.js';
import { injectT } from './useI18n.js';

export function useNotes() {
    const { ref, computed, watch } = Vue;
    const t = injectT();  // v0.8.9: 自動注入翻譯函數

    // State
    const notes = ref([]);
    const notesLoading = ref(false);
    const loadingMore = ref(false);  // 專用於無限滾動的 loading 狀態
    const notesError = ref(null);
    
    // Pagination
    const currentPage = ref(1);
    const totalNotes = ref(0);
    const totalPages = ref(1);
    const hasMore = computed(() => currentPage.value < totalPages.value);
    
    // Filters - types 現在由外部 categories 提供，這裡保留預設值
    const defaultTypes = ['all', '提示詞', '筆記', '教學', '資料', '靈感'];
    const types = ref(defaultTypes);
    const selectedType = ref('all');
    const selectedTags = ref([]);
    const tagFilterMode = ref('AND'); // 'AND' | 'OR'
    const searchKeyword = ref('');
    const debouncedSearchKeyword = ref('');
    
    // View
    const viewMode = ref('grid'); // 'grid' | 'list'
    
    // Selection Mode
    const isSelectionMode = ref(false);
    const selectedNoteIds = ref([]);
    
    // Batch Dropdowns
    const batch_typeDropdown = ref(false);
    const batch_tagsDropdown = ref(false);

    // Debounced Search Handler
    let searchTimeout = null;
    const handleSearchInput = () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            debouncedSearchKeyword.value = searchKeyword.value;
        }, 300);
    };

    // Fetch Notes from API
    const fetchNotes = async (page = 1, append = false) => {
        console.log('[useNotes] fetchNotes called, page:', page, 'append:', append);
        
        // 使用不同的 loading 狀態以避免 UI 閃爍
        if (append) {
            loadingMore.value = true;
        } else {
            notesLoading.value = true;
        }
        notesError.value = null;

        try {
            const params = {
                page: page,
                per_page: 20
            };

            // Add filters
            if (debouncedSearchKeyword.value) {
                params.q = debouncedSearchKeyword.value;
            }
            if (selectedType.value && selectedType.value !== 'all') {
                params.type = selectedType.value;
            }
            if (selectedTags.value.length > 0) {
                params.tags = selectedTags.value.join(',');
                params.tag_mode = tagFilterMode.value; // 'AND' or 'OR'
            }

            console.log('[useNotes] Fetching with params:', params);
            const result = await api.getNotes(params);
            console.log('[useNotes] API response:', result);

            if (result.status === 'success') {
                const newNotes = result.data.map(note => ({
                    ...note,
                    tags: note.tags || [],
                    urls: note.urls || []
                }));

                if (append) {
                    // 直接 push 而不是重新創建陣列，避免觸發完整重渲染
                    notes.value.push(...newNotes);
                } else {
                    notes.value = newNotes;
                }
                console.log('[useNotes] Notes updated, count:', notes.value.length);

                currentPage.value = result.pagination.page;
                totalNotes.value = result.pagination.total;
                totalPages.value = result.pagination.total_pages;
            }
        } catch (error) {
            console.error('[useNotes] Fetch notes error:', error);
            notesError.value = t('messages.networkError', '無法載入筆記');
        } finally {
            notesLoading.value = false;
            loadingMore.value = false;
        }
    };

    // Load More Notes (Pagination)
    const loadMoreNotes = () => {
        if (hasMore.value && !notesLoading.value && !loadingMore.value) {
            fetchNotes(currentPage.value + 1, true);
        }
    };

    // Computed: filteredNotes (直接回傳 notes，因過濾由後端處理)
    const filteredNotes = computed(() => notes.value);

    // Selection Mode
    const toggleSelectionMode = () => {
        isSelectionMode.value = !isSelectionMode.value;
        selectedNoteIds.value = [];
    };

    const toggleNoteSelection = (id) => {
        if (!isSelectionMode.value) return;
        const index = selectedNoteIds.value.indexOf(id);
        if (index === -1) {
            selectedNoteIds.value.push(id);
        } else {
            selectedNoteIds.value.splice(index, 1);
        }
    };

    const selectAllNotes = () => {
        selectedNoteIds.value = filteredNotes.value.map(n => n.id);
    };

    // Batch Operations
    const batch_changeType = async (newType) => {
        if (selectedNoteIds.value.length === 0) return;
        
        try {
            await api.batchUpdateType(selectedNoteIds.value, newType);
            await fetchNotes(1, false);
            selectedNoteIds.value = [];
            batch_typeDropdown.value = false;
            alert(t('messages.batchTypeChangeSuccess', `已將 ${selectedNoteIds.value.length} 則筆記分類變更為「${newType}」`).replace('{count}', selectedNoteIds.value.length).replace('{type}', newType));
        } catch (error) {
            console.error('Batch update type error:', error);
            alert(t('messages.batchTypeChangeFailed'));
        }
    };

    const batch_addTag = async (tagName) => {
        if (selectedNoteIds.value.length === 0) return;
        
        try {
            await api.batchUpdateTags(selectedNoteIds.value, [tagName], 'append');
            await fetchNotes(1, false);
            batch_tagsDropdown.value = false;
            alert(t('messages.batchTagAddSuccess', `已為 ${selectedNoteIds.value.length} 則筆記新增標籤「#${tagName}」`).replace('{count}', selectedNoteIds.value.length).replace('{tag}', tagName));
        } catch (error) {
            console.error('Batch add tag error:', error);
            alert(t('messages.batchTagAddFailed'));
        }
    };

    const deleteSelectedNotes = async () => {
        if (selectedNoteIds.value.length === 0) return;

        if (!confirm(t('messages.confirmBatchDelete', `確定要刪除選中的 ${selectedNoteIds.value.length} 則筆記嗎？此動作無法復原。`).replace('{count}', selectedNoteIds.value.length))) {
            return;
        }

        try {
            await api.batchDeleteNotes(selectedNoteIds.value);
            await fetchNotes(1, false);
            selectedNoteIds.value = [];
            isSelectionMode.value = false;
            alert(t('messages.deleteSuccess'));
        } catch (error) {
            console.error('Batch delete error:', error);
            alert(t('messages.partialDeleteFailed'));
        }
    };

    const exportSelectedNotes = async () => {
        if (selectedNoteIds.value.length === 0) return;

        try {
            await api.exportBatch(selectedNoteIds.value);
            alert(t('messages.exportSuccess', `成功匯出 ${selectedNoteIds.value.length} 則筆記`).replace('{count}', selectedNoteIds.value.length));
        } catch (error) {
            console.error('Export error:', error);
            alert(t('messages.exportFailed', '匯出失敗'));
        }
    };

    // Image Helpers
    const getNoteCover = (note) => {
        if (note.cover_image) {
            return note.cover_image;
        }
        return extractFirstImage(note.content);
    };

    const getNoteThumbnail = (note) => {
        const originalUrl = getNoteCover(note);
        return getThumbUrl(originalUrl);
    };

    // Quick Actions
    const quickCopy = async (note) => {
        try {
            await navigator.clipboard.writeText(note.content);
            console.log(`[Copy] "${note.title}" 已複製到剪貼簿`);
        } catch (error) {
            console.error('Copy failed:', error);
            alert(t('messages.copyFailed'));
        }
    };

    const runPrompt = (note) => {
        const encodedPrompt = encodeURIComponent(note.content);
        const chatGptUrl = `https://chat.openai.com/?q=${encodedPrompt}`;
        window.open(chatGptUrl, '_blank');
    };

    // Toggle Pin/Unpin Note
    const togglePinNote = async (note) => {
        try {
            const response = await fetch(`/api/notes/${note.id}/pin`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})  // 必須發送空 JSON 物件
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                // 更新本地狀態
                note.is_pinned = result.data.is_pinned;
                
                // 重新排序：釘選的筆記在前
                notes.value = [...notes.value].sort((a, b) => {
                    if (a.is_pinned && !b.is_pinned) return -1;
                    if (!a.is_pinned && b.is_pinned) return 1;
                    return 0;
                });
                
                console.log(`[Pin] Note ${note.id} is now ${result.data.is_pinned ? 'pinned' : 'unpinned'}`);
            } else {
                alert(t('messages.operationFailed') + ': ' + result.message);
            }
        } catch (error) {
            console.error('Toggle pin error:', error);
            alert(t('messages.operationFailed'));
        }
    };

    // 同步 categories 到 types
    const syncTypesFromCategories = (categories) => {
        if (categories && categories.length > 0) {
            types.value = ['all', ...categories.map(c => c.name)];
        } else {
            types.value = defaultTypes;
        }
    };

    // ===================================================================
    // Drag & Drop Reordering (v0.9.0)
    // ===================================================================
    
    const isDragging = ref(false);
    const draggedNoteIndex = ref(null);
    const sortMode = ref('updated');  // 'updated' | 'custom' | 'created'
    
    const startDrag = (index, event) => {
        if (isSelectionMode.value) return; // 選擇模式下禁用拖放
        
        isDragging.value = true;
        draggedNoteIndex.value = index;
        
        // 設置拖曳數據
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', index.toString());
        }
    };
    
    const onDragOver = (index, event) => {
        event.preventDefault();
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'move';
        }
    };
    
    const onDrop = async (targetIndex, event) => {
        event.preventDefault();
        
        if (draggedNoteIndex.value === null || draggedNoteIndex.value === targetIndex) {
            isDragging.value = false;
            draggedNoteIndex.value = null;
            return;
        }
        
        const sourceIndex = draggedNoteIndex.value;
        
        // 前端立即更新位置 (樂觀更新)
        const [draggedNote] = notes.value.splice(sourceIndex, 1);
        notes.value.splice(targetIndex, 0, draggedNote);
        
        isDragging.value = false;
        draggedNoteIndex.value = null;
        
        // 切換到自訂排序模式
        sortMode.value = 'custom';
        
        // 呼叫 API 持久化排序
        try {
            const noteIds = notes.value.map(n => n.id);
            await api.reorderNotes(noteIds);
            console.log('[Reorder] Notes reordered successfully');
        } catch (error) {
            console.error('[Reorder] Failed to save order:', error);
            // 發生錯誤時重新載入
            await fetchNotes(1, false);
        }
    };
    
    const endDrag = () => {
        isDragging.value = false;
        draggedNoteIndex.value = null;
    };
    
    // 切換排序模式
    const toggleSortMode = async (mode) => {
        if (sortMode.value === mode) return;
        
        sortMode.value = mode;
        
        // 重新載入筆記以套用新排序
        const params = {
            page: 1,
            per_page: 20,
            sort: mode
        };
        
        if (debouncedSearchKeyword.value) {
            params.q = debouncedSearchKeyword.value;
        }
        if (selectedType.value && selectedType.value !== 'all') {
            params.type = selectedType.value;
        }
        if (selectedTags.value.length > 0) {
            params.tags = selectedTags.value.join(',');
            params.tag_mode = tagFilterMode.value;
        }
        
        notesLoading.value = true;
        try {
            const result = await api.getNotes(params);
            if (result.status === 'success') {
                notes.value = result.data.map(note => ({
                    ...note,
                    tags: note.tags || [],
                    urls: note.urls || []
                }));
                currentPage.value = result.pagination.page;
                totalNotes.value = result.pagination.total;
                totalPages.value = result.pagination.total_pages;
            }
        } catch (error) {
            console.error('[Sort] Failed to change sort mode:', error);
        } finally {
            notesLoading.value = false;
        }
    };

    return {
        // State
        notes,
        notesLoading,
        loadingMore,
        notesError,
        
        // Filters
        types,
        selectedType,
        selectedTags,
        tagFilterMode,
        searchKeyword,
        debouncedSearchKeyword,
        handleSearchInput,
        
        // Pagination
        currentPage,
        totalNotes,
        totalPages,
        hasMore,
        loadMoreNotes,
        
        // Computed
        filteredNotes,
        
        // Actions
        fetchNotes,
        
        // View
        viewMode,
        
        // Selection
        isSelectionMode,
        selectedNoteIds,
        toggleSelectionMode,
        toggleNoteSelection,
        selectAllNotes,
        
        // Batch
        batch_typeDropdown,
        batch_tagsDropdown,
        batch_changeType,
        batch_addTag,
        deleteSelectedNotes,
        exportSelectedNotes,
        
        // Helpers
        getNoteCover,
        getNoteThumbnail,
        quickCopy,
        runPrompt,
        togglePinNote,
        syncTypesFromCategories,
        
        // Drag & Drop (v0.9.0)
        isDragging,
        draggedNoteIndex,
        sortMode,
        startDrag,
        onDragOver,
        onDrop,
        endDrag,
        toggleSortMode
    };
}
