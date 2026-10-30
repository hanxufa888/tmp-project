# scripts

仕様書チェックの各Stepで用いる独立スクリプト群。

> **実行時の共通ルール（重要）**: 各スクリプトはプロジェクトの `.claude`（PowerShellツールの既定カレントディレクトリ）を起点に実行する。`cd` は不要。スクリプトパスは `skills/speccheck-workflow/scripts/<name>.py`、入出力パスは `specification_check/...` の形で、いずれも `.claude` からの相対パスで指定する（ユーザー名を含む絶対パスを書かないため、`settings.json` の許可 `PowerShell(python:*)` と合わせてメンバー間で共有可能）。

## csv_to_diff_json.py（Step1 手順1）

`specification_check/output/` 配下の差分CSV（`spec2model-cloud-diff` / `spec2model-local-diff` の出力を固定名 `spec_diff.csv` で出力したもの）を取り込み、後続手順の入力JSONへ変換する。

### セットアップ

追加の依存パッケージは不要（標準ライブラリのみで動作）。

### 実行

```text
python skills/speccheck-workflow/scripts/csv_to_diff_json.py --in "specification_check/output/spec_diff.csv" --out "specification_check/output/spec_diff.json"
```

### 主なオプション

| オプション | 既定 | 説明 |
|---|---|---|
| `--in` | (必須) | 入力 CSV パス（`specification_check/output/spec_diff.csv`。spec2model diff 出力CSVを固定パスへ出力したもの） |
| `--out` | `diff.json` | 出力 JSON パス |

### 入力CSVの構成

spec2model diff の共通スキーマ（`spec2model-cloud-diff` / `spec2model-local-diff` で同一）。列名で対応付ける（順不同・欠落は空文字扱い）。主な列：
`file_old`, `file_new`, `sheet_name`, `chapter_key`, `chapter_title_old`, `chapter_title_new`, `paragraph_key`, `paragraph_title_old`, `paragraph_title_new`, `before_markdown`, `after_markdown` ほか

### 出力

各行を次の8キーへ対応付けて JSON 化する：
`file_old`, `sheet_old`, `chapter_old`, `file_new`, `sheet_new`, `chapter_new`, `before_markdown`, `after_markdown`

列対応：

| 出力キー | CSV列 |
|---|---|
| `file_old` | `file_old`（ファイル名部分のみ） |
| `sheet_old` | `sheet_name` |
| `chapter_old` | `paragraph_title_old` → `chapter_title_old` → `paragraph_key` → `chapter_key`（最初に非空の値） |
| `file_new` | `file_new`（ファイル名部分のみ） |
| `sheet_new` | `sheet_name` |
| `chapter_new` | `paragraph_title_new` → `chapter_title_new` → `paragraph_key` → `chapter_key`（最初に非空の値） |
| `before_markdown` | `before_markdown` |
| `after_markdown` | `after_markdown` |

- CSVの1行=変更ブロック単位の差分（章節へ集約しない）。行の抽出・破棄は行わず、各セルの値そのものは要約・改変しない。

## newformat_md_to_newspec_json.py（Step1「新設・ファイル追加」/ 新フォーマット .xlsm 用）

差分データが存在しないケース（①新設仕様書／②差分データに現れない追加ファイル）で、`check_spec/<仕様書名>/` 配下の変換済みmd（本体・添付資料）を、通常差分JSONと互換のレコードJSONへ変換する（全内容を「追加」として `before_markdown=""` で生成）。

### 実行

```text
python skills/speccheck-workflow/scripts/newformat_md_to_newspec_json.py --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
```

### 主なオプション

| オプション | 既定 | 説明 |
|---|---|---|
| `--spec-dir` | (必須) | `check_spec/<仕様書名>/` ディレクトリ（配下の全mdを取込） |
| `--out` | (必須) | 出力 JSON パス |

### 仕様

- **DMSファイル（通信仕様書）は変換対象から除外**する（ファイル名に "DMS" を含むものをスキップ）。
- **添付資料（`_Appendix`/`_Attachment`/`添付` を含むファイル）は変換対象から除外**する（旧フォーマット扱いとし、`oldformat_md_to_newspec_json.py --attachment-only` で別途変換して結合する。スキップ対象はログ出力）。
- 粒度は「シート×章節」。1レコード=1章節(段落)の表全体を原文のまま保持（`item="(章節全体)"`）。章節見出しを持たないシート（添付資料等）はシート全体を1レコードとする。
- 無効シート（MSG/Variable_MSG/SW_MSG/Revision history）・無効章節（1.システム内容説明 等）は `excluded:true`。項目(列)単位の無効情報は章節レコード内に原文保持され、Step2のラベリング時に `mark_invalid_items.py` が `invalid_items` として付与し、サブエージェントが当該列を照合対象から除外する（依存: 標準ライブラリのみ）。

## oldformat_md_to_newspec_json.py（旧フォーマット新設仕様書用 / Step1）

