"""parser の単体テスト。"""
import unittest

from kotonoha.ast_nodes import (Assign, BinOp, Block, BoolLit, Call, FloatLit,
                                Function, If, IntLit, Loop, Print, Program,
                                Return, StringLit, Unary, Var, VarDecl)
from kotonoha.error import KotonohaError
from kotonoha.lexer import Lexer
from kotonoha.parser import Parser


def parse(src: str) -> Program:
    return Parser(Lexer(src).tokenize()).parse()


def parse_raises(src: str, needle: str = "") -> KotonohaError:
    try:
        parse(src)
    except KotonohaError as e:
        if needle in e.message:
            return e
        raise AssertionError(f"メッセージ {e.message!r} に {needle!r} が含まれない") from None
    raise AssertionError(f"エラーが発生しなかった: {src!r}")


class TestParse(unittest.TestCase):
    def test_var_decl(self):
        p = parse("主処理 { 変数 x: 整数 を 10 とする。 }")
        stmt = p.main.body[0]
        self.assertIsInstance(stmt, VarDecl)
        self.assertEqual(stmt.name, "x")
        self.assertEqual(stmt.type_name, "整数")
        self.assertIsInstance(stmt.init, IntLit)
        self.assertEqual(stmt.init.value, 10)

    def test_assignment(self):
        p = parse("主処理 { x を 20 とする。 }")
        stmt = p.main.body[0]
        self.assertIsInstance(stmt, Assign)
        self.assertEqual(stmt.name, "x")
        self.assertEqual(stmt.value.value, 20)

    def test_function(self):
        p = parse("関数 足す（a: 整数、b: 整数） -> 整数 { 返す a + b。 } "
                  "主処理 { }")
        f = p.functions[0]
        self.assertIsInstance(f, Function)
        self.assertEqual(f.name, "足す")
        self.assertEqual(f.params, [("a", "整数"), ("b", "整数")])
        self.assertEqual(f.ret_type, "整数")
        ret = f.body[0]
        self.assertIsInstance(ret, Return)
        self.assertIsInstance(ret.value, BinOp)
        self.assertEqual(ret.value.op, "+")

    def test_function_no_params(self):
        p = parse("関数 挨拶（） -> 文字列 { 返す \"やあ\"。 } 主処理 { }")
        self.assertEqual(p.functions[0].params, [])

    def test_if(self):
        p = parse("主処理 { もし 真 ならば { 表示 1。 } そうでなければ { 表示 2。 } }")
        stmt = p.main.body[0]
        self.assertIsInstance(stmt, If)
        self.assertIsInstance(stmt.cond, BoolLit)
        self.assertIsInstance(stmt.then_body[0], Print)
        self.assertIsInstance(stmt.else_body[0], Print)

    def test_if_no_else(self):
        p = parse("主処理 { もし 真 ならば { 表示 1。 } }")
        self.assertIsNone(p.main.body[0].else_body)

    def test_loop(self):
        p = parse("主処理 { i を 1 から 10 まで 繰り返す { 表示 i。 } }")
        stmt = p.main.body[0]
        self.assertIsInstance(stmt, Loop)
        self.assertEqual(stmt.var, "i")
        self.assertEqual(stmt.start.value, 1)
        self.assertEqual(stmt.end.value, 10)
        self.assertIsInstance(stmt.body[0], Print)

    def test_loop_expression_bounds(self):
        p = parse("主処理 { 変数 n: 整数 を 5 とする。 i を 0 から n まで 繰り返す { 表示 i。 } }")
        stmt = p.main.body[1]
        self.assertIsInstance(stmt.end, Var)
        self.assertEqual(stmt.end.name, "n")

    def test_print(self):
        p = parse('主処理 { 表示 "やあ"。 }')
        stmt = p.main.body[0]
        self.assertIsInstance(stmt, Print)
        self.assertEqual(stmt.value.value, "やあ")

    def test_precedence(self):
        p = parse("主処理 { 表示 1 + 2 * 3。 }")
        e = p.main.body[0].value
        self.assertEqual(e.op, "+")
        self.assertEqual(e.right.op, "*")

    def test_parenthesized(self):
        # 括弧は全角（仕様どおり）
        p = parse("主処理 { 表示 （1 + 2） * 3。 }")
        e = p.main.body[0].value
        self.assertEqual(e.op, "*")
        self.assertEqual(e.left.op, "+")

    def test_unary_minus(self):
        p = parse("主処理 { 表示 -1 + 2。 }")
        e = p.main.body[0].value
        self.assertEqual(e.op, "+")
        self.assertIsInstance(e.left, Unary)
        self.assertEqual(e.left.op, "-")
        self.assertEqual(e.left.operand.value, 1)

    def test_not_precedence_over_comparison(self):
        # ではない x == 7 は !(x == 7)
        p = parse("主処理 { もし ではない x == 7 ならば { 表示 1。 } }")
        cond = p.main.body[0].cond
        self.assertIsInstance(cond, Unary)
        self.assertEqual(cond.op, "ではない")
        self.assertEqual(cond.operand.op, "==")

    def test_and_or(self):
        p = parse("主処理 { もし a かつ b または c ならば { 表示 1。 } }")
        cond = p.main.body[0].cond
        self.assertEqual(cond.op, "または")
        self.assertEqual(cond.left.op, "かつ")

    def test_call(self):
        p = parse("主処理 { 表示 足す（1、2）。 }")
        e = p.main.body[0].value
        self.assertIsInstance(e, Call)
        self.assertEqual(e.name, "足す")
        self.assertEqual(len(e.args), 2)

    def test_float_lit(self):
        p = parse("主処理 { 変数 x: 小数 を 3.14 とする。 }")
        self.assertIsInstance(p.main.body[0].init, FloatLit)

    def test_multiple_functions(self):
        p = parse("関数 a（） -> 整数 { 返す 1。 } 関数 b（） -> 整数 { 返す a（）。 } 主処理 { 表示 b（）。 }")
        self.assertEqual([f.name for f in p.functions], ["a", "b"])

    # ---- エラーケース ------------------------------------------------------
    def test_missing_main(self):
        e = parse_raises("関数 a（） -> 整数 { 返す 1。 }", "主処理")

    def test_function_after_main(self):
        parse_raises("主処理 { } 関数 a（） -> 整数 { 返す 1。 }", "前")

    def test_trailing_tokens(self):
        parse_raises("主処理 { } x", "予期しない")

    def test_decl_missing_period(self):
        parse_raises("主処理 { 変数 x: 整数 を 10 とする }", "句点")

    def test_decl_missing_tosu(self):
        parse_raises("主処理 { 変数 x: 整数 を 10 です。 }", "「と」")

    def test_bad_type(self):
        parse_raises("主処理 { 変数 x: 長整数 を 1 とする。 }", "型名")

    def test_unexpected_statement_token(self):
        parse_raises("主処理 { 返す }", "式")

    def test_missing_close_brace(self):
        parse_raises("主処理 { 表示 1。", "閉じ括弧")

    def test_missing_if_cond(self):
        parse_raises("主処理 { もし ならば { } }", "式")

    def test_loop_without_repeat(self):
        parse_raises("主処理 { i を 1 から 10 まで 回す { } }", "「繰り返す」")

    def test_trailing_tokens_after_statement(self):
        # 「ああ」は有効な識別子なのでエラーにならない。文の後に余分なトークンがある場合はエラー
        parse_raises("主処理 { 表示 5 5。 }", "トークン")

    def test_unclosed_paren_call(self):
        parse_raises("主処理 { 表示 f（1、 }", "式")

    def test_error_position(self):
        e = parse_raises("主処理 { 表示 1 }", "句点")
        self.assertEqual((e.line, e.col), (1, 12))

    def test_error_position_multiline(self):
        e = parse_raises("主処理 {\n    変数 x: 整数 を 1 とする\n}", "句点")
        self.assertEqual((e.line, e.col), (3, 1))


if __name__ == "__main__":
    unittest.main()
