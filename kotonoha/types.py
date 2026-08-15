"""ことのはの型定義と C 型への対応。"""

INT = "整数"
FLOAT = "小数"
STRING = "文字列"
BOOL = "論理"
NONE = "なし"

ALL_TYPES = (INT, FLOAT, STRING, BOOL, NONE)
NUMERIC = (INT, FLOAT)

# C への対応（設計判断 D12）
C_TYPE = {
    INT: "long long",
    FLOAT: "double",
    STRING: "const char *",
    BOOL: "bool",
    NONE: "void",
}


def is_numeric(t: str) -> bool:
    return t in NUMERIC


def is_widenable(src: str, dst: str) -> bool:
    """src 型の値が dst 型として使えるか（設計判断 D3: 整数→小数のみ）。"""
    if src == dst:
        return True
    return src == INT and dst == FLOAT
