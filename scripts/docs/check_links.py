#!/usr/bin/env python3
"""Check the relative links, images and anchors of the docsify site under docs/.

Every Markdown page under the docs directory is read, and every link is resolved the way docsify 4 resolves
it in the browser, with the options set in the site's index.html (`homepage`, `relativePath`):

- A link `[text](path.md#heading)` is a route. Without `relativePath` docsify resolves it from the docs root,
  whatever directory the linking page is in: `jana.md` on apis/cpp.md opens docs/jana.md, and `../apis/cpp.md`
  climbs out of the site, which is served from a subpath (/ccdb/ on GitHub Pages).
- An image `![alt](path.png)` is resolved from the directory of the page that shows it.
- An anchor `#heading` or `?id=heading` must equal the id docsify gives a heading of the target page: its slug
  of the heading as marked renders it, with `-1`, `-2` added to repeated headings. docsify lower-cases the ASCII
  letters of the anchor of a Markdown link; only `id` attributes count, since docsify scrolls by id.
- A link titled `':ignore'`, and a raw HTML `<a href>` or `<img src>`, is left to the browser, which resolves it
  from index.html, that is from the docs root. A raw `<a href>` to a .md file opens the Markdown source, and an
  ignored link that starts with `./` becomes a route under the open page: both are reported.

External links (anything with `:` or `//`, as docsify's isAbsolutePath says) are not fetched.

Usage: check_links.py [DOCS_DIR]      (default: the docs directory of this repository)
Prints one line per broken link, `file:line: link: reason`, and exits 1 when there is any.
"""

import argparse
import os
import posixpath
import re
import sys
from urllib.parse import unquote

# --- Markdown scanning ---------------------------------------------------------------------------------------------

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
ATX_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
SETEXT_UNDERLINE_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
# a line that cannot be the text of a setext heading: blank, a list item, a quote, a table row, a heading, a rule
NOT_SETEXT_TEXT_RE = re.compile(r"^\s*$|^\s*([-*+]|\d+[.)])\s|^\s*>|^\s*\||^ {0,3}#|^ {0,3}([-*_])(\s*\2){2,}\s*$")

# destination: <...>, or a run without spaces that may hold one level of balanced parentheses
DESTINATION = r"(<[^>\n]*>|[^\s()]*(?:\([^\s()]*\)[^\s()]*)*)"
TITLE = r"""(?:\s+("[^"]*"|'[^']*'|\([^)]*\)))?"""
# link text: brackets nested one level deep, so `[![badge](img.svg)](page.md)` is one link holding one image
IMAGE_RE = re.compile(r"(?<!\\)!\[[^\]]*\]\(\s*" + DESTINATION + TITLE + r"\s*\)")
LINK_RE = re.compile(r"(?<![!\\])\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*" + DESTINATION + TITLE + r"\s*\)")
REFERENCE_DEFINITION_RE = re.compile(r"^ {0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)" + TITLE + r"\s*$")
HTML_ATTRIBUTE_RE = re.compile(r"<(a|img)\b[^>]*?\b(href|src)\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE)
HTML_ID_RE = re.compile(r"<[a-zA-Z][^>]*?\bid\s*=\s*(\"[^\"]*\"|'[^']*')")
CODE_SPAN_RE = re.compile(r"(`+)(.+?)(?<!`)\1(?!`)")
# the same inside one block, where a code span may wrap onto the next line
CODE_SPAN_ML_RE = re.compile(r"(`+)(.+?)(?<!`)\1(?!`)", re.S)


def strip_code_spans(line):
    """The line with every inline code span blanked, so links shown as code are not checked."""
    return CODE_SPAN_RE.sub(lambda match: " " * len(match.group(0)), line)


def markdown_lines(text):
    """(line number, line) of every line outside fenced code blocks."""
    fence = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)
                continue
            yield number, line
        elif match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) \
                and not line.strip()[len(match.group(1)):].strip():
            fence = None


class Reference:
    """One link or image of a page."""

    def __init__(self, line, kind, target, title="", tag=""):
        self.line = line
        self.kind = kind          # "link", "image" or "html" (a raw <a href> or <img src>)
        self.target = target
        self.title = title
        self.tag = tag            # "a" or "img" for a raw HTML reference


def unwrap(destination):
    return destination[1:-1] if destination.startswith("<") and destination.endswith(">") else destination


def blocks(text):
    """(first line number, text) of every run of non-blank lines outside fenced code, HTML comments blanked."""
    text = re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    block, start = [], None
    for number, line in markdown_lines(text):
        if line.strip():
            if start is None or number != start + len(block):
                if block:
                    yield start, "\n".join(block)
                block, start = [], number
            block.append(line)
        else:
            if block:
                yield start, "\n".join(block)
            block, start = [], None
    if block:
        yield start, "\n".join(block)


