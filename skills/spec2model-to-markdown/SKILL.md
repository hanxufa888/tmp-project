---
name: spec2model-to-markdown
description: "ローカルの Office 文書を spec2model で Markdown に変換する skill。添付ファイルまたは明示的なローカルパスの .xlsx/.xlsm/.xls/.docx/.doc/.pptx を、単体またはディレクトリ単位で .md に変換するときに使用する。画像抽出、TOC、Excel セルの塗りつぶし・パターン情報の style メタデータ化にも対応する。PDF、ファイル名だけで示されたクラウド/KGA 文書の取得・変換、文書差分には使用しない。"
argument-hint: "<local-file-or-directory> [--no-style-metadata] [--toc]"
---

# spec2model to Markdown

## 用途

この skill は、アクセス可能なローカル文書を現在の workspace の `tools/spec2model` で解析し、Markdown ファイルへ変換します。

対象入力：

- 添付ファイル
- 明示的なローカルファイルパス
- 対応文書を含む明示的なローカルディレクトリ

対応形式：

```text
.xlsx .xlsm .xls .docx .doc .pptx
```

PDF、ファイル名だけで示されたクラウド/KGA 文書の変換、文書差分、Markdown から別形式への変換には使用しません。

入力ファイルが PDF の場合は、この skill では変換できないことをユーザーへ明示します。PDF から Markdown への変換が必要な場合は、Azure AI Document Intelligence の Layout モデル `prebuilt-layout` を使用し、`outputContentFormat=markdown` を指定するよう案内します。API の利用には Azure Document Intelligence リソース、ネットワーク接続、サービスの endpoint/key が必要です。この workspace の既存実装で使用する環境変数名は `AZURE_DI_ENDPOINT` と `AZURE_DI_API_KEY` です。PDF 内の画像実体は保存されないことも伝えます。

## 必須条件

- workspace の `tools/spec2model` のみを使用しなければならない（MUST）。
- Python は OS に応じた固定 venv（Windows: `tools\spec2model\.venv\Scripts\python.exe`、POSIX: `tools/spec2model/.venv/bin/python`）を使用しなければならない（MUST）。
- Python のバージョンは `>=3.10,<3.14` でなければならない（MUST）。
- 変換には同梱スクリプト [`scripts/export_to_markdown.py`](./scripts/export_to_markdown.py) を使用する（MUST）。
- 入力元ファイルを変更してはならない（MUST NOT）。
- `:Zone.Identifier` と未対応形式は変換対象に含めてはならない（MUST NOT）。
- ユーザーが要求していない場合、生成 Markdown の全文を会話へ貼り付けてはならない（MUST NOT）。

## 標準手順

### 1. 入力を確認

入力が実在するローカルファイル、添付ファイル、またはディレクトリであることを確認します。ファイル名だけでローカルパスが不明な場合は、この skill を使用して推測してはなりません。

### 2. 環境を確認

workspace ルートで実行します。

Windows PowerShell：

```powershell
$python = "tools\spec2model\.venv\Scripts\python.exe"
Test-Path $python
& $python --version
& $python ".agents\skills\spec2model-to-markdown\scripts\export_to_markdown.py" --help
```

Windows で venv がない場合は、まず利用可能な Python を確認します。3.10～3.13 のいずれかを選び、`tools/spec2model` 配下だけに作成します。

```powershell
py -0p
py -3.11 -m venv "tools\spec2model\.venv"
$python = "tools\spec2model\.venv\Scripts\python.exe"
& $python -m pip install -r "tools\spec2model\requirements.txt"
& $python ".agents\skills\spec2model-to-markdown\scripts\export_to_markdown.py" --help
```

`py -3.11` は例です。利用可能な 3.10～3.13 に置き換えます。

POSIX shell：

```bash
test -x tools/spec2model/.venv/bin/python
tools/spec2model/.venv/bin/python --version
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py --help
```

POSIX で venv がない場合は `tools/spec2model` 配下だけに作成します。

```bash
python3 -m venv tools/spec2model/.venv
tools/spec2model/.venv/bin/python -m pip install -r tools/spec2model/requirements.txt
```

