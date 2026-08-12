import { Component, lazy, Suspense, type ErrorInfo, type ReactNode } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { ConfirmDialogProvider } from './components/ui/ConfirmDialog'
import { t } from './i18n'

const PromptBuilder = lazy(() => import('./pages/PromptBuilder').then((module) => ({ default: module.PromptBuilder })))
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((module) => ({ default: module.SettingsPage })))

function RouteLoadFallback() {
  return (
    <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-text-muted" role="status">
      <Loader2 size={18} className="animate-spin" />
      {t('common.loading')}
    </div>
  )
}

class RouteLoadErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Lazy route failed to load', error, info)
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="mx-auto max-w-md rounded-lg border border-danger/30 bg-danger/10 p-5 text-center" role="alert">
          <p className="text-sm text-text-primary">{t('home.loadFailed')}</p>
          <button
            type="button"
            className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-light"
            onClick={() => window.location.reload()}
          >
            {t('home.retry')}
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

const lazyRoute = (page: ReactNode) => (
  <RouteLoadErrorBoundary>
    <Suspense fallback={<RouteLoadFallback />}>
      {page}
    </Suspense>
  </RouteLoadErrorBoundary>
)

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="prompt-builder" element={lazyRoute(<PromptBuilder />)} />
          <Route path="settings" element={lazyRoute(<SettingsPage />)} />
        </Route>
      </Routes>
      <ConfirmDialogProvider />
    </>
  )
}

export default App
