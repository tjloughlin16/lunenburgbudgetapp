import { useState } from 'react'
import MANIFEST from '../data/agent-manifest.json'

/** A prompt you paste into Claude, with the addresses already in it.
 *
 *  WHY THIS PAGE EXISTS, AND WHY THE PROMPT IS THE WHOLE POINT
 *
 *  Every agent that has tried to read this site has failed the same way, and none of the
 *  failures was the agent's fault. They reach the homepage, read it correctly, describe
 *  what the site offers -- and then cannot fetch a single thing under it.
 *
 *  Three of them, three different reasons:
 *
 *    - one followed anchors from a page it fetched DIRECTLY, and was refused everything
 *      when the same page arrived through the lburg.org redirect;
 *    - one follows only links that came back from a SEARCH RESULT, and searched for this
 *      domain and found nothing;
 *    - one could fetch anything at all, because the user had typed the URL.
 *
 *  That third one is not a lucky case. It is the rule underneath all three. **A URL a
 *  person puts in their own message is authorised by the person**, which is exactly the
 *  guardrail working as designed: a fetched page must not be able to talk an assistant
 *  into requesting somewhere else, but you can ask it to go anywhere you like.
 *
 *  So the fix that works today, for every assistant, needing nothing from Google and
 *  nothing from Cloudflare, is to put the addresses in the PERSON'S message. That is all
 *  this page is. `/agents` puts the same addresses in the link graph for agents that read
 *  link graphs; this one hands them to the reader to paste, for the ones that do not.
 *
 *  THE PROMPT IS GENERATED, NOT TYPED
 *
 *  Every URL comes from `agent-manifest.json`, which `build_agent_manifest.py` writes.
 *  A URL typed into this component would be a figure typed into prose -- rule 2 -- and
 *  would go stale the first time an endpoint moved, with nothing to catch it. The same
 *  list feeds `llms.txt` and the footer, so the three cannot drift apart.
 *
 *  It also carries the two warnings that matter, for the same reason the MCP tools carry
 *  them: an instruction in a prompt is read every time, and a caveat in a document is read
 *  once, if ever. Budgets are not actuals, and a budget line is net.
 */

/** Absolute, always. The reader is going to paste this somewhere with no notion of what
 *  site it came from, so a relative path in it is not merely unhelpful, it is broken. */
const abs = (p: string) => `${MANIFEST.site}${p}`

function buildPrompt() {
  const lines: string[] = []
  lines.push(
    'I want to look into the Lunenburg, Massachusetts town and school budget using an',
    'independent public archive. Please fetch these and use them to answer my questions.',
    '',
    'START HERE — what exists, and how to ask it something:')
  for (const q of MANIFEST.query) lines.push(`  ${abs(q.path)}`, `      ${q.note}`)
  lines.push('', 'FILES THAT ANSWER A PARTICULAR QUESTION:')
  for (const a of MANIFEST.answers) lines.push(`  ${abs(a.path)}`, `      ${a.question}`)
  lines.push(
    '',
    'TWO THINGS TO GET RIGHT, because the data lets you get them wrong quietly:',
    '',
    `  1. ${MANIFEST.warning}`,
    '',
    '  2. Cite the document. Every figure here traces to a published document with a',
    '     sha256, and the query endpoint returns the documents its rows came from. If an',
    '     answer cannot be traced to one, say so rather than giving me the number.',
    '',
    'If a query fails, that is a rate or cost limit, not missing data — say which.',
    '',
    'My question: ')
  return lines.join('\n')
}

