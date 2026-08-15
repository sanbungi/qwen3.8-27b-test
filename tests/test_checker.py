"""checker（型検査・意味解析）の単体テスト。"""
import unittest

from kotonoha.error import KotonohaError
from kotonoha.lexer import Lexer
from kotonoha.parser import Parser
from kotonoha.checker import Checker


def check(src: str):
    prog = Parser(Lexer(src).tokenize()).parse()
    Checker(prog).check()
    return prog


def check_err(src: str, needle: str) -> KotonohaError:
    try:
        check(src)
    except KotonohaError as e:
        if needle in e.message:
            return e
        raise AssertionError(f"メッセージ {e.message!r} に {needle!r} が含まれない") from None
    raise AssertionError(f"エラーが発生しなかった: {src!r}")


def with_main(body: str) -> str:
    return "主処理 {\n" + body + "\n}"


class TestCheckerValid(unittest.TestCase):
    def test_full_program(self):
        check("""
関数 足す（a: 整数、b: 整数） -> 整数 {
    返す a + b。
}
主処理 {
    変数 x: 整数 を 足す（1、2） とする。
    x を 20 とする。
    もし x > 10 ならば {
        表示 x。
    }
    i を 1 から x まで 繰り返す {
        表示 i。
    }
}""")

    def test_widening_int_to_float(self):
        check(with_main("変数 f: 小数 を 1 とする。"))
        check(with_main("変数 f: 小数 を 1 とする。 f を 2.5 とする。"))

    def test_float_arith(self):
        check(with_main("変数 f: 小数 を 3.0 * 2 とする。"))
        check(with_main("変数 f: 小数 を 1 + 2.5 とする。"))

    def test_int_div_gives_float(self):
        check(with_main("変数 f: 小数 を 5 / 2 とする。"))

    def test_bool_ops(self):
        check(with_main("変数 b: 論理 を 真 かつ 偽 とする。"))
        check(with_main("もし ではない 偽 ならば { 表示 1。 }"))
        check(with_main("もし 真 または 偽 かつ 真 ならば { 表示 1。 }"))

    def test_string_eq(self):
        check(with_main('もし "a" == "a" ならば { 表示 1。 }'))
        check(with_main('変数 s: 文字列 を "a" とする。 もし s != "b" ならば { 表示 1。 }'))

    def test_if_both_branches_return(self):
        check("""
関数 f（n: 整数） -> 整数 {
    もし n > 0 ならば { 返す 1。 } そうでなければ { 返す -1。 }
}
主処理 { 表示 f（1）。 }""")

    def test_none_function(self):
        check("""
関数 g（） -> なし {
    表示 42。
}
主処理 { g（）。 }""")

    def test_recursion(self):
        check("""
関数 階乗（n: 整数） -> 整数 {
    もし n <= 1 ならば { 返す 1。 }
    返す n * 階乗（n - 1）。
}
主処理 { 表示 階乗（5）。 }""")

    def test_mutual_recursion(self):
        check("""
関数 偶（n: 整数） -> 論理 {
    もし n == 0 ならば { 返す 真。 }
    返す 奇（n - 1）。
}
関数 奇（n: 整数） -> 論理 {
    もし n == 0 ならば { 返す 偽。 }
    返す 偶（n - 1）。
}
主処理 { 表示 偶（10）。 }""")

    def test_shadowing_nested(self):
        check(with_main("""
変数 x: 整数 を 1 とする。
もし 真 ならば {
    変数 x: 整数 を 2 とする。
    表示 x。
}
表示 x。"""))

    def test_loop_var_shadow(self):
        check(with_main("""
変数 i: 整数 を 9 とする。
i を 1 から 3 まで 繰り返す {
    表示 i。
}
表示 i。"""))

    def test_widening_in_call(self):
        check("""
関数 足す（a: 整数、b: 小数） -> 小数 {
    返す a + b。
}
主処理 { 表示 足す（1、2）。 }""")

    def test_numeric_comparison_mixed(self):
        check(with_main("もし 1 < 2.5 ならば { 表示 1。 }"))

    def test_unary_minus(self):
        check(with_main("変数 n: 整数 を -5 とする。"))
        check(with_main("変数 f: 小数 を -1.5 とする。"))

    def test_empty_block(self):
        check(with_main("もし 偽 ならば { }"))

    def test_use_func_as_var(self):
        check_err("関数 f（） -> 整数 { 返す 1。 } 主処理 { 表示 f。 }", "関数なので")


