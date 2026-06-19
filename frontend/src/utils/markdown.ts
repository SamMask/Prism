import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const SAFE_MARKDOWN_URI = /^(?:(?:https?|mailto|tel):|\/(?!\/)|\.{0,2}\/|#|(?!(?:[a-z][a-z0-9+.-]*:|\/\/))[^\s:]+$)/i

const MARKDOWN_SANITIZE_CONFIG = {
  USE_PROFILES: { html: true },
  FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'svg', 'math', 'style', 'link', 'meta', 'base'],
  ALLOW_DATA_ATTR: false,
  ALLOWED_URI_REGEXP: SAFE_MARKDOWN_URI,
}

function escapeHTML(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function sanitizeMarkdownHTML(html: string): string {
  return DOMPurify.sanitize(html, MARKDOWN_SANITIZE_CONFIG)
}

export function renderSafeMarkdown(markdown: string, emptyContent = ''): string {
  if (!markdown.trim()) {
    return sanitizeMarkdownHTML(`<p class="text-text-muted">${escapeHTML(emptyContent)}</p>`)
  }
  try {
    return sanitizeMarkdownHTML(marked(markdown) as string)
  } catch {
    return sanitizeMarkdownHTML(`<p>${escapeHTML(markdown)}</p>`)
  }
}
