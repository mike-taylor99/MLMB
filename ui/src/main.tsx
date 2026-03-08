import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Clarity from '@microsoft/clarity'
import './index.css'
import App from './App.tsx'

const clarityId = import.meta.env.VITE_CLARITY_PROJECT_ID
if (clarityId) {
  Clarity.init(clarityId)
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
