import { Outlet } from 'react-router-dom'
import { CommandPalette } from './CommandPalette'
import { FilterStrip } from './FilterStrip'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { useAppStore } from '../stores/appStore'

export function Layout() {
  const { totalNotes, tags } = useAppStore()

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
          <span>本地連線</span>
          <span>·</span>
          <span>SQLite WAL</span>
          <span>·</span>
          <span>{totalNotes.toLocaleString()} 筆記</span>
          <span>·</span>
          <span>{tags.length.toLocaleString()} 標籤</span>
        </footer>
      </div>

      <CommandPalette />
    </div>
  )
}
