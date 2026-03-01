import { useExport } from '../../hooks/useExport'

export function ExportButton() {
  const { exportCSV, filteredCount } = useExport()

  return (
    <button
      onClick={() => exportCSV()}
      className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
      title={`Export ${filteredCount} rows as CSV`}
    >
      <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      <span className="text-gray-700">Export {filteredCount} rows</span>
    </button>
  )
}