def find_references(text):
    """Every link, image and raw HTML reference of a page. Each block is scanned as one text, because marked
    renders a link whose text wraps onto the next line."""
    references = []
    for first, block in blocks(text):
        block = CODE_SPAN_ML_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), block)

        def line_of(position):
            return first + block.count("\n", 0, position)

        for match in IMAGE_RE.finditer(block):
            references.append(Reference(line_of(match.start()), "image", unwrap(match.group(1)), match.group(2) or ""))
        without_images = IMAGE_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), block)
        for match in LINK_RE.finditer(without_images):
            references.append(Reference(line_of(match.start()), "link", unwrap(match.group(1)), match.group(2) or ""))
        for offset, line in enumerate(block.split("\n")):
            match = REFERENCE_DEFINITION_RE.match(line)
            if match:
                references.append(Reference(first + offset, "link", unwrap(match.group(1)), match.group(2) or ""))
        for match in HTML_ATTRIBUTE_RE.finditer(block):
            references.append(Reference(line_of(match.start()), "html", match.group(3)[1:-1], tag=match.group(1).lower()))
    references.sort(key=lambda reference: reference.line)
    return references


# --- Heading ids, as docsify 4 makes them --------------------------------------------------------------------------

# docsify's slugify (src/core/render/slugify.js): the punctuation it removes, General Punctuation (the em dash among
# it) and Supplemental Punctuation included
SLUG_PUNCTUATION_RE = re.compile(r"[\u2000-\u206F\u2E00-\u2E7F\\'!\"#$%&()*+,./:;<=>?@\[\]^`{|}~]")
# docsify's getAndRemoveConfig: ` :id=name` and similar options inside a heading
HEADING_OPTION_RE = re.compile(r"(?:^|\s):([\w-]+:?)=?([\w%-]+)?")
ENTITY_RE = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|\w+);")


def escape_html(text):
    """marked's escape(): `&` that starts no entity, `<`, `>`, `"` and `'` become entities."""
    text = re.sub(r"&(?!#?\w+;)", "&amp;", text)
    return text.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


INLINE_HTML_RE = re.compile(r"</?[A-Za-z][^<>]*>|<!--.*?-->")


def render_heading_text(text):
    """The heading's inline Markdown as marked renders it, to the precision slugify needs: code spans become
    <code>, emphasis markers and link syntax go, images and backslash escapes are resolved, text is escaped."""
    pieces = []
    position = 0
    for match in CODE_SPAN_RE.finditer(text):
        pieces.append(render_inline_text(text[position:match.start()]))
        pieces.append("<code>" + escape_html(match.group(2).strip()) + "</code>")
        position = match.end()
    pieces.append(render_inline_text(text[position:]))
    return "".join(pieces)


def render_inline_text(text):
    text = IMAGE_RE.sub("", text)                                        # an <img> tag with its src: see README
    text = re.sub(r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\([^)]*\)", r"\1", text)  # a link keeps its text
    text = re.sub(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    text = re.sub(r"\*(?=\S)(.+?)(?<=\S)\*", r"\1", text)
    text = re.sub(r"(?<![A-Za-z0-9])_(?=\S)(.+?)(?<=\S)_(?![A-Za-z0-9])", r"\1", text)
    text = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"\1", text)
    # raw HTML stays as it is; everything else is text that marked escapes
    pieces = []
    position = 0
    for match in INLINE_HTML_RE.finditer(text):
        pieces.append(escape_html(unescape_backslashes(text[position:match.start()])))
        pieces.append(match.group(0))
        position = match.end()
    pieces.append(escape_html(unescape_backslashes(text[position:])))
    return "".join(pieces)


def unescape_backslashes(text):
    return re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", text)


