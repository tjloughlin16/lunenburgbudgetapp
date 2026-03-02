import { useRef, useState, useEffect } from 'react'
import { useBudgetData } from '../../hooks/useBudgetData'
import { useBudgetStore } from '../../store/budgetStore'
import { downloadAIReadyCSV, downloadOriginalXLSX } from '../../data/exportAI'

export function DownloadsMenu() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { data } = useBudgetData()
  const { primaryYear, compareYear } = useBudgetStore()

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
        title="Download budget data"
      >
        <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span className="text-gray-700 hidden sm:inline">Download</span>
        <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50 overflow-hidden">
          {/* AI-Ready CSV */}
          <button
            disabled={!data}
            onClick={() => {
              if (data) downloadAIReadyCSV(data, primaryYear, compareYear)
              setOpen(false)
            }}
            className="w-full flex items-start gap-3 px-4 py-3 hover:bg-blue-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-left border-b border-gray-100"
          >
            <div className="mt-0.5 w-7 h-7 rounded-md bg-blue-100 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">AI-Ready Budget CSV</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-snug">
                Flat, fully-annotated CSV — upload to ChatGPT or Claude to ask questions about the budget.
              </p>
            </div>
          </button>

          {/* Original XLSX */}
          <button
            onClick={() => { downloadOriginalXLSX(); setOpen(false) }}
            className="w-full flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
          >
            <div className="mt-0.5 w-7 h-7 rounded-md bg-green-100 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-green-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">Original Budget (XLSX)</p>
              <p className="text-xs text-gray-500 mt-0.5 leading-snug">
                The source spreadsheet as published by Lunenburg Public Schools.
              </p>
            </div>
          </button>
        </div>
      )}
    </div>
  )
}
