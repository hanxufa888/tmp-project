---
name: speccheck-workflow
description: "仕様書チェックを行うためのルールと手順です。手順にはチェック項目毎の実施要否判定方法も含まれます。仕様書チェックを行う場合は必ず利用して下さい。"
---

# 仕様書チェック

## 仕様書チェックの目的

正式発効前の仕様書について、チェック項目に従い、内容の不備不足の有無や他の仕様書への影響を確認し、問題を検出してレポートする。

## 用語定義

- **チェック対象仕様書**: ユーザープロンプトで与えられる、メータ仕様書の要件が記載されているファイル。

## 仕様書チェックのステップ

| Step | 内容 | 詳細ファイル |
|---|---|---|
| Step 1 | チェック対象データの作成 | [steps/step1_prep_checkdata.md](steps/step1_prep_checkdata.md) |
| Step 2 | チェック項目ラベリング | [steps/step2_labeling.md](steps/step2_labeling.md) |
| Step 3 | サブエージェントによるチェック実施 | [steps/step3_check.md](steps/step3_check.md) |
| Step 4 | 結果集約・レポート出力 | [steps/step4_report.md](steps/step4_report.md) |

## 共通テンプレート

- [ラベリングサブエージェントプロンプト](templates/labeling_subagent_prompt.md)
- [サブエージェントプロンプト](templates/subagent_prompt.md)
- [レポートフォーマット](templates/report_format.md)

## 最重要ルール（親エージェントが厳守すべき事項）

入力の選択（Step1）:

- **変更後仕様書（チェック対象仕様書）のmd変換（Step1）**: 変更後仕様書のローカル office ファイルを spec2model-to-markdown skill で Markdown 化し、`check_spec/<変更後仕様書名>/` 配下へ格納する（変換対象は変更後仕様書のみ。差分CSVの用意手順には影響しない）。詳細は [steps/step1_prep_checkdata.md](steps/step1_prep_checkdata.md) の「手順（変更後仕様書のマークダウン変換）」を参照。
- 通常は差分データ(CSV, spec2model-cloud-diff / spec2model-local-diff の出力を固定パス `specification_check/output/spec_diff.csv` へ出力したもの)を入力とする。
  - 差分CSVが未生成で、変更前・変更後の仕様書ファイルが与えられた場合は、まず差分skillで差分CSVを固定パス `specification_check/output/spec_diff.csv` へ生成してからStep1を実行する（`--out-csv` / `--out-html` に固定パスを明示。詳細は step1）。変更後仕様書はローカル（`check_spec/<変更後仕様書名>/`）、変更前仕様書は通常クラウド（KGA）とし、**既定は spec2model-cloud-diff**、変更前がクラウドに無い場合のみ spec2model-local-diff を用いる。詳細は [steps/step1_prep_checkdata.md](steps/step1_prep_checkdata.md) の「手順（差分CSVの用意）」を参照。
- 次のいずれかは差分が存在しないため、`check_spec/<仕様書名>/` 配下のmdを入力とし、全内容を「追加」の差分相当レコードへ変換して Step1〜4 を実行する。
  - ① 変更前仕様書が無し（新設仕様書）。
  - ② 変更後仕様書に変更前に無いファイルが追加され、当該ファイルが差分データに現れない（ファイル追加）。
- ②で既存ファイルの差分も併存する場合は、既存ファイルを差分データから、追加ファイルを `check_spec` から変換し、両レコードを結合する。
- DMSファイル（通信仕様書, ファイル名に "DMS" を含む）は上記の変換対象から除外する。
- フォーマットはファイル単位で判定する。新設仕様書で本体（新フォーマット）と添付資料（`_Appendix`/`_Attachment`/`添付` を含む＝旧フォーマット扱い）が混在する場合、本体は `newformat_md_to_newspec_json.py`（添付資料を自動除外）、添付資料は `oldformat_md_to_newspec_json.py --attachment-only --append` で同一JSONへ結合する。Step2の適用フォーマット節もレコード単位で切り替える（本体＝新／添付資料＝旧）。
- 詳細は [steps/step1_prep_checkdata.md](steps/step1_prep_checkdata.md) の「手順（新設・ファイル追加）」を参照。

## MCP（graph_*）探索スコープのカテゴリ制約

チェック対象仕様書以外の別仕様書を MCP（`graph_*`）で探索する際の対象カテゴリは、以下のポリシーで決定する。親エージェントは本ポリシーを守り、かつ **Step2（ラベリング）・Step3（チェック）の全サブエージェントプロンプトに必ず引き継ぐ**こと（サブエージェント側は親から渡された探索カテゴリ制約に従う）。

