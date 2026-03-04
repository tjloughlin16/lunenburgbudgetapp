import { YearSelector } from '../filters/YearSelector'
import { DownloadsMenu } from '../ui/DownloadsMenu'

export function TopBar() {
  return (
    <div className="flex items-center gap-3 px-6 py-3 bg-white border-b border-gray-200 justify-end">
      <YearSelector mode="compare" label="From" />
      <span className="text-gray-400 text-sm">→</span>
      <YearSelector mode="primary" label="To" />
      <DownloadsMenu />
    </div>
  )
}
