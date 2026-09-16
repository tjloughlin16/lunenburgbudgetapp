import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { installBeacon } from './lib/track'

installBeacon()

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
)
