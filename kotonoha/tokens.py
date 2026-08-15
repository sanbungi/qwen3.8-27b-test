"""トークン種別の定義。"""
from dataclasses import dataclass
from enum import Enum, auto


class TT(str, Enum):
    # リテラル / 識別子
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    IDENT = auto()

    # キーワード
    KW_変数 = auto()
    KW_を = auto()
    KW_と = auto()
    KW_する = auto()
    KW_関数 = auto()
    KW_返す = auto()
    KW_もし = auto()
    KW_ならば = auto()
    KW_そうでなければ = auto()
    KW_繰り返す = auto()
    KW_から = auto()
    KW_まで = auto()
    KW_主処理 = auto()
    KW_真 = auto()
    KW_偽 = auto()
    KW_表示 = auto()
    KW_かつ = auto()
    KW_または = auto()
    KW_ではない = auto()
    # 型名（リテラル兼キーワード）
    KW_整数 = auto()
    KW_小数 = auto()
    KW_文字列 = auto()
    KW_論理 = auto()
    KW_なし = auto()

    # 演算子
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    EQ = auto()
    NE = auto()
    ARROW = auto()  # ->

    # 句読点・括弧
    LBRACE = auto()   # {
    RBRACE = auto()   # }
    LPAREN = auto()   # （
    RPAREN = auto()   # ）
    COMMA = auto()    # 、
    PERIOD = auto()   # 。
    COLON = auto()    # :

    EOF = auto()


KEYWORDS = {
    "変数": TT.KW_変数,
    "を": TT.KW_を,
    "と": TT.KW_と,
    "する": TT.KW_する,
    "関数": TT.KW_関数,
    "返す": TT.KW_返す,
    "もし": TT.KW_もし,
    "ならば": TT.KW_ならば,
    "そうでなければ": TT.KW_そうでなければ,
    "繰り返す": TT.KW_繰り返す,
    "から": TT.KW_から,
    "まで": TT.KW_まで,
    "主処理": TT.KW_主処理,
    "真": TT.KW_真,
    "偽": TT.KW_偽,
    "表示": TT.KW_表示,
    "かつ": TT.KW_かつ,
    "または": TT.KW_または,
    "ではない": TT.KW_ではない,
    "整数": TT.KW_整数,
    "小数": TT.KW_小数,
    "文字列": TT.KW_文字列,
    "論理": TT.KW_論理,
    "なし": TT.KW_なし,
}

TYPE_KEYWORDS = {
    TT.KW_整数,
    TT.KW_小数,
    TT.KW_文字列,
    TT.KW_論理,
    TT.KW_なし,
}


@dataclass
class Token:
    kind: TT
    value: str  # INT/FLOAT/STRING/IDENT の内容、またはキーワード・記号の文字列
    line: int   # 1始まり
    col: int    # 1始まり（文字単位、バイトでなくコードポイント）

    def __repr__(self):
        return f"Token({self.kind.name}, {self.value!r}, {self.line},{self.col})"
