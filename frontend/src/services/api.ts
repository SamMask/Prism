import axios from "axios";

// Types matching backend schema
export interface Note {
  id: number;
  title: string;
  content: string;
  type: string;
  remarks?: string;
  cover_image?: string;
  cover_position?: "top" | "center" | "bottom";
  is_pinned: boolean;
  is_archived: boolean;
  category_id?: number;
  category_name?: string;
  tags: Tag[];
  urls: string[];
  created_at: string;
  updated_at: string;
  // V2 Fields (from SCHEMA-V2.md)
  ai_summary?: string;
  ai_tags?: string[];
  embedding_status?: "pending" | "indexed";
  // Phase 3.7: Card Lineage
  parent_id?: number;
  parent_title?: string;
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
  is_pinned?: boolean;
  is_archived?: boolean;
  cover_image?: string;
  cover_position?: "top" | "center" | "bottom";
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
  tags?: string; // Tag IDs, comma-separated (e.g., "1,2,3")
  sort?: "updated" | "created" | "custom"; // Backend sort options
  pinned_only?: boolean;
  archived?: boolean;
}

// Create axios instance
const client = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

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
    const apiParams: Record<string, any> = {
      page: params.page,
      per_page: params.per_page,
      q: params.search,
      type: params.type,
      tags: params.tags, // Backend expects comma-separated tag IDs
      sort: params.sort, // 'updated', 'created', or 'custom'
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
    return data.note;
  },

  createNote: async (note: NotePayload): Promise<{ note_id: number }> => {
    const { data } = await client.post("/notes", note);
    return data.data; // Backend returns { status, data: { note_id } }
  },

  updateNote: async (id: number, note: NotePayload): Promise<Note> => {
    const { data } = await client.put(`/notes/${id}`, note);
    return data.note;
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

  // Categories
  getCategories: async (): Promise<Category[]> => {
    const { data } = await client.get("/categories");
    return data.data || [];
  },

  // Tags
  getTags: async (): Promise<Tag[]> => {
    const { data } = await client.get("/tags");
    return data.data || [];
  },

  // File Upload
  uploadImage: async (
    file: File
  ): Promise<{ url: string; filename?: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await client.post("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data.data;
  },

  // ===================================================================
  // AI API (Phase 3: Local Intelligence)
  // ===================================================================

  // Get Ollama status
  getAIStatus: async (): Promise<{
    available: boolean;
    models: string[];
    vision_ready: boolean;
    text_ready: boolean;
    error?: string;
  }> => {
    const { data } = await client.get("/ai/status");
    return data.data;
  },

  // Analyze image and get suggested tags
  analyzeImage: async (
    file: File,
    options?: {
      model?: string;
      language?: "en" | "zh";
    }
  ): Promise<{
    tags: string[];
    description: string;
  }> => {
    const formData = new FormData();
    formData.append("file", file);
    if (options?.model) formData.append("model", options.model);
    if (options?.language) formData.append("language", options.language);

    const { data } = await client.post("/ai/tag_image", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000, // 2 minutes for AI processing
    });
    return data.data;
  },

  // Analyze existing image by path
  analyzeImageByPath: async (
    imagePath: string,
    options?: {
      model?: string;
      language?: "en" | "zh";
    }
  ): Promise<{
    tags: string[];
    description: string;
  }> => {
    const { data } = await client.post(
      "/ai/tag_image",
      {
        image_path: imagePath,
        ...options,
      },
      {
        timeout: 120000,
      }
    );
    return data.data;
  },

  // Analyze full note (content + images)
  analyzeNote: async (
    noteId: number,
    includeImages?: boolean
  ): Promise<{
    suggested_tags: string[];
    summary: string;
    image_analyses: Array<{
      path: string;
      tags: string[];
      description: string;
    }>;
  }> => {
    const { data } = await client.post(
      "/ai/analyze_note",
      {
        note_id: noteId,
        include_images: includeImages ?? true,
      },
      {
        timeout: 180000, // 3 minutes for full analysis
      }
    );
    return data.data;
  },

  // Phase 3.1.4: Batch AI Tagging
  startBatchTag: async (
    scope: "all" | "category" | "untagged",
    categoryId?: number
  ): Promise<{
    task_id: string | null;
    total: number;
    message: string;
  }> => {
    const { data } = await client.post("/ai/batch_tag", {
      scope,
      category_id: categoryId,
    });
    return data.data;
  },

  getBatchStatus: async (
    taskId: string
  ): Promise<{
    task_id: string;
    status: "running" | "completed" | "stopped" | "error";
    total: number;
    completed: number;
    success: number;
    failed: number;
    progress: number;
  }> => {
    const { data } = await client.get(`/ai/batch_tag/${taskId}`);
    return data.data;
  },

  stopBatchTask: async (taskId: string): Promise<void> => {
    await client.post(`/ai/batch_tag/${taskId}/stop`);
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
  // Semantic Search API (Phase 3.2)
  // ===================================================================

  // Semantic search
  semanticSearch: async (
    query: string,
    limit?: number
  ): Promise<{
    data: Array<{
      id: number;
      title: string;
      content_preview: string;
      similarity: number;
      category: string;
      category_icon: string;
      tags: string[];
    }>;
    total: number;
  }> => {
    const { data } = await client.get("/search/semantic", {
      params: { q: query, limit: limit || 20 },
    });
    return data;
  },

  // Get search service status
  getSearchStatus: async (): Promise<{
    available: boolean;
    model_name: string;
    dimensions: number;
    model_loaded: boolean;
    total_notes: number;
    indexed_notes: number;
    index_coverage: string;
  }> => {
    const { data } = await client.get("/search/status");
    return data.data;
  },

  // Rebuild search index
  rebuildSearchIndex: async (): Promise<{
    total: number;
    success: number;
    failed: number;
  }> => {
    const { data } = await client.post(
      "/index/rebuild",
      {},
      {
        timeout: 300000, // 5 minutes for large databases
      }
    );
    return data.data;
  },

  // Generate embedding for single note
  embedNote: async (noteId: number): Promise<void> => {
    await client.post(`/notes/${noteId}/embed`);
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
};
