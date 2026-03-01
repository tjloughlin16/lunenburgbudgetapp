interface Props {
  message: string
}

export function ErrorBanner({ message }: Props) {
  return (
    <div className="m-4 p-4 bg-red-50 border border-red-200 rounded-lg">
      <h3 className="text-red-800 font-semibold mb-1">Failed to load budget data</h3>
      <p className="text-red-600 text-sm font-mono">{message}</p>
    </div>
  )
}
