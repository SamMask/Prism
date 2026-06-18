import axios from "axios";
import { toast } from "../components/ui/Toast";
import { t } from "../i18n";

// Types matching backend schema
export interface Note {
  id: number;
  title: string;
  content: string;
  type: string;
  remarks?: string;
  cover_image?: string;
  cover_position?: "top" | "center" | "bottom";
  editor_layout?: "single" | "dual";
  is_pinned: boolean;
  is_archived: boolean;
  category_id?: number;
  category_name?: string;
  tags: Tag[];
  urls: string[];
  created_at: string;
  updated_at: string;
  // Phase 3.7: Card Lineage
  parent_id?: number;
  parent_title?: string;
  variants_count?: number;
}

export interface Category {
  id: number;
  name: string;
  icon?: string;
  sort_order: number;
  is_default: boolean;
  count?: number; // Number of notes in this category
}

export interface Tag {
  id: number;
  name: string;
  count?: number; // Number of notes with this tag
}

// Payload for creating/updating notes (tags as string array)
export interface NotePayload {
  title?: string;
  content?: string;
  category_id?: number;
  remarks?: string;
  tags?: string[];
  urls?: string[];
  is_pinned?: boolean;
  is_archived?: boolean;
  cover_image?: string;
  cover_position?: "top" | "center" | "bottom";
  editor_layout?: "single" | "dual";
  prompt_params?: Record<string, unknown>;
}

export interface NotesResponse {
  notes: Note[];
  total: number;
  page: number;
  per_page: number;
}

interface GetNotesParams {
  page?: number;
  per_page?: number;
  search?: string;
  type?: string;
  category_id?: number;
  parent_id?: number;
  tags?: string; // Tag IDs, comma-separated (e.g., "1,2,3")
  tag_mode?: "AND" | "OR";
  sort?: "updated" | "created" | "custom"; // Backend sort options
  pinned_only?: boolean;
  archived?: boolean;
  include_archived?: boolean;
}

// ===================================================================
// Server Dashboard Types (Phase 8.2)
// ===================================================================

export interface HardwareStatus {
  cpu_temp: number | null;
  memory: {
    total_mb: number;
    used_mb: number;
    available_mb: number;
    percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  database: {
    size_mb: number;
    wal_size_mb: number;
  };
  data_dir?: string;
  platform: {
    system: string;
    machine: string;
    hostname: string;
    go_version: string;
  };
  service_management?: {
    available: boolean;
    reason: string;
  };
  uptime_seconds: number | null;
}

export interface ChangelogEntry {
  date: string;
  title: string;
  body: string;
}

export interface VersionInfo {
  version: string;
  changelog: ChangelogEntry[];
  is_frozen: boolean;
  v2_mode: boolean;
  platform: string;
}

export interface BackupItem {
  filename: string;
  size_bytes: number;
  size_mb: number;
  created_at: string;
}

export interface BackupListResponse {
  backups: BackupItem[];
  count: number;
  total_size_mb: number;
}

export interface DeleteBackupResponse {
  deleted: string;
}

export interface ServerLogsResponse {
  lines: string[];
  total_lines: number;
  filtered_lines: number;
  log_file: string;
  log_size_kb: number;
}

export interface RotateBackupsResponse {
  new_backup: string;
  kept_backups: BackupItem[];
  deleted_backups: string[];
  total_size_mb: number;
}

export interface RestoreBackupResponse {
  restarting: boolean;
  backup: string;
  supervised: boolean;
}

export interface RestartServiceResponse {
  status: 'success' | 'error';
  message: string;
}

export interface SearchIntegrityResponse {
  status: 'ok' | 'needs_rebuild';
  notes_count: number;
  fts_rows: number;
  missing_fts_rows: number;
  orphan_fts_rows: number;
  rebuild_route: string;
  auto_repair: boolean;
}

export interface SearchIntegrityRebuildResponse {
  notes_count: number;
  fts_rows: number;
  message: string;
}

// Create axios instance
const API_BASE_URL = "/api";
const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Global error interceptor — unified error handling for all API calls.
// Individual catch blocks only need to handle business-logic-specific cases.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      // Network error / server unreachable
      toast.error(t("apiErrors.networkUnavailable"));
      return Promise.reject(error);
    }

    const { status, data } = error.response;
    const msg = data?.message || data?.error;

    // 404/409: caller handles (e.g. "note not found" has specific UX)
    if (status === 404 || status === 409) {
      return Promise.reject(error);
    }

    // 5xx: always toast — server is broken, not the user's fault
    if (status >= 500) {
      toast.error(msg || t("apiErrors.serverError", { status }));
    }

    return Promise.reject(error);
  }
);

