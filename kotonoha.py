#!/usr/bin/env python3
"""ことのはコンパイラ（ラッパー）。例: python3 kotonoha.py hello.koto --run"""
import sys
from kotonoha.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
