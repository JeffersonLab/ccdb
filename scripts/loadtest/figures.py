#!/usr/bin/env python3
"""The figures of the load test (docs/deployment/scaling.md), drawn as SVG from the client.py reports.

    python scripts/loadtest/figures.py [RESULTS_DIR] --svg DIR [--png DIR]

Three figures anyone can read, bars with the number at the tip, no logarithmic axes, light and dark versions:
- delivered: of 1 000 and of 20 000 jobs starting together, how many got their constants, per configuration;
- wait: how long one job waits for its 200 tables, per configuration, at 1 000 jobs (SQLite from its own runs);
- requests: how many times the database (or the API behind the cache) was asked, for 1 000 jobs.
PNG output needs rsvg-convert (librsvg). report.py embeds the light SVGs in the page; the PNGs are for slides.
Colors: the validated categorical palette of the dataviz reference (slots 1-4), text and grid tokens; the same
drawing in both themes, with each theme's own steps.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

FONT = "'Noto Sans', 'DejaVu Sans', 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "secondary": "#52514e", "grid": "#e9e8e3", "axis": "#c3c2b7",
              "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]},
    "dark": {"surface": "#1a1a19", "ink": "#f0efec", "secondary": "#c3c2b7", "grid": "#2a2a28", "axis": "#383835",
             "series": ["#3987e5", "#d95926", "#199e70", "#c98500"]},
}

# Every configuration with a plain name, in a fixed order (color follows the configuration, never its rank)
CONFIGURATIONS = [
    ("mysql", "Jobs ask MySQL directly"),
    ("api", "Jobs ask the HTTP API, no cache"),
    ("api-nginx", "Jobs ask the API through a cache, table by table"),
    ("bundle-nginx", "Jobs download a run bundle through a cache"),
    ("sqlite", "Jobs read a SQLite copy on their own node"),
    ("sqlite-analyze", "The same SQLite copy after ANALYZE"),
]
SERVER_CONFIGURATIONS = CONFIGURATIONS[:4]


def load(directory):
    """{label: [report, …] by jobs}; files without a label (manifests) are skipped"""
    runs = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        with open(path) as stream:
            report = json.load(stream)
        if "label" in report:
            runs.setdefault(report["label"], []).append(report)
    for reports in runs.values():
        reports.sort(key=lambda report: report["jobs"])
    return runs


def seconds(value, decimals=None):
    """A duration for an axis or a label: 65 ms, 1 s, 1.2 s, 17 s, 780 s; decimals forces that many on seconds"""
    if value < 0.0995:
        return "{0:.0f} ms".format(value * 1000) if value >= 0.0095 else "{0:g} ms".format(round(value * 1000, 1))
    if value < 0.9995:
        return "{0:.0f} ms".format(value * 1000)
    if decimals is not None:
        return "{0:,.{1}f} s".format(value, decimals).replace(",", " ")
    if value < 9.995:
        return "{0:g} s".format(round(value, 1))
    return "{0:,.0f} s".format(value).replace(",", " ")


def count(value):
    return "{0:,}".format(value).replace(",", " ")


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    """A small SVG writer with the theme's tokens"""

    def __init__(self, width, height, theme, title):
        self.t = THEMES[theme]
        self.width, self.height = width, height
        self.parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {0} {1}" width="{0}" height="{1}" role="img" '
                      'aria-label="{2}" font-family="{3}">'.format(width, height, esc(title), FONT),
                      '<rect width="{0}" height="{1}" rx="0" fill="{2}"/>'.format(width, height, self.t["surface"])]

    def text(self, x, y, text, size=12, color=None, anchor="start", weight="normal", tabular=False):
        style = ' font-variant-numeric="tabular-nums"' if tabular else ""
        self.parts.append('<text x="{0:.1f}" y="{1:.1f}" font-size="{2}" fill="{3}" text-anchor="{4}" font-weight="{5}"{6}>{7}</text>'.format(
            x, y, size, color or self.t["ink"], anchor, weight, style, esc(text)))

    def line(self, x1, y1, x2, y2, color, width=1, cap="butt"):
        self.parts.append('<line x1="{0:.1f}" y1="{1:.1f}" x2="{2:.1f}" y2="{3:.1f}" stroke="{4}" stroke-width="{5}" stroke-linecap="{6}"/>'.format(
            x1, y1, x2, y2, color, width, cap))

    def polyline(self, points, color):
        self.parts.append('<polyline fill="none" stroke="{0}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="{1}"/>'.format(
            color, " ".join("{0:.1f},{1:.1f}".format(x, y) for x, y in points)))

    def marker(self, x, y, color, hollow=False, radius=5):
        # a 2 px ring in the surface color keeps a marker legible on a line or over another marker
        self.parts.append('<circle cx="{0:.1f}" cy="{1:.1f}" r="{2}" fill="{3}" stroke="{4}" stroke-width="2"/>'.format(
            x, y, radius + 1, self.t["surface"], self.t["surface"]))
        if hollow:
            self.parts.append('<circle cx="{0:.1f}" cy="{1:.1f}" r="{2}" fill="{3}" stroke="{4}" stroke-width="2"/>'.format(
                x, y, radius - 1, self.t["surface"], color))
        else:
            self.parts.append('<circle cx="{0:.1f}" cy="{1:.1f}" r="{2}" fill="{3}"/>'.format(x, y, radius, color))

    def swatch(self, x, y, color):
        self.line(x, y, x + 18, y, color, 2, "round")
        self.parts.append('<circle cx="{0:.1f}" cy="{1:.1f}" r="4" fill="{2}"/>'.format(x + 9, y, color))

    def done(self):
        return "\n".join(self.parts + ["</svg>"]) + "\n"


