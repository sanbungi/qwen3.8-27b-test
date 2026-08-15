"""C コード生成。"""
import re

from .ast_nodes import (Assign, BinOp, BoolLit, Call, CallStmt, FloatLit, Function,
                        If, IntLit, Loop, Print, Program, Return, StringLit, Unary,
                        Var, VarDecl)
from . import types as K

_HEADER = """\
// このファイルは「ことのは」コンパイラが生成した C コードです。
// ソース: {filename}
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
"""


class _Names:
    def __init__(self):
        self.var_count = 0
        self.func_count = 0
        self.func_names: dict[str, str] = {}
        self.main_name: str | None = None

    def func(self, name: str) -> str:
        if name not in self.func_names:
            c = f"_f{self.func_count}"
            self.func_count += 1
            self.func_names[name] = c
        return self.func_names[name]

    def var(self) -> str:
        v = f"_v{self.var_count}"
        self.var_count += 1
        return v


class CodeGen:
    def __init__(self, program: Program, filename: str = "<入力>"):
        self.program = program
        self.filename = filename
        self.names = _Names()
        self.scopes: list[dict[str, str]] = []  # 日本語名 -> C 名

    # ---- 入口 -----------------------------------------------------------
    def generate(self) -> str:
        out = [_HEADER.format(filename=self.filename), ""]
        # 前置宣言（任意の順序・相互再帰を許す、D14）
        for f in self.program.functions:
            out.append(self._prototype(f))
        out.append(f"static void {self._main_c()}(void); // 主処理")
        out.append("")
        for f in self.program.functions:
            out.append(self._function(f))
            out.append("")
        out.append(self._main_block())
        out.append("")
        out.append("int main(void) {")
        out.append(f"    {self._main_c()}();")
        out.append("    return 0;")
        out.append("}")
        return "\n".join(out) + "\n"

    def _main_c(self) -> str:
        if self.names.main_name is None:
            self.names.main_name = f"_f{self.names.func_count}"
            self.names.func_count += 1
        return self.names.main_name

    def _scope(self) -> dict[str, str]:
        return self.scopes[-1]

    def _enter_scope(self) -> None:
        self.scopes.append({})

    def _leave_scope(self) -> None:
        self.scopes.pop()

    def _bind(self, name: str) -> str:
        c = self.names.var()
        self._scope()[name] = c
        return c

    def _lookup(self, name: str) -> str:
        for s in reversed(self.scopes):
            if name in s:
                return s[name]
        raise KeyError(name)

    # ---- 関数 -----------------------------------------------------------
    def _param_info(self, f: Function) -> tuple[str, list[str]]:
        """引数名の C 名割当をキャッシュ（プロトタイプと定義で同一に）。"""
        if not hasattr(self, "_param_cache"):
            self._param_cache: dict[str, tuple[str, list[str]]] = {}
        if f.name in self._param_cache:
            return self._param_cache[f.name]
        self._enter_scope()
        cnames = [self._bind(pname) for pname, _ in f.params]
        parts = [f"{K.C_TYPE[ptype]} {c}" for (pname, ptype), c in zip(f.params, cnames)]
        self._leave_scope()
        result = (", ".join(parts) if parts else "void", cnames)
        self._param_cache[f.name] = result
        return result

    def _prototype(self, f: Function) -> str:
        c = self.names.func(f.name)
        params, _ = self._param_info(f)
        return f"static {K.C_TYPE[f.ret_type]} {c}({params}); // {f.name}"

    def _function(self, f: Function) -> str:
        c = self.names.func(f.name)
        params, cnames = self._param_info(f)
        lines = [f"static {K.C_TYPE[f.ret_type]} {c}({params}) {{ // {f.name}"]
        self._enter_scope()
        for (pname, _), c in zip(f.params, cnames):
            self._scope()[pname] = c
        for stmt in f.body:
            lines.extend(self._stmt_lines(stmt, 1))
        self._leave_scope()
        lines.append("}")
        return "\n".join(lines)

    def _main_block(self) -> str:
        c = self._main_c()
        lines = [f"static void {c}(void) {{ // 主処理"]
        self._enter_scope()
        for stmt in self.program.main.body:
            lines.extend(self._stmt_lines(stmt, 1))
        self._leave_scope()
        lines.append("}")
        return "\n".join(lines)

    # ---- 文 ---------------------------------------------------------------
    def _stmt_lines(self, stmt, indent: int) -> list[str]:
        pad = "    " * indent
        if isinstance(stmt, VarDecl):
            c = self._bind(stmt.name)
            return [f"{pad}{K.C_TYPE[stmt.type_name]} {c} = {self._expr(stmt.init)}; // {stmt.name}"]
        if isinstance(stmt, Assign):
            return [f"{pad}{self._lookup(stmt.name)} = {self._expr(stmt.value)}; // {stmt.name}"]
        if isinstance(stmt, Return):
            return [f"{pad}return {self._expr(stmt.value)};"]
        if isinstance(stmt, Print):
            return [f"{pad}{self._print(stmt.value)};"]
        if isinstance(stmt, CallStmt):
            return [f"{pad}{self._expr(stmt.call)};"]
        if isinstance(stmt, If):
            lines = [f"{pad}if ({self._expr(stmt.cond)}) {{"]
            self._enter_scope()
            for s in stmt.then_body:
                lines.extend(self._stmt_lines(s, indent + 1))
            self._leave_scope()
            if stmt.else_body is not None:
                lines.append(f"{pad}}} else {{")
                self._enter_scope()
                for s in stmt.else_body:
                    lines.extend(self._stmt_lines(s, indent + 1))
                self._leave_scope()
            lines.append(f"{pad}}}")
            return lines
        if isinstance(stmt, Loop):
            lv = self._bind(stmt.var)
            lines = [
                f"{pad}for ({K.C_TYPE[K.INT]} {lv} = {self._expr(stmt.start)}; "
                f"{lv} <= {self._expr(stmt.end)}; {lv} = {lv} + 1) {{ // {stmt.var}"
            ]
            self._enter_scope()
            for s in stmt.body:
                lines.extend(self._stmt_lines(s, indent + 1))
            self._leave_scope()
            lines.append(f"{pad}}}")
            return lines
        raise ValueError(f"未対応の文法ノード {type(stmt).__name__}")

    def _print(self, e) -> str:
        t = e._type
        if t == K.INT:
            return f'printf("%lld\\n", (long long)({self._expr(e)}))'
        if t == K.FLOAT:
            return f'printf("%g\\n", (double)({self._expr(e)}))'
        if t == K.STRING:
            return f'printf("%s\\n", {self._expr(e)})'
        if t == K.BOOL:
            return f'printf("%s\\n", ({self._expr(e)}) ? "真" : "偽")'
        raise ValueError(f"表示できる型ではありません: {t}")

    # ---- 式 ---------------------------------------------------------------
    def _expr(self, e) -> str:
        if isinstance(e, IntLit):
            return f"{e.value}LL"
        if isinstance(e, FloatLit):
            return _c_float(e.value)
        if isinstance(e, StringLit):
            return _c_string(e.value)
        if isinstance(e, BoolLit):
            return "true" if e.value else "false"
        if isinstance(e, Var):
            return self._lookup(e.name)
        if isinstance(e, Call):
            c = self.names.func(e.name)
            args = ", ".join(self._expr(a) for a in e.args)
            return f"{c}({args})"
        if isinstance(e, Unary):
            o = self._expr(e.operand)
            if e.op == "-":
                return f"(-({o}))"
            if e.op == "ではない":
                return f"(!({o}))"
            raise ValueError(f"未対応の単項演算子 {e.op}")
        if isinstance(e, BinOp):
            return self._binop(e)
        raise ValueError(f"未対応の式ノード {type(e).__name__}")

    def _binop(self, e: BinOp) -> str:
        l = self._expr(e.left)
        r = self._expr(e.right)
        lt, rt = e.left._type, e.right._type
        if e.op == "/":
            # 仕様: 整数 / 整数 も小数（C 側で常に倍精度除算にする）
            return f"((double)({l}) / (double)({r}))"
        if e.op in ("+", "-", "*"):
            return f"({l} {e.op} {r})"
        if e.op in ("<", "<=", ">", ">="):
            return f"({l} {e.op} {r})"
        if e.op in ("==", "!="):
            if lt == K.STRING:
                op = "==" if e.op == "==" else "!="
                return f"(strcmp({l}, {r}) {op} 0)"
            return f"({l} {e.op} {r})"
        if e.op == "かつ":
            return f"({l} && {r})"
        if e.op == "または":
            return f"({l} || {r})"
        raise ValueError(f"未対応の演算子 {e.op}")


def _c_string(s: str) -> str:
    out = []
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\x{ord(ch):02x}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _c_float(v: float) -> str:
    s = repr(v)
    if re.fullmatch(r"[+-]?\d+", s):
        s += ".0"
    # 巨大値は 1e+308 などの C で有効な形になる
    return s