- **既定（ユーザプロンプトでカテゴリ指定が無い場合）**: MCP（`graph_*`）での別仕様書探索は、対象をカテゴリ「**MET_COMMON**」に限定する。
- **ユーザプロンプトでカテゴリ指定がある場合**: そのカテゴリ指定に従う（既定の MET_COMMON ではなく、指定されたカテゴリに限定する）。指定が複数カテゴリの場合はそのすべてを対象とする。
- いずれの場合も、確定した探索カテゴリ制約を Step2・Step3 の各サブエージェントプロンプトへ**原文で明記して引き継ぐ**（引き継ぎ漏れを禁止する）。サブエージェントは `graph_list_document_categories` 等で当該カテゴリを確認しつつ、`graph_search_keyword`／`graph_search_hybrid`／`graph_list_nodes` 等の探索を当該カテゴリの文書に絞って実施する。

## 実行環境の注意（コマンド実行・サンドボックス）

- Step1〜4で実行する同梱pythonスクリプト（`skills/speccheck-workflow/scripts/` 配下）は、`specification_check/output/` 配下へファイルを書き込む。
- **speccheck-workflow 同梱スクリプト（`csv_to_diff_json.py` / `checkno_split_merge.py` / `mark_invalid_items.py` / `newformat_md_to_newspec_json.py` / `oldformat_md_to_newspec_json.py` / `merge_results_to_report.py` / `report_md_to_xlsx.py` 等）は、素の `python skills/speccheck-workflow/scripts/...` で実行する**（既存 allow `PowerShell(python:*)` に一致させ承認プロンプトを回避）。`tools/spec2model/.venv/Scripts/python.exe`（venv python）は spec2model の parse/compare/変換 を伴う **spec2model-cloud-diff / spec2model-local-diff の解析・差分ステップ、および spec2model-to-markdown による変更後仕様書のmd変換（Step1「手順（変更後仕様書のマークダウン変換）」）専用**であり、speccheck-workflow スクリプトには流用しない（venv python は `PowerShell(python:*)` にマッチしないため）。なお venv python を起動する際は **必ずフォワードスラッシュ表記 `tools/spec2model/.venv/Scripts/python.exe`** を用いる（allow `PowerShell(tools/spec2model/.venv/Scripts/python.exe:*)` に一致させるため）。バックスラッシュ表記 `tools\spec2model\.venv\Scripts\python.exe` は権限パターン照合で `\` がエスケープ扱いとなりマッチせず、承認プロンプトが発生するため使わない。
- **`dangerouslyDisableSandbox` は使用しないこと。** 既存の allow 設定 `PowerShell(python:*)` が全 python 実行を許可しており、本運用環境（Windows / PowerShellツール）では書込みサンドボックスの強制が無いため、通常実行のまま承認プロンプトなしで書き込みが完了する。`dangerouslyDisableSandbox: true` は allow 登録の有無に関わらず**必ず対話確認が発生する**ため使わない。
- **コマンドは1つずつ個別に実行し、`;` / `&&` / `if ($?) { … }` 等で連結しないこと。** 連結すると1つの複合コマンド文字列となり `PowerShell(python:*)`（先頭一致）にマッチせず承認プロンプトが発生する。依存する複数スクリプトは、前段の完了を確認してから次段を個別のツール呼び出しで実行する。
- 上記以外のコマンドも通常どおりサンドボックス下で実行する（サンドボックス回避を他コマンドへ流用しない）。settings.json 側のサンドボックス設定は変更しない。
- （最終手段の例外）書込みサンドボックスを強制する環境でスクリプトの書き込みがブロックされる場合に限り、当該スクリプトを**単独で**（連結せず）`dangerouslyDisableSandbox: true` で実行してよい。出力先は `specification_check/` 配下に限定する。通常運用では使用しない。

## ファイル一覧取得の運用

- **ディレクトリ／ファイル一覧の確認は原則 Glob ツールを用いる**（`check_spec/<仕様書名>/` 配下のmd一覧や添付資料トークン検出等）。`Get-ChildItem` を用いる場合も、`;` によるコマンド連結や `Select-Object` 等との併用を避け、`Get-ChildItem <path>` の単独実行とする（allow の `PowerShell(Get-ChildItem:*)` に一致させるため）。