**旧フォーマット仕様書（Word由来 .doc/.docx の変換md）の新設仕様書・ファイル追加**専用スクリプト。旧フォーマット（md先頭が `# 目次`、`## 章節`、`### 段落` のみでシート見出しを持たない）では `newformat_md_to_newspec_json.py`（`# 見出し=シート, ## 見出し=章節` を前提）では表が捕捉されないため、本スクリプトで Step1（章節単位レコード化）のみを実行する。`checkno` は付与せず、Step2の付与はサブエージェント（`checkno_split_merge.py`）で行う。

### 実行

```text
python skills/speccheck-workflow/scripts/oldformat_md_to_newspec_json.py --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
```

本体（新フォーマット）と添付資料（旧フォーマット扱い）が混在する新設仕様書では、本体を `newformat_md_to_newspec_json.py`（添付資料を自動スキップ）で変換した後、添付資料のみを本スクリプトで変換し**同一JSONへ結合**する（`--attachment-only` / `--append`）:

```text
python skills/speccheck-workflow/scripts/newformat_md_to_newspec_json.py --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
python skills/speccheck-workflow/scripts/oldformat_md_to_newspec_json.py --attachment-only --append --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
```

### 主なオプション

| オプション | 既定 | 説明 |
|---|---|---|
| `--spec-dir` | (必須) | `check_spec/<仕様書名>/` ディレクトリ（配下の全mdを取込。DMSファイルは除外） |
| `--out` | (必須) | 出力 JSON パス |
| `--attachment-only` | 無効 | 添付資料（`_Appendix`/`_Attachment`/`添付`）のみを変換対象とする（本体が新フォーマットで、添付資料のみを旧フォーマット扱いする場合に指定） |
| `--append` | 無効 | `--out` が既存の配列JSONの場合、上書きせず末尾へレコードを追記する（本体の新フォーマットJSONへ添付資料レコードを結合する場合に指定） |

### 仕様

- 粒度は「章節（`##`）」。`### 段落`は章節本文に含める（1レコード=1章節の表全体を原文保持、`item="(章節全体)"`, `source="new_spec"`）。出力スキーマは `newformat_md_to_newspec_json.py` と同一（`checkno` は付与しない）。
- **`## 章節` を1つも持たないmd**（添付資料等: `# シート見出し`＋表のみ）は、`#` 見出し（「目次」を除く）を章節見出しとみなして1レコード化する（`sheet_new=""`・`chapter_new=<# 見出し>`）。
- **変更履歴章節**（変更履歴/変更概要/更新履歴/Revision history）は `excluded:true`。**DMSファイル**は変換対象から除外。
- 章節名の同義（`guide-oldformat.md`）: `*.入力`=`*.入力・定数`, `*.通常制御`=`*.制御仕様`。
- `checkno` は付与しない（機械判定は行わない）。Step2の付与はサブエージェント（`checkno_split_merge.py`）で行う（依存: 標準ライブラリのみ）。

## mark_invalid_items.py（Step2 列除外アノテータ / 新設フロー）

新設・ファイル追加（`new_spec`, 新フォーマット）レコードに、項目(列)単位の無効列を `invalid_items`(配列) として付与する。Step2ラベリングのサブエージェントが、章節テーブル走査時に無効列（識別子列 要求ID/Ver/No 等、`guide-newformat-invalid.md` 由来の各種"数"・R/R・"特別処理が必要な理由" 等）を場所条件照合から除外するために用いる。原文（`after_markdown`）は改変しない。無効列の定義は `newformat_md_to_newspec_json.py`（IDENTIFIER_HEADERS / INVALID_ITEMS_ALL / INVALID_ITEMS_BY_SHEET）を再利用する。

### 実行

```text
python skills/speccheck-workflow/scripts/mark_invalid_items.py --io "specification_check/output/<仕様書名>_newspec.json"
```

| オプション | 既定 | 説明 |
|---|---|---|
| `--io` | (必須) | 入出力JSON（Step1出力の newspec.json。`invalid_items` を付与して上書き） |

- `excluded:true` レコードは `invalid_items=[]`。
- 対象は新フォーマットの章節テーブルを持つレコード。旧フォーマットでは概ね空になる。
- チェック項目の追加・変更では本スクリプトの更新は不要（無効列自体が増えた場合のみ）。依存: 標準ライブラリのみ。
- 付与した `invalid_items` は `checkno_split_merge.py split` により各 `rec_XXXXX.json` へ引き継がれる。

## checkno_split_merge.py（Step2 ラベリングのサブエージェント化）

Step2ラベリングを「1レコード=1サブエージェント」で行うための分割/マージスクリプト。親エージェントが差分本文を読み込まずに各レコードをサブエージェントへ配布し、サブエージェントが付与した `checkno` を機械的に元JSONへ書き戻すために用いる（親コンテキストの圧迫による精度低下を防止）。通常差分（`spec_diff.json`。分割先は `spec_diff_records`）・新設/ファイル追加（`<仕様書名>_newspec.json`）の双方に用いる（本スクリプト自体は `--in`/`--outdir`/`--out` を引数に取る汎用ツールで、以下の `<name>` は総称）。

### 実行

