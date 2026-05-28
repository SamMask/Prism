import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

const clampNumber = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

const readNumberSetting = (key: string, fallback: number, min: number, max: number) => {
  const value = Number(localStorage.getItem(key))
  return Number.isFinite(value) ? clampNumber(value, min, max) : fallback
}

// Initialize appearance from localStorage
const savedAccentColor = localStorage.getItem('prism.accentColor') || localStorage.getItem('colorTheme')
document.documentElement.setAttribute('data-accent', savedAccentColor || 'default')
document.documentElement.removeAttribute('data-theme')

const backgroundSchemes = ['neutral', 'black', 'warm', 'green', 'paper'] as const
const savedBackgroundScheme = localStorage.getItem('prism.backgroundScheme')
const backgroundScheme = backgroundSchemes.includes(savedBackgroundScheme as typeof backgroundSchemes[number])
  ? (savedBackgroundScheme as typeof backgroundSchemes[number])
  : 'neutral'
document.documentElement.setAttribute('data-bg', backgroundScheme)

const normalizeAestheticMode = (value: string | null) => {
  if (value === 'linear' || value === 'editorial' || value === 'studio') return 'editorial'
  return 'editorial'
}
document.documentElement.setAttribute('data-aesthetic', normalizeAestheticMode(localStorage.getItem('prism.aestheticMode')))

const savedMode = localStorage.getItem('theme') || 'dark'
document.documentElement.classList.toggle('light', savedMode === 'light')
document.documentElement.setAttribute('data-mode', savedMode)

const savedCornerRadius = readNumberSetting('prism.cornerRadius', 10, 4, 24)
document.documentElement.style.setProperty('--prism-corner-radius', `${savedCornerRadius}px`)
const savedSidebarWidth = readNumberSetting('prism.sidebarWidth', 248, 208, 320)
document.documentElement.style.setProperty('--prism-sidebar-width', `${savedSidebarWidth}px`)
document.documentElement.style.setProperty('--sidebar-w', `${savedSidebarWidth}px`)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
