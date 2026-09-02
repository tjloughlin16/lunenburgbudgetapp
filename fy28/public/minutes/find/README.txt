Which meeting documents contain a word.

The bundles at /minutes/<board>.txt are the whole text of a board, and the two largest --
select-board and school-committee -- are around 1MB, which is more than most callers can
read in one fetch. This index exists so you do not have to.

HOW TO USE IT

  1. Lowercase your word. Take its first two characters. Fetch that shard:
         https://lunenburgbudgetproject.org/minutes/find/je.json
     It is an object of term -> array of document numbers:
         {"jersey":[412,908], "jerseys":[412], ...}
     A term absent from the shard appears in no document. A missing shard file means no
     term starts with those two characters.

  2. Fetch the document table ONCE and keep it:
         https://lunenburgbudgetproject.org/minutes/find/documents.json
     An array. Position N is the document that the number N refers to:
         {"board":"school-committee","date":"2025-09-17","kind":"minutes",
           "id":7408,"path":"/docs/minutes/text/school-committee/2025-09-17-minutes-7408.txt"}

  3. Fetch the documents you want, at https://lunenburgbudgetproject.org<path>. They average 4.5KB.

Cite the individual document, never this index and never a bundle.

WHAT IT IS AND IS NOT

It reports which documents contain a word. It does not rank them, does not support phrases
or wildcards, and does not know that two words mean the same thing -- searching "jerseys"
will not find a document that only says "uniforms". Search both.

Terms shorter than 3 characters are not indexed. Terms appearing in more than
40% of documents are not indexed either: they cannot narrow anything and their
postings would be most of the index. 77 terms were dropped on that rule.

Words are matched exactly as they appear in the text, so plurals and possessives are
separate terms. The text is extracted from scans, so it carries OCR errors.

BUILT FROM

1,383 documents, 16,294 indexed terms, 469 shards.
Rebuild with scripts/build_minutes_search.py. The documents are the source; this is
derived and can be thrown away.
