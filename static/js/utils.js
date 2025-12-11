/**
 * Local Insight Utils
 * 通用工具函式庫
 */

// Debounce 函數 (用於防止頻繁觸發搜尋)
export function debounce(func, wait) {
  let timeout;
  return function (...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), wait);
  };
}

// 格式化日期時間 (ISO to Local String)
export function formatDate(isoString) {
  if (!isoString) return "";
  return new Date(isoString).toLocaleDateString("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// 從 Markdown 內容中提取第一張圖片 URL
export function extractFirstImage(content) {
  if (!content) return null;

  // Match Markdown image syntax: ![alt](url)
  const markdownMatch = content.match(/!\[.*?\]\((.*?)\)/);
  if (markdownMatch) {
    return markdownMatch[1];
  }

  // Also match HTML img src
  const htmlMatch = content.match(/<img[^>]+src=["']([^"']+)["']/i);
  if (htmlMatch) {
    return htmlMatch[1];
  }

  return null;
}

// 轉換為縮圖 URL (Image Virtualization)
export function getThumbUrl(originalUrl) {
  if (!originalUrl) return null;

  // 只處理本地上傳的圖片 /static/uploads/
  if (!originalUrl.startsWith("/static/uploads/")) {
    return originalUrl;
  }

  // 移除副檔名，加上 _thumb.webp
  // v0.9.0: 防止重複疊加 _thumb (例如 _thumb_thumb.webp)
  if (originalUrl.endsWith("_thumb.webp")) {
    return originalUrl;
  }

  const lastDotIndex = originalUrl.lastIndexOf(".");
  if (lastDotIndex === -1) return originalUrl;

  return originalUrl.substring(0, lastDotIndex) + "_thumb.webp";
}

// 驗證圖片檔案
export function validateImageFile(file) {
  const allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"];

  if (!allowedTypes.includes(file.type)) {
    return {
      valid: false,
      message: "不支援的檔案格式。請上傳 JPG、PNG、WebP 或 GIF 圖片。",
    };
  }

  const maxSize = 5 * 1024 * 1024; // 5MB
  if (file.size > maxSize) {
    return { valid: false, message: "檔案過大。請上傳 5MB 以下的圖片。" };
  }

  return { valid: true };
}