この workspace では変換スクリプトが `tools/spec2model/src` を import path に追加します。したがって、`python -c "import spec2model"` はパッケージが editable install されていない正常な venv でも失敗するため、環境確認には使用しません。

### 3. Markdown に変換

Windows PowerShell での単一ファイルの標準コマンド：

```powershell
$python = "tools\spec2model\.venv\Scripts\python.exe"
& $python ".agents\skills\spec2model-to-markdown\scripts\export_to_markdown.py" `
  "<local-file>" `
  --output-dir "data\output_data\markdown"
```

Windows PowerShell でディレクトリ内の対応文書を一括変換：

```powershell
$python = "tools\spec2model\.venv\Scripts\python.exe"
& $python ".agents\skills\spec2model-to-markdown\scripts\export_to_markdown.py" `
  "<local-directory>" `
  --recursive `
  --output-dir "data\output_data\markdown"
```

以下は POSIX shell でのコマンドです。

単一ファイルの標準コマンド：

```bash
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py \
  "<local-file>" \
  --output-dir "data/output_data/markdown"
```

ディレクトリ内の対応文書を一括変換：

```bash
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py \
  "<local-directory>" \
  --recursive \
  --output-dir "data/output_data/markdown"
```

Excel の塗りつぶし色とパターン種別は、既定でセル内メタデータとして残します：

```bash
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py \
  "<local-excel-file>" \
  --output-dir "data/output_data/markdown"
```

出力例：

```text
セル値 (style: fill:#BFBFBF, pattern:solid)
```

### 4. 出力を検証して報告

終了コードが `0` で、各入力に対応する `<stem>.md` が出力されたことを確認します。標準では画像を `<output-dir>/images` に保存し、Markdown から相対リンクします。

回答では変換成功数と失敗数、Markdown 出力先、画像出力先、使用した主要オプションを簡潔に報告します。

## オプション選択

- `--style-metadata`: Excel セルの `fill` と `pattern` を Markdown セルへ追記する（既定）。
- `--no-style-metadata`: Excel セルの style メタデータを出力しない。
- `--toc` / `--no-toc`: parser config の既定値を上書きする。
- `--no-images`: 画像抽出を無効にする。
- `--images-dir <path>`: 画像出力先を指定する。
- `--image-mode link|embed`: Markdown の画像表現を指定する。既定は `link`。
- `--recursive`: 入力ディレクトリを再帰検索する。
- `--fail-fast`: 最初の変換エラーで停止する。

完全な CLI は次で確認できます。

Windows PowerShell：

```powershell
& "tools\spec2model\.venv\Scripts\python.exe" `
  ".agents\skills\spec2model-to-markdown\scripts\export_to_markdown.py" --help
```

POSIX shell：

```bash
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py --help
```

## 失敗時対応

- Windows で `.venv/bin/python` が見つからない：`.venv\Scripts\python.exe` を使用する。
- Python が 3.10 未満または 3.14 以上：`py -0p` で 3.10～3.13 のインストールを確認し、対応版で固定 venv を再作成する。
- `--help` が失敗する：固定 venv の依存関係を修復してから再実行する。裸の `import spec2model` の成否だけでは判定しない。
- 入力が見つからない：添付の実体パスまたは明示されたローカルパスを再確認する。
- 入力が PDF：この skill では非対応であることを伝え、Azure AI Document Intelligence の `prebuilt-layout` と `outputContentFormat=markdown` による変換を案内する。
- 入力がその他の未対応形式：この skill では Markdown に変換できないことと、対応形式 `.xlsx`、`.xlsm`、`.xls`、`.docx`、`.doc`、`.pptx` をユーザーへ明示する。
- 同名出力が衝突する：同じ stem の文書を別々の出力ディレクトリへ変換する。
- 一部文書だけ失敗する：`[ERROR]` の対象と理由を報告する。成功済み出力は削除しない。
- 画像依存で失敗する：ユーザーが画像を必要としない場合に限り `--no-images` で再実行する。

## 参考

- [README](./README.md)
- [変換スクリプト](./scripts/export_to_markdown.py)
- [spec2model README](../../../tools/spec2model/README.md)