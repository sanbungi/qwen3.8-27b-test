"""ことのはコンパイラの診断エラー定義。"""


class KotonohaError(Exception):
    """コンパイラエラー。行・列番号（1始まり）を持つ。"""

    def __init__(self, message: str, line: int, col: int):
        self.message = message
        self.line = line
        self.col = col
        super().__init__(message)

    def render(self, filename: str = "<入力>") -> str:
        return f"{filename}:{self.line}:{self.col}: error: {self.message}"