import math  # noqa: E402

DELIVERED_COMPLETE = 0.95        # a run counts as complete when this share of its jobs got their constants
PANELS = (("a", "Jobs that got their constants"), ("b", "Wait per job"), ("c", "Requests reaching the database"))


def complete_runs(runs, label):
    """The runs of a configuration whose jobs were served, by jobs"""
    return [report for report in runs.get(label, []) if (1 - (report["result"]["error_rate"] or 0)) >= DELIVERED_COMPLETE]


def decades(low, high):
    first, last = math.floor(math.log10(low)), math.ceil(math.log10(high * 1.0001))
    return [10 ** power for power in range(first, max(last, first + 1) + 1)]


def compact(value):
    """1 000 → 1k, 1 000 000 → 1M, for axis ticks"""
    if value >= 1e6:
        return "{0:g}M".format(value / 1e6)
    if value >= 1e3:
        return "{0:g}k".format(value / 1e3)
    return "{0:g}".format(value)


class Panel:
    """One panel of the scaling figure: a log x axis of jobs, a linear or log y axis"""

    def __init__(self, svg, x, y, width, height, x_ticks, y_ticks, log_y, letter, title):
        self.svg, self.t = svg, svg.t
        self.x, self.y, self.width, self.height = x, y, width, height
        self.x_ticks, self.y_ticks, self.log_y = x_ticks, y_ticks, log_y
        svg.text(x, y - 14, letter, 13, self.t["ink"], weight="700")
        svg.text(x + 14, y - 14, title, 12.5, self.t["ink"], weight="600")

    def px(self, jobs):
        low, high = math.log10(self.x_ticks[0]), math.log10(self.x_ticks[-1])
        return self.x + (math.log10(jobs) - low) / (high - low) * self.width

    def py(self, value):
        if self.log_y:
            low, high = math.log10(self.y_ticks[0]), math.log10(self.y_ticks[-1])
            return self.y + (high - math.log10(value)) / (high - low) * self.height
        low, high = self.y_ticks[0], self.y_ticks[-1]
        return self.y + (high - value) / (high - low) * self.height

    def axes(self, y_label, x_tick_labels=True):
        for tick, label in self.y_ticks_labeled():
            self.svg.line(self.x, self.py(tick), self.x + self.width, self.py(tick), self.t["grid"], 1)
            self.svg.text(self.x - 8, self.py(tick) + 4, label, 10.5, self.t["secondary"], "end", tabular=True)
        self.svg.line(self.x, self.y + self.height, self.x + self.width, self.y + self.height, self.t["axis"], 1)
        for tick in self.x_ticks:
            self.svg.line(self.px(tick), self.y + self.height, self.px(tick), self.y + self.height + 4, self.t["axis"], 1)
            if x_tick_labels:
                self.svg.text(self.px(tick), self.y + self.height + 17, compact(tick), 10.5, self.t["secondary"], "middle", tabular=True)

    def y_ticks_labeled(self):
        return [(tick, self.y_format(tick)) for tick in self.y_ticks]

    def series(self, points, color):
        """points: [(jobs, value)] in jobs order; a line through them and a ringed marker at each"""
        coordinates = [(self.px(jobs), self.py(value)) for jobs, value in points]
        if len(coordinates) > 1:
            self.svg.polyline(coordinates, color)
        for cx, cy in coordinates:
            self.svg.marker(cx, cy, color, radius=4.5)

    def reference(self, value, label):
        """A thin horizontal reference line with a short label at its right end"""
        y = self.py(value)
        self.svg.line(self.x, y, self.x + self.width, y, self.t["secondary"], 1)
        self.svg.text(self.x + self.width - 4, y - 5, label, 10, self.t["secondary"], "end")