class TestCheckerErrors(unittest.TestCase):
    def test_decl_type_mismatch(self):
        check_err(with_main('変数 x: 整数 を 1.5 とする。'), "型が一致しません")

    def test_decl_string_to_int(self):
        check_err(with_main('変数 x: 整数 を "a" とする。'), "型が一致しません")

    def test_assign_type_mismatch(self):
        check_err(with_main('変数 x: 整数 を 1 とする。 x を 1.5 とする。'), "型が一致しません")
        check_err(with_main('変数 x: 整数 を 1 とする。 x を "a" とする。'), "型が一致しません")

    def test_float_not_widened_to_int(self):
        check_err(with_main("変数 x: 整数 を 1 とする。 x を 2.5 とする。"), "型が一致しません")

    def test_undeclared_var(self):
        check_err(with_main("表示 y。"), "未定義の変数「y」")

    def test_undefined_func(self):
        check_err(with_main("表示 f（）。"), "未定義の関数「f」")

    def test_call_a_var(self):
        check_err(with_main("変数 x: 整数 を 1 とする。 表示 x（）。"), "変数なので")

    def test_arg_count(self):
        check_err("関数 足す（a: 整数、b: 整数） -> 整数 { 返す a + b。 } 主処理 { 表示 足す（1）。 }",
                  "引数の数")

    def test_arg_type(self):
        check_err("関数 足す（a: 整数、b: 整数） -> 整数 { 返す a + b。 } 主処理 { 表示 足す（\"a\"、1）。 }",
                  "型が一致しません")

    def test_condition_not_bool(self):
        check_err(with_main("変数 x: 整数 を 1 とする。 もし x ならば { 表示 1。 }"), "論理型")
        check_err(with_main('もし "a" ならば { 表示 1。 }'), "論理型")

    def test_loop_bound_not_int(self):
        check_err(with_main("i を 1 から 2.5 まで 繰り返す { 表示 i。 }"), "終端")
        check_err(with_main("変数 s: 文字列 を \"a\" とする。 変数 i: 整数 を 1 とする。 i を s から i まで 繰り返す { 表示 i。 }"),
                  "始端")

    def test_missing_return(self):
        check_err("関数 f（） -> 整数 { 表示 1。 } 主処理 { 表示 f（）。 }", "必ず")

    def test_missing_return_after_if(self):
        check_err("関数 f（n: 整数） -> 整数 { もし n > 0 ならば { 返す 1。 } } 主処理 { 表示 f（1）。 }",
                  "必ず")

    def test_return_in_main(self):
        check_err(with_main("返す 1。"), "主処理")

    def test_return_in_none_func(self):
        check_err("関数 f（） -> なし { 返す 1。 } 主処理 { f（）。 }", "なし")

    def test_return_type_mismatch(self):
        check_err("関数 f（） -> 整数 { 返す 1.5。 } 主処理 { 表示 f（）。 }", "戻り値")
        check_err('関数 f（） -> 文字列 { 返す 1。 } 主処理 { 表示 f（）。 }', "戻り値")

    def test_duplicate_function(self):
        check_err("関数 f（） -> 整数 { 返す 1。 } 関数 f（） -> 整数 { 返す 2。 } 主処理 { 表示 f（）。 }",
                  "重複")

    def test_duplicate_var_same_scope(self):
        check_err(with_main("変数 x: 整数 を 1 とする。 変数 x: 整数 を 2 とする。"), "既に宣言")

    def test_string_concat_not_allowed(self):
        check_err(with_main('変数 s: 文字列 を "a" + "b" とする。'), "数値")

    def test_string_less_than(self):
        check_err(with_main('もし "a" < "b" ならば { 表示 1。 }'), "数値")

    def test_cross_type_eq(self):
        check_err(with_main('もし "a" == 1 ならば { 表示 1。 }'), "同じ型")
        check_err(with_main("もし 真 == 1 ならば { 表示 1。 }"), "同じ型")

    def test_not_on_int(self):
        check_err(with_main("もし ではない 1 ならば { 表示 1。 }"), "論理型")

    def test_and_mixed(self):
        check_err(with_main("変数 x: 整数 を 1 とする。 もし x かつ 真 ならば { 表示 1。 }"),
                  "論理型")

    def test_unary_minus_string(self):
        check_err(with_main('変数 s: 文字列 を -"a" とする。'), "数値")

    def test_bool_div(self):
        check_err(with_main("変数 f: 小数 を 真 / 偽 とする。"), "数値")

    def test_main_missing(self):
        check_err("関数 f（） -> 整数 { 返す 1。 }", "主処理")

    def test_error_position(self):
        e = check_err(with_main("表示 y。"), "未定義の変数")
        # with_main により y は 2行4列目
        self.assertEqual((e.line, e.col), (2, 4))


if __name__ == "__main__":
    unittest.main()
