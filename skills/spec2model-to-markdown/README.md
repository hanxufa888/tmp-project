# spec2model-to-markdown

## 概要

ローカルの Office 文書を、workspace に含まれる `tools/spec2model` で Markdown に変換する Agent Skill です。単一ファイルとディレクトリ一括変換に対応し、画像抽出、目次、Excel セルスタイルのメタデータ化を選択できます。

この skill はローカル文書専用です。KGA/クラウド文書の取得、クラウド文書名だけを使った変換、文書差分は対象外です。

## 構成

```text
spec2model-to-markdown/
├── SKILL.md
├── README.md
└── scripts/
    └── export_to_markdown.py
```

- `SKILL.md`: エージェント向けの発見条件、制約、標準手順。
- `scripts/export_to_markdown.py`: 実際の変換を行う CLI。
- `README.md`: 開発者・利用者向けの仕様と実行例。

## 対応入力

| 形式 | 拡張子 | 備考 |
|---|---|---|
| Excel | `.xlsx`, `.xlsm`, `.xls` | style metadata を既定で出力 |
| Word | `.docx`, `.doc` | parser の対応範囲に従う |
| PowerPoint | `.pptx` | PDF 変換依存関係が必要な場合がある |

PDF はこの skill の変換対象外です。PDF から Markdown への変換が必要な場合は、Azure AI Document Intelligence の Layout モデル `prebuilt-layout` を使用し、`outputContentFormat=markdown` を指定してください。API の利用には Azure Document Intelligence リソース、ネットワーク接続、サービスの endpoint/key が必要です。workspace の既存実装では `AZURE_DI_ENDPOINT` と `AZURE_DI_API_KEY` を参照します。なお、この方式では PDF 内の画像実体は保存されません。

`:Zone.Identifier` は自動的に除外されます。

## 環境

workspace ルートをカレントディレクトリとして、固定の Python を使用します。

```bash
tools/spec2model/.venv/bin/python
```

環境確認：

```bash
tools/spec2model/.venv/bin/python -c "import spec2model; print('spec2model environment ok')"
```

## 基本的な使い方

### 単一ファイル

```bash
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py \
  test_data/MET-C_HCS-CSTD-A0-03-A-C0.xlsm \
  --output-dir data/output_data/markdown
```

生成物：

```text
data/output_data/markdown/
├── MET-C_HCS-CSTD-A0-03-A-C0.md
└── images/
```

### 複数ファイル

```bash
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py \
  path/to/a.xlsx path/to/b.docx \
  --output-dir data/output_data/markdown
```

### ディレクトリ一括変換

```bash
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py \
  path/to/specifications \
  --recursive \
  --output-dir data/output_data/markdown
```

未指定時はディレクトリ直下だけを処理し、`--recursive` でサブディレクトリも処理します。

## Excel スタイルメタデータ

Excel parser が取得したセルの塗りつぶし色とパターン種別は、既定で Markdown テーブル内に追記します。

```bash
tools/spec2model/.venv/bin/python \
  .agents/skills/spec2model-to-markdown/scripts/export_to_markdown.py \
  path/to/specification.xlsm \
  --output-dir data/output_data/markdown
```

変換例：

```text
要求値 (style: fill:#BFBFBF, pattern:solid)
```

透明色、無効な色、範囲外のセル位置は出力しません。スタイル情報がない文書では通常の Markdown と同じ結果になります。

style metadata が不要な場合は `--no-style-metadata` を指定します。

## 画像

既定では parser config の Excel/Word 画像抽出を有効にし、画像を `<output-dir>/images` に保存します。Markdown 内のリンクは出力ファイルからの相対パスです。

```text
--images-dir data/output_data/assets  # 画像出力先を変更
--no-images                           # 画像抽出を無効化
--image-mode embed                    # Base64 埋め込み
```

## Markdown オプション

| オプション | 意味 | 既定値 |
|---|---|---|
| `--toc` | 目次を有効化 | parser config に従う |
| `--no-toc` | 目次を無効化 | parser config に従う |
| `--heading-base-level 1..6` | 見出し開始レベル | `1` |
| `--no-section-heading` | Sheet/Section 見出しを省略 | 見出しを出力 |
| `--no-block-spacing` | ブロック間空行を省略 | 空行を出力 |
| `--image-mode link|embed` | 画像表現 | `link` |

## 入出力と終了コード

- Markdown は `<output-dir>/<input-stem>.md` に UTF-8 で出力されます。
- 既定の出力先は `data/output_data/markdown` です。
- すべて成功した場合の終了コードは `0` です。
- 1 件以上の変換失敗がある場合の終了コードは `1` です。
- CLI 引数、入力、設定に問題がある場合の終了コードは `2` です。
- 同じ stem の入力が複数ある場合、上書きを避けるため変換前にエラーとなります。
- 既存の同名 Markdown は、変換が成功した時点で更新されます。

通常は失敗した文書があっても残りを処理します。最初の失敗で停止するには `--fail-fast` を指定します。

実行ログ例：

```text
[INFO] inputs=1 output=... toc=disabled images=...
[INFO] converting: .../specification.xlsm
[OK] .../specification.md
[DONE] converted=1 failed=0
```

## parser config

既定では `tools/spec2model/config/parser_config.yaml` を読み込みます。別設定は `--config path/to/parser_config.yaml` で指定できます。

元の設定ファイルは変更しません。CLI は一時設定を作成し、`--no-images` の有無だけを一時設定へ反映します。

## トラブルシューティング

### `spec2model` を import できない

`tools/spec2model/.venv` の依存関係を確認します。system Python や別の仮想環境へ切り替えず、固定 venv を修復してください。

### 対応ファイルが見つからない

入力パス、拡張子、`--recursive` の有無を確認します。ファイル名だけでローカルパスを推測しないでください。

### その他の未対応形式

PDF 以外の未対応形式を指定した場合も、その形式はこの skill では Markdown に変換できないことをエラーで通知します。対応形式は `.xlsx`、`.xlsm`、`.xls`、`.docx`、`.doc`、`.pptx` です。ディレクトリ入力に未対応形式が含まれる場合も、対象ファイルを暗黙に無視せず変換前に通知します。`:Zone.Identifier` は例外として無視します。

### PDF を変換したい

この skill では PDF を Markdown に変換できません。Azure AI Document Intelligence の `prebuilt-layout` モデルへ PDF を送り、出力形式に Markdown（`outputContentFormat=markdown`）を指定してください。利用には Azure リソース、endpoint/key、ネットワーク接続が必要です。スキャン PDF は OCR 品質に依存し、暗号化 PDF は処理できません。また、PDF 内の画像実体は保存されません。

### 画像処理で失敗する

画像が不要なら `--no-images` で原因を切り分けます。画像が必要なら optional image dependencies と parser config を確認します。

### 出力名が衝突する

同じ stem の入力を別々の `--output-dir` へ変換します。CLI は意図しない上書きを防ぐため、同一実行内の名前衝突を許可しません。

## 参考

- [Agent Skill 手順](SKILL.md)
- [変換 CLI](scripts/export_to_markdown.py)
- [spec2model README](../../../tools/spec2model/README.md)