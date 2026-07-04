import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const SAFE_MARKDOWN_URI = /^(?:(?:https?|mailto|tel):|\/(?!\/)|\.{0,2}\/|#|(?!(?:[a-z][a-z0-9+.-]*:|\/\/))[^\s:]+$)/i
const GITHUB_ALERTS: Record<string, { className: string; title: string }> = {
  NOTE: { className: 'note', title: 'Note' },
  TIP: { className: 'tip', title: 'Tip' },
  IMPORTANT: { className: 'important', title: 'Important' },
  WARNING: { className: 'warning', title: 'Warning' },
  CAUTION: { className: 'caution', title: 'Caution' },
}
const MARKFORGE_BOXES: Record<string, string> = {
  info: 'Info',
  success: 'Success',
  warning: 'Warning',
}

const MARKDOWN_SANITIZE_CONFIG = {
  USE_PROFILES: { html: true },
  FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'svg', 'math', 'style', 'link', 'meta', 'base'],
  ADD_TAGS: ['mark', 'aside', 'details', 'summary', 'button'],
  ADD_ATTR: ['aria-label', 'checked', 'class', 'disabled', 'href', 'id', 'title', 'type'],
  ALLOW_DATA_ATTR: false,
  ALLOWED_URI_REGEXP: SAFE_MARKDOWN_URI,
}

export interface MarkdownHeading {
  id: string
  text: string
  depth: number
}

export interface MarkdownRenderOptions {
  codeCopyLabel?: string
  codeCopyAriaLabel?: string
}

export interface MarkdownCodeCopyOptions {
  copiedLabel?: string
  failedLabel?: string
}

interface FootnoteDefinition {
  id: string
  text: string
}

interface FootnoteReferences {
  markdown: string
  usedIds: string[]
}

