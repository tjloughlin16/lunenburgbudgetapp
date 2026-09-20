import { Body, H2, ReportShell } from '../components/report'
import type { Tab } from '../routes'

const TAB: Tab = 'about'

/** WHO MADE THIS, AND THE RULE IT IS MADE UNDER.
 *
 *  TJ, 19 September 2026: "Can we have an 'About' page that describes ME and the basics of
 *  this app. With a photo of me."
 *
 *  A public budget tool with no author is asking to be read as an institution, and it is
 *  not one — it is one resident with a spreadsheet habit and a records-request account.
 *  Saying so plainly is worth more than the authority the anonymity would borrow: a reader
 *  who knows the author has kids in the schools and a wife working in them can weigh the
 *  work accordingly, which is what they should be doing anyway.
 *
 *  THE SECOND HALF IS THE LOAD-BEARING ONE. The evidence rule below is the whole reason
 *  the site's figures can be argued with, and it is TJ's own standard written without the
 *  edge he wrote it with — he asked for it "without contentious language", and it reads
 *  better as a rule the project holds itself to than as a complaint about anyone. */
export function About() {
  return (
    <ReportShell
      tab={TAB}
      title="About this project"
      standfirst="One resident, the town's own documents, and a rule about what counts as evidence."
    >
      <div className="sm:flex sm:gap-6 sm:items-start mt-2">
        <img
          src="/img/tj-loughlin.jpg"
          alt="TJ Loughlin"
          width={900} height={600}
          className="rounded-xl w-full sm:w-64 shrink-0 mb-4 sm:mb-0"
          style={{ objectFit: 'cover', aspectRatio: '3 / 2' }}
        />
        <div className="min-w-0">
          <H2>Who I am</H2>
          <Body>
            I'm TJ Loughlin. I've owned a home in Lunenburg since 2016, and I have two kids
            in the schools — one at the middle school, one at the high school. Both are
            athletes and both take the academic side seriously. My wife is a
            paraprofessional in the district.
          </Body>
          <Body>
            I'm the current president of Lunenburg Youth Baseball and Softball. I've been
            following the town's budgets since the first year of a major deficit — the year
            we landed the override — and I was part of the citizens' group behind it. Two
            years ago I was the resident who put an override on the Town Meeting warrant.
          </Body>
          <Body>
            Outside all this I work in the tech industry and I train MMA.
          </Body>
        </div>
      </div>

      {/* CUT AGAIN. TJ: "definitely too long still" -- and the reading-time badge said
          SEVEN MINUTES on a page whose whole job is to say who wrote this and under what
          rule. Four sections became two, and each rule keeps exactly one sentence. */}
      <H2>Why, and the rule</H2>
      <Body>
        I built this because data is how I'd rather make a decision — and because most
        budget arguments turn on a figure somebody half-remembers.
      </Body>
      <Body>
        <strong>Everything here comes from documents I actually hold</strong>, published by
        the town, the district or the state, or obtained by records request. If I can't get
        the document behind a figure, it doesn't go on the site.{' '}
        <strong>Projections are the one exception</strong> — no document exists for a year
        that hasn't happened — and they're labelled wherever they appear.
      </Body>
      <Body>
        A lot simply isn't published. No dataset shows how the schools' costs have actually
        moved, only what was budgeted. Requests are out;{' '}
        <a className="underline" href="/what-we-cannot-answer">what we cannot answer</a>{' '}
        lists the rest.
      </Body>

      <H2>On being wrong</H2>
      <Body>
        This doesn't claim every calculation is right — it claims every one is shown, so it
        can be checked. Find a discrepancy and I want to hear about it.
      </Body>
      <Body>
        <a className="underline" href="/ask-us">Ask a question or flag something</a> ·{' '}
        <a className="underline" href="/sources">Every document this is built on</a> ·{' '}
        <a className="underline" href="/what-we-cannot-answer">What we cannot answer</a>
      </Body>
    </ReportShell>
  )
}
