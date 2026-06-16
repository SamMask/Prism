import { useCallback } from 'react'
import { api } from '../../services/api'
import { toast } from '../../components/ui/Toast'
import { t } from '../../i18n'

// ---- HTML → Markdown conversion (pure function, no deps) ----
const BLOCK_TAGS = new Set(['p','div','br','h1','h2','h3','h4','h5','h6','li','tr'])

function nodeToMarkdown(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent || ''
  if (node.nodeType !== Node.ELEMENT_NODE) return ''

  const el = node as Element
  const tag = el.tagName.toLowerCase()

  if (tag === 'img') {
    const src = el.getAttribute('src')
    return src && (src.startsWith('http://') || src.startsWith('https://'))
      ? `\n![image](${src})\n`
      : ''
  }

  const inner = Array.from(el.childNodes).map(nodeToMarkdown).join('')
  if (tag === 'br') return '\n'
  if (tag === 'strong' || tag === 'b') return `**${inner}**`
  if (tag === 'em' || tag === 'i') return `*${inner}*`
  if (tag === 'a') { const href = el.getAttribute('href'); return href ? `[${inner}](${href})` : inner }
  if (tag.match(/^h[1-6]$/)) return '\n' + '#'.repeat(parseInt(tag[1])) + ' ' + inner + '\n'
  if (tag === 'li') return '\n- ' + inner
  if (BLOCK_TAGS.has(tag)) return '\n' + inner + '\n'
  return inner
}

function extractRemoteImageUrls(markdown: string): string[] {
  const urls: string[] = []
  const pattern = /!\[image\]\((https?:\/\/[^)]+)\)/g
  let m
  while ((m = pattern.exec(markdown)) !== null) urls.push(m[1])
  return urls
}

// Download remote images in background and swap URLs in content
async function downloadAndReplaceImages(
  urls: string[],
  setContent: React.Dispatch<React.SetStateAction<string>>
) {
  let successCount = 0, failCount = 0
  const urlMapping: Record<string, string> = {}

  await Promise.all(urls.map(async (url) => {
    try {
      const result = await api.downloadImageFromUrl(url, true)
      urlMapping[url] = result.url
      successCount++
    } catch {
      failCount++
    }
  }))

  if (successCount > 0) {
    setContent((prev) => {
      let updated = prev
      for (const url of urls) {
        if (urlMapping[url]) updated = updated.split(url).join(urlMapping[url])
      }
      return updated
    })
    toast.success(t('editor.uploadToast.downloadedImages', {
      success: successCount,
      failed: failCount > 0 ? t('editor.uploadToast.downloadFailedSuffix', { count: failCount }) : '',
    }))
  } else if (failCount > 0) {
    toast.warning(t('editor.uploadToast.downloadImagesFailed', { count: failCount }))
  }
}

// ---- Hook ----
export function usePasteHandler(
  setContent: React.Dispatch<React.SetStateAction<string>>
) {
  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const htmlData = e.clipboardData.getData('text/html')
    const textData = e.clipboardData.getData('text/plain')

    // Priority 1: Direct image paste (screenshot / copied image file)
    for (const item of e.clipboardData.items) {
      if (!item.type.startsWith('image/')) continue
      e.preventDefault()
      const file = item.getAsFile()
      if (!file) continue
      try {
        toast.info(t('editor.uploadToast.imageUploading'))
        const result = await api.uploadImage(file)
        setContent((prev) => prev + '\n' + `![image](${result.url})`)
        toast.success(t('editor.uploadToast.imageUploaded'))
      } catch {
        toast.error(t('editor.uploadToast.imageUploadFailed'))
      }
      return
    }

    // Priority 2: HTML with embedded images — insert immediately, swap URLs in background
    if (htmlData && htmlData.includes('<img')) {
      e.preventDefault()
      try {
        const doc = new DOMParser().parseFromString(htmlData, 'text/html')
        const markdown = nodeToMarkdown(doc.body).replace(/\n{3,}/g, '\n\n').trim()
        setContent((prev) => (prev.trim() ? prev + '\n\n' + markdown : markdown))

        const remoteUrls = extractRemoteImageUrls(markdown)
        if (remoteUrls.length > 0) {
          // Fire-and-forget: runs after current event loop
          downloadAndReplaceImages(remoteUrls, setContent)
        }
      } catch {
        setContent((prev) => prev + '\n' + textData)
        toast.error(t('editor.uploadToast.htmlParseFailed'))
      }
      return
    }

    // Priority 3: Plain text — let browser handle natively (no preventDefault)
  }, [setContent])

  return { handlePaste }
}
