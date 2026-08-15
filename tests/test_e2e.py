"""e2e：CLI（python3 -m kotonoha）経由で gcc まで実行して標準出力を検証。"""
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples")


def run_cli(args, cwd=None):
    import sys
    return subprocess.run(
        [sys.executable, "-m", "kotonoha", *args],
        cwd=cwd or ROOT, capture_output=True, text=True)


class TestExamples(unittest.TestCase):
    CASES = [
        ("hello.koto", "こんにちは、世界！\n"),
        ("factorial.koto", "120\n"),
        ("loop_sum.koto", "55\n"),
        ("division.koto", "2.5\n3.5\n0.25\n2\n18\n"),
        ("ifelse.koto", "5 以上 10 以下\n小さい\n負\n大きい\n"),
        ("string.koto", "一致\nそれ以外\n"),
    ]

    def test_examples_run(self):
        for name, expected in self.CASES:
            with self.subTest(name=name):
                r = run_cli([os.path.join("examples", name), "--run"])
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout, expected)

    def test_generates_c_file(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_cli([os.path.join("examples", "hello.koto"),
                         "-o", f"{d}/hello.c"])
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(f"{d}/hello.c", encoding="utf-8") as f:
                c = f.read()
            self.assertIn("int main(void)", c)
            self.assertIn("こんにちは、世界！", c)


class TestErrors(unittest.TestCase):
    def _write(self, d, src):
        p = os.path.join(d, "bad.koto")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src)
        return p

    def test_undefined_variable(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "主処理 { 表示 y。 }\n")
            r = run_cli([p])
            self.assertEqual(r.returncode, 1)
            self.assertIn("bad.koto:1:10", r.stderr)
            self.assertIn("未定義の変数「y」", r.stderr)

    def test_type_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "主処理 { 変数 x: 整数 を \"a\" とする。 表示 x。 }\n")
            r = run_cli([p])
            self.assertEqual(r.returncode, 1)
            self.assertIn("型が一致しません", r.stderr)

    def test_undefined_char(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "主処理 { 表示 1 ( 2。 }\n")
            r = run_cli([p])
            self.assertEqual(r.returncode, 1)
            self.assertIn("未定義の文字", r.stderr)

    def test_missing_file(self):
        r = run_cli(["/nonexistent/nope.koto"])
        self.assertEqual(r.returncode, 2)

    def test_missing_main(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "関数 f（） -> なし { }")
            r = run_cli([p])
            self.assertEqual(r.returncode, 1)
            self.assertIn("主処理", r.stderr)

    def test_missing_return(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._write(d, "関数 f（） -> 整数 { 変数 x: 整数 を 1 とする。 } 主処理 { 表示 f（）。 }\n")
            r = run_cli([p])
            self.assertEqual(r.returncode, 1)
            self.assertIn("返す", r.stderr)


if __name__ == "__main__":
    unittest.main()
