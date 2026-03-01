export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-full min-h-64">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
        <p className="text-gray-500 text-sm">Loading budget data…</p>
      </div>
    </div>
  )
}
