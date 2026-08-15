"""再帰下降による構文解析。"""
from .ast_nodes import (Assign, BinOp, Block, BoolLit, Call, CallStmt, FloatLit,
                        Function, If, IntLit, Loop, Print, Program, Return, StringLit,
                        Unary, Var, VarDecl)
from .error import KotonohaError
from .tokens import TYPE_KEYWORDS, Token, TT
from . import types as K

_COMPARISONS = {TT.LT: "<", TT.LE: "<=", TT.GT: ">", TT.GE: ">=", TT.EQ: "==", TT.NE: "!="}


def _describe(tok: Token) -> str:
    if tok.kind == TT.EOF:
        return "入力の終端"
    if tok.kind == TT.IDENT:
        return f"識別子「{tok.value}」"
    return f"トークン「{tok.value}」"


class Parser:
    def __init__(self, tokens: list[Token], filename: str = "<入力>"):
        self.toks = tokens
        self.pos = 0
        self.filename = filename

    # ---- 基本ユーティリティ ---------------------------------------------
    def _peek(self, offset: int = 0) -> Token:
        j = min(self.pos + offset, len(self.toks) - 1)
        return self.toks[j]

    def _err(self, msg: str, tok: Token) -> KotonohaError:
        return KotonohaError(msg, tok.line, tok.col)

    def _advance(self) -> Token:
        tok = self.toks[self.pos]
        if tok.kind != TT.EOF:
            self.pos += 1
        return tok

    def _expect(self, kind: TT, what: str) -> Token:
        tok = self.toks[self.pos]
        if tok.kind != kind:
            raise self._err(f"{what}を期待しましたが{_describe(tok)}が来てしまいました", tok)
        return self._advance()

    # ---- プログラム -------------------------------------------------------
    def parse(self) -> Program:
        functions = []
        main = None
        while self.toks[self.pos].kind == TT.KW_関数:
            functions.append(self._function())
        if self.toks[self.pos].kind == TT.KW_関数:
            raise self._err("関数定義は「主処理」より前に置くなければなりません",
                            self.toks[self.pos])
        if self.toks[self.pos].kind == TT.KW_主処理:
            main = self._main()
        elif main is None:
            raise self._err("エントリーポイント「主処理 { ... }」がありません",
                            self.toks[self.pos])
        if self.toks[self.pos].kind != TT.EOF:
            tok = self.toks[self.pos]
            if tok.kind == TT.KW_関数:
                raise self._err("関数定義は「主処理」より前に置くなければなりません", tok)
            raise self._err(
                "「主処理」ブロックの閉じ括弧「}」のあとに予期しないトークンがあります", tok)
        return Program(line=1, col=1, functions=functions, main=main)

    def _main(self) -> Block:
        kw = self._expect(TT.KW_主処理, "「主処理」")
        return self._block(kw)

    def _function(self) -> Function:
        kw = self._expect(TT.KW_関数, "「関数」")
        name = self._expect(TT.IDENT, "関数名")
        params = self._params()
        self._expect(TT.ARROW, "戻り型への矢印「->」")
        ret_type = self._type()
        blk = self._block(kw)
        return Function(line=kw.line, col=kw.col, name=name.value,
                        params=params, ret_type=ret_type, body=blk.body)

    def _params(self) -> list[tuple[str, str]]:
        self._expect(TT.LPAREN, "開き括弧「（」")
        params = []
        if self.toks[self.pos].kind != TT.RPAREN:
            while True:
                pname = self._expect(TT.IDENT, "引数の名前")
                self._expect(TT.COLON, "型を定めるコロン「:」")
                ptype = self._type()
                params.append((pname.value, ptype))
                if self.toks[self.pos].kind == TT.COMMA:
                    self._advance()
                    continue
                break
        self._expect(TT.RPAREN, "閉じ括弧「）」")
        return params

    def _type(self) -> str:
        tok = self.toks[self.pos]
        if tok.kind in TYPE_KEYWORDS:
            self._advance()
            return tok.value
        raise self._err(f"型名を期待しましたが{_describe(tok)}が来てしまいました", tok)

    def _block(self, at: Token) -> Block:
        self._expect(TT.LBRACE, "開き括弧「{」")
        body = []
        while self.toks[self.pos].kind != TT.RBRACE:
            if self.toks[self.pos].kind == TT.EOF:
                raise self._err("ブロックの閉じ括弧「}」がありません", self.toks[self.pos])
            body.append(self._statement())
        close = self._expect(TT.RBRACE, "閉じ括弧「}」")
        return Block(line=at.line, col=at.col, body=body)

    # ---- 文 ---------------------------------------------------------------
    def _statement(self):
        tok = self.toks[self.pos]
        if tok.kind == TT.KW_変数:
            return self._var_decl()
        if tok.kind == TT.KW_返す:
            return self._return()
        if tok.kind == TT.KW_表示:
            return self._print()
        if tok.kind == TT.KW_もし:
            return self._if()
        if tok.kind == TT.IDENT and self._peek(1).kind == TT.KW_を:
            return self._wsu(tok)
        if tok.kind == TT.IDENT and self._peek(1).kind == TT.LPAREN:
            name_tok = self._advance()
            call = self._call(name_tok)
            self._expect(TT.PERIOD, "句点「。」")
            return CallStmt(line=tok.line, col=tok.col, call=call)
        raise self._err(f"文の先頭として{_describe(tok)}使うことはできません", tok)

    def _wsu(self, name_tok: Token):
        """「名詞 を 式」で始まる文。式のあとが「から」ならループ、「と」なら代入。"""
        name = self._expect(TT.IDENT, "変数名")
        self._expect(TT.KW_を, "「を」")
        expr = self._expr()
        if self.toks[self.pos].kind == TT.KW_から:
            self._advance()
            end = self._expr()
            self._expect(TT.KW_まで, "「まで」")
            kw = self._expect(TT.KW_繰り返す, "「繰り返す」")
            body = self._block(kw).body
            return Loop(line=name_tok.line, col=name_tok.col, var=name.value,
                        start=expr, end=end, body=body)
        if self.toks[self.pos].kind == TT.KW_と:
            self._expect(TT.KW_と, "「と」")
            self._expect(TT.KW_する, "「する」")
            self._expect(TT.PERIOD, "句点「。」")
            return Assign(line=name_tok.line, col=name_tok.col, name=name.value, value=expr)
        tok = self.toks[self.pos]
        raise self._err(
            f"式の後には「から」（ループ）か「と」（代入）が必要ですが{_describe(tok)}が来てしまいました",
            tok)

    def _var_decl(self) -> VarDecl:
        kw = self._expect(TT.KW_変数, "「変数」")
        name = self._expect(TT.IDENT, "変数名")
        self._expect(TT.COLON, "型を定めるコロン「:」")
        type_name = self._type()
        self._expect(TT.KW_を, "「を」")
        init = self._expr()
        self._assert_tosu()
        return VarDecl(line=kw.line, col=kw.col, name=name.value,
                       type_name=type_name, init=init)

    def _assert_tosu(self) -> None:
        self._expect(TT.KW_と, "「と」")
        self._expect(TT.KW_する, "「する」")
        self._expect(TT.PERIOD, "句点「。」")

    def _return(self) -> Return:
        kw = self._expect(TT.KW_返す, "「返す」")
        value = self._expr()
        self._expect(TT.PERIOD, "句点「。」")
        return Return(line=kw.line, col=kw.col, value=value)

    def _print(self) -> Print:
        kw = self._expect(TT.KW_表示, "「表示」")
        value = self._expr()
        self._expect(TT.PERIOD, "句点「。」")
        return Print(line=kw.line, col=kw.col, value=value)

    def _if(self) -> If:
        kw = self._expect(TT.KW_もし, "「もし」")
        cond = self._expr()
        self._expect(TT.KW_ならば, "「ならば」")
        then_body = self._block(kw).body
        else_body = None
        if self.toks[self.pos].kind == TT.KW_そうでなければ:
            kw_else = self._advance()
            else_body = self._block(kw_else).body
        return If(line=kw.line, col=kw.col, cond=cond,
                  then_body=then_body, else_body=else_body)

    def _loop(self, var_tok: Token) -> Loop:
        var = self._expect(TT.IDENT, "ループ変数の名前")
        self._expect(TT.KW_を, "「を」")
        start = self._expr()
        self._expect(TT.KW_から, "「から」")
        end = self._expr()
        self._expect(TT.KW_まで, "「まで」")
        kw = self._expect(TT.KW_繰り返す, "「繰り返す」")
        body = self._block(kw).body
        return Loop(line=var_tok.line, col=var_tok.col, var=var.value,
                    start=start, end=end, body=body)

    # ---- 式（優先度: または < かつ < ではない < 比較 < + - < * / < 一元） ----
    def _expr(self):
        return self._or()

    def _or(self):
        left = self._and()
        while self.toks[self.pos].kind == TT.KW_または:
            op = self._advance()
            right = self._and()
            left = BinOp(line=left.line, col=left.col, op="または",
                         left=left, right=right)
        return left

    def _and(self):
        left = self._not()
        while self.toks[self.pos].kind == TT.KW_かつ:
            op = self._advance()
            right = self._not()
            left = BinOp(line=left.line, col=left.col, op="かつ",
                         left=left, right=right)
        return left

    def _not(self):
        if self.toks[self.pos].kind == TT.KW_ではない:
            kw = self._advance()
            operand = self._not()
            return Unary(line=kw.line, col=kw.col, op="ではない", operand=operand)
        return self._comparison()

    def _comparison(self):
        left = self._additive()
        if self.toks[self.pos].kind in _COMPARISONS:
            op = self._advance()
            right = self._additive()
            return BinOp(line=left.line, col=left.col, op=_COMPARISONS[op.kind],
                         left=left, right=right)
        return left

    def _additive(self):
        left = self._mult()
        while self.toks[self.pos].kind in (TT.PLUS, TT.MINUS):
            op = self._advance()
            right = self._mult()
            left = BinOp(line=left.line, col=left.col,
                         op="+" if op.kind == TT.PLUS else "-",
                         left=left, right=right)
        return left

    def _mult(self):
        left = self._unary()
        while self.toks[self.pos].kind in (TT.STAR, TT.SLASH):
            op = self._advance()
            right = self._unary()
            left = BinOp(line=left.line, col=left.col,
                         op="*" if op.kind == TT.STAR else "/",
                         left=left, right=right)
        return left

    def _unary(self):
        if self.toks[self.pos].kind == TT.MINUS:
            op = self._advance()
            operand = self._unary()
            return Unary(line=op.line, col=op.col, op="-", operand=operand)
        return self._primary()

    def _primary(self):
        tok = self.toks[self.pos]
        if tok.kind == TT.INT:
            self._advance()
            return IntLit(line=tok.line, col=tok.col, value=int(tok.value))
        if tok.kind == TT.FLOAT:
            self._advance()
            return FloatLit(line=tok.line, col=tok.col, value=float(tok.value))
        if tok.kind == TT.STRING:
            self._advance()
            return StringLit(line=tok.line, col=tok.col, value=tok.value)
        if tok.kind == TT.KW_真:
            self._advance()
            return BoolLit(line=tok.line, col=tok.col, value=True)
        if tok.kind == TT.KW_偽:
            self._advance()
            return BoolLit(line=tok.line, col=tok.col, value=False)
        if tok.kind == TT.IDENT:
            name = self._advance()
            if self.toks[self.pos].kind == TT.LPAREN:
                return self._call(name)
            return Var(line=tok.line, col=tok.col, name=tok.value)
        if tok.kind == TT.LPAREN:
            self._advance()
            inner = self._expr()
            self._expect(TT.RPAREN, "閉じ括弧「）」")
            return inner
        raise self._err(f"式として{_describe(tok)}を使うことはできません", tok)

    def _call(self, name_tok: Token) -> Call:
        self._expect(TT.LPAREN, "開き括弧「（」")
        args = []
        if self.toks[self.pos].kind != TT.RPAREN:
            while True:
                args.append(self._expr())
                if self.toks[self.pos].kind == TT.COMMA:
                    self._advance()
                    continue
                break
        self._expect(TT.RPAREN, "閉じ括弧「）」")
        return Call(line=name_tok.line, col=name_tok.col, name=name_tok.value, args=args)
