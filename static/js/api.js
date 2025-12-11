/**
 * Local Insight API Service
 * 統一處理 Fetch 請求與錯誤
 */

const API_BASE = '/api';

class ApiService {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const defaultHeaders = {
            'Content-Type': 'application/json'
        };

        // 如果是 FormData，不要設置 Content-Type (瀏覽器會自動設置 multipart/form-data boundary)
        if (options.body instanceof FormData) {
            delete defaultHeaders['Content-Type'];
        }

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);
            
            // 處理非 200 回應
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP Error ${response.status}`);
            }

            // 處理 204 No Content (例如 DELETE 成功)
            if (response.status === 204) {
                return null;
            }

            const result = await response.json();
            
            if (result.status === 'error') {
                throw new Error(result.message);
            }

            return result;
        } catch (error) {
            console.error(`API Request Failed: ${endpoint}`, error);
            throw error;
        }
    }

    // Notes
    getNotes(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/notes?${queryString}`);
    }

    getNote(id) {
        return this.request(`/notes/${id}`);
    }

    createNote(data) {
        return this.request('/notes', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    updateNote(id, data) {
        return this.request(`/notes/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    deleteNote(id) {
        return this.request(`/notes/${id}`, {
            method: 'DELETE'
        });
    }

    duplicateNote(id) {
        return this.request(`/notes/${id}/duplicate`, {
            method: 'POST'
        });
    }

    // Batch Operations
    batchUpdateType(noteIds, type) {
        return this.request('/notes/batch/type', {
            method: 'POST',
            body: JSON.stringify({ note_ids: noteIds, type })
        });
    }

    batchUpdateTags(noteIds, tags, mode = 'append') {
        return this.request('/notes/batch/tags', {
            method: 'POST',
            body: JSON.stringify({ note_ids: noteIds, tags, mode })
        });
    }

    batchDeleteNotes(noteIds) {
        return this.request('/notes/batch/delete', {
            method: 'POST',
            body: JSON.stringify({ note_ids: noteIds })
        });
    }

    // Reorder Notes (v0.9.0 - Drag & Drop)
    reorderNotes(noteIds) {
        return this.request('/notes/reorder', {
            method: 'PUT',
            body: JSON.stringify({ note_ids: noteIds })
        });
    }

    // Note History
    getNoteHistory(noteId) {
        return this.request(`/notes/${noteId}/history`);
    }

    restoreNoteVersion(noteId, historyId) {
        return this.request(`/notes/${noteId}/restore/${historyId}`, {
            method: 'POST',
            body: JSON.stringify({})  // 必須發送空 JSON 物件
        });
    }

    deleteNoteHistory(noteId) {
        return this.request(`/notes/${noteId}/history`, {
            method: 'DELETE'
        });
    }

    async exportBatch(noteIds) {
        const response = await fetch(`${API_BASE}/notes/export/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note_ids: noteIds })
        });
        
        if (!response.ok) {
            throw new Error('Export failed');
        }
        
        // 觸發下載
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'local_insight_export.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        return { status: 'success' };
    }

    // Tags
    getTags() {
        return this.request('/tags');
    }

    renameTag(id, name) {
        return this.request(`/tags/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ name })
        });
    }

    deleteTag(id) {
        return this.request(`/tags/${id}`, {
            method: 'DELETE'
        });
    }

    mergeTags(sourceTagIds, targetTagId) {
        return this.request('/tags/merge', {
            method: 'POST',
            body: JSON.stringify({ source_tag_ids: sourceTagIds, target_tag_id: targetTagId })
        });
    }

    // Categories
    getCategories() {
        return this.request('/categories');
    }

    createCategory(data) {
        return this.request('/categories', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    updateCategory(id, data) {
        return this.request(`/categories/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    deleteCategory(id, targetCategory = null) {
        const body = targetCategory ? { target_category: targetCategory } : {};
        return this.request(`/categories/${id}`, {
            method: 'DELETE',
            body: JSON.stringify(body)
        });
    }

    // Upload
    // options: { thumbnailOnly: boolean } (v0.8.9)
    uploadFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        // 僅縮圖模式 (v0.8.9)
        if (options.thumbnailOnly) {
            formData.append('thumbnail_only', 'true');
        }
        
        return this.request('/upload', {
            method: 'POST',
            body: formData
        });
    }

    // Delete image (original + thumbnail)
    deleteImage(url) {
        return this.request('/upload/delete', {
            method: 'POST',
            body: JSON.stringify({ url })
        });
    }

    // Cleanup (v0.8)
    getOrphanImages() {
        return this.request('/cleanup/orphan-images');
    }

    deleteOrphanImages(filenames) {
        return this.request('/cleanup/orphan-images', {
            method: 'DELETE',
            body: JSON.stringify({ filenames })
        });
    }

    // Original Images Cleanup (v0.8.9)
    getOriginalImages() {
        return this.request('/cleanup/originals');
    }

    deleteAllOriginals() {
        return this.request('/cleanup/originals', {
            method: 'DELETE'
        });
    }

    // Broken Image Paths (v0.8.9)
    getBrokenImages() {
        return this.request('/cleanup/broken-images');
    }

    fixBrokenImages() {
        return this.request('/cleanup/broken-images', {
            method: 'POST'
        });
    }

    // Export (Redirects)
    getExportJsonUrl() {
        return `${API_BASE}/export/json`;
    }

    getExportDbUrl() {
        return `${API_BASE}/export/db`;
    }
}

export const api = new ApiService();

