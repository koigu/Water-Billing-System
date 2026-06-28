import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'

const el = document.getElementById('root')
if (!el) {
  // eslint-disable-next-line no-console
  console.error('Root element #root not found. React cannot mount.')
  document.body.innerHTML =
    '<div style="font-family:system-ui;padding:24px">Error: React mount failed (missing #root).</div>'
} else {
  // eslint-disable-next-line no-console
  console.log('Mounting React app...')

  createRoot(el).render(
    <StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </StrictMode>,
  )
}

