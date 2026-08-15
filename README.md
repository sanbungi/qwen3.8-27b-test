# Qwen3.8 27B q4が生成した日本語プログラミング言語コンパイラ

## 構成
kotonoha.py            # ラッパー: python3 kotonoha.py prog.koto [-o out.c] [--build] [--run]
kotonoha/
  __main__.py          # CLI（進捗は stderr、エラーコード 0/1/2）
  error.py tokens.py lexer.py ast_nodes.py parser.py types.py checker.py codegen.py
tests/                 # test_lexer/parser/checker/codegen/e2e
examples/              # hello factorial loop_sum division ifelse string

## サンプル → C（examples/factorial.koto）
```
関数 階乗（n: 整数） -> 整数 {
    もし n <= 1 ならば { 返す 1。 }
    返す n * 階乗（n - 1）。
}
主処理 { 表示 階乗（5）。 }
```
→
```
static long long _f0(long long _v0); // 階乗
static long long _f0(long long _v0) { // 階乗
    if ((_v0 <= 1LL)) { return 1LL; }
    return (_v0 * _f0((_v0 - 1LL)));
}
int main(void) { _f1(); return 0; }
```

## 主なテストケース
- e2e: 各サンプルを CLI → gcc → 実行 → 標準出力完全一致
- 意味: 1..10 終端含め=55、から>まで は 0 回、再帰・相互呼び出し、5/2=2.5（D19）、シャドーイングは別 C 変数
- 診断: 未定義の変数「y」（file:1:10 付き）、型不一致、未定義の文字「(」、主処理 欠如、全経路 返す 欠如 → 終了コード 1
