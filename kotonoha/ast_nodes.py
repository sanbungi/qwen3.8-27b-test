"""AST ノード定義。全ノードに位置情報（line, col）を持つ。"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Node:
    line: int = 0
    col: int = 0


# ---- 式 ---------------------------------------------------------------
@dataclass
class IntLit(Node):
    value: int = 0


@dataclass
class FloatLit(Node):
    value: float = 0.0


@dataclass
class StringLit(Node):
    value: str = ""


@dataclass
class BoolLit(Node):
    value: bool = False


@dataclass
class Var(Node):
    name: str = ""


@dataclass
class Call(Node):
    name: str = ""
    args: list = field(default_factory=list)


@dataclass
class BinOp(Node):
    op: str = ""
    left: Node = None
    right: Node = None


@dataclass
class Unary(Node):
    op: str = ""  # "-" または "ではない"
    operand: Node = None


# ---- 文 ---------------------------------------------------------------
@dataclass
class VarDecl(Node):
    name: str = ""
    type_name: str = ""
    init: Node = None


@dataclass
class Assign(Node):
    name: str = ""
    value: Node = None


@dataclass
class Return(Node):
    value: Node = None


@dataclass
class Print(Node):
    value: Node = None


@dataclass
class CallStmt(Node):
    """関数呼出文「f（...）。（設計判断 D22）"""
    call: Call = None


@dataclass
class If(Node):
    cond: Node = None
    then_body: list = field(default_factory=list)
    else_body: Optional[list] = None


@dataclass
class Loop(Node):
    var: str = ""
    start: Node = None
    end: Node = None
    body: list = field(default_factory=list)


# ---- トプレベル ----------------------------------------------------------
@dataclass
class Function(Node):
    name: str = ""
    params: list = field(default_factory=list)  # [(name, type_name), ...]
    ret_type: str = ""
    body: list = field(default_factory=list)


@dataclass
class Block(Node):
    body: list = field(default_factory=list)


@dataclass
class Program(Node):
    functions: list = field(default_factory=list)
    main: Block = None
