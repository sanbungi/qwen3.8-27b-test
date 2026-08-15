"""lexer の単体テスト。"""
import unittest

from kotonoha.error import KotonohaError
from kotonoha.lexer import Lexer
from kotonoha.tokens import TT


def kinds(src: str):
    return [t.kind for t in Lexer(src).tokenize()]


def text(src: str):
    return [(t.kind.name, t.value, t.line, t.col) for t in Lexer(src).tokenize()]


class TestLexer(unittest.TestCase):
    def test_simple_program(self):
        src = "変数 x: 整数 を 10 とする。"
        toks = Lexer(src).tokenize()
        self.assertEqual(
            [t.kind for t in toks],
            [TT.KW_変数, TT.IDENT, TT.COLON, TT.KW_整数, TT.KW_を,
             TT.INT, TT.KW_と, TT.KW_する, TT.PERIOD, TT.EOF],
        )
        self.assertEqual(toks[5].value, "10")

    def test_function_signature(self):
        src = "関数 足す（a: 整数、b: 整数） -> 整数"
        self.assertEqual(
            kinds(src),
            [TT.KW_関数, TT.IDENT, TT.LPAREN, TT.IDENT, TT.COLON, TT.KW_整数,
             TT.COMMA, TT.IDENT, TT.COLON, TT.KW_整数, TT.RPAREN,
             TT.ARROW, TT.KW_整数, TT.EOF],
        )

    def test_operators(self):
        src = "a + b - c * d / e < f <= g > h >= i == j != k"
        self.assertEqual(
            kinds(src),
            [TT.IDENT, TT.PLUS, TT.IDENT, TT.MINUS, TT.IDENT, TT.STAR, TT.IDENT,
             TT.SLASH, TT.IDENT, TT.LT, TT.IDENT, TT.LE, TT.IDENT, TT.GT, TT.IDENT,
             TT.GE, TT.IDENT, TT.EQ, TT.IDENT, TT.NE, TT.IDENT, TT.EOF],
        )

    def test_float_literal(self):
        toks = Lexer("3.14").tokenize()
        self.assertEqual(toks[0].kind, TT.FLOAT)
        self.assertEqual(toks[0].value, "3.14")

    def test_int_not_float(self):
        # 浮動小数点は「数字.数字」の形のみ。「1.」や「.5」は不正
        with self.assertRaises(KotonohaError) as cm1:
            Lexer("1.").tokenize()
        self.assertEqual((cm1.exception.line, cm1.exception.col), (1, 2))
        with self.assertRaises(KotonohaError):
            Lexer(".5").tokenize()

    def test_string(self):
        toks = Lexer('"こんにちは、世界！"').tokenize()
        self.assertEqual(toks[0].kind, TT.STRING)
        self.assertEqual(toks[0].value, "こんにちは、世界！")

    def test_string_escapes(self):
        toks = Lexer(r'"a\"b\\c\nd\t"').tokenize()
        self.assertEqual(toks[0].value, 'a"b\\c\nd\t')

    def test_keywords(self):
        self.assertEqual(kinds("もし ならば そうでなければ")[0], TT.KW_もし)
        self.assertEqual(kinds("繰り返す から まで")[0], TT.KW_繰り返す)
        self.assertEqual(kinds("主処理")[0], TT.KW_主処理)
        self.assertEqual(kinds("真 偽")[0], TT.KW_真)
        self.assertEqual(kinds("かつ または ではない")[0], TT.KW_かつ)
        self.assertEqual(kinds("整数 小数 文字列 論理 なし")[0], TT.KW_整数)
        self.assertEqual(kinds("表示")[0], TT.KW_表示)

    def test_line_col_tracking(self):
        rows = text("x\n\ny + z")
        self.assertEqual(rows[0], ("IDENT", "x", 1, 1))
        self.assertEqual(rows[1], ("IDENT", "y", 3, 1))
        self.assertEqual(rows[2], ("PLUS", "+", 3, 3))
        self.assertEqual(rows[3], ("IDENT", "z", 3, 5))
        self.assertEqual(rows[4], ("EOF", "", 3, 6))

    def test_identifier_japanese_and_ascii(self):
        self.assertEqual(kinds("あいう x1_ 下書き_2")[0], TT.IDENT)

    def test_unterminated_string(self):
        with self.assertRaises(KotonohaError) as cm:
            Lexer('"abc').tokenize()
        self.assertEqual((cm.exception.line, cm.exception.col), (1, 1))

    def test_unterminated_string_multiline(self):
        with self.assertRaises(KotonohaError) as cm:
            Lexer('x"\na"').tokenize()
        self.assertEqual((cm.exception.line, cm.exception.col), (1, 2))

    def test_unknown_escape(self):
        with self.assertRaises(KotonohaError) as cm:
            Lexer(r'"a\qb"').tokenize()
        # エスケープの先頭（バックスラッシュ）位置を報告
        self.assertEqual((cm.exception.line, cm.exception.col), (1, 3))

    def test_keyword_concat_split(self):
        # 語間スペースなしのキーワード連結は分割される
        self.assertEqual(
            kinds("10とする。"),
            [TT.INT, TT.KW_と, TT.KW_する, TT.PERIOD, TT.EOF],
        )
        self.assertEqual(
            kinds("5 として x"),
            [TT.INT, TT.KW_と, TT.IDENT, TT.IDENT, TT.EOF],
        )

    def test_keyword_word_stays_whole(self):
        # キーワード自体は分割されない
        self.assertEqual(kinds("繰り返す"), [TT.KW_繰り返す, TT.EOF])
        self.assertEqual(kinds("そうでなければ"), [TT.KW_そうでなければ, TT.EOF])
        self.assertEqual(kinds("からまで"), [TT.KW_から, TT.KW_まで, TT.EOF])

    def test_ident_with_keyword_prefix_blocked_by_digit(self):
        # リテラルが続く「から10」は識別子全体として残る
        self.assertEqual(kinds("から10"), [TT.IDENT, TT.EOF])

    def test_bad_char(self):
        with self.assertRaises(KotonohaError) as cm:
            Lexer("x ＄ y").tokenize()
        self.assertEqual((cm.exception.line, cm.exception.col), (1, 3))
        self.assertIn("未定義の文字", cm.exception.message)

    def test_lone_equal(self):
        with self.assertRaises(KotonohaError) as cm:
            Lexer("x = y").tokenize()
        self.assertIn("==", cm.exception.message)

    def test_lone_bang(self):
        with self.assertRaises(KotonohaError) as cm:
            Lexer("x ! y").tokenize()
        self.assertIn("!=", cm.exception.message)

    def test_arrow(self):
        self.assertEqual(kinds(" -> ")[0], TT.ARROW)

    def test_braces(self):
        self.assertEqual(kinds("{ }"), [TT.LBRACE, TT.RBRACE, TT.EOF])


if __name__ == "__main__":
    unittest.main()
