# spec2model-cloud-diff

## 概要

ユーザーが指定した 1 件のローカル Office/PDF 文書と 1 件の KGA クラウド文書を比較し、構造化された CSV 差分を出力する。必要に応じて HTML レポートも出力する。

## ユースケース

- 利用シーン：ユーザーがアクセス可能なローカルファイルまたは添付ファイルを 1 件指定し、KGA クラウド文書またはその文書名を 1 件指定する。
- スコープ内：ローカルの `.xlsx`、`.xlsm`、`.xls`、`.docx`、`.pptx`、`.pdf` と、1 件の KGA クラウド文書の差分。
- 画像比較を要求された場合は、CSV/HTML と同時に画像差分 JSON を生成する。クラウド JSON の `kind: "image"` と `data_b64` を使用し、追加、削除、変更、不変、取得不能を個別に示す。
- スコープ外：2 件のローカルファイルの比較。ファイル名のみが与えられた 2 件のクラウド文書の比較。クラウド文書の代わりに全文、Markdown、検索スニペットまたは要約を用いる比較。

## 所有者・状態

- 対応エージェント：`SKILL.md` をサポートする Agent Skills 互換エージェント。

## 入出力例

入力：ユーザーが「添付した `MET-C_HCS-CSTD-A0-03-A-C0.xlsm` と、KGA 文書 `MET-C_HCS-CSTD-A0-04-A-C0.xlsm` の差分を比較してください」と依頼する。ローカル文書は明示的なローカルパスでも指定できる。

出力：構造化 CSV 差分レポート、および必要に応じて生成する HTML 差分レポート。回答では両レポートの保存先と差分の要約を案内する。

この skill は KGA MCP を通じてクラウド文書の構造化データをエクスポートし、現在のワークスペースの `tools/spec2model` で比較を実行する。既存の CSV/HTML レポートを使って比較の再実行を省略してはならない。

## 参考

- [SKILL.md](SKILL.md)
- [差分スクリプト](scripts/diff_local_with_cloud_json.py)
- [画像比較実装](scripts/image_diff.py)
- [spec2model プロジェクト README](../../../tools/spec2model/README.md)
