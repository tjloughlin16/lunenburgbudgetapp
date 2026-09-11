/** `**bold**` and `` `code` ``, and nothing else.
 *
 *  The copy is Markdown because it lives in a Markdown file that a person edits. Pulling
 *  a Markdown renderer in for two inline marks would be a dependency; stripping the marks
 *  would change the emphasis the author chose. So the two that are actually used are
 *  rendered and everything else is left as written -- which is visible if a third mark
 *  ever appears, rather than silently swallowed. */
export function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith('**') && p.endsWith('**') && p.length > 4) {
          return <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong>
        }
        if (p.startsWith('`') && p.endsWith('`') && p.length > 2) {
          return (
            <code key={i} className="text-[0.92em] px-1 py-0.5 rounded"
              style={{ background: 'var(--surface-3)' }}>{p.slice(1, -1)}</code>
          )
        }
        return <span key={i}>{p}</span>
      })}
    </>
  )
}
