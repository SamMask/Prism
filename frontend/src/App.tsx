import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { PromptBuilder } from './pages/PromptBuilder'
import { SettingsPage } from './pages/SettingsPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="prompt-builder" element={<PromptBuilder />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default App
