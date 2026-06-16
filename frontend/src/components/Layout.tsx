import { Outlet } from 'react-router-dom'
import { CommandPalette } from './CommandPalette'
import { FilterStrip } from './FilterStrip'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { useAppStore } from '../stores/appStore'
import { useTranslation } from '../hooks/useTranslation'

export function Layout() {
  const { totalNotes, tags } = useAppStore()
  const { t } = useTranslation()

  return (
    <div className="flex h-screen bg-bg-base text-text-primary" data-testid="app-container">
      <Sidebar />

      <div className="min-w-0 flex-1 flex flex-col overflow-hidden bg-bg-base">
        <Header />
        <FilterStrip />

        <main className="flex-1 overflow-auto px-5 py-5 lg:px-6 lg:py-6">
          <Outlet />
        </main>

        <footer className="hidden sm:flex h-7 shrink-0 items-center gap-3 border-t border-border-subtle bg-bg-base px-4 text-[11px] font-mono text-text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
          <span>{t('shell.localConnection')}</span>
          <span>·</span>
          <span>{t('shell.sqliteWal')}</span>
          <span>·</span>
          <span>{t('shell.notesCount', { count: totalNotes.toLocaleString() })}</span>
          <span>·</span>
          <span>{t('shell.tagsCount', { count: tags.length.toLocaleString() })}</span>
        </footer>
      </div>

      <CommandPalette />
    </div>
  )
}