def scaling_figure(runs, theme="light", panels=("a", "b", "c")):
    """The scaling figure: panels a (delivered share, linear), b (median wait, log) and c (requests, log) on one
    log axis of jobs; the legend once at the top; a path that stops delivering ends in b and c"""
    panel_w, panel_h, gap, left, top = 300, 230, 64, 64, 78
    count_panels = len(panels)
    width = left + count_panels * panel_w + (count_panels - 1) * gap + 24
    height = top + panel_h + 56
    svg = Svg(width, height, theme, "Scaling with the number of jobs: delivered share, wait per job and database requests")
    t = svg.t

    jobs_all = sorted({report["jobs"] for label, _ in SERVER_CONFIGURATIONS for report in runs.get(label, [])})
    x_ticks = jobs_all or [1000, 20000]

    # legend
    x = left
    for index, (label, name) in enumerate(SERVER_CONFIGURATIONS):
        svg.swatch(x, 26, t["series"][index])
        svg.text(x + 24, 30, name, 11, t["secondary"])
        x += 24 + 5.8 * len(name) + 26

    px = left
    for key in panels:
        letter, title = next(panel for panel in PANELS if panel[0] == key)
        if key == "a":
            panel = Panel(svg, px, top, panel_w, panel_h, x_ticks, [0, 25, 50, 75, 100], False, letter, title)
            panel.y_format = lambda tick: "{0:g} %".format(tick)
            panel.axes("")
            for index, (label, name) in enumerate(SERVER_CONFIGURATIONS):
                points = [(r["jobs"], 100.0 * (1 - (r["result"]["error_rate"] or 0))) for r in runs.get(label, [])]
                if points:
                    panel.series(points, t["series"][index])
        elif key == "b":
            values = [r["result"]["job_duration_s"]["median"] for label, _ in SERVER_CONFIGURATIONS for r in complete_runs(runs, label)]
            for label in ("sqlite", "sqlite-analyze"):
                values += [r["result"]["job_duration_s"]["median"] for r in runs.get(label, [])]
            y_ticks = decades(min(values), max(values)) if values else [0.01, 1000]
            panel = Panel(svg, px, top, panel_w, panel_h, x_ticks, y_ticks, True, letter, title)
            panel.y_format = seconds
            panel.axes("")
            for label, text in (("sqlite", "local SQLite file"), ("sqlite-analyze", "the same file after ANALYZE")):
                if runs.get(label):
                    panel.reference(runs[label][-1]["result"]["job_duration_s"]["median"], text)
            for index, (label, name) in enumerate(SERVER_CONFIGURATIONS):
                points = [(r["jobs"], r["result"]["job_duration_s"]["median"]) for r in complete_runs(runs, label)]
                if points:
                    panel.series(points, t["series"][index])
        else:
            values = [r["result"]["backend_requests"] for label, _ in SERVER_CONFIGURATIONS for r in complete_runs(runs, label)]
            y_ticks = decades(max(min(values), 1), max(values)) if values else [10, 1e6]
            panel = Panel(svg, px, top, panel_w, panel_h, x_ticks, y_ticks, True, letter, title)
            panel.y_format = compact
            panel.axes("")
            for index, (label, name) in enumerate(SERVER_CONFIGURATIONS):
                points = [(r["jobs"], r["result"]["backend_requests"]) for r in complete_runs(runs, label)]
                if points:
                    panel.series(points, t["series"][index])
        px += panel_w + gap
    svg.text(left + (width - left - 24) / 2, height - 14, "jobs starting within 5 minutes", 11, t["secondary"], "middle")
    return svg.done()


def panel_figure(key):
    def make(runs, theme="light"):
        return scaling_figure(runs, theme, panels=(key,))
    return make


FIGURES = [("scaling", scaling_figure), ("scaling_delivered", panel_figure("a")), ("scaling_wait", panel_figure("b")),
           ("scaling_requests", panel_figure("c"))]


def figure_files(runs):
    """{file name: svg text} for both themes"""
    files = {}
    for name, make in FIGURES:
        files[name + ".svg"] = make(runs, "light")
        files[name + "_dark.svg"] = make(runs, "dark")
    return files


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("results", nargs="?", default=os.path.join(here, "results"))
    parser.add_argument("--svg", required=True, help="directory for the SVG files")
    parser.add_argument("--png", help="directory for PNG renderings at 2x (needs rsvg-convert)")
    args = parser.parse_args()
    runs = load(args.results)
    os.makedirs(args.svg, exist_ok=True)
    if args.png:
        os.makedirs(args.png, exist_ok=True)
    for name, text in figure_files(runs).items():
        path = os.path.join(args.svg, name)
        with open(path, "w") as stream:
            stream.write(text)
        if args.png:
            png = os.path.join(args.png, name[:-4] + ".png")
            subprocess.check_call(["rsvg-convert", "--zoom", "2", "--output", png, path])
    print("figures: " + ", ".join(name for name, _ in FIGURES) + (" (SVG and PNG)" if args.png else " (SVG)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
