import { useState } from 'react'
import { api, Note } from '../../services/api'
import { confirm } from '../../components/ui/ConfirmDialog'
import { toast } from '../../components/ui/Toast'
import { useAppStore } from '../../stores/appStore'
import { t } from '../../i18n'

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
      toast.error(t('editor.historyToast.loadFailed'))
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const restoreVersion = async (historyId: number) => {
    if (!note) return
    const ok = await confirm({
      title: t('editor.historyToast.restoreTitle'),
      message: t('editor.historyToast.restoreMessage'),
      variant: 'warning',
    })
    if (!ok) return
    try {
      await api.restoreNoteVersion(note.id, historyId)
      toast.success(t('editor.historyToast.restored'))
      const updatedNote = await api.getNote(note.id)
      setContent(updatedNote.content)
      setShowHistory(false)
      fetchNotes(true)
    } catch {
      toast.error(t('editor.historyToast.restoreFailed'))
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
