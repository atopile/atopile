import React from 'react'
import ReactDOM from 'react-dom/client'
import { ComponentShowcase } from './components/ComponentShowcase'
import './styles/index.css'

const root = document.getElementById('root')
if (root) {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <ComponentShowcase />
    </React.StrictMode>
  )
}