class Slugger:
    """docsify's slugify with its per-page memory of slugs already given."""

    def __init__(self):
        self.counts = {}

    def slug(self, text):
        slug = text.strip()
        slug = re.sub(r"[A-Z]+", lambda match: match.group(0).lower(), slug)
        slug = re.sub(r"<[^>]+>", "", slug)
        slug = SLUG_PUNCTUATION_RE.sub("", slug)
        slug = re.sub(r"\s", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = re.sub(r"^([0-9])", r"_\1", slug)
        count = self.counts[slug] + 1 if slug in self.counts else 0
        self.counts[slug] = count
        return f"{slug}-{count}" if count else slug


def heading_id(rendered, slugger):
    """The id docsify's heading renderer gives: a `:id=name` option wins, else the slug of the text."""
    options = {}

    def take_option(match):
        key, value = match.group(1), match.group(2)
        if ":" in key:
            return match.group(0)
        options[key] = value.replace("&quot;", "") if value else True
        return ""

    text = HEADING_OPTION_RE.sub(take_option, rendered).strip()
    for marker in ("<!-- {docsify-ignore} -->", "{docsify-ignore}", "<!-- {docsify-ignore-all} -->", "{docsify-ignore-all}"):
        text = text.replace(marker, "", 1)
    explicit = options.get("id")
    return slugger.slug(explicit if isinstance(explicit, str) else text)


def headings(text):
    """(line number, raw heading text) of every ATX and setext heading outside code blocks."""
    found = []
    previous = None
    last_number, last_blank = 0, True
    for number, line in markdown_lines(text):
        starts_block = last_blank or number != last_number + 1      # after a blank line, a fence or the start
        last_number, last_blank = number, not line.strip()
        # marked renders an ATX heading inside a blockquote with an id too
        match = ATX_HEADING_RE.match(re.sub(r"^ {0,3}(?:> ?)+", "", line))
        if match:
            found.append((number, match.group(2) or ""))
            previous = None
            last_blank = True
            continue
        # marked 1.x (docsify 4) takes a setext heading only when its single text line starts a block
        if previous is not None and previous[2] and SETEXT_UNDERLINE_RE.match(line) \
                and not NOT_SETEXT_TEXT_RE.match(previous[1]):
            found.append((previous[0], previous[1].strip()))
            previous = None
            last_blank = True
            continue
        previous = (number, line, starts_block)
    return found


def page_ids(text):
    """Every id an anchor can reach on a page: the heading ids and the ids of raw HTML elements."""
    slugger = Slugger()
    ids = [heading_id(render_heading_text(heading), slugger) for _, heading in headings(text)]
    for _, line in markdown_lines(text):
        ids.extend(match.group(1)[1:-1] for match in HTML_ID_RE.finditer(strip_code_spans(line)))
    return ids


# --- Resolution, as docsify 4's router does it ---------------------------------------------------------------------

def is_absolute(target):
    """docsify's isAbsolutePath: a scheme, `mailto:` or a protocol-relative `//host` is external."""
    return ":" in target or "//" in target


class Site:
    def __init__(self, docs_dir):
        self.docs_dir = os.path.abspath(docs_dir)
        self.homepage, self.relative_path = read_config(os.path.join(self.docs_dir, "index.html"))
        self.ids = {}

    def exists(self, site_path):
        return os.path.isfile(os.path.join(self.docs_dir, *site_path.split("/")))

    def ids_of(self, site_path):
        if site_path not in self.ids:
            with open(os.path.join(self.docs_dir, *site_path.split("/")), encoding="utf-8") as page:
                self.ids[site_path] = page_ids(page.read())
        return self.ids[site_path]


def read_config(index_html):
    """`homepage` and `relativePath` of window.$docsify in index.html; docsify's defaults when absent."""
    homepage, relative_path = "README.md", False
    if os.path.isfile(index_html):
        with open(index_html, encoding="utf-8") as page:
            html = page.read()
        match = re.search(r"\bhomepage\s*:\s*['\"]([^'\"]+)['\"]", html)
        if match:
            homepage = match.group(1)
        match = re.search(r"\brelativePath\s*:\s*(true|false)", html)
        if match:
            relative_path = match.group(1) == "true"
    return homepage, relative_path


def route_of(site_path):
    """The route docsify shows a page under: docs/apis/cpp.md is /apis/cpp."""
    return "/" + re.sub(r"\.md$", "", site_path)


def split_anchor(target):
    """docsify's replaceSlug and parseQuery: the first `#` becomes `?id=`; returns (path, decoded id or None)."""
    target = target.replace("#", "?id=", 1)
    path, _, query = target.partition("?")
    anchor = None
    for parameter in query.split("&"):
        key, _, value = parameter.replace("+", " ").partition("=")
        if key == "id":
            anchor = unquote(value)
    return path, anchor


def normalize(site_path):
    """The path inside the site after the browser removes `.` and `..`, or None when it leaves the site."""
    normalized = posixpath.normpath(site_path.lstrip("/")) if site_path.strip("/") else "."
    if normalized == ".." or normalized.startswith("../"):
        return None
    return normalized


def check_route(site, page, target, compiled=True):
    """The reason a docsify route link is broken, or None. `page` is the linking page's path inside the site."""
    if target == site.homepage:
        target = "README"                      # docsify's link compiler maps the homepage link to the root
    local = target.startswith("#")
    path, anchor = split_anchor(target)
    if anchor is not None and compiled:
        # router.toURL writes the query with stringifyQuery, which lower-cases `id=value` (ASCII letters only,
        # since other characters are percent-encoded at that point)
        anchor = re.sub(r"[A-Z]+", lambda match: match.group(0).lower(), anchor)
    if local:
        path = route_of(page)
    path = re.sub(r"\.md$", "", path)
    if site.relative_path and not path.startswith("/"):
        path = posixpath.dirname(route_of(page)) + "/" + path

    # getFileName: `.md` is added unless the route ends in .md or .html; a trailing slash means its README.md
    if re.search(r"\.(md|html)$", path):
        file_path = path
    elif path.endswith("/") or path == "":
        file_path = path + "README.md"
    else:
        file_path = path + ".md"
    if file_path.strip("/") == "README.md":
        file_path = site.homepage
    resolved = normalize(file_path)
    if resolved is None:
        how = "the linking page's directory" if site.relative_path else "the docs root, not from the linking page"
        return f"'..' leaves the docs site (docsify resolves links from {how})"
    if not site.exists(resolved):
        where = "" if site.relative_path or "/" not in page else " (docsify resolves links from the docs root)"
        if re.search(r"\.\w+\.md$", file_path) and not path.endswith(".md"):
            return f"docsify loads it as page docs/{resolved}, which does not exist; add ':ignore' to link a file"
        return f"docs/{resolved} does not exist{where}"
    if anchor is not None and resolved.endswith(".md"):
        if page == "_sidebar.md" and local:
            return "an anchor-only link in _sidebar.md points into whichever page is open"
        ids = site.ids_of(resolved)
        if anchor not in ids:
            return f"no heading with id '{anchor}' in docs/{resolved}"
    return None


def check_file(site, base_dir, target):
    """The reason a link to a plain file is broken, or None. `base_dir` is the directory it resolves from."""
    path = target.split("#", 1)[0].split("?", 1)[0]
    if path.startswith("./"):
        path = path[2:]
    resolved = normalize(posixpath.join(base_dir, unquote(path)) if not path.startswith("/") else path)
    if resolved is None:
        return "'..' leaves the docs site"
    if not site.exists(resolved):
        return f"docs/{resolved} does not exist"
    return None


def check_reference(site, page, reference):
    target = reference.target.strip()
    if not target or is_absolute(target):
        return None
    if reference.kind == "image":
        # the image compiler: getPath(base, getParentPath(currentRoute), href), from the showing page's directory
        return check_file(site, posixpath.dirname(page), target)
    if reference.kind == "html":
        if target.startswith("#/"):
            return check_route(site, page, target[1:], compiled=False)
        if reference.tag == "a" and re.search(r"\.md(?:$|[?#])", target):
            return "a raw <a href> to a .md file opens the Markdown source, not the page; use '#/route' or a Markdown link"
        return check_file(site, "", target)
    if ":ignore" in reference.title:
        if target.startswith("./"):
            return "docsify turns './' in an ignored link into a route under the open page; drop the './'"
        return check_file(site, "", target)
    return check_route(site, page, target)


def pages(docs_dir):
    """Every Markdown page under docs_dir as a site path, sorted."""
    found = []
    for directory, subdirectories, files in os.walk(docs_dir):
        subdirectories.sort()
        for name in files:
            if name.endswith(".md"):
                found.append(os.path.relpath(os.path.join(directory, name), docs_dir).replace(os.sep, "/"))
    return sorted(found)


def check_site(docs_dir):
    """`(file, line, link, reason)` for every broken link under docs_dir."""
    site = Site(docs_dir)
    problems = []
    for page in pages(site.docs_dir):
        with open(os.path.join(site.docs_dir, *page.split("/")), encoding="utf-8") as page_file:
            text = page_file.read()
        for reference in find_references(text):
            reason = check_reference(site, page, reference)
            if reason:
                problems.append((os.path.join(site.docs_dir, *page.split("/")), reference.line, reference.target, reason))
    return problems


def main(argv=None):
    default_docs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs")
    parser = argparse.ArgumentParser(description="Check relative links, images and anchors of the docsify site.")
    parser.add_argument("docs_dir", nargs="?", default=default_docs, help="the docs directory (default: %(default)s)")
    options = parser.parse_args(argv)
    if not os.path.isdir(options.docs_dir):
        parser.error(f"no directory '{options.docs_dir}'")

    problems = check_site(options.docs_dir)
    for file_path, line, link, reason in problems:
        print(f"{os.path.relpath(file_path)}:{line}: {link}: {reason}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
