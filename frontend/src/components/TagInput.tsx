import { useState, useRef, useEffect } from 'react'
import { X } from 'lucide-react'
import { Tag } from '../services/api'
import { useAppStore } from '../stores/appStore'

interface TagInputProps {
  selectedTags: Tag[]
  onTagsChange: (tags: Tag[]) => void
}

export function TagInput({ selectedTags, onTagsChange }: TagInputProps) {
  const { tags: allTags, fetchTags } = useAppStore()
  const [input, setInput] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchTags()
  }, [fetchTags])

  // Filter suggestions based on input
  const suggestions = input.trim()
    ? allTags.filter(
        (tag) =>
          tag.name.toLowerCase().includes(input.toLowerCase()) &&
          !selectedTags.find((t) => t.id === tag.id)
      )
    : []

  const handleInputChange = (value: string) => {
    setInput(value)
    setShowSuggestions(value.trim().length > 0)
    setSelectedIndex(0)
  }

  const addTag = (tag: Tag) => {
    if (!selectedTags.find((t) => t.id === tag.id)) {
      onTagsChange([...selectedTags, tag])
    }
    setInput('')
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const addNewTag = () => {
    if (!input.trim()) return
    const newTag = { id: Date.now(), name: input.trim() }
    if (!selectedTags.find((t) => t.name.toLowerCase() === newTag.name.toLowerCase())) {
      onTagsChange([...selectedTags, newTag])
    }
    setInput('')
    setShowSuggestions(false)
  }

  const removeTag = (tagId: number) => {
    onTagsChange(selectedTags.filter((t) => t.id !== tagId))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => Math.min(prev + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (suggestions.length > 0 && showSuggestions) {
        addTag(suggestions[selectedIndex])
      } else if (input.trim()) {
        addNewTag()
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    } else if (e.key === 'Backspace' && !input && selectedTags.length > 0) {
      // Remove last tag when backspace on empty input
      removeTag(selectedTags[selectedTags.length - 1].id)
    }
  }

  return (
    <div className="relative">
      {/* Selected Tags */}
      <div
        className="flex flex-wrap gap-1.5 p-2 rounded-lg
                   bg-bg-elevated border border-border-default
                   focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/50
                   transition-colors"
        onClick={() => inputRef.current?.focus()}
      >
        {selectedTags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 px-2 py-0.5
                       text-xs rounded-full
                       bg-primary/10 text-primary-light"
          >
            {tag.name}
            <button
              onClick={(e) => {
                e.stopPropagation()
                removeTag(tag.id)
              }}
              className="hover:text-danger"
            >
              <X size={12} />
            </button>
          </span>
        ))}

        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => input.trim() && setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          placeholder={selectedTags.length === 0 ? '輸入標籤...' : ''}
          className="flex-1 min-w-[80px] bg-transparent border-none outline-none
                     text-text-primary text-sm placeholder-text-muted"
        />
      </div>

      {/* Suggestions Dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div
          className="absolute top-full left-0 right-0 mt-1 z-20
                     bg-bg-elevated border border-border-default rounded-lg
                     shadow-xl shadow-black/30 py-1 max-h-48 overflow-auto"
        >
          {suggestions.map((tag, index) => (
            <button
              key={tag.id}
              onClick={() => addTag(tag)}
              className={`w-full px-3 py-2 text-left text-sm
                          transition-colors
                          ${index === selectedIndex
                            ? 'bg-primary/20 text-primary-light'
                            : 'text-text-secondary hover:bg-bg-hover'
                          }`}
            >
              {tag.name}
            </button>
          ))}
        </div>
      )}

      {/* Create new tag hint */}
      {showSuggestions && input.trim() && suggestions.length === 0 && (
        <div
          className="absolute top-full left-0 right-0 mt-1 z-20
                     bg-bg-elevated border border-border-default rounded-lg
                     shadow-xl shadow-black/30 py-2 px-3"
        >
          <p className="text-sm text-text-secondary">
            按 <kbd className="px-1.5 py-0.5 bg-bg-hover rounded text-xs">Enter</kbd> 建立新標籤「{input.trim()}」
          </p>
        </div>
      )}
    </div>
  )
}
