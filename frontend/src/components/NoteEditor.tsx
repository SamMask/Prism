import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { Modal, Button, toast } from "./ui";
import { Note, api, Tag } from "../services/api";
import { useAppStore } from "../stores/appStore";
import {
  Save,
  X,
  Image,
  Tag as TagIcon,
  FolderOpen,
  Eye,
  Edit3,
  Sparkles,
  Loader2,
  Paperclip,
  FileText,
  Trash2,
  Plus,
  History,
  RotateCcw,
  Clipboard,
  Link2,
} from "lucide-react";
import { marked } from "marked";

interface Attachment {
  id: number;
  file_path: string;
  file_type: string;
  title: string;
  size_bytes: number;
  is_auto_extracted: boolean;
  created_at: string;
}

interface NoteEditorProps {
  note: Note | null;
  onClose: () => void;
}

export function NoteEditor({ note, onClose }: NoteEditorProps) {
  const { categories, fetchNotes } = useAppStore();

  // Form State
  const [title, setTitle] = useState(note?.title || "");
  const [content, setContent] = useState(note?.content || "");
  const [categoryId, setCategoryId] = useState<number | undefined>(
    note?.category_id
  );
  const [selectedTags, setSelectedTags] = useState<Tag[]>(note?.tags || []);
  const [remarks, setRemarks] = useState(note?.remarks || "");
  const [coverPosition, setCoverPosition] = useState<"top" | "center" | "bottom">(
    note?.cover_position || "center"
  );
  const [editorLayout, setEditorLayout] = useState<"single" | "dual">(
    note?.editor_layout || "single"
  );
  const [sourceUrls, setSourceUrls] = useState<string[]>(note?.urls || []);
  const [urlInput, setUrlInput] = useState("");

  // UI State
  const [isPreview, setIsPreview] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [tagInput, setTagInput] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const dropZoneRef = useRef<HTMLDivElement>(null); // Reference to drop zone container

  // AI State
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
  const [aiDescription, setAiDescription] = useState("");

  // Attachment State
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const attachmentInputRef = useRef<HTMLInputElement>(null);

  // History State
  interface HistoryVersion {
    id: number;
    content: string;
    diff_summary: string;
    created_at: string;
  }
  const [historyVersions, setHistoryVersions] = useState<HistoryVersion[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Prompt Extraction State
  const [hasAIPrompt, setHasAIPrompt] = useState(false);
  const [isCheckingPrompt, setIsCheckingPrompt] = useState(false);

  const isEditing = !!note;

  // Render markdown to HTML for preview
  const renderedContent = useMemo(() => {
    if (!content) return "";
    try {
      // Configure marked for security
      marked.setOptions({
        breaks: true, // Convert \n to <br>
        gfm: true, // GitHub Flavored Markdown
      });
      return marked(content) as string;
    } catch (e) {
      console.error("Markdown parse error:", e);
      return content;
    }
  }, [content]);

  // Separation threshold (sync with backend)
  const SEPARATION_THRESHOLD = 5000;

  // Handle save
  const handleSave = async () => {
    if (!title.trim() && !content.trim()) {
      toast.warning("請輸入標題或內容");
      return;
    }

    setIsSaving(true);
    try {
      // Include pending URL input if any
      let finalUrls = [...sourceUrls];
      if (urlInput.trim()) {
        let url = urlInput.trim();
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
          url = "https://" + url;
        }
        if (!finalUrls.includes(url)) {
          finalUrls.push(url);
        }
        setUrlInput("");
        setSourceUrls(finalUrls);
      }

      const payload = {
        title: title.trim() || "無標題",
        content,
        category_id: categoryId,
        remarks,
        tags: selectedTags.map((t) => t.name),
        cover_position: coverPosition,
        editor_layout: editorLayout,
        urls: finalUrls,
      };

      let savedNoteId: number;

      if (isEditing) {
        await api.updateNote(note.id, payload);
        savedNoteId = note.id;
        toast.success("筆記已更新");
      } else {
        const result = await api.createNote(payload);
        savedNoteId = result.note_id;
        toast.success("筆記已建立");
      }

      // Auto-separate for long content (no prompt)
      if (content.length > SEPARATION_THRESHOLD) {
        try {
          await api.separateContent(savedNoteId);
          // Silent success - no toast needed
        } catch (sepError) {
          console.error("Auto-separation failed:", sepError);
          // Silent failure - content is still saved in full
        }
      }

      fetchNotes(true);
      onClose();
    } catch (error) {
      console.error("Save failed:", error);
      toast.error("儲存失敗，請重試");
    } finally {
      setIsSaving(false);
    }
  };

  // Handle paste - support images and HTML content with embedded images
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    const htmlData = e.clipboardData.getData("text/html");
    const textData = e.clipboardData.getData("text/plain");
    
    // Priority 1: Handle direct image paste (screenshot, copied image file)
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (!file) continue;

        try {
          toast.info("上傳圖片中...");
          const result = await api.uploadImage(file);
          const markdown = `![image](${result.url})`;
          setContent((prev) => prev + "\n" + markdown);
          toast.success("圖片已上傳");
        } catch (error) {
          toast.error("圖片上傳失敗");
        }
        return; // Exit after handling image
      }
    }
    
    // Priority 2: Handle HTML content with images (from web pages)
    if (htmlData && htmlData.includes("<img")) {
      e.preventDefault();
      
      try {
        // Parse HTML to extract images and text
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlData, "text/html");
        
        // Find all images
        const images = doc.querySelectorAll("img");
        const imageUrls: string[] = [];
        
        images.forEach((img) => {
          const src = img.getAttribute("src");
          if (src && (src.startsWith("http://") || src.startsWith("https://"))) {
            imageUrls.push(src);
          }
        });
        
        // Download remote images and replace URLs
        const urlMapping: Record<string, string> = {};
        
        if (imageUrls.length > 0) {
          toast.info(`正在下載 ${imageUrls.length} 張圖片...`);
          
          let successCount = 0;
          let failCount = 0;
          
          for (const url of imageUrls) {
            try {
              const result = await api.downloadImageFromUrl(url, true);
              urlMapping[url] = result.url;
              successCount++;
            } catch (error) {
              console.error(`Failed to download: ${url}`, error);
              failCount++;
              // Keep original URL if download fails
              urlMapping[url] = url;
            }
          }
          
          if (successCount > 0) {
            toast.success(`已下載 ${successCount} 張圖片${failCount > 0 ? `，${failCount} 張失敗` : ""}`);
          } else if (failCount > 0) {
            toast.warning(`圖片下載失敗 ${failCount} 張，保留原始 URL`);
          }
        }
        
        // Convert HTML to Markdown-like text
        // Replace images with markdown format
        let markdown = textData || "";
        
        // If there are images, append them as markdown
        if (imageUrls.length > 0) {
          markdown += "\n";
          for (const url of imageUrls) {
            const localUrl = urlMapping[url] || url;
            markdown += `\n![image](${localUrl})`;
          }
        }
        
        setContent((prev) => {
          if (prev.trim()) {
            return prev + "\n\n" + markdown;
          }
          return markdown;
        });
        
      } catch (error) {
        console.error("Failed to process HTML paste:", error);
        // Fallback: just paste the text
        setContent((prev) => prev + "\n" + textData);
        toast.error("處理 HTML 內容時發生錯誤");
      }
      
      return;
    }
    
    // Priority 3: Let browser handle plain text paste normally
    // (No preventDefault, browser will handle it)
  }, []);

  // Handle drag & drop - using relatedTarget to properly detect leaving the container
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Set dropEffect to copy to show proper cursor
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Only set isDragging to false if we're actually leaving the drop zone
    // relatedTarget is the element we're moving TO
    const relatedTarget = e.relatedTarget as Node | null;
    const dropZone = dropZoneRef.current;
    
    // If relatedTarget is null (left the window) or is outside the drop zone, stop dragging
    if (!dropZone || !relatedTarget || !dropZone.contains(relatedTarget)) {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      const imageFiles = files.filter((f) => f.type.startsWith("image/"));
      const mdFiles = files.filter(
        (f) =>
          f.name.endsWith(".md") ||
          f.name.endsWith(".txt") ||
          f.name.endsWith(".markdown")
      );

      // Upload images
      for (const file of imageFiles) {
        try {
          toast.info("上傳圖片中...");
          const result = await api.uploadImage(file);
          const markdown = `![image](${result.url})`;
          setContent((prev) => prev + "\n" + markdown);
          toast.success("圖片已上傳");
        } catch (error) {
          toast.error("圖片上傳失敗");
        }
      }

      // Upload .md files as attachments (only in editing mode)
      if (mdFiles.length > 0 && note?.id) {
        for (const file of mdFiles) {
          try {
            toast.info(`上傳 ${file.name}...`);
            const result = await api.uploadAttachment(note.id, file);
            setAttachments((prev) => [
              ...prev,
              {
                id: result.id,
                file_path: result.file_path,
                file_type: file.name.split(".").pop() || "md",
                title: result.title,
                size_bytes: result.size_bytes,
                is_auto_extracted: false,
                created_at: new Date().toISOString(),
              },
            ]);
            toast.success(`附件 "${result.title}" 已上傳`);
          } catch (error: any) {
            toast.error(error?.response?.data?.message || "附件上傳失敗");
          }
        }
      } else if (mdFiles.length > 0) {
        toast.warning("請先儲存筆記後再上傳附件");
      }
    },
    [note?.id]
  );

  // Handle tag input
  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && tagInput.trim()) {
      e.preventDefault();
      const newTag = { id: Date.now(), name: tagInput.trim() };
      if (
        !selectedTags.find(
          (t) => t.name.toLowerCase() === newTag.name.toLowerCase()
        )
      ) {
        setSelectedTags([...selectedTags, newTag]);
      }
      setTagInput("");
    }
  };

  const removeTag = (tagId: number) => {
    setSelectedTags(selectedTags.filter((t) => t.id !== tagId));
  };

  // Add AI suggested tag
  const addAiTag = (tagName: string) => {
    if (
      !selectedTags.find((t) => t.name.toLowerCase() === tagName.toLowerCase())
    ) {
      setSelectedTags([...selectedTags, { id: Date.now(), name: tagName }]);
    }
    // Remove from suggestions
    setAiSuggestions(aiSuggestions.filter((t) => t !== tagName));
  };

  // AI Analysis
  const handleAiAnalyze = async () => {
    // Extract images from content
    const imagePattern = /!\[.*?\]\((.*?)\)/g;
    const images: string[] = [];
    let match;
    while ((match = imagePattern.exec(content)) !== null) {
      images.push(match[1]);
    }

    if (images.length === 0 && content.length < 50) {
      toast.warning("請先加入圖片或輸入更多內容");
      return;
    }

    setIsAnalyzing(true);
    setAiSuggestions([]);
    setAiDescription("");

    try {
      // Check AI status first
      const status = await api.getAIStatus();

      if (!status.available) {
        toast.error("Ollama 服務未啟動，請先啟動 Ollama");
        return;
      }

      if (images.length > 0 && !status.vision_ready) {
        toast.error("請先安裝視覺模型: ollama pull llava");
        return;
      }

      // Analyze first image if available
      if (images.length > 0) {
        toast.info("✨ AI 正在分析圖片...");
        // Use user-selected model from localStorage
        const savedVisionModel = localStorage.getItem('ai_vision_model') || 'llava';
        const result = await api.analyzeImageByPath(images[0], {
          language: "zh",
          model: savedVisionModel,
        });

        if (result.tags && result.tags.length > 0) {
          setAiSuggestions(result.tags);
          setAiDescription(result.description || "");
          toast.success(`AI 找到 ${result.tags.length} 個建議標籤`);
        } else {
          toast.info("AI 未能識別足夠的特徵");
        }
      } else if (isEditing) {
        // Analyze existing note
        toast.info("✨ AI 正在分析筆記...");
        const result = await api.analyzeNote(note.id);

        if (result.suggested_tags && result.suggested_tags.length > 0) {
          setAiSuggestions(result.suggested_tags);
          if (result.summary) {
            setAiDescription(result.summary);
          }
          toast.success(`AI 找到 ${result.suggested_tags.length} 個建議標籤`);
        }
      }
    } catch (error: any) {
      console.error("AI analysis failed:", error);
      toast.error(error?.response?.data?.message || "AI 分析失敗");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Load attachments when editing (and auto-load separated content)
  const loadAttachments = useCallback(async () => {
    if (!note?.id) return;

    try {
      const data = await api.getNoteAttachments(note.id);
      setAttachments(data);

      // Auto-load separated content into editor (no API call, just fetch content)
      const autoExtracted = data.find((a) => a.is_auto_extracted);
      if (autoExtracted) {
        try {
          // Load content from attachment file directly
          const { content: fullContent } = await api.getAttachmentContent(
            autoExtracted.id
          );
          setContent(fullContent);
        } catch (error) {
          console.error("Failed to load attachment content:", error);
          toast.error("無法載入完整內容，目前顯示預覽");
        }
      }
    } catch (error) {
      console.error("Failed to load attachments:", error);
    }
  }, [note?.id]);

  // Load attachments on mount for editing mode
  useEffect(() => {
    if (isEditing) {
      loadAttachments();
    }
  }, [isEditing, loadAttachments]);

  // Handle attachment file selection
  const handleAttachmentSelect = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !note?.id) return;

    for (const file of Array.from(files)) {
      try {
        toast.info(`上傳 ${file.name}...`);
        const result = await api.uploadAttachment(note.id, file);
        setAttachments((prev) => [
          ...prev,
          {
            id: result.id,
            file_path: result.file_path,
            file_type: file.name.split(".").pop() || "md",
            title: result.title,
            size_bytes: result.size_bytes,
            is_auto_extracted: false,
            created_at: new Date().toISOString(),
          },
        ]);
        toast.success(`附件 "${result.title}" 已上傳`);
      } catch (error: any) {
        toast.error(error?.response?.data?.message || "附件上傳失敗");
      }
    }

    // Reset input
    if (attachmentInputRef.current) {
      attachmentInputRef.current.value = "";
    }
  };

  // Handle delete attachment
  const handleDeleteAttachment = async (attachmentId: number) => {
    if (!confirm("確定要刪除此附件？")) return;

    try {
      await api.deleteAttachment(attachmentId);
      setAttachments((prev) => prev.filter((a) => a.id !== attachmentId));
      toast.success("附件已刪除");
    } catch (error) {
      toast.error("刪除附件失敗");
    }
  };

  // Handle load attachment content (click to view)
  const handleLoadAttachment = async (
    attachmentId: number,
    isAutoExtracted: boolean
  ) => {
    try {
      const { content: attachmentContent } = await api.getAttachmentContent(
        attachmentId
      );

      if (isAutoExtracted) {
        // For auto-extracted, load content to editor
        setContent(attachmentContent);
        toast.success("內容已載入");
      } else {
        // For regular attachments, open in new window
        const win = window.open("", "_blank");
        if (win) {
          win.document.write(`
            <html>
              <head>
                <title>附件內容</title>
                <style>
                  body { font-family: monospace; padding: 20px; background: #1a1a2e; color: #e0e0e0; }
                  pre { white-space: pre-wrap; word-wrap: break-word; }
                </style>
              </head>
              <body><pre>${attachmentContent}</pre></body>
            </html>
          `);
          win.document.close();
        }
      }
    } catch (error) {
      toast.error("讀取附件失敗");
    }
  };

  // Load note history
  const loadHistory = async () => {
    if (!note) return;
    setIsLoadingHistory(true);
    try {
      const result = await api.getNoteHistory(note.id);
      setHistoryVersions(result.history);
      setShowHistory(true);
    } catch (error) {
      toast.error("載入歷史版本失敗");
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Restore to a specific version
  const restoreVersion = async (historyId: number) => {
    if (!note) return;
    if (!confirm("確定要還原到此版本嗎？目前的內容會被覆蓋。")) return;

    try {
      await api.restoreNoteVersion(note.id, historyId);
      toast.success("已還原到指定版本");
      // Reload note content
      const updatedNote = await api.getNote(note.id);
      setContent(updatedNote.content);
      setShowHistory(false);
      fetchNotes(true);
    } catch (error) {
      toast.error("還原失敗");
    }
  };

  // Check for AI prompts in images
  useEffect(() => {
    const checkForPrompt = async () => {
      // Extract first image from content
      const imagePattern = /!\[.*?\]\((\/static\/uploads\/[^\)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/;
      const match = content?.match(imagePattern);
      if (!match) {
        setHasAIPrompt(false);
        return;
      }
      
      const imagePath = match[1] || match[2];
      if (!imagePath) {
        setHasAIPrompt(false);
        return;
      }
      
      try {
        setIsCheckingPrompt(true);
        const result = await api.extractImagePrompt(imagePath);
        setHasAIPrompt(result.has_prompt);
      } catch {
        setHasAIPrompt(false);
      } finally {
        setIsCheckingPrompt(false);
      }
    };
    
    // Debounce the check
    const timer = setTimeout(checkForPrompt, 500);
    return () => clearTimeout(timer);
  }, [content]);

  // Copy AI prompt to clipboard
  const handleCopyPrompt = async () => {
    // Extract all images from content
    const imagePattern = /!\[.*?\]\((\/static\/uploads\/[^\)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/g;
    const matches: string[] = [];
    let match;
    while ((match = imagePattern.exec(content || "")) !== null) {
      matches.push(match[1] || match[2]);
    }
    
    if (matches.length === 0) {
      toast.warning("未找到圖片");
      return;
    }
    
    // Try to find prompt from all images
    for (const imagePath of matches) {
      try {
        const result = await api.extractImagePrompt(imagePath);
        if (result.has_prompt && result.prompt) {
          let textToCopy = result.prompt;
          if (result.negative_prompt) {
            textToCopy += `\n\nNegative prompt: ${result.negative_prompt}`;
          }
          await navigator.clipboard.writeText(textToCopy);
          toast.success(`已複製 ${result.source || "AI"} 提示詞`);
          return;
        }
      } catch {
        // Continue to next image
      }
    }
    
    toast.warning("圖片中未找到 AI 提示詞");
  };

  // Textarea ref for formatting shortcuts
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Apply markdown formatting to selected text
  const applyFormat = (prefix: string, suffix: string = prefix) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = content.substring(start, end);
    const newText = content.substring(0, start) + prefix + selectedText + suffix + content.substring(end);
    
    setContent(newText);
    
    // Restore selection after React re-render
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + prefix.length, end + prefix.length);
    }, 0);
  };

  // Keyboard shortcuts: Ctrl+S (save), Ctrl+B (bold), Ctrl+I (italic), Ctrl+K (link)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case "s":
            e.preventDefault();
            handleSave();
            break;
          case "b":
            e.preventDefault();
            applyFormat("**");
            break;
          case "i":
            e.preventDefault();
            applyFormat("*");
            break;
          case "k":
            e.preventDefault();
            applyFormat("[", "](url)");
            break;
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [title, content, categoryId, selectedTags, remarks]);

  return (
    <>
    <Modal isOpen onClose={onClose} size="xl">
      <div className="flex flex-col h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
          <h2 className="text-lg font-semibold text-text-primary">
            {isEditing ? "編輯筆記" : "新增筆記"}
          </h2>
          <div className="flex items-center gap-2">
            {/* AI Analyze Button */}
            <button
              onClick={handleAiAnalyze}
              disabled={isAnalyzing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                         transition-all duration-200
                         ${
                           isAnalyzing
                             ? "bg-accent/20 text-accent cursor-wait"
                             : "bg-accent/10 text-accent hover:bg-accent/20"
                         }`}
              title="AI 智慧分析"
            >
              {isAnalyzing ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Sparkles size={16} />
              )}
              {isAnalyzing ? "分析中..." : "AI 分析"}
            </button>

            {/* Extract Prompt Button */}
            <button
              onClick={handleCopyPrompt}
              disabled={isCheckingPrompt}
              className={`p-2 rounded-lg transition-all duration-200 relative
                         ${
                           hasAIPrompt
                             ? "bg-success/20 text-success hover:bg-success/30 shadow-lg shadow-success/20"
                             : isCheckingPrompt
                               ? "bg-bg-elevated text-text-muted cursor-wait"
                               : "bg-bg-elevated text-text-muted hover:text-text-primary hover:bg-bg-hover"
                         }`}
              title={hasAIPrompt ? "複製 AI 提示詞" : "提取圖片提示詞"}
            >
              {isCheckingPrompt ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Clipboard size={16} />
              )}
              {hasAIPrompt && (
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-success rounded-full animate-pulse" />
              )}
            </button>

            {/* History Button (only for existing notes) */}
            {isEditing && (
              <button
                onClick={loadHistory}
                disabled={isLoadingHistory}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                           transition-all duration-200
                           ${
                             isLoadingHistory
                               ? "bg-warning/20 text-warning cursor-wait"
                               : "bg-warning/10 text-warning hover:bg-warning/20"
                           }`}
                title="歷史版本"
              >
                {isLoadingHistory ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <History size={16} />
                )}
                歷史
              </button>
            )}

            {/* Preview Toggle */}
            <button
              onClick={() => setIsPreview(!isPreview)}
              className={`p-2 rounded-lg transition-colors ${
                isPreview
                  ? "bg-primary text-white"
                  : "text-text-muted hover:bg-bg-hover"
              }`}
              title={isPreview ? "編輯模式" : "預覽模式"}
            >
              {isPreview ? <Edit3 size={18} /> : <Eye size={18} />}
            </button>

            {/* Save Button */}
            <Button onClick={handleSave} variant="primary" disabled={isSaving}>
              <Save size={16} />
              {isSaving ? "儲存中..." : "儲存"}
            </Button>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-text-muted hover:bg-bg-hover"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Image Gallery (Dual Mode) */}
          {editorLayout === "dual" && (
            <div className="w-56 flex-shrink-0 border-r border-border-subtle p-3 overflow-auto bg-bg-elevated/30">
              <h4 className="text-sm font-medium text-text-secondary mb-3 flex items-center gap-2">
                <Image size={14} />
                圖片預覽
              </h4>
              {(() => {
                const imagePattern = /!\[.*?\]\((\/static\/uploads\/[^\)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/g;
                const images: string[] = [];
                let match;
                const contentToParse = content || "";
                while ((match = imagePattern.exec(contentToParse)) !== null) {
                  images.push(match[1] || match[2]);
                }
                if (images.length === 0) {
                  return (
                    <div className="text-center text-text-muted text-sm py-8">
                      <Image size={32} className="mx-auto mb-2 opacity-30" />
                      <p>尚無圖片</p>
                      <p className="text-xs mt-1">在內容中加入圖片後會顯示在此</p>
                    </div>
                  );
                }
                return (
                  <div className="space-y-3">
                    {images.map((src, index) => (
                      <div key={index} className="relative group">
                        <img
                          src={src}
                          alt={`圖片 ${index + 1}`}
                          className="w-full rounded-lg border border-border-subtle cursor-pointer
                                     hover:border-primary transition-colors"
                          onClick={() => window.open(src, "_blank")}
                        />
                        <span className="absolute top-2 left-2 bg-black/50 text-white text-xs px-2 py-0.5 rounded">
                          {index + 1}
                        </span>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </div>
          )}

          {/* Editor Area */}
          <div
            ref={dropZoneRef}
            className={`flex-1 flex flex-col p-6 overflow-auto relative
                        ${
                          isDragging
                            ? "ring-2 ring-primary ring-inset bg-primary/5"
                            : ""
                        }`}
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {/* Drag Overlay - pointer-events-none to prevent triggering dragLeave */}
            {isDragging && (
              <div className="absolute inset-0 flex items-center justify-center bg-bg-surface/80 z-10 pointer-events-none">
                <div className="text-center pointer-events-none">
                  <Image size={48} className="mx-auto text-primary mb-2" />
                  <p className="text-text-primary font-medium">
                    拖放圖片或 .md 檔案至此上傳
                  </p>
                </div>
              </div>
            )}

            {/* Title */}
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="標題"
              className="text-xl font-semibold bg-transparent border-none outline-none
                         text-text-primary placeholder-text-muted mb-4"
            />

            {/* Content */}
            {isPreview ? (
              <div
                className="flex-1 prose prose-invert max-w-none
                           text-text-primary prose-headings:text-text-primary
                           prose-a:text-primary prose-strong:text-text-primary
                           prose-code:bg-bg-elevated prose-code:px-1 prose-code:rounded
                           prose-img:rounded-lg prose-img:max-h-96"
                dangerouslySetInnerHTML={{ __html: renderedContent }}
              />
            ) : (
              <textarea
                ref={textareaRef}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onPaste={handlePaste}
                placeholder="開始輸入內容... (支援 Markdown，可直接貼上或拖曳圖片，Ctrl+B 粗體、Ctrl+I 斜體)"
                className="flex-1 bg-transparent border-none outline-none resize-none
                           text-text-primary placeholder-text-muted
                           font-mono text-sm leading-relaxed"
              />
            )}
          </div>

          {/* Sidebar */}
          <div className="w-64 flex-shrink-0 border-l border-border-subtle p-4 space-y-4 overflow-auto">
            {/* AI Suggestions */}
            {(aiSuggestions.length > 0 || aiDescription) && (
              <div className="p-3 rounded-lg bg-accent/5 border border-accent/20">
                <h4 className="flex items-center gap-2 text-sm font-medium text-accent mb-2">
                  <Sparkles size={14} />
                  AI 建議
                </h4>

                {aiDescription && (
                  <p className="text-xs text-text-secondary mb-2 leading-relaxed">
                    {aiDescription}
                  </p>
                )}

                {aiSuggestions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {aiSuggestions.map((tag, i) => (
                      <button
                        key={i}
                        onClick={() => addAiTag(tag)}
                        className="px-2 py-0.5 text-xs rounded-full
                                   bg-accent/10 text-accent
                                   hover:bg-accent/20 transition-colors"
                        title="點擊添加此標籤"
                      >
                        + {tag}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Category */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                <FolderOpen size={14} /> 分類
              </label>
              <select
                value={categoryId || ""}
                onChange={(e) =>
                  setCategoryId(
                    e.target.value ? Number(e.target.value) : undefined
                  )
                }
                className="w-full px-3 py-2 rounded-lg
                           bg-bg-elevated border border-border-default
                           text-text-primary text-sm
                           focus:outline-none focus:border-primary"
              >
                <option value="">選擇分類</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.icon} {cat.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Tags */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                <TagIcon size={14} /> 標籤
              </label>
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                placeholder="輸入標籤後按 Enter"
                className="w-full px-3 py-2 rounded-lg
                           bg-bg-elevated border border-border-default
                           text-text-primary text-sm
                           focus:outline-none focus:border-primary"
              />
              {selectedTags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {selectedTags.map((tag) => (
                    <span
                      key={tag.id}
                      className="inline-flex items-center gap-1 px-2 py-0.5
                                 text-xs rounded-full
                                 bg-primary/10 text-primary-light"
                    >
                      {tag.name}
                      <button
                        onClick={() => removeTag(tag.id)}
                        className="hover:text-danger"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Source URLs */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                <Link2 size={14} /> 來源連結
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && urlInput.trim()) {
                      e.preventDefault();
                      let url = urlInput.trim();
                      if (!url.startsWith("http://") && !url.startsWith("https://")) {
                        url = "https://" + url;
                      }
                      if (!sourceUrls.includes(url)) {
                        setSourceUrls([...sourceUrls, url]);
                      }
                      setUrlInput("");
                    }
                  }}
                  onBlur={() => {
                    if (urlInput.trim()) {
                      let url = urlInput.trim();
                      if (!url.startsWith("http://") && !url.startsWith("https://")) {
                        url = "https://" + url;
                      }
                      if (!sourceUrls.includes(url)) {
                        setSourceUrls([...sourceUrls, url]);
                      }
                      setUrlInput("");
                    }
                  }}
                  placeholder="輸入 URL 後按 Enter 或點擊其他地方"
                  className="flex-1 px-3 py-2 rounded-lg
                             bg-bg-elevated border border-border-default
                             text-text-primary text-sm
                             focus:outline-none focus:border-primary"
                />
              </div>
              {sourceUrls.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  {sourceUrls.map((url, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 p-2 rounded-lg bg-bg-elevated group"
                    >
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 text-xs text-primary truncate hover:underline"
                      >
                        {url}
                      </a>
                      <button
                        onClick={() =>
                          setSourceUrls(sourceUrls.filter((_, i) => i !== index))
                        }
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-danger/10 text-text-muted hover:text-danger"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Remarks */}
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                備註
              </label>
              <textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="簡短備註..."
                rows={3}
                className="w-full px-3 py-2 rounded-lg
                           bg-bg-elevated border border-border-default
                           text-text-primary text-sm resize-none
                           focus:outline-none focus:border-primary"
              />
            </div>

            {/* Cover Position */}
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                封面位置
              </label>
              <div className="flex gap-2">
                {([
                  { value: "top", label: "頂部" },
                  { value: "center", label: "中間" },
                  { value: "bottom", label: "底部" },
                ] as const).map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setCoverPosition(option.value)}
                    className={`flex-1 px-3 py-1.5 rounded-lg text-sm transition-colors
                               ${coverPosition === option.value
                                 ? "bg-primary text-white"
                                 : "bg-bg-elevated text-text-secondary hover:bg-bg-hover"
                               }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Editor Layout */}
            <div>
              <label className="text-sm font-medium text-text-secondary mb-2 block">
                編輯版面
              </label>
              <div className="flex gap-2">
                {([
                  { value: "single", label: "單欄" },
                  { value: "dual", label: "雙欄" },
                ] as const).map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setEditorLayout(option.value)}
                    className={`flex-1 px-3 py-1.5 rounded-lg text-sm transition-colors
                               ${editorLayout === option.value
                                 ? "bg-primary text-white"
                                 : "bg-bg-elevated text-text-secondary hover:bg-bg-hover"
                               }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              {editorLayout === "dual" && (
                <p className="text-xs text-text-muted mt-1.5">
                  圖片會顯示在左側，編輯區在右側
                </p>
              )}
            </div>

            {/* Attachments (Phase 3.4) */}
            {isEditing && (
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                  <Paperclip size={14} /> 附件
                  {attachments.length > 0 && (
                    <span className="text-xs bg-bg-elevated px-1.5 py-0.5 rounded">
                      {attachments.length}
                    </span>
                  )}
                </label>

                {/* Attachment List */}
                {attachments.length > 0 && (
                  <div className="space-y-1.5 mb-2">
                    {attachments.map((att) => (
                      <div
                        key={att.id}
                        className={`flex items-center gap-2 px-2 py-1.5 rounded-lg
                                   bg-bg-elevated text-text-secondary text-xs
                                   hover:bg-bg-hover group cursor-pointer
                                   ${
                                     att.is_auto_extracted
                                       ? "border-l-2 border-primary"
                                       : ""
                                   }`}
                        onClick={() =>
                          handleLoadAttachment(att.id, att.is_auto_extracted)
                        }
                        title={
                          att.is_auto_extracted
                            ? "點擊還原完整內容"
                            : "點擊查看附件"
                        }
                      >
                        <FileText
                          size={14}
                          className={`flex-shrink-0 ${
                            att.is_auto_extracted
                              ? "text-accent"
                              : "text-primary"
                          }`}
                        />
                        <span className="truncate flex-1" title={att.title}>
                          {att.title}
                          {att.is_auto_extracted && (
                            <span className="text-accent ml-1">(完整內容)</span>
                          )}
                        </span>
                        <span className="text-text-muted">
                          {(att.size_bytes / 1024).toFixed(0)}KB
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation(); // Prevent opening file
                            handleDeleteAttachment(att.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-danger
                                     transition-opacity"
                          title="刪除附件"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Upload Button */}
                <input
                  ref={attachmentInputRef}
                  type="file"
                  accept=".md,.txt,.markdown"
                  onChange={handleAttachmentSelect}
                  className="hidden"
                />
                <button
                  onClick={() => attachmentInputRef.current?.click()}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2
                             rounded-lg border border-dashed border-border-default
                             text-text-muted text-sm
                             hover:border-primary hover:text-primary
                             transition-colors"
                >
                  <Plus size={14} />
                  新增 .md 附件
                </button>
                <p className="text-xs text-text-muted mt-1.5">
                  支援拖曳 .md 檔案到編輯區
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </Modal>

    {/* History Modal */}
    {showHistory && (
      <Modal isOpen onClose={() => setShowHistory(false)} size="md">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <History size={20} className="text-warning" />
              歷史版本
            </h3>
            <button
              onClick={() => setShowHistory(false)}
              className="p-2 rounded-lg text-text-muted hover:bg-bg-hover"
            >
              <X size={18} />
            </button>
          </div>

          {historyVersions.length === 0 ? (
            <p className="text-text-muted text-center py-8">
              沒有歷史版本記錄
            </p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {historyVersions.map((version) => (
                <div
                  key={version.id}
                  className="p-4 rounded-lg bg-bg-elevated border border-border-subtle"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-text-primary">
                        {version.diff_summary || '內容變更'}
                      </p>
                      <p className="text-xs text-text-muted mt-1">
                        {new Date(version.created_at).toLocaleString('zh-TW')}
                      </p>
                    </div>
                    <button
                      onClick={() => restoreVersion(version.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                                 bg-primary/10 text-primary hover:bg-primary/20
                                 transition-colors"
                    >
                      <RotateCcw size={14} />
                      還原
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    )}
  </>
  );
}
