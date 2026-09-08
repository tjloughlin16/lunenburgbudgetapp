-- The question inbox. A SEPARATE D1 database from lunenburg-budget, on purpose.
--
-- On the Workers Free plan D1 does not bill, it STOPS: 100,000 writes a day. The site's
-- own database sync writes ~70,000 of those in a single push. If submissions shared that
-- budget, a spam flood would not cost money -- it would mean the day's data push fails,
-- and the public database goes stale until tomorrow. Isolating the write budget is the
-- whole reason this is its own database.

CREATE TABLE IF NOT EXISTS question (
  id           TEXT PRIMARY KEY,          -- random, so an id cannot be enumerated
  asked_at     TEXT NOT NULL,             -- ISO 8601 UTC
  body         TEXT NOT NULL,             -- the question. Capped at 2,000 chars on write
  email        TEXT,                      -- optional. NULL when they did not leave one
  topic        TEXT,                      -- optional, from a short fixed list
  -- Kept for rate limiting and abuse review, NOT for identifying anybody. A truncated
  -- hash rather than the address itself: enough to spot one source flooding, not enough
  -- to recover who it was. Deliberately lossy.
  source_hash  TEXT,
  country      TEXT,                      -- Cloudflare's cf.country, for abuse patterns
  status       TEXT NOT NULL DEFAULT 'new'
      CHECK (status IN ('new', 'reviewing', 'answered', 'declined', 'spam')),
  note         TEXT,                      -- our review note
  answered_url TEXT                       -- where the answer was published, if it was
);

CREATE INDEX IF NOT EXISTS ix_question_status ON question(status, asked_at);
CREATE INDEX IF NOT EXISTS ix_question_day    ON question(substr(asked_at, 1, 10));
CREATE INDEX IF NOT EXISTS ix_question_source ON question(source_hash, asked_at);
