"""Tests of check_links.py: each builds a small docsify site in a temporary directory.

Run from the repository root:  python3 -m unittest discover -s scripts/docs -p 'test_*.py'
"""

import contextlib
import io
import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_links  # noqa: E402

INDEX_HTML = """<script>
    window.$docsify = {
        homepage: 'index.md',
        loadSidebar: true,
    }
</script>
"""


class SiteTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.docs = os.path.join(self.temp_dir.name, "docs")
        os.makedirs(self.docs)
        self.write("index.html", INDEX_HTML)
        self.write("index.md", "# Home\n\n## Quick start\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write(self, site_path, text):
        path = os.path.join(self.docs, *site_path.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(textwrap.dedent(text))

    def broken(self):
        """{(site path, line, link): reason} of every broken link."""
        return {(os.path.relpath(path, self.docs).replace(os.sep, "/"), line, link): reason
                for path, line, link, reason in check_links.check_site(self.docs)}


class TestRouteResolution(SiteTestCase):

    def test_links_resolve_from_the_docs_root(self):
        self.write("apis/cpp.md", "# C++\n")
        self.write("apis/jana.md", "# JANA\n\nSee [C++](cpp.md) and [C++ again](apis/cpp.md) and [no ext](apis/cpp).\n")
        broken = self.broken()
        self.assertEqual(list(broken), [("apis/jana.md", 3, "cpp.md")])
        self.assertIn("docs/cpp.md does not exist", broken[("apis/jana.md", 3, "cpp.md")])
        self.assertIn("from the docs root", broken[("apis/jana.md", 3, "cpp.md")])

    def test_parent_directory_leaves_the_site(self):
        self.write("get-started/installation.md", "# Installation\n")
        self.write("apis/python.md", "# Python\n\n[Install](../get-started/installation.md)\n"
                                     "[Install too](./get-started/installation.md)\n"
                                     "[Up and down](apis/../get-started/installation.md)\n")
        broken = self.broken()
        self.assertEqual(list(broken), [("apis/python.md", 3, "../get-started/installation.md")])
        self.assertIn("'..' leaves the docs site", broken[("apis/python.md", 3, "../get-started/installation.md")])

    def test_homepage_and_readme(self):
        self.write("cli.md", "# CLI\n\n[Home](index.md) [Root](/) [Readme](README.md) [Start](index.md#quick-start)\n")
        self.assertEqual(self.broken(), {})

    def test_relative_path_option(self):
        self.write("index.html", INDEX_HTML.replace("loadSidebar: true,", "loadSidebar: true, relativePath: true,"))
        self.write("apis/cpp.md", "# C++\n")
        self.write("apis/jana.md", "# JANA\n\n[C++](cpp.md) [Home](../index.md) [Out](../../x.md)\n")
        self.assertEqual(list(self.broken()), [("apis/jana.md", 3, "../../x.md")])

    def test_file_link_needs_ignore(self):
        self.write("images/plot.svg", "<svg/>")
        self.write("cli.md", "# CLI\n\n[plot](images/plot.svg)\n[plot](images/plot.svg ':ignore')\n"
                             "[gone](images/gone.svg ':ignore')\n")
        broken = self.broken()
        self.assertEqual(sorted(broken), [("cli.md", 3, "images/plot.svg"), ("cli.md", 5, "images/gone.svg")])
        self.assertIn("add ':ignore'", broken[("cli.md", 3, "images/plot.svg")])

    def test_external_links_are_not_checked(self):
        self.write("cli.md", "# CLI\n\n[a](https://example.org/x.md) [b](mailto:a@b.c) [c](//host/x) "
                             "<https://example.org>\n")
        self.assertEqual(self.broken(), {})


class TestSidebar(SiteTestCase):

    def test_sidebar_names_only_existing_pages(self):
        self.write("cli.md", "# CLI\n\n## Commands overview\n")
        self.write("_sidebar.md", """\
            - [GitHub](https://github.com/JeffersonLab/ccdb ':target=_blank')
            - [Introduction](index.md "CCDB")
            - [CLI](cli.md)
            - [Commands](cli.md#commands-overview)
            - [Upgrade](deployment/upgrade-2.5.md)
            - [Missing anchor](cli.md#commands)
            """)
        self.assertEqual(sorted(self.broken()), [("_sidebar.md", 5, "deployment/upgrade-2.5.md"),
                                                 ("_sidebar.md", 6, "cli.md#commands")])


class TestAnchors(SiteTestCase):

    def test_local_and_remote_anchors(self):
        self.write("cli.md", """\
            # Command line

            ## Connecting to DB

            [here](#connecting-to-db) [nowhere](#connecting) [there](index.md#quick-start)
            [query form](index.md?id=quick-start) [bad](index.md#quick)
            """)
        broken = self.broken()
        self.assertEqual(sorted(broken), [("cli.md", 5, "#connecting"), ("cli.md", 6, "index.md#quick")])
        self.assertIn("no heading with id 'connecting' in docs/cli.md", broken[("cli.md", 5, "#connecting")])

    def test_duplicate_headings_get_numbers(self):
        self.write("schema.md", """\
            # Schema

            ## columns

            ## Columns

            ## columns

            [1](#columns) [2](#columns-1) [3](#columns-2) [4](#columns-3)
            """)
        self.assertEqual(list(self.broken()), [("schema.md", 9, "#columns-3")])

    def test_slugify_rules(self):
        self.write("page.md", """\
            # Page

            ## Utilities & scripts

            ## Option E: cleo (Poetry's CLI library)

            ## Upgrade — what changes

            ## 1. What the CLI is

            ## The `vers -l` output

            ## **Bold** and _emphasis_ in snake_case_name

            ## [Linked](index.md) heading

            ## Custom :id=my-anchor

            Setext heading
            --------------

            [a](#utilities-amp-scripts) [b](#option-e-cleo-poetry39s-cli-library) [c](#upgrade-what-changes)
            [d](#_1-what-the-cli-is) [e](#the-vers-l-output) [f](#bold-and-emphasis-in-snake_case_name)
            [g](#linked-heading) [h](#my-anchor) [i](#setext-heading)
            """)
        self.assertEqual(self.broken(), {})

    def test_html_ids_are_anchors(self):
        self.write("page.md", '# Page\n\n<a id="legacy-anchor"></a>\n\n[x](#legacy-anchor)\n')
        self.assertEqual(self.broken(), {})

    def test_percent_encoded_anchor(self):
        self.write("page.md", "# Page\n\n## Größe\n\n[x](#gr%C3%B6%C3%9Fe)\n")
        self.assertEqual(self.broken(), {})


class TestImagesAndFiles(SiteTestCase):

    def test_images_resolve_from_the_page_directory(self):
        self.write("images/a.png", "png")
        self.write("concepts/concepts.md", "# Concepts\n\n![a](../images/a.png)\n![b](images/a.png)\n")
        self.write("cli.md", "# CLI\n\n![a](images/a.png ':size=50')\n![out](../a.png)\n")
        broken = self.broken()
        self.assertEqual(sorted(broken), [("cli.md", 4, "../a.png"), ("concepts/concepts.md", 4, "images/a.png")])
        self.assertIn("docs/concepts/images/a.png does not exist", broken[("concepts/concepts.md", 4, "images/a.png")])

    def test_image_inside_a_link(self):
        self.write("images/badge.svg", "<svg/>")
        self.write("cli.md", "# CLI\n\n[![badge](images/badge.svg)](index.md) [![gone](images/gone.svg)](cli.md)\n")
        self.assertEqual(list(self.broken()), [("cli.md", 3, "images/gone.svg")])

    def test_raw_html_resolves_from_the_docs_root(self):
        self.write("images/a.png", "png")
        self.write("concepts/page.md", '# Page\n\n<img src="images/a.png">\n<img src="../images/a.png">\n'
                                       '<a href="#/cli">CLI</a>\n')
        self.assertEqual(sorted(self.broken()), [("concepts/page.md", 4, "../images/a.png"),
                                                 ("concepts/page.md", 5, "#/cli")])


class TestCode(SiteTestCase):

    def test_code_is_not_checked(self):
        self.write("cli.md", """\
            # CLI

            ```bash
            # not a heading
            echo "[x](missing.md)"
            ```

            ~~~
            [y](missing.md)
            ~~~

            Inline `[z](missing.md)` code and ``[w](missing.md)`` too.

            [anchor](#not-a-heading)
            """)
        self.assertEqual(list(self.broken()), [("cli.md", 14, "#not-a-heading")])

    def test_reference_definitions(self):
        self.write("cli.md", "# CLI\n\nSee [the home][home] and [lost][lost].\n\n[home]: index.md\n[lost]: lost.md\n")
        self.assertEqual(list(self.broken()), [("cli.md", 6, "lost.md")])


class TestDocsifyDetails(SiteTestCase):
    """Cases where marked and docsify 4 behave in ways a line-by-line reading misses."""

    def test_link_text_wrapped_onto_two_lines(self):
        self.write("cli.md", "# CLI\n\nSee [across two\nlines](nowhere.md) here.\n\n"
                             "A code span `[c](nowhere-code.md)\nstill code` is no link.\n")
        self.assertEqual(list(self.broken()), [("cli.md", 3, "nowhere.md")])

    def test_raw_html_link_to_a_markdown_file(self):
        self.write("cli.md", '# CLI\n\n<a href="cli.md">source</a> <a href="#/cli">page</a>\n')
        broken = self.broken()
        self.assertEqual(list(broken), [("cli.md", 3, "cli.md")])
        self.assertIn("opens the Markdown source", broken[("cli.md", 3, "cli.md")])

    def test_ignored_link_starting_with_dot_slash(self):
        self.write("images/a.png", "png")
        self.write("cli.md", "# CLI\n\n[a](./images/a.png ':ignore') [b](images/a.png ':ignore')\n")
        broken = self.broken()
        self.assertEqual(list(broken), [("cli.md", 3, "./images/a.png")])
        self.assertIn("drop the './'", broken[("cli.md", 3, "./images/a.png")])

    def test_name_attribute_is_no_anchor(self):
        self.write("page.md", '# Page\n\n<a name="by-name"></a> <p id="by-id"></p>\n\n[x](#by-name) [y](#by-id)\n')
        self.assertEqual(list(self.broken()), [("page.md", 5, "#by-name")])

    def test_setext_heading_only_at_block_start(self):
        self.write("page.md", """\
            # Page

            Line one
            line two
            ========

            > ## Quoted heading

            [x](#line-two) [y](#quoted-heading)
            """)
        self.assertEqual(list(self.broken()), [("page.md", 9, "#line-two")])

    def test_markdown_link_anchor_is_lower_cased(self):
        self.write("page.md", """\
            # Page

            ## Twice

            ## Twice

            [x](#Twice-1) [y](index.md#Quick-Start)
            <a href="#/page?id=Twice-1">raw</a>
            """)
        self.assertEqual(list(self.broken()), [("page.md", 8, "#/page?id=Twice-1")])

    def test_heading_ids_drop_tags_and_ignore_markers(self):
        self.write("page.md", """\
            # Page

            ## Width <span style="width:10px">x</span>

            ## Plain heading {docsify-ignore}

            ## Hidden heading <!-- {docsify-ignore} -->

            [a](#width-x) [b](#plain-heading) [c](#hidden-heading)
            """)
        self.assertEqual(self.broken(), {})

    def test_comments_and_escaped_brackets_are_no_links(self):
        self.write("cli.md", """\
            # CLI

            <!-- [a](missing-a.md) -->
            <!--
            [b](missing-b.md)
            -->
            Escaped \\[c](missing-c.md) text, and [d](missing-d.md).
            """)
        self.assertEqual(list(self.broken()), [("cli.md", 7, "missing-d.md")])


class TestMain(SiteTestCase):

    def test_output_and_exit_code(self):
        self.write("apis/jana.md", "# JANA\n\n[C++](cpp.md)\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = check_links.main([self.docs])
        self.assertEqual(exit_code, 1)
        line = output.getvalue().strip()
        self.assertEqual(len(line.splitlines()), 1)
        self.assertTrue(line.endswith("jana.md:3: cpp.md: docs/cpp.md does not exist (docsify resolves links from "
                                      "the docs root)"), line)

    def test_clean_site_exits_zero(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = check_links.main([self.docs])
        self.assertEqual((exit_code, output.getvalue()), (0, ""))


if __name__ == "__main__":
    unittest.main()
