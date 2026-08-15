"""字句解析器。"""
from .error import KotonohaError
from .tokens import KEYWORDS, Token, TT

_ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "t": "\t"}


class Lexer:
    def __init__(self, source: str, filename: str = "<入力>"):
        self.src = source
        self.filename = filename
        self.i = 0
        self.line = 1
        self.col = 1

    # ---- 位置管理 -------------------------------------------------------
    def _err(self, msg: str, line=None, col=None) -> KotonohaError:
        return KotonohaError(msg, line if line is not None else self.line,
                             col if col is not None else self.col)

    def _char(self) -> str:
        c = self.src[self.i]
        self.i += 1
        if c == "\n":
            self.line += 1
            self.col = 1
        elif c == "\r":
            pass  # CRLF の \r は計上しない
        else:
            self.col += 1
        return c

    def _peek(self, offset: int = 0) -> str:
        j = self.i + offset
        if j < len(self.src):
            return self.src[j]
        return ""

    def _skip_ws(self) -> None:
        while self.i < len(self.src) and self.src[self.i] in " \t\r\n":
            self._char()

    # ---- 抽出 -----------------------------------------------------------
    def _is_ident_start(self, c: str) -> bool:
        return c == "_" or (c.isalpha() and not c.isspace())

    def _is_ident_cont(self, c: str) -> bool:
        return c == "_" or c.isalnum() and not c.isspace()

    def _lex_ident(self, start: int) -> list[Token]:
        line, col = self.line, self.col
        text = self.src[start]
        self.i += 1
        self.col += 1
        while self.i < len(self.src) and self._is_ident_cont(self.src[self.i]):
            self._char()
            text = self.src[start:self.i]
        return self._split_ident(text, line, col)

    def _split_ident(self, text: str, line: int, col: int) -> list[Token]:
        """キーワード連結を分詞する（例: 「とする」→ 「と」＋「する」）。

        日本語は語間にスペースが不要なため、識別子文字列がそのまま
        キーワードでなければ、最左のキーワード接頭辞で分割する。
        """
        if text in KEYWORDS:
            return [Token(KEYWORDS[text], text, line, col)]
        for L in range(1, len(text)):
            prefix, rest = text[:L], text[L:]
            if prefix in KEYWORDS and self._is_ident_start(rest[0]):
                return (self._split_ident(prefix, line, col)
                        + self._split_ident(rest, line, col + L))
        return [Token(TT.IDENT, text, line, col)]

    def _lex_number(self, start: int, line: int, col: int) -> Token:
        while self.i < len(self.src) and self.src[self.i].isdigit():
            self._char()
        if self.i < len(self.src) and self.src[self.i] == "." \
                and self.i + 1 < len(self.src) and self.src[self.i + 1].isdigit():
            self._char()  # ドット
            while self.i < len(self.src) and self.src[self.i].isdigit():
                self._char()
            return Token(TT.FLOAT, self.src[start:self.i], line, col)
        return Token(TT.INT, self.src[start:self.i], line, col)

    def _lex_string(self, quote_line: int, quote_col: int) -> Token:
        parts = []
        while True:
            if self.i >= len(self.src):
                raise self._err("未終端の文字列リテラル", quote_line, quote_col)
            c = self.src[self.i]
            if c == "\n":
                raise self._err("未終端の文字列リテラル", quote_line, quote_col)
            if c == '"':
                self._char()
                return Token(TT.STRING, "".join(parts), quote_line, quote_col)
            if c == "\\":
                esc_line, esc_col = self.line, self.col
                self._char()
                if self.i >= len(self.src) or self.src[self.i] not in _ESCAPES:
                    raise self._err("不明なエスケープシーケンス", esc_line, esc_col)
                parts.append(_ESCAPES[self.src[self.i]])
                self._char()
            else:
                parts.append(c)
                self._char()

    # ---- 本体 -----------------------------------------------------------
    def tokenize(self) -> list[Token]:
        toks: list[Token] = []
        while True:
            self._skip_ws()
            if self.i >= len(self.src):
                toks.append(Token(TT.EOF, "", self.line, self.col))
                return toks
            line, col = self.line, self.col
            c = self.src[self.i]
            n2 = self.src[self.i:self.i + 2]

            if c.isdigit():
                toks.append(self._lex_number(self.i, line, col))
            elif c == '"':
                self._char()
                toks.append(self._lex_string(line, col))
            elif self._is_ident_start(c):
                toks.extend(self._lex_ident(self.i))
            elif n2 == "->":
                self._char(); self._char()
                toks.append(Token(TT.ARROW, "->", line, col))
            elif n2 == "<=":
                self._char(); self._char()
                toks.append(Token(TT.LE, "<=", line, col))
            elif n2 == ">=":
                self._char(); self._char()
                toks.append(Token(TT.GE, ">=", line, col))
            elif n2 == "==":
                self._char(); self._char()
                toks.append(Token(TT.EQ, "==", line, col))
            elif n2 == "!=":
                self._char(); self._char()
                toks.append(Token(TT.NE, "!=", line, col))
            elif c == "+":
                self._char(); toks.append(Token(TT.PLUS, "+", line, col))
            elif c == "*":
                self._char(); toks.append(Token(TT.STAR, "*", line, col))
            elif c == "/":
                self._char(); toks.append(Token(TT.SLASH, "/", line, col))
            elif c == "-":
                self._char(); toks.append(Token(TT.MINUS, "-", line, col))
            elif c == "<":
                self._char(); toks.append(Token(TT.LT, "<", line, col))
            elif c == ">":
                self._char(); toks.append(Token(TT.GT, ">", line, col))
            elif c == "!":
                raise self._err("予期しない文字「!」（「!=」が正しい形式です）", line, col)
            elif c == "=":
                raise self._err("予期しない文字「=」（「==」が正しい形式です）", line, col)
            elif c == "{":
                self._char(); toks.append(Token(TT.LBRACE, "{", line, col))
            elif c == "}":
                self._char(); toks.append(Token(TT.RBRACE, "}", line, col))
            elif c == "（":
                self._char(); toks.append(Token(TT.LPAREN, "（", line, col))
            elif c == "）":
                self._char(); toks.append(Token(TT.RPAREN, "）", line, col))
            elif c == "、":
                self._char(); toks.append(Token(TT.COMMA, "、", line, col))
            elif c == "。":
                self._char(); toks.append(Token(TT.PERIOD, "。", line, col))
            elif c == ":":
                self._char(); toks.append(Token(TT.COLON, ":", line, col))
            else:
                raise self._err(f"未定義の文字「{c}」", line, col)
