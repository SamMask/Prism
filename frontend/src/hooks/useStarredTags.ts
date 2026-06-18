import { useCallback, useEffect, useMemo, useState } from 'react'

export const STARRED_TAG_IDS_STORAGE_KEY = 'prism.starredTags.v1'
export const STARRED_TAGS_CHANGED_EVENT = 'prism:starred-tags-changed'

type TagLike = {
  id: number
}

function normalizeStarredTagIds(value: unknown): number[] {
  if (!Array.isArray(value)) return []

  const seen = new Set<number>()
  const ids: number[] = []

  for (const item of value) {
    const id = typeof item === 'number' ? item : Number(item)
    if (!Number.isInteger(id) || id <= 0 || seen.has(id)) continue
    seen.add(id)
    ids.push(id)
  }

  return ids
}

export function readStarredTagIds(): number[] {
  if (typeof window === 'undefined') return []

  try {
    return normalizeStarredTagIds(JSON.parse(window.localStorage.getItem(STARRED_TAG_IDS_STORAGE_KEY) || '[]'))
  } catch {
    return []
  }
}

export function writeStarredTagIds(ids: readonly number[]): number[] {
  const normalized = normalizeStarredTagIds([...ids])

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STARRED_TAG_IDS_STORAGE_KEY, JSON.stringify(normalized))
    window.dispatchEvent(new CustomEvent(STARRED_TAGS_CHANGED_EVENT))
  }

  return normalized
}

export function useStarredTags(tags: readonly TagLike[]) {
  const [storedTagIds, setStoredTagIds] = useState(readStarredTagIds)

  useEffect(() => {
    const sync = () => setStoredTagIds(readStarredTagIds())

    window.addEventListener('storage', sync)
    window.addEventListener(STARRED_TAGS_CHANGED_EVENT, sync)

    return () => {
      window.removeEventListener('storage', sync)
      window.removeEventListener(STARRED_TAGS_CHANGED_EVENT, sync)
    }
  }, [])

  const availableTagIds = useMemo(() => new Set(tags.map((tag) => tag.id)), [tags])
  const starredTagIdSet = useMemo(
    () => new Set(storedTagIds.filter((id) => availableTagIds.has(id))),
    [availableTagIds, storedTagIds],
  )

  const toggleStarredTag = useCallback((tagId: number) => {
    setStoredTagIds((current) => {
      const next = current.includes(tagId)
        ? current.filter((id) => id !== tagId)
        : [...current, tagId]
      return writeStarredTagIds(next)
    })
  }, [])

  return {
    starredTagIdSet,
    toggleStarredTag,
  }
}
