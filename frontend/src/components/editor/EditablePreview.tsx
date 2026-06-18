import { useMemo, useState } from 'react'
import { marked } from 'marked'
import { Edit3, Trash2 } from 'lucide-react'
import { removeImageReferences } from './imageReferences'
import { useTranslation } from '../../hooks/useTranslation'
import { ImageLightbox, type LightboxImage } from '../ImageLightbox'

interface EditablePreviewProps {
  content: string
  coverImage: string | undefined
  onContentChange: (newContent: string) => void
  onSetCover: (url: string | null) => void
}

interface PreviewBlock {
  kind: 'text' | 'image'
  source: string
  start: number
  end: number
  imageUrl?: string
}

export function EditablePreview({
  content,
  coverImage,
  onContentChange,
  onSetCover,
}: EditablePreviewProps) {
  const { t } = useTranslation()
  const [activeBlockStart, setActiveBlockStart] = useState<number | null>(null)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const blocks = useMemo(() => splitPreviewBlocks(content), [content])
  const previewImages = useMemo<LightboxImage[]>(
    () => blocks
      .filter((block): block is PreviewBlock & { imageUrl: string } => (
        block.kind === 'image' && Boolean(block.imageUrl)
      ))
      .map((block, index) => ({
        src: block.imageUrl,
        alt: t('editor.noteEditor.imageAlt', { index: index + 1 }),
      })),
    [blocks, t],
  )

  const updateBlock = (block: PreviewBlock, nextSource: string) => {
    onContentChange(content.slice(0, block.start) + nextSource + content.slice(block.end))
  }

  const removeImage = (url: string) => {
    onContentChange(removeImageReferences(content, [url]))
    if (coverImage === url) onSetCover(null)
  }

  const openLightboxForSource = (src: string) => {
    const imageIndex = previewImages.findIndex((image) => image.src === src)
    if (imageIndex >= 0) setLightboxIndex(imageIndex)
  }

  if (blocks.length === 0) {
    return (
      <textarea
        value={content}
        onChange={(event) => onContentChange(event.target.value)}
        placeholder={t('editor.preview.contentPlaceholder')}
        className="flex-1 min-h-[16rem] bg-transparent border-none outline-none resize-none text-text-primary placeholder-text-muted font-mono text-sm leading-relaxed"
      />
    )
  }

  return (
    <>
      <div className="flex-1 space-y-4">
        {blocks.map((block) => {
          if (block.kind === 'image' && block.imageUrl) {
            return (
              <figure
                key={`${block.kind}-${block.start}`}
                data-testid="preview-image-block"
                className="relative group inline-flex min-h-20 min-w-20 max-w-full items-center justify-center rounded-lg border border-border-subtle bg-bg-elevated/40 overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => openLightboxForSource(block.imageUrl as string)}
                  data-testid="preview-image-lightbox-trigger"
                  className="block max-w-full cursor-zoom-in"
                  aria-label={t('reading.lightboxOpenImage')}
                  title={t('reading.lightboxOpenImage')}
                >
                  <img
                    src={block.imageUrl}
                    alt="preview"
                    className="max-h-96 max-w-full object-contain"
                  />
                </button>
                <button
                  type="button"
                  onClick={() => removeImage(block.imageUrl as string)}
                  data-testid="preview-remove-image"
                  className="absolute top-2 right-2 z-10 p-2 rounded-lg bg-danger/90 text-white opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                  title={t('editor.preview.removeImageReference')}
                >
                  <Trash2 size={16} />
                </button>
              </figure>
            )
          }

          const isActive = activeBlockStart === block.start
          if (isActive) {
            return (
              <textarea
                key={`${block.kind}-${block.start}`}
                value={block.source}
                onChange={(event) => updateBlock(block, event.target.value)}
                onBlur={() => setActiveBlockStart(null)}
                autoFocus
                className="w-full min-h-[7rem] p-3 rounded-lg bg-bg-elevated border border-primary outline-none resize-y text-text-primary font-mono text-sm leading-relaxed"
              />
            )
          }

          return (
            <section
              key={`${block.kind}-${block.start}`}
              data-testid="preview-text-block"
              className="relative group rounded-lg border border-transparent hover:border-border-subtle hover:bg-bg-elevated/30 transition-colors"
            >
              <button
                type="button"
                onClick={() => setActiveBlockStart(block.start)}
                data-testid="preview-edit-block"
                className="absolute top-2 right-2 p-1.5 rounded-md bg-bg-elevated text-text-muted opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-text-primary transition-all"
                title={t('editor.preview.editBlock')}
              >
                <Edit3 size={14} />
              </button>
              <div
                className="pr-10"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(block.source) }}
              />
            </section>
          )
        })}
      </div>
      {lightboxIndex !== null && (
        <ImageLightbox
          images={previewImages}
          activeIndex={lightboxIndex}
          onActiveIndexChange={setLightboxIndex}
          onClose={() => setLightboxIndex(null)}
        />
      )}
    </>
  )
}

function renderMarkdown(markdown: string): string {
  if (!markdown.trim()) return ''
  try {
    marked.setOptions({ breaks: true, gfm: true })
    return marked(markdown) as string
  } catch {
    return markdown
  }
}

function splitPreviewBlocks(content: string): PreviewBlock[] {
  const blocks: PreviewBlock[] = []
  const lines = content.split('\n')
  let offset = 0
  let textStart: number | null = null
  let textSource = ''
  let textEnd = 0
  let isFence = false

  const flushText = () => {
    if (textStart === null || !textSource.trim()) {
      textStart = null
      textSource = ''
      return
    }

    blocks.push({
      kind: 'text',
      source: textSource,
      start: textStart,
      end: textEnd,
    })
    textStart = null
    textSource = ''
  }

  for (let index = 0; index < lines.length; index += 1) {
    const hasNewline = index < lines.length - 1
    const rawLine = `${lines[index]}${hasNewline ? '\n' : ''}`
    const lineStart = offset
    const lineEnd = offset + rawLine.length
    const trimmed = lines[index].trim()
    const imageUrl = isFence ? null : getStandaloneImageUrl(trimmed)

    if (imageUrl) {
      flushText()
      blocks.push({
        kind: 'image',
        source: rawLine,
        start: lineStart,
        end: lineEnd,
        imageUrl,
      })
    } else {
      if (textStart === null) textStart = lineStart
      textSource += rawLine
      textEnd = lineEnd

      if (!isFence && trimmed === '') flushText()
    }

    if (trimmed.startsWith('```')) isFence = !isFence
    offset = lineEnd
  }

  flushText()
  return blocks
}

function getStandaloneImageUrl(line: string): string | null {
  const markdownMatch = line.match(/^!\[[^\]]*\]\(([^)\s]+)(?:\s+["'][^"']*["'])?\)$/)
  if (markdownMatch) return markdownMatch[1]

  const htmlMatch = line.match(/^<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>$/i)
  return htmlMatch?.[1] ?? null
}