// API Functions
export const api = {
  // Health check
  health: async () => {
    const { data } = await client.get("/test");
    return data;
  },

  // Notes CRUD
  getNotes: async (params: GetNotesParams = {}): Promise<NotesResponse> => {
    // Transform params to match backend API exactly
    const apiParams: Record<string, string | number | boolean | undefined> = {
      page: params.page,
      per_page: params.per_page,
      q: params.search,
      type: params.type,
      category_id: params.category_id,
      parent_id: params.parent_id,
      tags: params.tags, // Backend expects comma-separated tag IDs
      tag_mode: params.tag_mode,
      sort: params.sort, // 'updated', 'created', or 'custom'
      pinned_only: params.pinned_only,
      archived: params.archived,
      include_archived: params.include_archived,
    };

    // Remove undefined values
    Object.keys(apiParams).forEach((key) => {
      if (apiParams[key] === undefined || apiParams[key] === "") {
        delete apiParams[key];
      }
    });

    const { data } = await client.get("/notes", { params: apiParams });
    // Backend returns { status, data: [...], pagination: { total, ... } }
    return {
      notes: data.data || [],
      total: data.pagination?.total || 0,
      page: data.pagination?.page || params.page || 1,
      per_page: data.pagination?.per_page || params.per_page || 20,
    };
  },

  getNote: async (id: number): Promise<Note> => {
    const { data } = await client.get(`/notes/${id}`);
    return data.data;  // Backend returns { status, data: {...} }
  },

  createNote: async (note: NotePayload): Promise<{ note_id: number }> => {
    const { data } = await client.post("/notes", note);
    return data.data; // Backend returns { status, data: { note_id } }
  },

  updateNote: async (id: number, note: NotePayload): Promise<void> => {
    await client.put(`/notes/${id}`, note);
    // Backend returns { status: 'success' } only
  },

  deleteNote: async (id: number): Promise<void> => {
    await client.delete(`/notes/${id}`);
  },

  // Phase 3.7: Duplicate / Create Variant
  duplicateNote: async (
    id: number,
    options?: {
      as_variant?: boolean;
      title_suffix?: string;
    }
  ): Promise<{
    note_id: number;
    parent_id?: number;
    is_variant: boolean;
  }> => {
    const { data } = await client.post(`/notes/${id}/duplicate`, options || {});
    return data.data;
  },

  // Reorder notes (drag & drop)
  reorderNotes: async (noteIds: number[]): Promise<void> => {
    await client.put("/notes/reorder", { note_ids: noteIds });
  },

  // Categories
  getCategories: async (): Promise<Category[]> => {
    const { data } = await client.get("/categories");
    return data.data || [];
  },

  createCategory: async (
    name: string,
    icon?: string
  ): Promise<{ id: number }> => {
    const { data } = await client.post("/categories", { name, icon });
    return data.data;
  },

  updateCategory: async (
    id: number,
    updates: { name?: string; icon?: string; sort_order?: number }
  ): Promise<{ updated_notes_count: number }> => {
    const { data } = await client.put(`/categories/${id}`, updates);
    return data.data;
  },

  deleteCategory: async (
    id: number,
    targetCategoryId?: number
  ): Promise<{ migrated_notes_count: number }> => {
    const { data } = await client.delete(`/categories/${id}`, {
      data: targetCategoryId ? { target_category_id: targetCategoryId } : undefined,
    });
    return data.data;
  },

  // Tags
  getTags: async (): Promise<Tag[]> => {
    const { data } = await client.get("/tags");
    return data.data || [];
  },

  renameTag: async (id: number, name: string): Promise<void> => {
    await client.put(`/tags/${id}`, { name });
  },

  deleteTag: async (id: number): Promise<void> => {
    await client.delete(`/tags/${id}`);
  },

  mergeTags: async (
    sourceTagIds: number[],
    targetTagId: number
  ): Promise<{ merged_count: number }> => {
    const { data } = await client.post("/tags/merge", {
      source_tag_ids: sourceTagIds,
      target_tag_id: targetTagId,
    });
    return data.data;
  },

  // File Upload
  uploadImage: async (
    file: File
  ): Promise<{ url: string; filename?: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    
    // Read image save mode preference from localStorage
    const imageSaveMode = localStorage.getItem('imageSaveMode') || 'both';
    if (imageSaveMode === 'thumbnail_only') {
      formData.append("thumbnail_only", "true");
    }
    
    const { data } = await client.post("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data.data;
  },

  // Download remote image URL and save locally
  downloadImageFromUrl: async (
    imageUrl: string,
    thumbnailOnly?: boolean
  ): Promise<{ url: string; filename: string; original_url: string }> => {
    const { data } = await client.post("/upload/url", {
      url: imageUrl,
      thumbnail_only: thumbnailOnly ?? true, // Default to thumbnail only for faster loading
    });
    return data.data;
  },

  // Extract AI prompt from image metadata
  extractImagePrompt: async (
    imagePath: string
  ): Promise<{
    prompt: string | null;
    negative_prompt: string | null;
    source: string | null;
    has_prompt: boolean;
  }> => {
    const { data } = await client.post("/upload/extract-prompt", {
      image_path: imagePath,
    });
    return data.data;
  },

  // ===================================================================
  // Attachments API (Phase 3.4)
  // ===================================================================

  // Get attachments for a note
  getNoteAttachments: async (
    noteId: number
  ): Promise<
    Array<{
      id: number;
      file_path: string;
      file_type: string;
      title: string;
      size_bytes: number;
      is_auto_extracted: boolean;
      created_at: string;
    }>
  > => {
    const { data } = await client.get(`/notes/${noteId}/attachments`);
    return data.data || [];
  },

  // Upload attachment to note
  uploadAttachment: async (
    noteId: number,
    file: File,
    title?: string
  ): Promise<{
    id: number;
    file_path: string;
    title: string;
    size_bytes: number;
  }> => {
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);

    const { data } = await client.post(
      `/notes/${noteId}/attachments`,
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );
    return data.data;
  },

  // Get attachment content
  getAttachmentContent: async (
    attachmentId: number
  ): Promise<{
    id: number;
    title: string;
    file_type: string;
    content: string;
  }> => {
    const { data } = await client.get(`/attachments/${attachmentId}`);
    return data.data;
  },

  // Delete attachment
  deleteAttachment: async (attachmentId: number): Promise<void> => {
    await client.delete(`/attachments/${attachmentId}`);
  },

  // ===================================================================
  // 3.4.4 Auto-Separation API
  // ===================================================================

  // Check if note content should be separated
  checkSeparation: async (
    noteId: number
  ): Promise<{
    should_separate: boolean;
    content_length: number;
    threshold: number;
  }> => {
    const { data } = await client.get(`/notes/${noteId}/check_separation`);
    return data.data;
  },

  // Separate long content into attachment
  separateContent: async (
    noteId: number,
    previewLength?: number
  ): Promise<{
    attachment_id: number;
    file_path: string;
    original_length: number;
    preview_length: number;
  }> => {
    const { data } = await client.post(
      `/notes/${noteId}/separate`,
      previewLength ? { preview_length: previewLength } : {}
    );
    return data.data;
  },

  // Restore separated content back to note
  restoreContent: async (noteId: number): Promise<void> => {
    await client.post(`/notes/${noteId}/restore`);
  },

  // ===================================================================
  // Cleanup API
  // ===================================================================

  // Get orphan images (images not referenced by any note)
  getOrphanImages: async (): Promise<{
    orphan_images: Array<{ filename: string; size: number; path: string }>;
    total_count: number;
    total_size_bytes: number;
    total_size_mb: number;
  }> => {
    const { data } = await client.get("/cleanup/orphan-images");
    return data.data;
  },

  // Delete orphan images
  deleteOrphanImages: async (
    filenames: string[]
  ): Promise<{
    deleted: string[];
    deleted_count: number;
    errors: Array<{ filename: string; error: string }>;
  }> => {
    const { data } = await client.delete("/cleanup/orphan-images", {
      data: { filenames },
    });
    return data.data;
  },

  // Get original images stats (images that have thumbnails)
  getOriginalImages: async (): Promise<{
    original_count: number;
    original_size_bytes: number;
    original_size_mb: number;
    thumbnail_count: number;
  }> => {
    const { data } = await client.get("/cleanup/originals");
    return data.data;
  },

  // Delete all originals (keep only thumbnails)
  deleteOriginalImages: async (): Promise<{
    deleted_count: number;
    saved_bytes: number;
    saved_mb: number;
    updated_notes: number;
  }> => {
    const { data } = await client.delete("/cleanup/originals");
    return data.data;
  },

  // Get broken image paths
  getBrokenImages: async (): Promise<{
    broken_paths: Array<{
      note_id: number;
      original_path: string;
      thumbnail_path: string | null;
      can_fix: boolean;
      reason: string;
    }>;
    total_count: number;
    fixable_count: number;
  }> => {
    const { data } = await client.get("/cleanup/broken-images");
    return data.data;
  },

  // Fix broken image paths
  fixBrokenImages: async (): Promise<{
    fixed_count: number;
    updated_notes: number;
  }> => {
    const { data } = await client.post("/cleanup/broken-images");
    return data.data;
  },

  // ===================================================================
  // Export API
  // ===================================================================

  // Export all data as JSON (triggers download)
  exportJSON: async (): Promise<void> => {
    window.location.href = `${API_BASE_URL}/export/json`;
  },

  // Export database file (triggers download)
  exportDB: async (): Promise<void> => {
    window.location.href = `${API_BASE_URL}/export/db`;
  },

  // Export all notes as Markdown zip (one .md per note + _manifest.json)
  exportMarkdown: async (): Promise<void> => {
    window.location.href = `${API_BASE_URL}/export/markdown`;
  },

  // Export images as ZIP
  exportImages: async (images: string[], noteTitle: string): Promise<void> => {
    const response = await client.post(
      "/export/images",
      { images, note_title: noteTitle },
      { responseType: "blob" }
    );
    
    // Trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${noteTitle}_images.zip`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // Import JSON data
  importJSON: async (
    data: unknown,
    mode: "skip" | "duplicate"
  ): Promise<{
    imported: number;
    skipped: number;
    duplicates: string[];
  }> => {
    const { data: response } = await client.post("/import/json", {
      data,
      mode,
    });
    return response.data;
  },

  // ===================================================================
  // Note Actions API
  // ===================================================================

  // Toggle pin status
  togglePin: async (noteId: number): Promise<{ is_pinned: boolean }> => {
    const { data } = await client.post(`/notes/${noteId}/pin`, {});
    return data.data;
  },

  // Toggle archive status
  toggleArchive: async (noteId: number): Promise<{ is_archived: boolean }> => {
    const { data } = await client.post(`/notes/${noteId}/archive`, {});
    return data.data;
  },

  // ===================================================================
  // Note History API
  // ===================================================================

  // Get note history versions
  getNoteHistory: async (
    noteId: number
  ): Promise<{
    history: Array<{
      id: number;
      content: string;
      diff_summary: string;
      created_at: string;
    }>;
    total: number;
  }> => {
    const { data } = await client.get(`/notes/${noteId}/history`);
    return data.data;
  },

  // Restore note to a specific version
  restoreNoteVersion: async (
    noteId: number,
    historyId: number
  ): Promise<void> => {
    await client.post(
      `/notes/${noteId}/restore/${historyId}`,
      {}
    );
    // Backend returns { status: 'success', message: ... }
  },

  // Delete note history
  deleteNoteHistory: async (
    noteId: number
  ): Promise<{ deleted_count: number }> => {
    const { data } = await client.delete(`/notes/${noteId}/history`);
    return data.data;
  },

  // ===================================================================
  // System Maintenance
  // ===================================================================

  // WAL Checkpoint
  walCheckpoint: async (): Promise<{
    wal_size_before: number;
    pages_checkpointed: number;
  }> => {
    const { data } = await client.post("/system/wal-checkpoint", {});
    return data.data;
  },

  // Data Consistency Check
  checkConsistency: async (): Promise<{
    orphan_note_tags: number;
    unused_tags: number;
    null_category_id: number;
    fk_enabled: boolean;
    health: 'healthy' | 'warning' | 'critical';
  }> => {
    const { data } = await client.get("/system/check-consistency");
    return data.data;
  },

  getSearchIntegrity: async (): Promise<SearchIntegrityResponse> => {
    const { data } = await client.get("/system/search-integrity");
    return data.data;
  },

  rebuildSearchIndex: async (): Promise<SearchIntegrityRebuildResponse> => {
    const { data } = await client.post("/system/search-integrity/rebuild-fts", {});
    return data.data;
  },

  // ===================================================================
  // Image Management (v1.5.0)
  // ===================================================================

  // Delete an uploaded image file
  deleteImage: async (url: string): Promise<{ deleted: string[]; count: number }> => {
    const { data } = await client.post("/upload/delete", { url });
    return data.data;
  },

  // ===================================================================
  // Update Check (v2.1.0 - Task 7.1)
  // ===================================================================

  checkUpdate: async (): Promise<{
    current_version: string;
    latest_version: string | null;
    has_update: boolean;
    release_url: string;
    release_notes: string;
    message?: string;
    error?: string;
  }> => {
    const { data } = await client.get('/system/check-update');
    return data.data;
  },

  // ===================================================================
  // Migration Status (v2.1.0 - Task 7.3)
  // ===================================================================

  getMigrationStatus: async (): Promise<{
    current_version: number;
    latest_version: number;
    completed: { version: number; name: string }[];
    pending: { version: number; name: string }[];
  }> => {
    const { data } = await client.get('/system/migration-status');
    return data.data;
  },

  // ===================================================================
  // Port Configuration (v1.5.0)
  // ===================================================================

  // Get port configuration
  getPortConfig: async (): Promise<{
    preferred_port: number;
    fallback_enabled: boolean;
    fallback_range: number;
    current_port: number;
  }> => {
    const { data } = await client.get("/system/port-config");
    return data.data;
  },

  // Save port configuration
  savePortConfig: async (config: {
    preferred_port: number;
    fallback_enabled: boolean;
    fallback_range: number;
  }): Promise<{
    preferred_port: number;
    fallback_enabled: boolean;
    fallback_range: number;
  }> => {
    const { data } = await client.post("/system/port-config", config);
    return data.data;
  },

  // Get CSRF protection state (Origin/Referer enforcement on writes)
  getCsrfProtection: async (): Promise<boolean> => {
    const { data } = await client.get("/system/csrf-protection");
    return data.data.csrf_protection;
  },

  // Toggle CSRF protection (takes effect immediately, no restart)
  setCsrfProtection: async (enabled: boolean): Promise<boolean> => {
    const { data } = await client.post("/system/csrf-protection", {
      csrf_protection: enabled,
    });
    return data.data.csrf_protection;
  },

  // ===================================================================
  // Server Dashboard (Phase 8.2)
  // ===================================================================

  getHardwareStatus: async (): Promise<HardwareStatus> => {
    const { data } = await client.get('/server/hardware');
    return data.data;
  },

  getVersionInfo: async (): Promise<VersionInfo> => {
    const { data } = await client.get('/server/version');
    return data.data;
  },

  listBackups: async (): Promise<BackupListResponse> => {
    const { data } = await client.get('/server/backup/list');
    return data.data;
  },

  getServerLogs: async (lines: number = 100, level: string = 'ALL'): Promise<ServerLogsResponse> => {
    const { data } = await client.get(`/server/logs?lines=${lines}&level=${level}`);
    return data.data;
  },

  downloadBackup: async (): Promise<void> => {
    const response = await client.get('/server/backup/download', {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const filename = response.headers['content-disposition']
      ?.match(/filename="?(.+?)"?$/)?.[1] || `prism_backup_${Date.now()}.db`;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  rotateBackups: async (keepCount: number = 3): Promise<RotateBackupsResponse> => {
    const { data } = await client.post('/server/backup/rotate', { keep_count: keepCount });
    return data.data;
  },

  deleteBackup: async (filename: string): Promise<DeleteBackupResponse> => {
    const { data } = await client.delete(`/server/backup/${encodeURIComponent(filename)}`);
    return data.data;
  },

  restoreBackup: async (filename: string): Promise<RestoreBackupResponse> => {
    const { data } = await client.post('/server/backup/restore', { backup: filename });
    return data.data;
  },

  // Poll the health endpoint until the server is back after a restart.
  waitForHealthy: async (timeoutMs: number = 30000): Promise<boolean> => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      try {
        const res = await client.get('/healthz', { baseURL: '', timeout: 2000 });
        if (res.status === 200) return true;
      } catch {
        // server still restarting; keep polling
      }
      await new Promise((r) => setTimeout(r, 1000));
    }
    return false;
  },

  restartService: async (): Promise<RestartServiceResponse> => {
    const { data } = await client.post('/server/restart');
    return data;
  },
};
