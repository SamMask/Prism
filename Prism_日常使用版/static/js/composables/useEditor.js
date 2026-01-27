/**
 * useEditor Composable
 * 編輯器 Modal、儲存、刪除、歷史紀錄、相關圖片管理
 * v0.8.9: 使用 inject 取得 i18n
 */

import { api } from '../api.js';
import { validateImageFile } from '../utils.js';
import { injectT } from './useI18n.js';

export function useEditor(getQuickAddDefaultType, getNewNoteDefaultType, getImageSaveMode, getCardOpenMode) {
    const { ref, computed } = Vue;
    const t = injectT();  // v0.8.9: 自動注入翻譯函數
    
    // v1.1.1: 確保 getCardOpenMode 有預設值
    if (typeof getCardOpenMode !== 'function') {
        getCardOpenMode = () => 'reading';  // 預設閱讀模式
    }
    
    // v0.9.0: 兼容舊調用 (如果不傳 getNewNoteDefaultType，參數會位移)
    // 實際上 app.js 會更新，但以防萬一
    if (typeof getNewNoteDefaultType !== 'function' && typeof getImageSaveMode === 'undefined') {
        // 舊簽名: (getQuickAddDefaultType, getImageSaveMode)
        getImageSaveMode = getNewNoteDefaultType;
        getNewNoteDefaultType = () => '筆記'; 
    }
    // Modal State
    const isEditing = ref(false);
    const isPromptMode = ref(false);
    const activeTab = ref('basic'); // 'basic' | 'content' | 'images' | 'history'
    const isContentPreview = ref(false);
    const isReadingMode = ref(false);  // v1.1: 純文字閱讀模式
    const isDeletingImage = ref(false);
    const isQuickAddOpen = ref(false); // v0.9.0 Quick Add Modal

    // Editor Loading States
    const isSaving = ref(false);
    const isDeleting = ref(false);
    const isDuplicating = ref(false);
    const isUploading = ref(false);
    const isRestoring = ref(false);
    
    // 追蹤此次編輯過程中上傳的圖片 (v0.8.7)
    // 用於取消時清理未保存的孤兒圖片
    const sessionUploadedImages = ref([]);

    // Current Note
    const currentNote = ref({
        id: null,
        title: '',
        content: '',
        type: '筆記',
        remarks: '',
        cover_image: null,
        cover_position: 'top',
        editor_layout: 'single',
        tags: [],
        urls: []
    });
    
    // 追蹤原始筆記狀態（用於檢測未保存變更）
    const originalNote = ref(null);
    
    // 檢測是否有未保存的變更
    const hasUnsavedChanges = computed(() => {
        if (!originalNote.value) return false;
        
        const curr = currentNote.value;
        const orig = originalNote.value;
        
        // 輔助函數：正規化值（處理 null/undefined/'' 差異）
        const normalize = (val) => val == null ? '' : String(val);
        
        // 比較基本欄位
        if (normalize(curr.title) !== normalize(orig.title)) return true;
        if (normalize(curr.content) !== normalize(orig.content)) return true;
        if (normalize(curr.type) !== normalize(orig.type)) return true;
        if (normalize(curr.remarks) !== normalize(orig.remarks)) return true;
        if (normalize(curr.cover_image) !== normalize(orig.cover_image)) return true;
        if (normalize(curr.cover_position) !== normalize(orig.cover_position)) return true;
        if (normalize(curr.editor_layout) !== normalize(orig.editor_layout)) return true;
        
        // 比較 tags
        const currTags = JSON.stringify(curr.tags || []);
        const origTags = JSON.stringify(orig.tags || []);
        if (currTags !== origTags) return true;
        
        // 比較 urls
        const currUrls = JSON.stringify(curr.urls || []);
        const origUrls = JSON.stringify(orig.urls || []);
        if (currUrls !== origUrls) return true;
        
        return false;
    });
    
    // 從內容中提取所有圖片 URL
    const contentImages = computed(() => {
        const content = currentNote.value.content || '';
        const images = [];
        
        // 匹配 Markdown 圖片語法 ![alt](/static/uploads/xxx.jpg)
        const mdPattern = /!\[([^\]]*)\]\(([^)]+)\)/g;
        let match;
        while ((match = mdPattern.exec(content)) !== null) {
            const url = match[2];
            if (url.includes('/static/uploads/')) {
                images.push({
                    url: url,
                    alt: match[1] || '',
                    syntax: match[0]
                });
            }
        }
        
        // 匹配 HTML img 標籤 <img src="/static/uploads/xxx.jpg">
        const htmlPattern = /<img[^>]+src=["']([^"']+)["'][^>]*>/g;
        while ((match = htmlPattern.exec(content)) !== null) {
            const url = match[1];
            if (url.includes('/static/uploads/') && !images.find(img => img.url === url)) {
                images.push({
                    url: url,
                    alt: '',
                    syntax: `![](${url})`
                });
            }
        }
        
        return images;
    });
    
    // 刪除圖片（從內容中移除 + 刪除實體檔案）
    const deleteImageFromContent = async (imageUrl, deleteFile = false) => {
        // 從內容中移除圖片
        let content = currentNote.value.content || '';
        
        // 移除 Markdown 語法
        const escapedUrl = imageUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const mdPattern = new RegExp(`!\\[[^\\]]*\\]\\(${escapedUrl}\\)\\n?`, 'g');
        content = content.replace(mdPattern, '');
        
        // 移除 HTML img 標籤
        const htmlPattern = new RegExp(`<img[^>]+src=["']${escapedUrl}["'][^>]*>\\n?`, 'g');
        content = content.replace(htmlPattern, '');
        
        currentNote.value.content = content;
        
        // 如果需要刪除實體檔案
        if (deleteFile) {
            isDeletingImage.value = true;
            try {
                await api.deleteImage(imageUrl);
            } catch (error) {
                console.error('Delete image file error:', error);
            } finally {
                isDeletingImage.value = false;
            }
        }
    };
    
    // 複製圖片語法到剪貼簿
    const copyImageSyntax = async (syntax) => {
        try {
            await navigator.clipboard.writeText(syntax);
            return true;
        } catch (error) {
            console.error('Copy failed:', error);
            return false;
        }
    };
    
    // 匯出所有圖片（逐一下載原圖）
    const exportImages = async () => {
        if (contentImages.value.length === 0) {
            alert(t('messages.noImagesToExport'));
            return;
        }
        
        // 下載每張圖片（瀏覽器可能會詢問是否允許多個下載）
        for (const img of contentImages.value) {
            try {
                const a = document.createElement('a');
                a.href = img.url;
                a.download = img.url.split('/').pop();
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } catch (error) {
                console.error('Download image error:', error);
            }
        }
    };

    // Tag Input
    const newTagInput = ref('');

    // History
    const noteHistory = ref([]);
    const historyLoading = ref(false);

    // Create empty note template
    const getEmptyNote = (type = '筆記') => ({
        id: null,
        title: '',
        content: '',
        type: type,
        remarks: '',
        cover_image: null,
        cover_position: 'top',
        editor_layout: 'single',
        tags: [],
        urls: []
    });

    // Open Quick Add Modal (v0.9.0)
    const openQuickAdd = () => {
        isQuickAddOpen.value = true;
        activeTab.value = 'content'; // 雖然 Quick Add 沒有 tab，但這有助於後續處理
        isContentPreview.value = false;
        
        // 預設空的筆記，類型為使用者的快速新增預設類型，或是純文字
        const defaultType = getQuickAddDefaultType() || '筆記';
        currentNote.value = getEmptyNote(defaultType);
        currentNote.value.urls = ['']; // 預先準備一個空位供輸入，方便 v-model 綁定
        
        // 保存原始狀態
        originalNote.value = JSON.parse(JSON.stringify(currentNote.value));
        sessionUploadedImages.value = [];
    };

    // Open Editor
    const openEditor = (note = null, mode = 'normal') => {
        isQuickAddOpen.value = false; // 確保 Quick Add 關閉
        isPromptMode.value = mode === 'prompt';
        noteHistory.value = [];
        sessionUploadedImages.value = []; // 重置追蹤列表 (v0.8.7)

        if (note) {
            // Edit mode - 根據用戶設定決定開啟模式 (v1.1.1)
            activeTab.value = 'content';
            
            // 獲取用戶預設的卡片開啟模式
            const defaultOpenMode = getCardOpenMode();
            
            if (defaultOpenMode === 'reading') {
                isContentPreview.value = false;
                isReadingMode.value = true;
            } else if (defaultOpenMode === 'edit') {
                isContentPreview.value = false;
                isReadingMode.value = false;
            } else {
                // 'preview' 模式 (Markdown 預覽)
                isContentPreview.value = true;
                isReadingMode.value = false;
            }
            
            // 智能預設佈局 (v0.8.6)
            // 如果有保存的設定就使用，否則根據是否有圖片決定
            let smartLayout = note.editor_layout;
            if (!smartLayout) {
                // 檢查內容中是否有圖片
                const hasImages = /!\[[^\]]*\]\([^)]+\)|<img[^>]+src=/i.test(note.content || '');
                smartLayout = hasImages ? 'dual' : 'single';
            }
            
            currentNote.value = {
                id: note.id,
                title: note.title,
                content: note.content,
                type: note.type || '筆記',
                remarks: note.remarks || '',
                cover_image: note.cover_image,
                cover_position: note.cover_position || 'top',
                editor_layout: smartLayout,
                tags: note.tags ? [...note.tags] : [],
                urls: note.urls ? [...note.urls] : []
            };
        } else {
            // New Note
            activeTab.value = mode === 'prompt' ? 'basic' : 'content';
            isContentPreview.value = false;
            
            // Default type (v0.9.0: Respect user default setting)
            let type = getNewNoteDefaultType ? (getNewNoteDefaultType() || '筆記') : '筆記';
            if (mode === 'prompt') type = '提示詞';
            
            currentNote.value = getEmptyNote(type);
            
            // Initialize arrays for safety
            if (!currentNote.value.urls) currentNote.value.urls = [];
            if (!currentNote.value.tags) currentNote.value.tags = [];
        }
        
        // 保存原始狀態 (深拷貝)
        originalNote.value = JSON.parse(JSON.stringify(currentNote.value));

        isEditing.value = true;
    };

    // Close Editor (帶未保存提示)
    const closeEditor = (force = false) => {
        // 注意：當從模板 @click="closeEditor" 調用時，force 會是 PointerEvent
        // 所以需要明確檢查 force 是否為 true (布林值)
        const isForceClose = force === true;
        
        // 如果有未保存變更且不是強制關閉，詢問用戶
        if (!isForceClose && hasUnsavedChanges.value) {
            const shouldDiscard = confirm(t('editor.unsavedChanges'));
            if (!shouldDiscard) {
                return; // 用戶選擇繼續編輯
            }
        }
        
        // 清理未保存的圖片 (v0.8.7)
        // 只有在非強制關閉（即取消而非保存後）且有上傳過圖片時才清理
        // isForceClose = true 表示保存成功後關閉，不需要清理
        if (!isForceClose && sessionUploadedImages.value.length > 0) {
            console.log('[useEditor] Cleaning up unsaved images:', sessionUploadedImages.value);
            // 異步刪除，不阻塞關閉
            for (const imageUrl of sessionUploadedImages.value) {
                api.deleteImage(imageUrl).catch(err => {
                    console.warn('Failed to delete orphan image:', imageUrl, err);
                });
            }
        }
        
        isEditing.value = false;
        isQuickAddOpen.value = false; // 同時關閉 Quick Add
        setTimeout(() => {
            currentNote.value = getEmptyNote();
            originalNote.value = null;
            newTagInput.value = '';
            noteHistory.value = [];
            sessionUploadedImages.value = []; // 清空追蹤列表
        }, 300);
    };

    // Save Note
    const saveNote = async (onSuccess) => {
        // v1.3: 自動生成標題 - 使用內容第一行前50字元，或建立時間
        if (!currentNote.value.title.trim()) {
            const content = currentNote.value.content || '';
            // 取第一行
            let firstLine = content.split('\n')[0].trim();
            // 移除 Markdown 符號
            firstLine = firstLine.replace(/^[#>*\-\s]+/, '').trim();
            
            if (firstLine) {
                currentNote.value.title = firstLine.substring(0, 50) + (firstLine.length > 50 ? '...' : '');
            } else {
                // Fallback: 使用建立時間
                const date = new Date();
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                currentNote.value.title = `Note - ${year}/${month}/${day} ${hours}:${minutes}`;
            }
        }
        
        if (!currentNote.value.content.trim()) {
            alert(t('messages.enterContent'));
            return;
        }

        isSaving.value = true;

        try {
            const noteData = {
                title: currentNote.value.title.trim(),
                content: currentNote.value.content,
                type: currentNote.value.type,
                remarks: currentNote.value.remarks,
                cover_image: currentNote.value.cover_image,
                cover_position: currentNote.value.cover_position,
                editor_layout: currentNote.value.editor_layout,
                tags: currentNote.value.tags.map(t => t.name || t),
                urls: currentNote.value.urls.filter(u => u && u.trim())
            };

            let result;
            if (currentNote.value.id) {
                result = await api.updateNote(currentNote.value.id, noteData);
            } else {
                result = await api.createNote(noteData);
            }

            if (result.status === 'success') {
                // 保存成功，強制關閉（不檢查未保存變更）
                closeEditor(true);
                if (onSuccess) onSuccess();
            }
        } catch (error) {
            console.error('Save note error:', error);
            alert(t('messages.saveFailed') + ': ' + error.message);
        } finally {
            isSaving.value = false;
        }
    };

    // Delete Note
    const deleteNote = async (onSuccess) => {
        if (!currentNote.value.id) return;

        if (!confirm(t('messages.confirmDeleteNote', `確定要刪除「${currentNote.value.title}」嗎？此動作無法復原。`).replace('{title}', currentNote.value.title))) {
            return;
        }

        isDeleting.value = true;

        try {
            await api.deleteNote(currentNote.value.id);
            closeEditor();
            if (onSuccess) onSuccess();
        } catch (error) {
            console.error('Delete note error:', error);
            alert(t('messages.deleteFailed'));
        } finally {
            isDeleting.value = false;
        }
    };

    // Duplicate Note
    const duplicateNote = async (onSuccess) => {
        if (!currentNote.value.id) return;

        isDuplicating.value = true;

        try {
            const result = await api.duplicateNote(currentNote.value.id);

            if (result.status === 'success') {
                // Fetch the new note
                const newNoteResult = await api.getNote(result.data.note_id);
                
                if (newNoteResult.status === 'success') {
                    const noteData = newNoteResult.data;
                    currentNote.value = {
                        id: noteData.id,
                        title: noteData.title,
                        content: noteData.content,
                        type: noteData.type,
                        remarks: noteData.remarks || '',
                        cover_image: noteData.cover_image,
                        tags: noteData.tags || [],
                        urls: noteData.urls || []
                    };
                    alert(t('messages.duplicateCreated'));
                    if (onSuccess) onSuccess();
                }
            }
        } catch (error) {
            console.error('Duplicate note error:', error);
            alert(t('messages.duplicateFailed'));
        } finally {
            isDuplicating.value = false;
        }
    };

    // URL Management
    const addUrl = () => {
        currentNote.value.urls.push('');
    };

    const removeUrl = (index) => {
        currentNote.value.urls.splice(index, 1);
    };

    // Tag Management
    const addTag = () => {
        const tagName = newTagInput.value.trim();
        if (!tagName) return;

        const exists = currentNote.value.tags.some(t => {
            const existingName = (t.name || t).toLowerCase();
            return existingName === tagName.toLowerCase();
        });

        if (!exists) {
            currentNote.value.tags.push({ name: tagName });
            newTagInput.value = '';
        }
    };

    const removeTag = (index) => {
        currentNote.value.tags.splice(index, 1);
    };

    const toggleTag = (tag) => {
        const exists = currentNote.value.tags.some(t => {
            return t.id === tag.id || (t.name || t).toLowerCase() === tag.name.toLowerCase();
        });

        if (!exists) {
            currentNote.value.tags.push({ id: tag.id, name: tag.name });
        }
    };

    const isTagSelected = (tag) => {
        return currentNote.value.tags.some(t => {
            return t.id === tag.id || (t.name || t).toLowerCase() === tag.name.toLowerCase();
        });
    };

    // Image Upload
    const handleUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const validation = validateImageFile(file);
        if (!validation.valid) {
            alert(validation.message);
            event.target.value = '';
            return;
        }

        isUploading.value = true;

        try {
            // 根據設定決定是否僅保存縮圖 (v0.8.9)
            const thumbnailOnly = getImageSaveMode() === 'thumbnail_only';
            const result = await api.uploadFile(file, { thumbnailOnly });

            if (result.status === 'success') {
                const imageMarkdown = `\n![${file.name}](${result.data.url})\n`;
                currentNote.value.content += imageMarkdown;
                
                // 追蹤上傳的圖片 (v0.8.7): 取消時需要清理
                sessionUploadedImages.value.push(result.data.url);
                
                // 智能佈局切換 (v0.8.6): 只有新增筆記時，第一次插入圖片才自動切到雙欄
                if (!currentNote.value.id && currentNote.value.editor_layout === 'single') {
                    currentNote.value.editor_layout = 'dual';
                }
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert(t('messages.uploadFailed'));
        } finally {
            isUploading.value = false;
            event.target.value = '';
        }
    };

    // Clipboard Paste - Optimized: Text appears immediately, images download in background
    const handlePasteInEditor = async (event) => {
        const clipboardData = event.clipboardData;
        if (!clipboardData) return;
        
        const items = clipboardData.items;
        const htmlData = clipboardData.getData('text/html');
        const textData = clipboardData.getData('text/plain');

        // Priority 1: Handle direct image paste (screenshot, copied image file)
        let imageFile = null;
        for (let item of items) {
            if (item.type.startsWith('image/')) {
                imageFile = item.getAsFile();
                break;
            }
        }

        if (imageFile) {
            event.preventDefault();
            
            const validation = validateImageFile(imageFile);
            if (!validation.valid) {
                alert(validation.message);
                return;
            }

            const textarea = event.target;
            const cursorPosition = textarea.selectionStart;

            isUploading.value = true;

            try {
                // 根據設定決定是否僅保存縮圖 (v0.8.9)
                const thumbnailOnly = getImageSaveMode() === 'thumbnail_only';
                const result = await api.uploadFile(imageFile, { thumbnailOnly });

                if (result.status === 'success') {
                    const fileName = imageFile.name || 'image';
                    const imageMarkdown = `![${fileName}](${result.data.url})`;

                    const content = currentNote.value.content;
                    const before = content.substring(0, cursorPosition);
                    const after = content.substring(cursorPosition);

                    currentNote.value.content = before + imageMarkdown + after;

                    setTimeout(() => {
                        const newPosition = cursorPosition + imageMarkdown.length;
                        textarea.setSelectionRange(newPosition, newPosition);
                        textarea.focus();
                    }, 0);
                    
                    // 追蹤上傳的圖片 (v0.8.7): 取消時需要清理
                    sessionUploadedImages.value.push(result.data.url);
                    
                    // 智能佈局切換 (v0.8.6): 只有新增筆記時，第一次插入圖片才自動切到雙欄
                    if (!currentNote.value.id && currentNote.value.editor_layout === 'single') {
                        currentNote.value.editor_layout = 'dual';
                    }
                }
            } catch (error) {
                console.error('Paste upload error:', error);
                alert(t('messages.pasteFailed'));
            } finally {
                isUploading.value = false;
            }
            return;
        }
        
        // Priority 2: Handle HTML content with images (from web pages)
        // Optimized: Immediately insert text with images in original positions, then download in background
        if (htmlData && htmlData.includes('<img')) {
            event.preventDefault();
            
            const textarea = event.target;
            const cursorPosition = textarea.selectionStart;
            
            try {
                // Parse HTML to extract images and convert to structured content
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlData, 'text/html');
                
                // Walk through the DOM and build markdown with images in correct positions
                const processNode = (node) => {
                    if (node.nodeType === Node.TEXT_NODE) {
                        return node.textContent || '';
                    }
                    
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const tagName = node.tagName.toLowerCase();
                        
                        // Handle images - insert markdown syntax with original URL
                        if (tagName === 'img') {
                            const src = node.getAttribute('src');
                            if (src && (src.startsWith('http://') || src.startsWith('https://'))) {
                                return `\n![image](${src})\n`;
                            }
                            return '';
                        }
                        
                        // Handle block elements - add line breaks
                        const blockElements = ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'];
                        const isBlock = blockElements.includes(tagName);
                        
                        // Process children
                        let content = '';
                        for (const child of Array.from(node.childNodes)) {
                            content += processNode(child);
                        }
                        
                        // Add appropriate formatting
                        if (tagName === 'br') return '\n';
                        if (tagName === 'strong' || tagName === 'b') return `**${content}**`;
                        if (tagName === 'em' || tagName === 'i') return `*${content}*`;
                        if (tagName === 'a') {
                            const href = node.getAttribute('href');
                            if (href) return `[${content}](${href})`;
                            return content;
                        }
                        if (tagName.match(/^h[1-6]$/)) {
                            const level = parseInt(tagName[1]);
                            return '\n' + '#'.repeat(level) + ' ' + content + '\n';
                        }
                        if (tagName === 'li') return '\n- ' + content;
                        if (isBlock) return '\n' + content + '\n';
                        
                        return content;
                    }
                    
                    return '';
                };
                
                // Process the DOM to get markdown with images in correct positions
                let markdown = processNode(doc.body);
                
                // Clean up excessive newlines
                markdown = markdown.replace(/\n{3,}/g, '\n\n').trim();
                
                // Find all remote image URLs in the content
                const imageUrlPattern = /!\[image\]\((https?:\/\/[^)]+)\)/g;
                const remoteImages = [];
                let match;
                while ((match = imageUrlPattern.exec(markdown)) !== null) {
                    remoteImages.push({ match: match[0], url: match[1] });
                }
                
                // Immediately insert the content with original URLs
                const contentBefore = currentNote.value.content;
                const before = contentBefore.substring(0, cursorPosition);
                const after = contentBefore.substring(cursorPosition);
                
                if (before.trim() || after.trim()) {
                    currentNote.value.content = before + '\n\n' + markdown + after;
                } else {
                    currentNote.value.content = markdown;
                }
                
                // Auto switch to dual layout if images found
                if (remoteImages.length > 0 && !currentNote.value.id && currentNote.value.editor_layout === 'single') {
                    currentNote.value.editor_layout = 'dual';
                }
                
                // If there are remote images, download them in the background (non-blocking)
                if (remoteImages.length > 0) {
                    // Start background download immediately (no await, non-blocking)
                    (async () => {
                        let successCount = 0;
                        let failCount = 0;
                        const urlMapping = {};
                        
                        // Download all images in parallel for speed
                        const downloadPromises = remoteImages.map(async ({ url }) => {
                            try {
                                const thumbnailOnly = getImageSaveMode() === 'thumbnail_only';
                                const result = await api.downloadImageFromUrl(url, thumbnailOnly);
                                if (result.status === 'success' && result.data?.url) {
                                    urlMapping[url] = result.data.url;
                                    // Track uploaded images for cleanup on cancel
                                    sessionUploadedImages.value.push(result.data.url);
                                    successCount++;
                                }
                            } catch (error) {
                                console.error(`Background download failed: ${url}`, error);
                                failCount++;
                            }
                        });
                        
                        await Promise.all(downloadPromises);
                        
                        // Replace URLs in content with local URLs
                        if (successCount > 0) {
                            let updatedContent = currentNote.value.content;
                            for (const { url } of remoteImages) {
                                if (urlMapping[url]) {
                                    // Replace all occurrences of this URL
                                    updatedContent = updatedContent.split(url).join(urlMapping[url]);
                                }
                            }
                            currentNote.value.content = updatedContent;
                            
                            // Show subtle success notification
                            console.log(`[Paste] Downloaded ${successCount} images${failCount > 0 ? `, ${failCount} failed` : ''}`);
                        }
                    })();
                }
                
            } catch (error) {
                console.error('Failed to process HTML paste:', error);
                // Fallback: just paste the text
                const content = currentNote.value.content;
                const before = content.substring(0, cursorPosition);
                const after = content.substring(cursorPosition);
                currentNote.value.content = before + textData + after;
            }
            
            return;
        }
        
        // Priority 3: Let browser handle plain text paste normally
        // (No preventDefault, browser will handle it)
    };

    // History
    const loadNoteHistory = async () => {
        if (!currentNote.value.id) return;

        historyLoading.value = true;
        noteHistory.value = [];

        try {
            const result = await api.getNoteHistory(currentNote.value.id);
            if (result.status === 'success') {
                noteHistory.value = result.data.history || [];
            }
        } catch (error) {
            console.error('Load history error:', error);
        } finally {
            historyLoading.value = false;
        }
    };

    const restoreVersion = async (historyId) => {
        if (!currentNote.value.id || !historyId) return;

        if (!confirm(t('messages.confirmRestore', '確定要還原至此版本嗎？當前內容將會被保存為歷史版本。'))) {
            return;
        }

        isRestoring.value = true;

        try {
            const result = await api.restoreNoteVersion(currentNote.value.id, historyId);

            if (result.status === 'success') {
                const noteResult = await api.getNote(currentNote.value.id);
                if (noteResult.status === 'success') {
                    currentNote.value.content = noteResult.data.content;
                    alert(t('messages.restoreSuccess'));
                    await loadNoteHistory();
                }
            }
        } catch (error) {
            console.error('Restore error:', error);
            alert(t('messages.restoreFailed'));
        } finally {
            isRestoring.value = false;
        }
    };

    const clearNoteHistory = async () => {
        if (!currentNote.value.id) return;
        
        if (!confirm(t('messages.confirmClearHistory', '確定要清空此筆記的所有歷史版本嗎？此動作無法復原。'))) {
            return;
        }

        historyLoading.value = true;
        try {
            const result = await api.deleteNoteHistory(currentNote.value.id);
            if (result.status === 'success') {
                noteHistory.value = [];
                alert(t('messages.historyCleared', '歷史版本已清空'));
            }
        } catch (error) {
            console.error('Clear history error:', error);
            alert(t('messages.clearHistoryFailed', '清空歷史失敗') + ': ' + error.message);
        } finally {
            historyLoading.value = false;
        }
    };

    // Marked Content (Computed)
    const markedContent = computed(() => {
        if (!currentNote.value.content || currentNote.value.content.trim() === '') {
            return '';
        }
        try {
            const rawHtml = marked.parse(currentNote.value.content);
            return DOMPurify.sanitize(rawHtml, {
                ALLOWED_TAGS: [
                    'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre', 'a', 'img',
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
                    'blockquote', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
                ],
                ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class']
            });
        } catch (error) {
            console.error('Markdown parse error:', error);
            return DOMPurify.sanitize('<p class="text-red-400">Markdown 解析錯誤</p>');
        }
    });

    return {
        // Modal State
        isEditing,
        isQuickAddOpen, // v0.9.0
        isPromptMode,
        activeTab,
        isContentPreview,
        isReadingMode,  // v1.1
        
        // Loading States
        isSaving,
        isDeleting,
        isDuplicating,
        isUploading,
        isRestoring,
        
        // Note
        currentNote,
        newTagInput,
        
        // Actions
        openEditor,
        openQuickAdd, // v0.9.0
        closeEditor,
        saveNote,
        deleteNote,
        duplicateNote,
        
        // URL
        addUrl,
        removeUrl,
        
        // Tags
        addTag,
        removeTag,
        toggleTag,
        isTagSelected,
        
        // Upload
        handleUpload,
        handlePasteInEditor,
        
        // History
        noteHistory,
        historyLoading,
        loadNoteHistory,
        restoreVersion,
        clearNoteHistory,
        
        // Images (v0.8.2)
        contentImages,
        deleteImageFromContent,
        copyImageSyntax,
        exportImages,
        isDeletingImage,
        
        // Computed
        markedContent,
        hasUnsavedChanges
    };
}

