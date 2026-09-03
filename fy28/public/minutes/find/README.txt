Which meeting documents contain a word.

The bundles at /minutes/<board>.txt are the whole text of a board, and the two largest --
select-board and school-committee -- are around 1MB, which is more than most callers can
read in one fetch. This index exists so you do not have to.

COVERAGE -- READ THIS BEFORE CONCLUDING ANYTHING FROM AN EMPTY RESULT

This index covers 1,422 documents. The town has published 1,422.
Every published document is searchable.

An empty result means the word is not in the 1,422 documents indexed here. That is
not the same as nobody having said it, and the two are only distinguishable if you know the
denominator -- so it is published: https://lunenburgbudgetproject.org/minutes/find/coverage.json.

This is not hypothetical. 39 documents the town published as Word files were missing from
this archive while every count said otherwise, one of them School Committee minutes from the
middle of a fiscal year under analysis. They are here now. The count above is what makes the
next such gap visible instead of silent.

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
postings would be most of the index. 73 terms were dropped on that rule.

Words are matched exactly as they appear in the text, so plurals and possessives are
separate terms. The text is extracted from scans, so it carries OCR errors.

BUILT FROM

1,422 of 1,422 published documents, 16,476 indexed terms, 473 shards.
Rebuild with scripts/build_minutes_search.py. The documents are the source; this is
derived and can be thrown away.