function escapeHTML(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function isFenceLine(line: string): boolean {
  return /^(```|~~~)/.test(line.trim())
}

function transformOutsideFences(markdown: string, transform: (line: string) => string): string {
  let inFence = false
  return markdown
    .split('\n')
    .map((line) => {
      if (isFenceLine(line)) {
        inFence = !inFence
        return line
      }
      return inFence ? line : transform(line)
    })
    .join('\n')
}

function applyInlineMarkForgeSyntax(markdown: string): string {
  return transformOutsideFences(markdown, (line) => (
    line.replace(/==([^=\n]+)==/g, (_match, text: string) => `<mark>${escapeHTML(text)}</mark>`)
  ))
}

function extractFootnoteDefinitions(markdown: string): { markdown: string; definitions: FootnoteDefinition[] } {
  const definitions: FootnoteDefinition[] = []
  const keptLines: string[] = []
  let inFence = false

  markdown.split('\n').forEach((line) => {
    if (isFenceLine(line)) {
      inFence = !inFence
      keptLines.push(line)
      return
    }

    const match = inFence ? null : line.match(/^\[\^([^\]\s]+)\]:\s*(.*)$/)
    if (!match) {
      keptLines.push(line)
      return
    }

    if (!definitions.some((definition) => definition.id === match[1])) {
      definitions.push({ id: match[1], text: match[2] })
    }
  })

  return { markdown: keptLines.join('\n'), definitions }
}

function slugify(value: string, fallback: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

  return slug || fallback
}

function makeUniqueSlug(base: string, seen: Map<string, number>): string {
  const count = seen.get(base) ?? 0
  seen.set(base, count + 1)
  return count === 0 ? base : `${base}-${count + 1}`
}

function footnoteSlug(id: string): string {
  return slugify(id, 'footnote')
}

function applyFootnoteReferences(markdown: string, definitions: FootnoteDefinition[]): FootnoteReferences {
  const usedIds: string[] = []
  const knownIds = new Set(definitions.map((definition) => definition.id))
  const nextMarkdown = transformOutsideFences(markdown, (line) => (
    line.replace(/\[\^([^\]\s]+)\]/g, (match, id: string) => {
      if (!knownIds.has(id)) return match
      if (!usedIds.includes(id)) usedIds.push(id)
      const index = usedIds.indexOf(id) + 1
      const slug = footnoteSlug(id)
      return `<sup id="fnref-${slug}" class="prism-footnote-ref"><a href="#fn-${slug}">${index}</a></sup>`
    })
  ))

  return { markdown: nextMarkdown, usedIds }
}

function renderMarkdownFragment(markdown: string): string {
  if (!markdown.trim()) return ''
  try {
    return marked(applyInlineMarkForgeSyntax(markdown)) as string
  } catch {
    return `<p>${escapeHTML(markdown)}</p>`
  }
}

function renderInlineMarkdown(markdown: string): string {
  try {
    return marked.parseInline(applyInlineMarkForgeSyntax(markdown)) as string
  } catch {
    return escapeHTML(markdown)
  }
}

function renderCallout(kind: string, title: string, body: string): string {
  return [
    `<aside class="prism-callout prism-callout-${kind}">`,
    `<p class="prism-callout-title">${escapeHTML(title)}</p>`,
    renderMarkdownFragment(body),
    '</aside>',
  ].join('\n')
}

function renderDetails(title: string, body: string): string {
  return [
    '<details class="prism-details">',
    `<summary>${escapeHTML(title || 'Details')}</summary>`,
    renderMarkdownFragment(body),
    '</details>',
  ].join('\n')
}

function collectContainerBody(lines: string[], startIndex: number): { body: string; endIndex: number } {
  const body: string[] = []
  let index = startIndex + 1

  while (index < lines.length && lines[index].trim() !== ':::') {
    body.push(lines[index])
    index += 1
  }

  return { body: body.join('\n'), endIndex: Math.min(index, lines.length - 1) }
}

function transformMarkForgeContainers(markdown: string): string {
  const lines = markdown.split('\n')
  const output: string[] = []
  let inFence = false

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    const trimmed = line.trim()

    if (isFenceLine(line)) {
      inFence = !inFence
      output.push(line)
      continue
    }

    if (!inFence) {
      const alertMatch = line.match(/^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$/i)
      if (alertMatch) {
        const alert = GITHUB_ALERTS[alertMatch[1].toUpperCase()]
        const body: string[] = []
        let nextIndex = index + 1

        while (nextIndex < lines.length && /^>\s?/.test(lines[nextIndex])) {
          body.push(lines[nextIndex].replace(/^>\s?/, ''))
          nextIndex += 1
        }

        output.push(renderCallout(alert.className, alert.title, body.join('\n')))
        index = nextIndex - 1
        continue
      }

      const boxMatch = trimmed.match(/^:::markforge-box(?:\s+(info|success|warning))?\s*$/i)
      if (boxMatch) {
        const kind = (boxMatch[1] || 'info').toLowerCase()
        const { body, endIndex } = collectContainerBody(lines, index)
        output.push(renderCallout(kind, MARKFORGE_BOXES[kind], body))
        index = endIndex
        continue
      }

      const detailsMatch = trimmed.match(/^:::markforge-details(?:\s+(.+))?\s*$/i)
      if (detailsMatch) {
        const { body, endIndex } = collectContainerBody(lines, index)
        output.push(renderDetails(detailsMatch[1] || 'Details', body))
        index = endIndex
        continue
      }
    }

    output.push(line)
  }

  return output.join('\n')
}

function renderFootnotes(definitions: FootnoteDefinition[], usedIds: string[]): string {
  if (usedIds.length === 0) return ''
  const items = usedIds
    .map((id) => definitions.find((definition) => definition.id === id))
    .filter((definition): definition is FootnoteDefinition => Boolean(definition))
    .map((definition) => {
      const slug = footnoteSlug(definition.id)
      return `<li id="fn-${slug}">${renderInlineMarkdown(definition.text)}</li>`
    })
    .join('\n')

  return `<section class="prism-footnotes"><ol>${items}</ol></section>`
}

function prepareMarkdown(markdown: string): string {
  const footnoteState = extractFootnoteDefinitions(markdown)
  const withInlineSyntax = applyInlineMarkForgeSyntax(footnoteState.markdown)
  const withContainers = transformMarkForgeContainers(withInlineSyntax)
  const withReferences = applyFootnoteReferences(withContainers, footnoteState.definitions)
  const footnotes = renderFootnotes(footnoteState.definitions, withReferences.usedIds)

  return footnotes ? `${withReferences.markdown}\n\n${footnotes}` : withReferences.markdown
}

function normalizeHeadingText(value: string): string {
  return value
    .replace(/!\[[^\]]*]\([^)]+\)/g, '')
    .replace(/\[([^\]]+)]\([^)]+\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/<[^>]*>/g, '')
    .replace(/[*_~=#]/g, '')
    .trim()
}

export function extractMarkdownHeadings(markdown: string): MarkdownHeading[] {
  const seen = new Map<string, number>()
  const headings: MarkdownHeading[] = []
  let inFence = false

  markdown.split('\n').forEach((line) => {
    if (isFenceLine(line)) {
      inFence = !inFence
      return
    }
    if (inFence) return

    const match = line.match(/^(#{1,6})\s+(.+?)\s*#*\s*$/)
    if (!match) return

    const text = normalizeHeadingText(match[2])
    if (!text) return

    const base = slugify(text, `heading-${headings.length + 1}`)
    headings.push({
      id: makeUniqueSlug(base, seen),
      text,
      depth: match[1].length,
    })
  })

  return headings
}

function enhanceRenderedMarkdown(html: string, options: MarkdownRenderOptions = {}): string {
  if (typeof document === 'undefined') return html

  const template = document.createElement('template')
  template.innerHTML = html
  const seenHeadings = new Map<string, number>()

  template.content.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach((heading, index) => {
    const text = heading.textContent?.trim() || ''
    const base = slugify(text, `heading-${index + 1}`)
    const id = makeUniqueSlug(heading.id || base, seenHeadings)
    heading.id = id

    if (!heading.querySelector('.prism-heading-anchor')) {
      const anchor = document.createElement('a')
      anchor.className = 'prism-heading-anchor'
      anchor.href = `#${id}`
      anchor.setAttribute('aria-label', 'Link to heading')
      anchor.textContent = '#'
      heading.appendChild(anchor)
    }
  })

  template.content.querySelectorAll('table').forEach((table) => {
    if (table.parentElement?.classList.contains('prism-table-wrapper')) return
    const wrapper = document.createElement('div')
    wrapper.className = 'prism-table-wrapper'
    table.parentElement?.insertBefore(wrapper, table)
    wrapper.appendChild(table)
  })

  template.content.querySelectorAll('pre').forEach((pre) => {
    if (pre.parentElement?.classList.contains('prism-code-block')) return
    const wrapper = document.createElement('div')
    wrapper.className = 'prism-code-block'
    const copyButton = document.createElement('button')
    copyButton.type = 'button'
    copyButton.className = 'prism-code-copy'
    copyButton.setAttribute('aria-label', options.codeCopyAriaLabel || options.codeCopyLabel || 'Copy code')
    copyButton.textContent = options.codeCopyLabel || 'Copy'
    pre.parentElement?.insertBefore(wrapper, pre)
    wrapper.appendChild(copyButton)
    wrapper.appendChild(pre)
  })

  template.content.querySelectorAll('li > input[type="checkbox"]').forEach((input) => {
    const listItem = input.closest('li')
    const list = listItem?.closest('ul')
    const taskBox = document.createElement('span')
    taskBox.className = input.hasAttribute('checked')
      ? 'prism-task-box prism-task-box-checked'
      : 'prism-task-box'
    taskBox.setAttribute('aria-hidden', 'true')
    input.replaceWith(taskBox)
    listItem?.classList.add('prism-task-item')
    list?.classList.add('prism-task-list')
  })

  return template.innerHTML
}

