"""ことのはコンパイラの CLI 入口。

usage: python3 -m kotonoha <input> [-o OUT] [--build] [--run]
"""
import argparse
import os
import subprocess
import sys

from .error import KotonohaError
from .lexer import Lexer
from .parser import Parser
from .checker import Checker
from .codegen import CodeGen


def compile_source(source: str, filename: str) -> str:
    prog = Parser(Lexer(source, filename).tokenize(), filename).parse()
    Checker(prog, filename).check()
    return CodeGen(prog, filename).generate()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="kotonoha", description="「ことのは」言語コンパイラ（C へのコンパイル）")
    ap.add_argument("input", help="入力ファイル（例: hello.koto）")
    ap.add_argument("-o", "--out", help="出力する C ファイルのパス（既定: 入力ファイル名の .c）")
    ap.add_argument("--build", action="store_true", help="gcc で実行可能ファイルまで作る")
    ap.add_argument("--run", action="store_true", help="--build に加えて実行し標準出力を表示する")
    args = ap.parse_args(argv)

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"error: 入力ファイルを開けませんでした: {e}", file=sys.stderr)
        return 2

    base = os.path.splitext(args.input)[0]
    out = args.out or (base if base.endswith(".c") else base + ".c")
    binary = os.path.splitext(out)[0]

    try:
        c = compile_source(source, args.input)
    except KotonohaError as e:
        print(e.render(args.input), file=sys.stderr)
        return 1

    with open(out, "w", encoding="utf-8") as f:
        f.write(c)
    print(f"→ {out}", file=sys.stderr)

    if args.build or args.run:
        try:
            r = subprocess.run(["gcc", "-std=c11", "-O2", "-Wall", "-Wextra",
                                out, "-o", binary], capture_output=True, text=True)
        except FileNotFoundError:
            print("error: gcc が見つかりません", file=sys.stderr)
            return 2
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            return 2
        print(f"→ {binary}", file=sys.stderr)
        if args.run:
            r = subprocess.run([binary])
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
