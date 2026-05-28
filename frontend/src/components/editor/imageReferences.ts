export function extractImageReferences(content: string): string[] {
  const found: string[] = []
  const patterns = [
    /!\[[^\]]*\]\(\s*([^\s)]+)(?:\s+["'][^"']*["'])?\s*\)/g,
    /<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi,
  ]

  for (const pattern of patterns) {
    let match
    while ((match = pattern.exec(content)) !== null) {
      if (!found.includes(match[1])) found.push(match[1])
    }
  }

  return found
}

export function removeImageReferences(content: string, urls: string[]): string {
  let nextContent = content

  for (const url of urls) {
    const escapedUrl = escapeRegExp(url)
    const markdownImage = new RegExp(
      `\\n?!\\[[^\\]]*\\]\\(\\s*${escapedUrl}(?:\\s+["'][^"']*["'])?\\s*\\)\\n?`,
      'g'
    )
    const htmlImage = new RegExp(
      `\\n?<img\\b[^>]*\\bsrc=["']${escapedUrl}["'][^>]*>\\n?`,
      'gi'
    )

    nextContent = nextContent
      .replace(markdownImage, '\n')
      .replace(htmlImage, '\n')
  }

  return nextContent.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
