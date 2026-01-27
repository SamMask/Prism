import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { Modal, toast } from "./ui";
import { Note, api, Tag } from "../services/api";
import { useAppStore } from "../stores/appStore";
import { Image, X, History, RotateCcw } from "lucide-react";
import { EditorToolbar } from "./editor/EditorToolbar";
import { EditorSidebar } from "./editor/EditorSidebar";
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
  const { fetchNotes } = useAppStore();

  // Form State
  const [title, setTitle] = useState(note?.title || "");
  const [content, setContent] = useState(note?.content || "");
  const [categoryId, setCategoryId] = useState<number | undefined>(() => {
    if (note) return note.category_id;
    const saved = localStorage.getItem("quickAddDefaultCategory");
    return saved ? Number(saved) : undefined;
  });
  const [selectedTags, setSelectedTags] = useState<Tag[]>(note?.tags || []);
  const [remarks, setRemarks] = useState(note?.remarks || "");
  const [coverPosition, setCoverPosition] = useState<
    "top" | "center" | "bottom"
  >(note?.cover_position || "center");
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
  // Optimized: Text appears immediately, images download in background
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
    // Optimized: Immediately insert text with image placeholders, then download images in background
    if (htmlData && htmlData.includes("<img")) {
      e.preventDefault();

      try {
        // Parse HTML to extract images and convert to structured content
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlData, "text/html");

        // Create a map of image positions and their URLs
        const imageMap = new Map<string, string>(); // placeholder -> original URL
        let placeholderIndex = 0;

        // Walk through the DOM and build markdown with image placeholders in correct positions
        const processNode = (node: Node): string => {
          if (node.nodeType === Node.TEXT_NODE) {
            return node.textContent || "";
          }

          if (node.nodeType === Node.ELEMENT_NODE) {
            const element = node as Element;
            const tagName = element.tagName.toLowerCase();

            // Handle images - insert placeholder that will be replaced later
            if (tagName === "img") {
              const src = element.getAttribute("src");
              if (
                src &&
                (src.startsWith("http://") || src.startsWith("https://"))
              ) {
                const placeholder = `__IMG_PLACEHOLDER_${placeholderIndex}__`;
                imageMap.set(placeholder, src);
                placeholderIndex++;
                return `\n![image](${src})\n`;
              }
              return "";
            }

            // Handle block elements - add line breaks
            const blockElements = [
              "p",
              "div",
              "br",
              "h1",
              "h2",
              "h3",
              "h4",
              "h5",
              "h6",
              "li",
              "tr",
            ];
            const isBlock = blockElements.includes(tagName);

            // Process children
            let content = "";
            for (const child of Array.from(element.childNodes)) {
              content += processNode(child);
            }

            // Add appropriate formatting
            if (tagName === "br") return "\n";
            if (tagName === "strong" || tagName === "b")
              return `**${content}**`;
            if (tagName === "em" || tagName === "i") return `*${content}*`;
            if (tagName === "a") {
              const href = element.getAttribute("href");
              if (href) return `[${content}](${href})`;
              return content;
            }
            if (tagName.match(/^h[1-6]$/)) {
              const level = parseInt(tagName[1]);
              return "\n" + "#".repeat(level) + " " + content + "\n";
            }
            if (tagName === "li") return "\n- " + content;
            if (isBlock) return "\n" + content + "\n";

            return content;
          }

          return "";
        };

        // Process the DOM to get markdown with images in correct positions
        let markdown = processNode(doc.body);

        // Clean up excessive newlines
        markdown = markdown.replace(/\n{3,}/g, "\n\n").trim();

        // Find all remote image URLs in the content
        const imageUrlPattern = /!\[image\]\((https?:\/\/[^)]+)\)/g;
        const remoteImages: { match: string; url: string }[] = [];
        let match;
        while ((match = imageUrlPattern.exec(markdown)) !== null) {
          remoteImages.push({ match: match[0], url: match[1] });
        }

        // Immediately insert the content with original URLs
        setContent((prev) => {
          if (prev.trim()) {
            return prev + "\n\n" + markdown;
          }
          return markdown;
        });

        // If there are remote images, download them in the background
        if (remoteImages.length > 0) {
          // Start background download (no await, non-blocking)
          (async () => {
            let successCount = 0;
            let failCount = 0;
            const urlMapping: Record<string, string> = {};

            // Download all images in parallel for speed
            const downloadPromises = remoteImages.map(async ({ url }) => {
              try {
                const result = await api.downloadImageFromUrl(url, true);
                urlMapping[url] = result.url;
                successCount++;
              } catch (error) {
                console.error(`Background download failed: ${url}`, error);
                failCount++;
              }
            });

            await Promise.all(downloadPromises);

            // Replace URLs in content with local URLs
            if (successCount > 0) {
              setContent((prev) => {
                let updated = prev;
                for (const { url } of remoteImages) {
                  if (urlMapping[url]) {
                    // Replace all occurrences of this URL
                    updated = updated.split(url).join(urlMapping[url]);
                  }
                }
                return updated;
              });

              // Show subtle success notification
              toast.success(
                `已下載 ${successCount} 張圖片${
                  failCount > 0 ? ` (${failCount} 張失敗)` : ""
                }`
              );
            } else if (failCount > 0) {
              toast.warning(`圖片下載失敗 ${failCount} 張，保留原始 URL`);
            }
          })();
        }
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
        const savedVisionModel =
          localStorage.getItem("ai_vision_model") || "llava";
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
      const imagePattern =
        /!\[.*?\]\((\/static\/uploads\/[^\)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/;
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
    const imagePattern =
      /!\[.*?\]\((\/static\/uploads\/[^\)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/g;
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
    const newText =
      content.substring(0, start) +
      prefix +
      selectedText +
      suffix +
      content.substring(end);

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
          <EditorToolbar
            isEditing={isEditing}
            isAnalyzing={isAnalyzing}
            onAiAnalyze={handleAiAnalyze}
            hasAIPrompt={hasAIPrompt}
            isCheckingPrompt={isCheckingPrompt}
            onCopyPrompt={handleCopyPrompt}
            isLoadingHistory={isLoadingHistory}
            onLoadHistory={loadHistory}
            isPreview={isPreview}
            onTogglePreview={() => setIsPreview(!isPreview)}
            isSaving={isSaving}
            onSave={handleSave}
            onClose={onClose}
          />

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
                  const imagePattern =
                    /!\[.*?\]\((\/static\/uploads\/[^\)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/g;
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
                        <p className="text-xs mt-1">
                          在內容中加入圖片後會顯示在此
                        </p>
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
            <EditorSidebar
              aiSuggestions={aiSuggestions}
              aiDescription={aiDescription}
              onAddAiTag={addAiTag}
              categoryId={categoryId}
              onChangeCategory={setCategoryId}
              tagInput={tagInput}
              onTagInputChange={setTagInput}
              onTagInputKeyDown={handleTagKeyDown}
              selectedTags={selectedTags}
              onRemoveTag={removeTag}
              sourceUrls={sourceUrls}
              urlInput={urlInput}
              onUrlInputChange={setUrlInput}
              onUrlInputKeyDown={(e) => {
                if (e.key === "Enter" && urlInput.trim()) {
                  e.preventDefault();
                  let url = urlInput.trim();
                  if (
                    !url.startsWith("http://") &&
                    !url.startsWith("https://")
                  ) {
                    url = "https://" + url;
                  }
                  if (!sourceUrls.includes(url)) {
                    setSourceUrls([...sourceUrls, url]);
                  }
                  setUrlInput("");
                }
              }}
              onUrlInputBlur={() => {
                if (urlInput.trim()) {
                  let url = urlInput.trim();
                  if (
                    !url.startsWith("http://") &&
                    !url.startsWith("https://")
                  ) {
                    url = "https://" + url;
                  }
                  if (!sourceUrls.includes(url)) {
                    setSourceUrls([...sourceUrls, url]);
                  }
                  setUrlInput("");
                }
              }}
              onRemoveUrl={(index) =>
                setSourceUrls(sourceUrls.filter((_, i) => i !== index))
              }
              remarks={remarks}
              onChangeRemarks={setRemarks}
              coverPosition={coverPosition}
              onChangeCoverPosition={setCoverPosition}
              editorLayout={editorLayout}
              onChangeEditorLayout={setEditorLayout}
              isEditing={isEditing}
              attachments={attachments}
              onLoadAttachment={handleLoadAttachment}
              onDeleteAttachment={handleDeleteAttachment}
              onUploadAttachment={handleAttachmentSelect}
            />
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
                          {version.diff_summary || "內容變更"}
                        </p>
                        <p className="text-xs text-text-muted mt-1">
                          {new Date(version.created_at).toLocaleString("zh-TW")}
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