function flashCodeCopyButton(button: HTMLButtonElement, label: string): void {
  const original = button.textContent || 'Copy'
  button.textContent = label
  window.setTimeout(() => {
    button.textContent = original
  }, 1200)
}

export async function copyMarkdownCodeFromClick(
  target: EventTarget | null,
  options: MarkdownCodeCopyOptions = {},
): Promise<boolean> {
  const element = target instanceof Element ? target : null
  const button = element?.closest<HTMLButtonElement>('button.prism-code-copy')
  if (!button) return false

  const code = button.closest('.prism-code-block')?.querySelector('pre code')
  const codeText = code?.textContent ?? ''
  if (!codeText) return true

  try {
    await navigator.clipboard.writeText(codeText)
    flashCodeCopyButton(button, options.copiedLabel || 'Copied')
  } catch (error) {
    flashCodeCopyButton(button, options.failedLabel || 'Failed')
    throw error
  }

  return true
}

export function sanitizeMarkdownHTML(html: string): string {
  return DOMPurify.sanitize(html, MARKDOWN_SANITIZE_CONFIG)
}

export function renderSafeMarkdown(markdown: string, emptyContent = '', options: MarkdownRenderOptions = {}): string {
  if (!markdown.trim()) {
    return sanitizeMarkdownHTML(`<p class="text-text-muted">${escapeHTML(emptyContent)}</p>`)
  }
  try {
    return sanitizeMarkdownHTML(enhanceRenderedMarkdown(marked(prepareMarkdown(markdown)) as string, options))
  } catch {
    return sanitizeMarkdownHTML(`<p>${escapeHTML(markdown)}</p>`)
  }
}
