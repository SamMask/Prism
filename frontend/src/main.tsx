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

// Initialize color theme from localStorage
const savedColorTheme = localStorage.getItem('colorTheme') || 'default'
document.documentElement.setAttribute('data-theme', savedColorTheme)
const savedAccentColor = localStorage.getItem('prism.accentColor') || localStorage.getItem('colorTheme')
if (savedAccentColor) {
  document.documentElement.setAttribute('data-accent', savedAccentColor)
}

const savedAestheticMode = localStorage.getItem('prism.aestheticMode') || 'linear'
document.documentElement.setAttribute('data-aesthetic', savedAestheticMode)

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
