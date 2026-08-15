"""型検査・意味解析。"""
from .ast_nodes import (Assign, BinOp, BoolLit, Call, CallStmt, FloatLit, Function, If,
                        IntLit, Loop, Node, Print, Program, Return, StringLit, Unary, Var,
                        VarDecl)
from .error import KotonohaError
from . import types as K


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}  # name -> type

    def define(self, name: str, type_name: str) -> None:
        self.vars[name] = type_name

    def lookup(self, name: str):
        s = self
        while s is not None:
            if name in s.vars:
                return s.vars[name]
            s = s.parent
        return None


class Checker:
    def __init__(self, program: Program, filename: str = "<入力>"):
        self.program = program
        self.filename = filename
        self.functions: dict[str, Function] = {}
        self._current_func: Function | None = None

    # ---- 入口 -----------------------------------------------------------
    def check(self) -> None:
        for f in self.program.functions:
            if f.name in self.functions:
                raise self._err(f"関数「{f.name}」が重複して定義されています", f)
            self.functions[f.name] = f
        for f in self.program.functions:
            self._check_function(f)
        self._check_block(self.program.main.body, Scope())

    def _err(self, msg: str, node: Node) -> KotonohaError:
        return KotonohaError(msg, node.line, node.col)

    # ---- 関数 -----------------------------------------------------------
    def _check_function(self, f: Function) -> None:
        self._current_func = f
        scope = Scope()
        for pname, ptype in f.params:
            if pname in scope.vars:
                raise self._err(f"関数「{f.name}」の引数「{pname}」が重複しています", f)
            scope.define(pname, ptype)
        self._check_block(f.body, scope, f)
        self._check_return(f)
        self._current_func = None

    def _check_return(self, f: Function) -> None:
        if f.ret_type == K.NONE:
            # 「なし」関数は返す文を禁止（D6）
            for stmt in f.body:
                if isinstance(stmt, Return):
                    raise self._err(
                        f"「なし」を返す関数「{f.name}」に「返す」文を書くことはできません", stmt)
            return
        if not f.body or not self._returns_on_all_paths(f.body[-1]):
            raise self._err(
                f"関数「{f.name}」は必ず「{f.ret_type}」を返さなければなりません"
                "（全経路が「返す」で終わるようにしてください）", f)

    @staticmethod
    def _returns_on_all_paths(stmt) -> bool:
        if isinstance(stmt, Return):
            return True
        if isinstance(stmt, If):
            then_ok = (bool(stmt.then_body)
                       and Checker._returns_on_all_paths(stmt.then_body[-1]))
            else_ok = (stmt.else_body is not None and bool(stmt.else_body)
                       and Checker._returns_on_all_paths(stmt.else_body[-1]))
            return then_ok and else_ok
        return False

    # ---- ブロック -------------------------------------------------------
    def _check_block(self, body: list, scope: Scope, f: Function | None = None) -> None:
        for stmt in body:
            self._check_stmt(stmt, scope, f)

    def _check_stmt(self, stmt, scope: Scope, f: Function | None) -> None:
        if isinstance(stmt, VarDecl):
            if scope.vars and stmt.name in scope.vars:
                raise self._err(f"変数「{stmt.name}」はこのブロックで既に宣言されています", stmt)
            t = self._expr(stmt.init, scope)
            if not K.is_widenable(t, stmt.type_name):
                raise self._err(
                    f"変数「{stmt.name}」の宣言では型が一致しません"
                    f"（{stmt.type_name} 変数に {t} を代入しようとしました）", stmt)
            scope.define(stmt.name, stmt.type_name)
        elif isinstance(stmt, Assign):
            vt = self._lookup_var(stmt.name, scope, stmt)
            t = self._expr(stmt.value, scope)
            if not K.is_widenable(t, vt):
                raise self._err(
                    f"変数「{stmt.name}」への代入では型が一致しません"
                    f"（{vt} 型の変数に {t} を代入しようとしました）", stmt)
        elif isinstance(stmt, Return):
            if f is None:
                raise self._err("「主処理」に「返す」を書くことはできません", stmt)
            if f.ret_type == K.NONE:
                raise self._err(
                    f"「なし」を返す関数「{f.name}」に「返す」文を書くことはできません", stmt)
            t = self._expr(stmt.value, scope)
            if not K.is_widenable(t, f.ret_type):
                raise self._err(
                    f"関数「{f.name}」の戻り値の型が一致しません"
                    f"（{f.ret_type} と宣言されていますが {t} を返そうとしています）", stmt)
        elif isinstance(stmt, Print):
            self._expr(stmt.value, scope)
        elif isinstance(stmt, CallStmt):
            self._expr(stmt.call, scope)
        elif isinstance(stmt, If):
            t = self._expr(stmt.cond, scope)
            if t != K.BOOL:
                raise self._err(
                    f"「もし」の条件は論理型でなければなりません（{t} 型が来てしまいました）", stmt)
            then_scope = Scope(scope)
            self._check_block(stmt.then_body, then_scope, f)
            if stmt.else_body is not None:
                else_scope = Scope(scope)
                self._check_block(stmt.else_body, else_scope, f)
        elif isinstance(stmt, Loop):
            st = self._expr(stmt.start, scope)
            et = self._expr(stmt.end, scope)
            for label, t in (("始端", st), ("終端", et)):
                if t != K.INT:
                    raise self._err(
                        f"ループの{label}は整数型でなければなりません（{t} 型が来てしまいました）",
                        stmt)
            loop_scope = Scope(scope)
            if stmt.var in loop_scope.vars:
                raise self._err(f"ループ変数「{stmt.var}」は既にこのスコープに存在します", stmt)
            loop_scope.define(stmt.var, K.INT)
            self._check_block(stmt.body, loop_scope, f)
        else:
            raise self._err(f"未対応の文法ノード {type(stmt).__name__}", stmt)

    # ---- 名前解決 ---------------------------------------------------------
    def _lookup_var(self, name: str, scope: Scope, at: Node) -> str:
        t = scope.lookup(name)
        if t is not None:
            return t
        if name in self.functions:
            raise self._err(f"「{name}」は関数なので変数として使うことはできません", at)
        raise self._err(f"未定義の変数「{name}」", at)

    def _lookup_func(self, name: str, scope: Scope, at: Node) -> Function:
        if scope.lookup(name) is not None:
            raise self._err(f"「{name}」は変数なので関数として呼ぶことはできません", at)
        if name not in self.functions:
            raise self._err(f"未定義の関数「{name}」", at)
        return self.functions[name]

    # ---- 式 ---------------------------------------------------------------
    def _expr(self, e, scope: Scope) -> str:
        t = self._expr_type(e, scope)
        e._type = t  # codegen 用のアノテーション
        return t

    def _expr_type(self, e, scope: Scope) -> str:
        if isinstance(e, IntLit):
            return K.INT
        if isinstance(e, FloatLit):
            return K.FLOAT
        if isinstance(e, StringLit):
            return K.STRING
        if isinstance(e, BoolLit):
            return K.BOOL
        if isinstance(e, Var):
            return self._lookup_var(e.name, scope, e)
        if isinstance(e, Call):
            func = self._lookup_func(e.name, scope, e)
            if len(e.args) != len(func.params):
                raise self._err(
                    f"関数「{func.name}」の引数の数が違います"
                    f"（{len(e.args)} 個渡されましたが {len(func.params)} 個必要です）", e)
            for i, (arg, (pname, ptype)) in enumerate(zip(e.args, func.params), 1):
                t = self._expr(arg, scope)
                if not K.is_widenable(t, ptype):
                    raise self._err(
                        f"関数「{func.name}」の {i} 番目の引数（{pname}）では型が一致しません"
                        f"（{ptype} を渡しましたが {t} が来てしまいました）", e)
            return func.ret_type
        if isinstance(e, Unary):
            return self._unary(e, scope)
        if isinstance(e, BinOp):
            return self._binop(e, scope)
        raise self._err(f"未対応の式ノード {type(e).__name__}", e)

    def _unary(self, e: Unary, scope: Scope) -> str:
        t = self._expr(e.operand, scope)
        if e.op == "ではない":
            if t != K.BOOL:
                raise self._err(f"「ではない」は論理型にしか使えません（{t} 型が来てしまいました）", e)
            return K.BOOL
        if not K.is_numeric(t):
            raise self._err(f"単項の「-」は数値にしか使えません（{t} 型が来てしまいました）", e)
        return t

    def _binop(self, e: BinOp, scope: Scope) -> str:
        l = self._expr(e.left, scope)
        r = self._expr(e.right, scope)
        if e.op in ("+", "-", "*", "/"):
            if not (K.is_numeric(l) and K.is_numeric(r)):
                raise self._err(
                    f"演算子「{e.op}」は数値どうしにしか使えません"
                    f"（{l} と {r} を {e.op} しようとしました）", e)
            if e.op == "/":
                return K.FLOAT  # 仕様: 整数 / 整数 は 小数
            if l == K.INT and r == K.INT:
                return K.INT
            return K.FLOAT
        if e.op in ("<", "<=", ">", ">="):
            if not (K.is_numeric(l) and K.is_numeric(r)):
                raise self._err(
                    f"比較演算子「{e.op}」は数値どうしにしか使えません"
                    f"（{l} と {r} を {e.op} で比較しようとしました）", e)
            return K.BOOL
        if e.op in ("==", "!="):
            if K.is_numeric(l) and K.is_numeric(r):
                return K.BOOL
            if l == r and l in (K.STRING, K.BOOL):
                return K.BOOL
            raise self._err(
                f"「{e.op}」で比較できるのは同じ型の値だけです（{l} と {r} は比較できません）", e)
        if e.op == "かつ":
            self._require_bool(e, l, "かつ", "左辺")
            self._require_bool(e, r, "かつ", "右辺")
            return K.BOOL
        if e.op == "または":
            self._require_bool(e, l, "または", "左辺")
            self._require_bool(e, r, "または", "右辺")
            return K.BOOL
        raise self._err(f"未対応の演算子「{e.op}」", e)

    @staticmethod
    def _require_bool(e, t: str, op: str, side: str) -> None:
        if t != K.BOOL:
            raise KotonohaError(
                f"「{op}」の{side}は論理型でなければなりません（{t} 型が来てしまいました）",
                e.line, e.col)
