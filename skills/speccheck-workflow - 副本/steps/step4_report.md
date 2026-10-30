# Step4: 結果集約・レポート出力

## 目的

Step3で各サブエージェントが書き出した結果ファイル（JSON群）をスクリプトで集約し、最終レポート（Markdown＋Excel）を生成する。

## エージェントの責務

親エージェントは、以下2つのスクリプトを順に実行し、出力ファイルが生成されたことを確認する。結果ファイルの中身の読み込み・集約・整形はスクリプトが行うため、親は実行と存在確認のみを担う（プロジェクトの `.claude` を起点に実行。`cd` 不要。パスは `.claude` からの相対で指定。実行環境の共通ルールは [SKILL.md](../SKILL.md) の「実行環境の注意」を参照）。

1. Markdownレポート生成（結果ファイル群の集約）

   ```text
   python skills/speccheck-workflow/scripts/merge_results_to_report.py --resultsdir "specification_check/output/<仕様書名>_check_results" --out "specification_check/output/<仕様書名>_report.md" --spec-name "<仕様書名>" --diff "specification_check/output/spec_diff.json"
   ```

   - `--diff` はStep2出力JSON（通常差分フロー: `spec_diff.json`、新設・ファイル追加フロー: `<仕様書名>_newspec.json`）を指定する。
   - **出力フォーマットの切り替え**: 既定は通常フォーマット（13列。先頭8列に加え「最終判定」「判定理由」「実施者」「確認者」「承認者」）。**ユーザープロンプトで「精度検証用フォーマット」での出力指示があった場合のみ** `--accuracy-format` を付与し、AI判定の正誤をラベリングするための列構成（14列。先頭8列に加え「チェック選定正誤判定」「チェック結果正誤判定」「判定理由」「実施者」「確認者」「期待チェックフラグ」）で出力する。指示が無ければ通常フォーマットとする。
   - **列「チェック項目」の機械補完（案X）**: 本スクリプトは結果JSONの `check_item` が空の場合、`checkno` から CHK定義（`check/CHK-*.md`）の「# チェック項目」本文を読み取り列「チェック項目」へ補完する。CHK定義フォルダは `--check-dir` で指定でき、既定は `skills/speccheck-workflow/check`。**`MET-G` を含む仕様書のチェックでは `--check-dir "skills/speccheck-workflow/MET-G_check"` を指定する**（Step2/Step3のチェック項目ファイル分岐と揃える）。
   - 欠落・重複・読込失敗の警告が出た場合は、該当サブエージェント（該当 `index`）をStep3で再実行して結果ファイルを出力し直し、再度本スクリプトを実行する。

2. Excelレポート生成（Markdownからの機械変換）

   ```text
   python skills/speccheck-workflow/scripts/report_md_to_xlsx.py --in "specification_check/output/<仕様書名>_report.md" --out "specification_check/output/<仕様書名>_report.xlsx"
   ```

   - 依存パッケージ `openpyxl` が必要（未導入の場合は `pip install openpyxl`）。

`<仕様書名>` はチェック対象仕様書の代表名（`check_spec/<仕様書名>/` のフォルダ名）とし、1回のチェックで全体を1レポートに集約する。レポート構成は[レポートフォーマット](../templates/report_format.md)を参照。

## ユーザーへの最終報告

親エージェントがユーザーへ返す完了報告は、以下のみとする。

- 生成したレポートのファイルパス（`<仕様書名>_report.md` / `<仕様書名>_report.xlsx`）。
- 集約スクリプトが標準出力に示した件数・警告（例: `結果行数=N`、欠落indexの警告有無）。
- チェック結果の詳細（各CHKの判定・根拠・該当記述等）はレポートファイルを参照する旨の案内。

## 禁止事項

- 親エージェントが結果ファイルの中身を読み込み、手作業で表を組む・要約・言い換え・転記すること（集約はスクリプトの責務）。
- 親エージェントが結果ファイルまたは生成レポート（md/xlsx）を読み込み、チェック結果の内容サマリ（各CHKの判定・判定根拠・該当記述等）をユーザー向けに再構成・提示すること。最終報告は上記「ユーザーへの最終報告」に限定する。
- 生成されたMarkdown／Excelの内容を要約・改変・追記すること（Markdownレポートを正とし、Excelはその機械変換とする）。

## 自己チェック

- [ ] `merge_results_to_report.py` を実行し、Markdownレポート(`<仕様書名>_report.md`)を生成したか？
- [ ] 欠落・重複・読込失敗の警告が無いことを確認したか？（あれば該当サブエージェントを再実行し、再集約したか）
- [ ] `report_md_to_xlsx.py` を実行し、Excelレポート(`<仕様書名>_report.xlsx`)を生成したか？
- [ ] 親エージェントが結果ファイルの中身を読み込み・要約・転記していないか？
- [ ] ユーザーへの完了報告を、ファイルパスとスクリプト出力（件数・警告）のみに留めたか？（判定内容のサマリを作っていないか）
