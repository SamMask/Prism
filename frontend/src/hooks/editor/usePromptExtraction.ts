import { useState, useEffect, useCallback } from 'react'
import { api } from '../../services/api'
import { toast } from '../../components/ui/Toast'
import { t } from '../../i18n'

const IMAGE_PATTERN_SINGLE =
  /!\[.*?\]\((\/static\/uploads\/[^)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/
const IMAGE_PATTERN_GLOBAL =
  /!\[.*?\]\((\/static\/uploads\/[^)]+)\)|<img[^>]+src=["'](\/static\/uploads\/[^"']+)["']/g

export function usePromptExtraction(content: string) {
  const [hasAIPrompt, setHasAIPrompt] = useState(false)
  const [isCheckingPrompt, setIsCheckingPrompt] = useState(false)

  useEffect(() => {
    const checkForPrompt = async () => {
      const match = content?.match(IMAGE_PATTERN_SINGLE)
      if (!match) { setHasAIPrompt(false); return }
      const imagePath = match[1] || match[2]
      if (!imagePath) { setHasAIPrompt(false); return }
      try {
        setIsCheckingPrompt(true)
        const result = await api.extractImagePrompt(imagePath)
        setHasAIPrompt(result.has_prompt)
      } catch {
        setHasAIPrompt(false)
      } finally {
        setIsCheckingPrompt(false)
      }
    }
    const timer = setTimeout(checkForPrompt, 500)
    return () => clearTimeout(timer)
  }, [content])

  const handleCopyPrompt = useCallback(async () => {
    const matches: string[] = []
    let m
    const pattern = new RegExp(IMAGE_PATTERN_GLOBAL.source, 'g')
    while ((m = pattern.exec(content || '')) !== null) {
      matches.push(m[1] || m[2])
    }
    if (matches.length === 0) { toast.warning(t('editor.promptExtraction.noImage')); return }

    for (const imagePath of matches) {
      try {
        const result = await api.extractImagePrompt(imagePath)
        if (result.has_prompt && result.prompt) {
          let textToCopy = result.prompt
          if (result.negative_prompt) textToCopy += `\n\nNegative prompt: ${result.negative_prompt}`
          await navigator.clipboard.writeText(textToCopy)
          toast.success(t('editor.promptExtraction.copiedPrompt', { source: result.source || 'AI' }))
          return
        }
      } catch { /* try next image */ }
    }
    toast.warning(t('editor.promptExtraction.noPrompt'))
  }, [content])

  return { hasAIPrompt, isCheckingPrompt, handleCopyPrompt }
}
