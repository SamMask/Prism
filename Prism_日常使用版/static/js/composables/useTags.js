/**
 * useTags Composable
 * 標籤列表、重命名、合併、刪除
 * v0.8.9: 使用 inject 取得 i18n
 */

import { api } from '../api.js';
import { injectT } from './useI18n.js';

export function useTags() {
    const { ref } = Vue;
    const t = injectT();  // v0.8.9: 自動注入翻譯函數

    // State
    const tags = ref([]);
    const tagsLoading = ref(false);
    const tagsError = ref(null);

    // Context Menu State
    const tagContextMenu = ref({
        visible: false,
        x: 0,
        y: 0,
        tag: null
    });

    // Rename Modal State
    const tagRenameModal = ref({
        visible: false,
        newName: '',
        loading: false
    });

    // Merge Modal State
    const tagMergeModal = ref({
        visible: false,
        targetId: null,
        loading: false
    });

    // Fetch Tags
    const fetchTags = async () => {
        tagsLoading.value = true;
        tagsError.value = null;

        try {
            const result = await api.getTags();
            if (result.status === 'success') {
                tags.value = result.data || [];
            }
        } catch (error) {
            console.error('Fetch tags error:', error);
            tagsError.value = t('messages.networkError', '無法載入標籤');
        } finally {
            tagsLoading.value = false;
        }
    };

    // Open Context Menu
    const openTagContextMenu = (event, tag) => {
        tagContextMenu.value = {
            visible: true,
            x: event.clientX,
            y: event.clientY,
            tag: tag
        };
        
        // Close on click outside
        const closeMenu = () => {
            tagContextMenu.value.visible = false;
            document.removeEventListener('click', closeMenu);
        };
        setTimeout(() => document.addEventListener('click', closeMenu), 0);
    };

    // Close All Modals
    const closeTagModals = () => {
        tagContextMenu.value.visible = false;
        tagRenameModal.value = { visible: false, newName: '', loading: false };
        tagMergeModal.value = { visible: false, targetId: null, loading: false };
    };

    // Open Rename Modal
    const openTagRenameModal = () => {
        tagRenameModal.value = {
            visible: true,
            newName: tagContextMenu.value.tag?.name || '',
            loading: false
        };
        tagContextMenu.value.visible = false;
    };

    // Confirm Rename
    const confirmRenameTag = async (onSuccess) => {
        const tag = tagContextMenu.value.tag;
        const newName = tagRenameModal.value.newName.trim();
        
        if (!tag || !newName) return;
        if (newName === tag.name) {
            closeTagModals();
            return;
        }

        const noteCount = tag.count || 0;
        const confirmed = confirm(
            `將標籤「#${tag.name}」重新命名為「#${newName}」\n\n` +
            `⚠️ 這將影響 ${noteCount} 則筆記的標籤顯示。\n\n` +
            `確定要更新嗎？`
        );
        if (!confirmed) return;

        tagRenameModal.value.loading = true;
        try {
            const result = await api.renameTag(tag.id, newName);
            if (result.status === 'success') {
                await fetchTags();
                closeTagModals();
                if (onSuccess) onSuccess();
            }
        } catch (error) {
            console.error('Rename tag error:', error);
            alert(error.message || t('messages.renameFailed'));
        } finally {
            tagRenameModal.value.loading = false;
        }
    };

    // Delete Tag
    const deleteTag = async (onSuccess) => {
        const tag = tagContextMenu.value.tag;
        if (!tag) return;

        const noteCount = tag.count || 0;
        const confirmed = confirm(
            `確定要刪除標籤「#${tag.name}」嗎？\n\n` +
            `⚠️ 這將從 ${noteCount} 則筆記中移除此標籤。\n` +
            `此動作無法復原！`
        );
        if (!confirmed) {
            tagContextMenu.value.visible = false;
            return;
        }

        try {
            const result = await api.deleteTag(tag.id);
            if (result.status === 'success') {
                await fetchTags();
                closeTagModals();
                if (onSuccess) onSuccess();
            }
        } catch (error) {
            console.error('Delete tag error:', error);
            alert(error.message || t('messages.deleteFailed'));
        }
    };

    // Open Merge Modal
    const openTagMergeModal = () => {
        tagMergeModal.value = {
            visible: true,
            targetId: null,
            loading: false
        };
        tagContextMenu.value.visible = false;
    };

    // Confirm Merge
    const confirmMergeTag = async (onSuccess) => {
        console.log('[useTags] confirmMergeTag called');
        
        const sourceTag = tagContextMenu.value.tag;
        const targetId = tagMergeModal.value.targetId;
        
        if (!sourceTag || !targetId) {
            console.log('[useTags] Missing sourceTag or targetId, returning early');
            return;
        }

        const targetTag = tags.value.find(t => t.id === targetId);
        const targetName = targetTag?.name || '目標標籤';

        // 直接執行合併，不再彈出 confirm() 對話框
        // (因為已經有自訂 Modal 作為確認介面)
        tagMergeModal.value.loading = true;
        console.log('[useTags] Calling API mergeTags:', sourceTag.id, '->', targetId);
        
        try {
            const result = await api.mergeTags([sourceTag.id], targetId);
            console.log('[useTags] API result:', result);
            
            if (result.status === 'success') {
                console.log('[useTags] Merge successful, refreshing data...');
                await fetchTags();
                closeTagModals();
                if (onSuccess) {
                    console.log('[useTags] Calling onSuccess callback with targetId:', targetId);
                    // 傳遞 targetId 給回調，讓調用方可以選中新標籤
                    await onSuccess(targetId);
                }
                alert(t('messages.mergeSuccess').replace('{source}', sourceTag.name).replace('{target}', targetName));
            }
        } catch (error) {
            console.error('[useTags] Merge tag error:', error);
            alert(error.message || t('messages.mergeFailed'));
        } finally {
            tagMergeModal.value.loading = false;
        }
    };

    return {
        // State
        tags,
        tagsLoading,
        tagsError,
        
        // Context Menu
        tagContextMenu,
        openTagContextMenu,
        
        // Rename
        tagRenameModal,
        openTagRenameModal,
        confirmRenameTag,
        
        // Delete
        deleteTag,
        
        // Merge
        tagMergeModal,
        openTagMergeModal,
        confirmMergeTag,
        
        // Actions
        fetchTags,
        closeTagModals
    };
}
