# Docs link check

`check_links.py` checks every Markdown page under `docs/` the way the docsify site resolves it: relative
links, anchors, images and other local files. External links are not fetched. Python 3.9 or newer,
standard library only.

```bash
# from the repository root
python3 scripts/docs/check_links.py docs
python3 -m unittest discover -s scripts/docs -p 'test_*.py'
```

It prints one line per broken link, `file:line: link: reason`, and exits with 1 when there is any. The
`Documentation` workflow runs the tests and the check before it deploys the site.

## Rules

The rules follow docsify 4 with the options set in `docs/index.html` (`homepage`, `relativePath`):

- **Links resolve from the docs root.** `relativePath` is not set, so `[JANA](jana.md)` on
  `docs/apis/cpp.md` opens `docs/jana.md`, and `../get-started/installation.md` climbs out of the site,
  which GitHub Pages serves under `/ccdb/`. Write every link from the docs root:
  `[JANA](apis/jana.md)`. A link to the homepage (`index.md`, `README.md`, `/`) opens `docs/index.md`.
- **Images resolve from the page's directory.** `![plot](../images/plot.png)` on `docs/concepts/x.md`
  shows `docs/images/plot.png`.
- **Anchors** (`page.md#id`, `#id`, `page.md?id=id`) must equal the id docsify gives a heading of the
  target page: lower case, punctuation removed (the em dash too), spaces turned into `-`, a leading digit
  prefixed with `_`, `-1`, `-2` added to repeated headings. docsify makes the id from the heading as
  marked renders it, so `&` becomes `amp` and `'` becomes `39`: `## Utilities & scripts` has the id
  `utilities-amp-scripts`. A heading option `:id=name` sets the id, and `{docsify-ignore}` is left out
  of it. docsify lower-cases the ASCII letters of a Markdown link's anchor, so `#Quick-Start` reaches
  `quick-start`; the anchor of a raw `<a href="#/page?id=...">` is compared as written. `id` attributes
  of raw HTML elements count too; `name` attributes do not, since docsify scrolls by id.
- **Links to other files.** docsify loads every link as a page and appends `.md`, so a link to
  `images/plot.svg` needs the `':ignore'` title; the file must exist. An ignored link must not start
  with `./`: docsify turns it into a route under the open page.
- **Raw HTML** `<a href>` and `<img src>` resolve from the docs root, as the browser resolves them from
  `index.html`. A raw `<a href>` to a `.md` file opens the Markdown source instead of the page, so it
  is reported; link to `#/route` or use a Markdown link.
- **`_sidebar.md`** is checked like any page, so it names only existing pages and headings.

Links inside fenced code blocks, inline code (also when it wraps onto the next line) and HTML
comments are not checked, nor escaped brackets (`\[x](y.md)`). A link whose text wraps onto the next
line is checked. Headings are ATX (`## Title`, also inside a blockquote) or setext (a single line of
text that starts a block, underlined with `===` or `---`); an image inside a heading is left out of its
id.

Known limits: links inside indented code blocks and inside HTML blocks (a `<div>` with no blank line
before the Markdown) are checked, although marked renders no link there.
