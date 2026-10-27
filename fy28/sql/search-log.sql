-- EVERY SEARCH, LOGGED: one row per call to /api/search (functions/api/search.js, logSearch),
-- in the lunenburg-questions database, apart from the site's data. Create once:
--   cd fy28 && npx wrangler d1 execute lunenburg-questions --remote --file sql/search-log.sql
-- Until it exists the API's insert fails quietly and searches are simply not logged.
-- No IP address, no user agent, no identifier: two rows cannot be joined to one person.
CREATE TABLE IF NOT EXISTS search_log (
  at        TEXT NOT NULL,     -- ISO time the search was answered
  q         TEXT NOT NULL,     -- the words as typed, at most 200 characters
  board     TEXT,              -- filters, as sent
  since     TEXT,
  sort      TEXT,
  via       TEXT,              -- page (the search page), thread (a thread page), api (anything else)
  hits      INTEGER,           -- every kind's hits summed; NULL if a cached answer could not be read
  ms        INTEGER,           -- time spent querying; NULL when the edge cache answered
  rows_read INTEGER,           -- D1 rows read
  cache     INTEGER,           -- 1 when the edge cache answered
  error     TEXT,              -- empty, or why the search failed
  country   TEXT               -- two letters, as Cloudflare attaches it
);
CREATE INDEX IF NOT EXISTS search_log_at ON search_log (at);
