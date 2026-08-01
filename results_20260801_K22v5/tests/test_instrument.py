#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "metrics"))

from diffsites import compare, normalized_lines  # noqa: E402
from measure import MeasureError, measure  # noqa: E402


class TempSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path


class MetricsTests(TempSources):
    def test_python_output_list_is_not_window(self):
        path = self.write("core.py", '''# CORE_BEGIN
def run(xs):
    win = [0] * 3
    out = []
    filled = 0
    for n in range(len(xs)):
        win[1] = win[0]
        win[0] = xs[n]
        filled += 1
        out.append(win[0])
    return out
# CORE_END
''')
        counts, hits, _loc, _cyc = measure(path)
        self.assertEqual(counts["C3"], 1)
        self.assertEqual(counts["C2"], 1)
        names = {hit.name for hit in hits if hit.metric == "C3"}
        self.assertEqual(names, {"run.win"})

    def test_java_same_field_name_is_scoped_per_class(self):
        path = self.write("Core.java", '''class Core {
// CORE_BEGIN
  static class A {
    private final int[] input;
    private int[] win;
    private int filled;
    A(int[] input) { this.input = input; }
    public void open() { win = new int[3]; filled = 0; }
    public void flatMap(int x) {
      for (int k = 2; k > 0; k--) { win[k] = win[k - 1]; }
      win[0] = x;
      filled = filled + 1;
    }
  }
  static class B {
    private int[] win;
    private int filled;
    public void open() { win = new int[5]; filled = 0; }
    public void flatMap(int x) {
      for (int k = 4; k > 0; k--) { win[k] = win[k - 1]; }
      win[0] = x;
      filled++;
    }
  }
// CORE_END
}
''')
        counts, hits, _loc, _cyc = measure(path)
        self.assertEqual(counts["C3"], 2)
        self.assertEqual(counts["C2"], 2)
        self.assertNotIn("Core.A.input", {hit.name for hit in hits if hit.metric == "C2"})
        self.assertEqual({hit.name for hit in hits if hit.metric == "C3"}, {"A.win", "B.win"})

    def test_rql_declarations(self):
        path = self.write("core.rql", '''# CORE_BEGIN
DECLARE x INTEGER STREAM src, 1/100 FILE 'x.txt'
SELECT * STREAM win FROM src@(1,5)
SELECT win[0] STREAM out FROM win.avg
# CORE_END
''')
        counts, _hits, _loc, _cyc = measure(path)
        self.assertEqual(counts["C7"], 3)
        self.assertEqual(counts["C3d"], 1)
        self.assertEqual(counts["C4d"], 1)

    def test_missing_markers_is_error(self):
        path = self.write("bad.py", "x = 1\n")
        with self.assertRaises(MeasureError):
            measure(path)


class DiffSiteTests(TempSources):
    BASE = '''# CORE_BEGIN
alpha = 1
beta = alpha + 1
gamma = beta + 1
delta = gamma + 1
# CORE_END
'''

    def test_one_contiguous_site(self):
        base = self.write("base.py", self.BASE)
        variant = self.write("variant.py", self.BASE.replace("beta = alpha + 1", "beta = alpha + 2"))
        result = compare(base, variant)
        self.assertEqual((result["D1"], result["D2"]), (1, 1))

    def test_two_separated_sites(self):
        base = self.write("base.py", self.BASE)
        text = self.BASE.replace("alpha = 1", "alpha = 2").replace("delta = gamma + 1", "delta = gamma + 2")
        variant = self.write("variant.py", text)
        result = compare(base, variant)
        self.assertEqual((result["D1"], result["D2"]), (2, 2))

    def test_comments_and_whitespace_do_not_change_result(self):
        base = self.write("base.py", self.BASE)
        variant = self.write("variant.py", self.BASE.replace("alpha = 1", "alpha    =    1  # komentarz"))
        result = compare(base, variant)
        self.assertEqual((result["D1"], result["D2"]), (0, 0))

    def test_comment_marker_inside_string_is_preserved(self):
        path = self.write("core.py", '''# CORE_BEGIN
x = "a#b" # komentarz
# CORE_END
''')
        self.assertEqual(normalized_lines(path)[0][1], 'x = "a#b"')

    def test_move_counts_as_two_sites(self):
        base = self.write("base.py", self.BASE)
        variant = self.write("variant.py", '''# CORE_BEGIN
delta = gamma + 1
alpha = 1
beta = alpha + 1
gamma = beta + 1
# CORE_END
''')
        result = compare(base, variant)
        self.assertEqual(result["D2"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

