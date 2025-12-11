import React from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import App from './App'
import { GDP, Home, Map, Settings, AgentProfile, AllAgents, POIDetails } from './pages'
import './index.css'

// Apply saved theme before rendering to avoid flash
try {
  const savedTheme = localStorage.getItem('wsim_theme')
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark')
  } else if (savedTheme === 'light') {
    document.documentElement.classList.remove('dark')
  }
} catch {}

const root = createRoot(document.getElementById('root')!)
const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  { path: '/firm', element: <App /> },
  { path: '/gdp', element: <GDP /> },
  { path: '/map', element: <Map /> },
  { path: '/settings', element: <Settings /> },
  { path: '/agents', element: <AllAgents /> },
  { path: '/agent/:agentId', element: <AgentProfile /> },
  { path: '/poi/:osmId', element: <POIDetails /> },
], {
  future: {
    v7_startTransition: true,
    v7_relativeSplatPath: true
  }
})

root.render(<RouterProvider router={router} />)
