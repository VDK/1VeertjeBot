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

### The three awkward ones

These three are not plain `{{cite web}}` citations, so each needed its own
treatment. The reviewer name in every case comes from the archived page
(`Reviewed By:` in old snapshots, `Review.author.name` in newer JSON-LD).

| page | old shape | fix |
| --- | --- | --- |
| `V (Vanessa Hudgens album)` | cite with the `/details` URL archived on archive.today, title "Kids Music - Music Reviews" | rewrite to the real slug, Wayback 2008-02-14, author Tony Whittum |
| `Unfabulous and More` | `review.php?id=4515&type=Music`, marketing title, no author | rewrite, Wayback 2007-12-15, author Kathi Kamen Goldmark |
| `Goodbye (Kristinia DeBarge song)` | `author=This review was written by Jacqueline Rupp`, `url-status=live` | split into `last`/`first`, `url-status=dead` |

Two things that bit us:

* the old snapshots (2005-2008) carry **no** JSON-LD, so the author is only
  available from the rendered byline; the live pages now redirect to the movie
  index, so the snapshot is the only source left
* one pair contains an en dash (`"Goodbye" (CD single) - Music Review`); write it
  with an explicit `\u2013`, or a shell heredoc turns it into mojibake and the
  pair silently never matches

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
text, line 3 = next old text**, and so on. 112 pairs = 224 lines, no newlines
inside any pair, so it is one replacement per citation. One pair can serve
several pages, which is why 112 pairs cover 113 pages.

`-simulate` respects `-always` and shows the real diff without saving.

Verified in a full dry run: **112 pairs over 113 pages, 113 edits, 0 refusals,
0 errors.** Every old text in the file was re-checked against the live wikitext
immediately before that run, so each pair fires on exactly the page it belongs
to.

### Run as the main account, not the bot

The run uses **`1Veertje`** (`-user:1Veertje`), not `1VeertjeBot`. The bot
account is only in `*`/`user` on enwiki, while the main account is
`extendedconfirmed` — which matters for the two semi-protected pages
(`Miley Cyrus`, `Big Time Rush (group)`: `edit=autoconfirmed`). A bot password
for `1Veertje` already exists in `user-password.py`, so no extra config is
needed.

Always pass `-family:wikipedia -lang:en`; without them pywikibot falls back to
the `commons` family in `user-config.py` and every page is reported missing.

### Never let a pair add a parameter that is already there

Citation/CS1 treats `last`/`last1`/`author`, `first`/`first1`,
`archive-url`/`archiveurl`, `archive-date`/`archivedate` and
`access-date`/`accessdate` as the *same* parameter. An unconditional append
therefore renders a visible warning in the article:

```
{{cite web}}: More than one of |last1= and |last= specified (help);
More than one of |first1= and |first= specified (help)
```

19 of the 112 pairs originally did this, hitting 25 of the 113 pages. They are
now deduplicated inside the replacement text (`fix_pairs.py`). The match count
is unchanged (119 replacements over 113 pages), and a rendered check confirms the
warning is gone.

Guard before publishing: walk each replacement text and make sure no logical
parameter appears twice, using the alias map in `fix_pairs.py`.

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
