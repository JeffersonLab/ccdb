"""Unit tests of the load test scripts: the generator's distributions and determinism (make_db.py), the client's
plan and aggregation over a fixed sample (client.py), and the page's tables and charts (report.py).

    python -m unittest discover -s scripts/loadtest
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import client  # noqa: E402
import figures  # noqa: E402
import make_db  # noqa: E402
import report  # noqa: E402


class TestPlan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.shapes = make_db.load_profile()
        cls.layout = make_db.plan(cls.shapes, 0.05, 2026, 100000)

    def test_profile(self):
        self.assertEqual(len(self.shapes), 679)
        self.assertEqual(sum(shape[2] for shape in self.shapes), 821431)
        self.assertEqual(sum(shape[4] for shape in self.shapes), 235645)

    def test_every_table_once_with_scaled_assignments(self):
        self.assertEqual(len(self.layout), len(self.shapes))
        for table, shape in zip(self.layout, self.shapes):
            self.assertEqual(len(table["assignments"]), max(1, round(shape[2] * 0.05)))
            self.assertEqual((table["rows"], table["columns"], table["mean_set_bytes"]), (shape[0], shape[1], shape[3]))

    def test_shared_sets_as_surveyed(self):
        # tables large enough to share: the share of assignments that reuse a set is the surveyed one
        big = [(table, shape) for table, shape in zip(self.layout, self.shapes) if len(table["assignments"]) >= 200]
        assignments = sum(len(table["assignments"]) for table, _ in big)
        reused = sum(len(table["assignments"]) - table["sets"] for table, _ in big)
        expected = sum(len(table["assignments"]) * shape[4] / shape[2] for table, shape in big)
        self.assertGreater(assignments, 20000)
        self.assertAlmostEqual(reused / assignments, expected / assignments, delta=0.01)

    def test_run_ranges_and_times(self):
        for table in self.layout:
            first = table["assignments"][0]
            self.assertEqual((first[0], first[1]), (0, 99999))          # every run resolves
            for run_min, run_max, created, set_index in table["assignments"]:
                self.assertTrue(0 <= run_min <= run_max <= 99999)
                self.assertTrue(make_db.FIRST <= created <= make_db.LAST)
                self.assertLess(set_index, table["sets"])

    def test_deterministic(self):
        self.assertEqual(make_db.plan(self.shapes, 0.05, 2026, 100000), self.layout)
        self.assertNotEqual(make_db.plan(self.shapes, 0.05, 2027, 100000), self.layout)

    def test_vault_size(self):
        import random
        rng = random.Random(1)
        for rows, columns, mean in ((1, 1, 1), (10, 5, 400), (274, 2, 2935), (100, 6, 60000)):
            text = make_db.vault(rng, rows, columns, mean)
            self.assertEqual(len(text.split("|")), rows * columns)
            self.assertLess(abs(len(text) - mean), max(2, rows * columns))


class TestBuild(unittest.TestCase):

    def test_two_builds_hold_the_same_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            dumps = []
            for name in ("a", "b"):
                path = os.path.join(directory, name + ".sqlite")
                manifest = make_db.build("sqlite:///" + path, scale=0.002, tables=30)
                connection = sqlite3.connect(path)
                dumps.append("\n".join(connection.iterdump()))
                connection.close()
            self.assertEqual(dumps[0], dumps[1])
            self.assertEqual(len(manifest["tables"]), 30)
            connection = sqlite3.connect(path)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM assignments a JOIN constantSets s ON a.constantSetId = s.id "
                                                "JOIN typeTables t ON s.constantTypeId = t.id JOIN directories d ON t.directoryId = d.id "
                                                "WHERE d.name LIKE 'd%'").fetchone()[0], manifest["assignments"])
            connection.close()


class TestClient(unittest.TestCase):

    MANIFEST = {"runs": 100000, "campaign_time": "2026-01-01 00:00:00",
                "tables": [{"path": "/loadtest/d00/t{0:04d}".format(index)} for index in range(300)]}

    def test_job_plan(self):
        starts, runs, paths = client.job_plan(self.MANIFEST, 1000, 600, 100, 200, 7)
        self.assertEqual(len(starts), 1000)
        self.assertTrue(all(0 <= start < 600 for start in starts))
        self.assertEqual(sorted(set(runs)), [index * 1000 + 500 for index in range(100)])
        self.assertEqual(len(set(paths)), 200)
        self.assertEqual(client.job_plan(self.MANIFEST, 1000, 600, 100, 200, 7), (starts, runs, paths))

    def test_urls(self):
        bundle = client.job_urls("bundle", "http://h/api/v1", 1500, ["/a/b"], "2026-01-01 00:00:00")
        self.assertEqual(bundle, ["http://h/api/v1/bundle?run=1500&variation=default&time=2026-01-01T00%3A00%3A00.000000"])
        tables = client.job_urls("api", "http://h/api/v1", 1500, ["/a/b", "/a/c"], "2026-01-01 00:00:00")
        self.assertEqual(tables[0], "http://h/api/v1/assignments/data?request=/a/b:1500:default:2026-01-01%2000:00:00")

    def test_percentile(self):
        values = sorted([5, 1, 4, 2, 3, 10, 7, 6, 9, 8])
        self.assertEqual(client.percentile(values, 50), 5)
        self.assertEqual(client.percentile(values, 90), 9)
        self.assertEqual(client.percentile(values, 99), 10)
        self.assertEqual(client.percentile(values, 1), 1)
        self.assertIsNone(client.percentile([], 50))

    def test_histogram(self):
        counts = client.histogram([0.0005, 0.001, 0.0015, 1.0, 5000])
        self.assertEqual(sum(counts), 5)
        self.assertEqual(counts[0], 1)                                  # below 1 ms
        self.assertEqual(counts[1], 1)                                  # [1 ms, 1.26 ms)
        self.assertEqual(counts[2], 1)                                  # [1.26 ms, 1.58 ms)
        self.assertEqual(counts[-1], 1)                                 # above 1000 s

    def test_summarize_a_sample(self):
        # two processes' tallies, as run_process returns them
        parts = [{"request_latencies": [0.01, 0.02, 0.03], "job_durations": [0.06], "skews": [0.001], "errors": {},
                  "backend": 1, "requests": 3, "bytes": 300, "failed_jobs": 0, "abandoned": 0, "last_end": 110.0},
                 {"request_latencies": [0.01, 0.5], "job_durations": [0.51, 2.0], "skews": [0.002, 1.5],
                  "errors": {"http 503": 1}, "backend": 2, "requests": 2, "bytes": 100, "failed_jobs": 1, "abandoned": 1,
                  "last_end": 112.0}]
        result = client.summarize(parts, 100.0)
        self.assertEqual(result["jobs"], 4)
        self.assertEqual(result["failed_jobs"], 2)
        self.assertEqual(result["abandoned_jobs"], 1)
        self.assertEqual(result["error_rate"], 0.5)
        self.assertEqual(result["requests"], 5)
        self.assertEqual(result["backend_requests"], 3)
        self.assertEqual(result["wall_s"], 12.0)
        self.assertAlmostEqual(result["requests_per_s"], 5 / 12.0)
        self.assertEqual(result["request_latency_s"], {"median": 0.02, "p90": 0.5, "p99": 0.5, "max": 0.5})
        self.assertEqual(result["job_duration_s"]["median"], 0.51)
        self.assertEqual(result["start_skew_s"]["max"], 1.5)
        self.assertEqual(result["errors"], {"abandoned: the client's time limit": 1, "http 503": 1})


class TestReport(unittest.TestCase):

    def sample(self, jobs, median, p99, skew=0.01, errors=None):
        failed = sum((errors or {}).values())
        return {"label": "bundle-nginx", "jobs": jobs, "result": {
            "failed_jobs": failed, "error_rate": failed / jobs, "errors": errors or {}, "requests": jobs, "backend_requests": 100,
            "requests_per_s": jobs / 300.0, "job_duration_s": {"median": median, "p99": p99},
            "request_latency_s": {"p99": p99}, "start_skew_s": {"p99": skew}}}

    def test_table(self):
        text = report.table([self.sample(1000, 0.05, 0.2), self.sample(100000, 0.5, 3.0, skew=4.0, errors={"http 502": 7})])
        lines = text.splitlines()
        self.assertEqual(lines[2], "| 1 000 | 0 (0.0%) | 50 ms | 200 ms | 200 ms | 3 | 100 | 10 ms |")
        self.assertEqual(lines[3], "| 100 000 | 7 (0.0%) | 500 ms | 3.0 s | 3.0 s | 333 | 100 | 4.0 s ‡ |")
        self.assertIn("http 502 (7 at 100 000 jobs)", text)

    def test_figures_are_stable(self):
        runs = {"bundle-nginx": [self.sample(1000, 0.05, 0.2), self.sample(20000, 0.1, 0.9)],
                "mysql": [self.sample(1000, 0.3, 0.6), self.sample(20000, 0.009, 17.0, errors={"OperationalError 1040": 16661})],
                "api": [self.sample(1000, 41.0, 74.0)],
                "sqlite": [self.sample(100, 16.7, 19.4)], "sqlite-analyze": [self.sample(100, 0.065, 0.22)]}
        for run in runs.values():
            for sample in run:
                sample["result"]["backend_requests"] = 100
        files = figures.figure_files(runs)
        self.assertEqual(files, figures.figure_files(runs))
        self.assertEqual(sorted(files), ["scaling.svg", "scaling_dark.svg", "scaling_delivered.svg", "scaling_delivered_dark.svg",
                                         "scaling_requests.svg", "scaling_requests_dark.svg", "scaling_wait.svg", "scaling_wait_dark.svg"])
        figure = files["scaling.svg"]
        self.assertTrue(figure.startswith("<svg") and figure.rstrip().endswith("</svg>"))
        # panel a draws every run; panels b and c only the runs that delivered: the failed MySQL run ends its line
        self.assertEqual(figure.count("<polyline"), 2 + 1 + 1)            # a: mysql and bundle; b: bundle; c: bundle
        self.assertIn("local SQLite file", figure)
        self.assertIn("the same file after ANALYZE", figure)
        self.assertNotIn("#fcfcfb", files["scaling_dark.svg"])
        self.assertIn("Wait per job", files["scaling_wait.svg"])
        self.assertNotIn("Requests reaching", files["scaling_wait.svg"])
        json.dumps(files)

    def test_figures_without_runs(self):
        for name, make in figures.FIGURES:
            self.assertTrue(make({}).startswith("<svg"), name)


if __name__ == "__main__":
    unittest.main()
