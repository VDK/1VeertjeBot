# Repairing dead Common Sense Media links on enwiki

Common Sense Media (CSM) reorganised its site; the old
`commonsensemedia.org/.../review.php?id=` and `.../music-reviews/X.html` URLs are
dead or redirect to a section index. This job replaces every dead music-review
citation with a properly archived `{{cite web}}`.

The whole run is two `replace.py` commands — no bespoke uploader, no edit loop.

## What gets written

Per music-review citation:

* `archive-url` + `archive-date` (Wayback, the snapshot closest to the review)
* `url-status=dead`
* `author` from the archive snapshot's `application/ld+json`
  (`Review.author.name`) — split into `last`/`first`
* `date` from `datePublished`, only when the citation has no `date` yet
* the existing `access-date` is preserved verbatim
* the original parameter order and the citation body are otherwise untouched, so
  the diff stays on one line

Known traps baked into the pairs:

* `|accessdate=` and `|access-date=` are the **same** parameter to MediaWiki;
  writing both gives a "duplicate access date" cite error, so this never happens.
* An existing `date` is never overwritten: it is often the album release date,
  not the review date. Only missing dates are filled in.
* A citation whose URL is already archived on the page is skipped entirely — it
  is not "work", so it does not appear here at all.

### Resolving the author from the archive

The author is not on the live page (that redirects to an index); it is in the
Wayback snapshot:

```python
ld    = json.loads(block)                      # <script type="application/ld+json">
review = ld if ld.get("@type") == "Review" else ld.get("@graph", [{}])[0]
author = review.get("author", {}).get("name")  # e.g. "Tony Whittum"
date   = review.get("datePublished")           # e.g. "2006-10-23"
```

Two details matter:

* take the slug from the **URL** (`music-reviews/its-alright-its-ok-cd-single`),
  never from the title — `"It's"` slugifies to `it-s-` and the snapshot is missed
* a page can carry several snapshots; prefer the newest JSON-LD-bearing one

## Running it

Copy `csm_replace_pairs.txt` and `replace_pages.txt` next to your pywikibot
checkout and run from there:

```bash
# dry run first — prints a per-page diff and writes nothing
python pwb.py replace -lang:en -family:wikipedia \
    -file:replace_pages.txt \
    -pairsfile:csm_replace_pairs.txt \
    -simulate -always \
    -summary:"Repair dead Common Sense Media link (archive + author/date)"

# then for real (same command, minus -simulate)
python pwb.py replace -lang:en -family:wikipedia \
    -file:replace_pages.txt \
    -pairsfile:csm_replace_pairs.txt \
    -always \
    -summary:"Repair dead Common Sense Media link (archive + author/date)"
```

`csm_replace_pairs.txt` is a `-pairsfile`: **line 1 = old text, line 2 = new
text, line 3 = next old text**, and so on. 115 pairs = 230 lines, no newlines
inside any pair, so it is one replacement per citation.

`-simulate` respects `-always` and shows the real diff without saving. Verified
in a full dry run: 115 pairs over 115 pages, 113 processed, 2 refused (below).

### The two pages that cannot be edited

`Miley Cyrus` and `Big Time Rush (group)` are semi-protected
(`edit=autoconfirmed`). `1VeertjeBot` is only in `*`/`user` on enwiki, so
`replace.py` prints `WARNING: You can't edit page` and skips them. Either edit
those two by hand or first get the bot autoconfirmed there.

## Background

CSM retired the numbered `review.php` scheme and the `.html` music-review slugs.
Old-style citations look like:

```
{{cite web|url=http://www.commonsensemedia.org/music-reviews/V.html|title=V
 |publisher=Common Sense Media|access-date=2012-03-13}}
```

Everything in the pairs was checked against the live wikitext immediately before
being written, so a citation that someone else has since improved is left alone
rather than clobbered. That is also why the old text is the *entire* citation: it
matches exactly once and cannot partial-match a neighbouring reference.
