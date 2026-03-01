import { useState, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'

interface Props {
  title?: string  // bold heading line, e.g. "2xxx — Instructional"
  text: string
}

interface Pos { top: number; left: number }

export function InfoTooltip({ title, text }: Props) {
  const [pos, setPos] = useState<Pos | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const show = useCallback(() => {
    if (!svgRef.current) return
    const r = svgRef.current.getBoundingClientRect()
    setPos({ top: r.top, left: r.left + r.width / 2 })
  }, [])

  const hide = useCallback(() => setPos(null), [])

  return (
    <>
      <svg
        ref={svgRef}
        className="w-3.5 h-3.5 text-gray-400 hover:text-gray-600 cursor-help flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        tabIndex={0}
        aria-label={text}
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>

      {pos && createPortal(
        <div
          style={{
            position: 'fixed',
            top: pos.top - 8,
            left: pos.left,
            transform: 'translate(-50%, -100%)',
            zIndex: 9999,
          }}
          className="w-60 bg-gray-900 text-white text-xs rounded-lg px-3 py-2.5 shadow-xl pointer-events-none leading-relaxed"
        >
          {title && (
            <p className="font-semibold text-white mb-1">{title}</p>
          )}
          <p className="text-gray-300">{text}</p>
          {/* Arrow */}
          <span className="absolute left-1/2 -translate-x-1/2 top-full
            border-l-4 border-r-4 border-t-4
            border-l-transparent border-r-transparent border-t-gray-900" />
        </div>,
        document.body,
      )}
    </>
  )
}
