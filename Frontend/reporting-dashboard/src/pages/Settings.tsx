import React, { useEffect, useState } from 'react'
import { TopBar } from '../components/TopBar'
import { LeftNav } from '../components/LeftNav'
import { Settings as SettingsIcon, Palette, Monitor, Sun, Moon } from 'lucide-react'

const THEME_KEY = 'wsim_theme'

export default function Settings() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => (document.documentElement.classList.contains('dark') ? 'dark' : 'light'))

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  useEffect(() => {
    const saved = localStorage.getItem(THEME_KEY) as 'light' | 'dark' | null
    if (saved) setTheme(saved)
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      <TopBar simulationId={null} setSimulationId={() => {}} simulationOptions={[]} simulationLoading={false} />
      <LeftNav />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pt-24">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <SettingsIcon className="w-8 h-8 text-gray-700 dark:text-gray-300" />
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
          </div>
          <p className="text-gray-600 dark:text-gray-300">Customize your AtlasHorizon experience</p>
        </div>

        {/* Settings Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Appearance Settings */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Palette className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Appearance</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">Choose your preferred theme</p>
              </div>
            </div>
            
            <div className="space-y-4">
              {/* Theme Toggle Switch */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <Sun className="w-4 h-4 text-yellow-500" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Light</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Moon className="w-4 h-4 text-indigo-500" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Dark</span>
                  </div>
                </div>
                
                {/* Elegant Toggle Switch */}
                <button
                  onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    theme === 'dark' 
                      ? 'bg-blue-600 dark:bg-blue-500' 
                      : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                  role="switch"
                  aria-checked={theme === 'dark'}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      theme === 'dark' ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
              
              {/* Current Theme Display */}
              <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
                <div className={`p-2 rounded-lg ${
                  theme === 'light' 
                    ? 'bg-yellow-100 dark:bg-yellow-900/30' 
                    : 'bg-indigo-100 dark:bg-indigo-900/30'
                }`}>
                  {theme === 'light' ? (
                    <Sun className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                  ) : (
                    <Moon className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {theme === 'light' ? 'Light Mode' : 'Dark Mode'} Active
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {theme === 'light' 
                      ? 'Bright and clean interface for daytime use' 
                      : 'Easy on the eyes for low-light environments'
                    }
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Application Info */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
                <Monitor className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Application</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">System information</p>
              </div>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2">
                <span className="text-sm text-gray-600 dark:text-gray-300">Version</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">1.0.0</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-sm text-gray-600 dark:text-gray-300">Environment</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">Development</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-sm text-gray-600 dark:text-gray-300">API Status</span>
                <span className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-600">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                  Connected
                </span>
              </div>
            </div>
          </div>

          {/* Preferences */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                <SettingsIcon className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Preferences</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">Customize your experience</p>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                Additional settings will be available here as features are added.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


