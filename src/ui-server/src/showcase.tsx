import React from 'react'
import ReactDOM from 'react-dom/client'
import { ComponentShowcase } from './components/ComponentShowcase'
import { initializeTheme } from './hooks/useTheme'
import './styles/index.css'

initializeTheme();

const root = document.getElementById('root')
if (root) {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <ComponentShowcase />
    </React.StrictMode>
  )
}
