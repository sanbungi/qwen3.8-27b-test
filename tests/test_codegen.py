"""codegen の単体テスト。"""
import subprocess
import tempfile
import unittest

from kotonoha.lexer import Lexer
from kotonoha.parser import Parser
from kotonoha.checker import Checker
from kotonoha.codegen import CodeGen


def gen(src: str) -> str:
    prog = Parser(Lexer(src).tokenize()).parse()
    Checker(prog).check()
    return CodeGen(prog, "t.koto").generate()


def gen_and_run(src: str) -> str:
    c = gen(src)
    with tempfile.TemporaryDirectory() as d:
        cpath = f"{d}/t.c"
        binpath = f"{d}/t"
        with open(cpath, "w", encoding="utf-8") as f:
            f.write(c)
        subprocess.run(["gcc", "-std=c11", "-O2", "-Wall", "-Wextra",
                        cpath, "-o", binpath], check=True, capture_output=True)
        r = subprocess.run([binpath], check=True, capture_output=True, text=True)
        return r.stdout


class TestCodegen(unittest.TestCase):
    def test_structure(self):
        c = gen("主処理 { 表示 1。 }")
        self.assertIn("#include <stdio.h>", c)
        self.assertIn("#include <stdbool.h>", c)
        self.assertIn("#include <string.h>", c)
        self.assertIn("int main(void) {", c)
        self.assertIn("// 主処理", c)

    def test_int_suffixed(self):
        c = gen("主処理 { 表示 1。 }")
        self.assertIn("1LL", c)
        self.assertNotIn("1LLLL", c)

    def test_int_div_cast(self):
        c = gen("主処理 { 表示 5 / 2。 }")
        self.assertIn("(double)(5LL) / (double)(2LL)", c)

    def test_string_eq_strcmp(self):
        c = gen('主処理 { もし "a" == "b" ならば { 表示 1。 } }')
        self.assertIn("strcmp(" , c)
        self.assertIn("== 0)", c)
        c2 = gen('主処理 { もし "a" != "b" ならば { 表示 1。 } }')
        self.assertIn("!= 0)", c2)

    def test_string_ne_strcmp(self):
        pass

    def test_bool_output(self):
        out = gen_and_run("主処理 { 表示 真。 表示 偽。 }")
        self.assertEqual(out, "真\n偽\n")

    def test_printf_casts(self):
        c = gen("主処理 { 表示 1。 表示 1.5。 }")
        self.assertIn('printf("%lld\\n", (long long)(1LL))', c)
        self.assertIn('printf("%g\\n", (double)(1.5))', c)

    def test_unary_minus(self):
        c = gen("主処理 { 表示 -1。 }")
        self.assertIn("(-(1LL))", c)

    def test_not(self):
        c = gen("主処理 { 表示 ではない 真。 }")
        self.assertIn("(!(true))", c)

    def test_string_escape(self):
        c = gen(r'主処理 { 表示 "あ\"あ"。 }')
        self.assertIn('"あ\\"あ"', c)

    def test_shadowing_distinct_vars(self):
        c = gen("主処理 { 変数 x: 整数 を 1 とする。 もし 真 ならば { 変数 x: 整数 を 2 とする。 表示 x。 } 表示 x。 }")
        # 内側の x と外側の x は異なる C 変数
        self.assertRegex(c, r"long long _v\d+ = 1LL; // x")
        self.assertRegex(c, r"long long _v\d+ = 2LL; // x")

    def test_loop_inclusive_end(self):
        # 1 から 3 まで → 3 回
        out = gen_and_run("主処理 { 変数 n: 整数 を 0 とする。 i を 1 から 3 まで 繰り返し { n を n + i とする。 表示 n。 } }".replace("繰り返し", "繰り返す"))
        self.assertEqual(out, "1\n3\n6\n")

    def test_loop_descends_zero(self):
        # 始端 > 終端 は 0 回（設計判断 D10）
        out = gen_and_run("主処理 { 変数 n: 整数 を 0 とする。 i を 5 から 1 まで 繰り返す { n を n + i とする。 表示 n。 } 表示 n。 }")
        self.assertEqual(out, "0\n")

    def test_recursive_call(self):
        c = gen("関数 f（n: 整数） -> 整数 { もし n == 0 ならば { 返す 0。 } 返す f（n - 1）。 } 主処理 { 表示 f（1）。 }")
        # 前置宣言が先に来る
        self.assertLess(c.index("static long long _f0(long long _v0); // f"),
                        c.index("static long long _f0(long long _v0) { // f"))

    def test_void_call_stmt(self):
        c = gen("関数 g（） -> なし { 表示 1。 } 主処理 { g（）。 }")
        self.assertIn("_f1();", c)

    def test_compiles_clean(self):
        out = gen_and_run("""関数 足す（a: 整数、b: 整数） -> 整数 { 返す a + b。 }
主処理 {
    変数 s: 文字列 を "x" とする。
    もし s == "x" ならば { 表示 足す（1、2）。 }
    変数 f: 小数 を 1.5 * 2 とする。
    表示 f。
}""")
        self.assertEqual(out, "3\n3\n")


if __name__ == "__main__":
    unittest.main()
