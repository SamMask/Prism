import { useState } from 'react'
import { api, Note } from '../../services/api'
import { confirm } from '../../components/ui/ConfirmDialog'
import { toast } from '../../components/ui/Toast'
import { useAppStore } from '../../stores/appStore'

export interface HistoryVersion {
  id: number
  content: string
  diff_summary: string
  created_at: string
}

export function useNoteHistory(
  note: Note | null,
  setContent: (c: string) => void
) {
  const { fetchNotes } = useAppStore()
  const [historyVersions, setHistoryVersions] = useState<HistoryVersion[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)

  const loadHistory = async () => {
    if (!note) return
    setIsLoadingHistory(true)
    try {
      const result = await api.getNoteHistory(note.id)
      setHistoryVersions(result.history)
      setShowHistory(true)
    } catch {
      toast.error('載入歷史版本失敗')
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const restoreVersion = async (historyId: number) => {
    if (!note) return
    const ok = await confirm({
      title: '還原版本',
      message: '確定要還原到此版本嗎？目前的內容會被覆蓋。',
      variant: 'warning',
    })
    if (!ok) return
    try {
      await api.restoreNoteVersion(note.id, historyId)
      toast.success('已還原到指定版本')
      const updatedNote = await api.getNote(note.id)
      setContent(updatedNote.content)
      setShowHistory(false)
      fetchNotes(true)
    } catch {
      toast.error('還原失敗')
    }
  }

  return {
    historyVersions,
    showHistory, setShowHistory,
    isLoadingHistory,
    loadHistory,
    restoreVersion,
  }
}