export function AskAnAssistant() {
  const PROMPT = buildPrompt()
  const [copied, setCopied] = useState(false)

  // navigator.clipboard is unavailable over plain http and in some embedded browsers, so
  // the textarea below is the real interface and the button is the convenience. A copy
  // button that silently does nothing is worse than no button.
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(PROMPT)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-5 py-8">
      {/* THE PROMPT IS FIRST. Everything explaining it is below it, deliberately.
        * The reader arriving here has already decided to try this -- they followed a link
        * that said so -- and the box is the thing they came for. An explanation above it
        * is a paragraph between a person and the button they are looking for. */}
      <h1 className="text-2xl font-bold">This is how you query the data</h1>
      <p className="mt-2 text-[16px] leading-relaxed">
        Copy this. Paste it into Claude, ChatGPT or any assistant that can fetch a web
        page. Type your question at the end.
      </p>

      <div className="mt-4 flex items-center gap-3">
        <button onClick={copy}
          className="rounded px-4 py-2 text-[14px] font-semibold border"
          style={{ borderColor: 'var(--series-cost)', color: 'var(--series-cost)' }}>
          {copied ? 'Copied' : 'Copy the prompt'}
        </button>
        <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>
          or select the text below — {PROMPT.length.toLocaleString()} characters
        </span>
      </div>

      <textarea readOnly value={PROMPT} rows={20} spellCheck={false}
        onFocus={(e) => e.currentTarget.select()}
        className="mt-3 w-full rounded border p-3 text-[12px] leading-relaxed"
        style={{
          borderColor: 'var(--grid)', color: 'var(--text-secondary)',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          background: 'transparent',
        }} />

      <p className="mt-4 text-[15px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        It carries every address the assistant needs — the whole database, the budget
        lines, the town ledger, the annual town reports, and {MANIFEST.corpus} — so it
        reads the data instead of guessing at it, and cites the document each figure came
        from. You do not need to know any SQL, and you do not need an account anywhere.
      </p>

      <div className="mt-5 rounded border p-4 text-[14px] leading-relaxed"
        style={{ borderColor: 'var(--grid)' }}>
        <p className="font-semibold">Why the prompt has to include the links</p>
        <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
          Assistants generally refuse to fetch a URL they have not been given — a sensible
          rule, since it stops a web page from talking an assistant into visiting somewhere
          else. The side effect is that an assistant can read this site's front page,
          correctly describe everything it offers, and still not be allowed to open any of
          it. <strong>A link you paste yourself is authorised by you.</strong> That is the
          whole trick, and it works today with every assistant.
        </p>
      </div>

      <h2 className="mt-10 text-lg font-bold">What to ask it</h2>
      <p className="mt-2 text-[15px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        There are {MANIFEST.questions} questions this archive can answer, in plain English,
        each one already run against the data — so nothing on the list is a question we
        merely hope is answerable. Many carry a second line saying what the answer does <em>not</em> tell
        you, which is usually the more important half.
      </p>
      <ul className="mt-3 text-[14px] space-y-1">
        <li>
          <a href={abs('/docs/analyses/what-you-can-ask.pdf')} className="underline"
            style={{ color: 'var(--series-cost)' }}>What you can ask this archive (PDF)</a>
          {' '}— the list, in plain English, no queries
        </li>
        <li>
          <a href={abs('/docs/analyses/questions.md')} className="underline"
            style={{ color: 'var(--series-cost)' }}>The same list with the query behind each one</a>
        </li>
      </ul>

      <h2 className="mt-10 text-lg font-bold">If your assistant supports MCP</h2>
      <p className="mt-2 text-[15px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        There is a server at{' '}
        <a href={abs('/mcp')} className="underline" style={{ color: 'var(--series-cost)' }}>
          {MANIFEST.site.replace(/^https?:\/\//, '')}/mcp</a>{' '}
        — add it as a remote MCP server in your client's settings, not in the chat. It
        gives the assistant eight tools over the same data, each one shaped so the mistakes
        this archive documents cannot be made: budget history takes one stage at a time, so
        a growth rate cannot be measured from an actual to a budget.
      </p>

      <p className="mt-8 text-[13px]" style={{ color: 'var(--text-muted)' }}>
        Every address in the prompt is generated from the same list that produces{' '}
        <a href={abs('/llms.txt')} className="underline">llms.txt</a> and{' '}
        <a href={abs('/agents')} className="underline">the index of published addresses</a>,
        so the three cannot drift apart.
      </p>
    </div>
  )
}