```text
# 分割: Step1出力JSONをレコード単位に分割し manifest.json を出力
python skills/speccheck-workflow/scripts/checkno_split_merge.py split --in "specification_check/output/<name>_diff.json" --outdir "specification_check/output/<name>_records"

# マージ: サブエージェント結果(rec_XXXXX.checkno.json)を集約して checkno を書き戻す
python skills/speccheck-workflow/scripts/checkno_split_merge.py merge --in "specification_check/output/<name>_diff.json" --resultsdir "specification_check/output/<name>_records" --out "specification_check/output/<name>_diff.json"
```

| モード | オプション | 説明 |
|---|---|---|
| `split` | `--in`（必須） | 入力（Step1出力JSON） |
| `split` | `--outdir`（必須） | レコードファイル（`rec_XXXXX.json`）と `manifest.json` の出力先ディレクトリ |
| `merge` | `--in`（必須） | 入力（Step1出力JSON。`checkno` を書き戻す対象） |
| `merge` | `--resultsdir`（必須） | サブエージェント結果（`rec_XXXXX.checkno.json` = `{"index":i,"checkno":[..]}`）の格納ディレクトリ |
| `merge` | `--out`（必須） | 出力JSONパス（`--in` と同一指定で上書き可） |
| `merge` | `--strict` | 未処理レコードがある場合に非0終了 |

### 仕様

- `split`: `excluded:true` のレコードは分割対象外（マージで `checkno=[]` を機械付与）。`excluded:false` のレコードのみ `rec_XXXXX.json` として原文のまま出力。`manifest.json` は差分本文を含まない軽量メタ（`index`/`rec_file`/`result_file`/シート・章節等）のみ。親は `manifest.json` のみ読む。
- `merge`: `excluded:true` は `checkno=[]`。結果ファイルが見つからない `excluded:false` レコードは `checkno=[]` を暫定付与し、未処理indexを警告出力する（サブエージェント未完了の検知）。`checkno` 以外の既存項目は改変しない（依存: 標準ライブラリのみ）。
- 新設・ファイル追加（`source="new_spec"`）／旧フォーマットも本スクリプトでサブエージェントラベリングを行う。旧フォーマットは `oldformat_md_to_newspec_json.py` でStep1（章節レコード化）のみ生成してから、本スクリプトの split→サブエージェント→merge を実行する。

## merge_results_to_report.py（Step3→Step4 結果集約）

Step3で各サブエージェントが書き出した結果ファイル（`<仕様書名>_check_results/res_*.json`）を集約し、Step4のチェック結果レポート（Markdown）を生成する。親エージェントは結果ファイルの中身を読み込まず、本スクリプトへ集約を委ねる（親コンテキストの圧迫を防止）。生成後は `report_md_to_xlsx.py` でExcelへ変換する。

### 実行

```text
python skills/speccheck-workflow/scripts/merge_results_to_report.py --resultsdir "specification_check/output/<仕様書名>_check_results" --out "specification_check/output/<仕様書名>_report.md" --spec-name "<仕様書名>" --diff "specification_check/output/spec_diff.json"
```

| オプション | 既定 | 説明 |
|---|---|---|
| `--resultsdir` | (必須) | サブエージェント結果（`res_*.json`）の格納ディレクトリ |
| `--out` | (必須) | 出力 Markdown レポートのパス |
| `--spec-name` | 空 | 対象仕様書の代表名（レポート見出しに記載） |
| `--diff` | なし | 任意: Step2出力 `diff.json`。結果ファイルの欠落検知に使用 |
| `--strict` | 無効 | 欠落/重複/読込失敗がある場合に非0終了 |

- 結果ファイルのスキーマ・列対応・エスケープ処理の詳細はスクリプト冒頭のdocstringを参照。
- `--diff` 指定時に結果ファイルの欠落を警告する。警告が出たら該当サブエージェントを再実行し、再度本スクリプトを実行する（依存: 標準ライブラリのみ）。

## report_md_to_xlsx.py（Step4 出力）

Step4で生成したチェック結果レポート（Markdown, 例: `diff_summary_report.md`）内の結果テーブルを取り込み、Excel(.xlsx) へ変換する。Step4の出力は Markdown と Excel の双方とする。

### セットアップ

`openpyxl` が必要（未導入の場合は `pip install openpyxl`）。

### 実行

```text
python skills/speccheck-workflow/scripts/report_md_to_xlsx.py --in "specification_check/output/<仕様書名>_report.md" --out "specification_check/output/<仕様書名>_report.xlsx"
```

### 主なオプション

| オプション | 既定 | 説明 |
|---|---|---|
| `--in` | (必須) | 入力 Markdown レポートのパス |
| `--out` | `report.xlsx` | 出力 Excel パス |
| `--heading` | `結果出力` | 変換対象テーブルの見出しテキスト |
| `--sheet` | 見出しテキスト | 出力シート名 |

### 変換対象

- 既定では見出し「## 結果出力」直下の Markdown テーブルを変換する（`--heading` で変更可）。
- 見出しが見つからない場合は、ファイル内で最初に出現する Markdown テーブルを変換する。
- セル値の要約・改変は行わず、原文のまま出力する（Markdownレポートを正とする）。
