# spec2model-local-diff

## 概要

アクセス可能な 2 件のローカル文書を比較し、`spec2model` を使用して構造化された CSV 差分を出力する。必要に応じて HTML レポートも出力する。

## ユースケース

- 想定利用者：ローカル文書の改訂差分を確認する開発者、テスト担当者、仕様管理者。
- 利用シーン：ユーザーが 2 件のローカル添付ファイルまたは明示的なローカルファイルパスを提示し、before/after の内容比較を依頼する。
- スコープ内：2 件のローカル Office/PDF 文書の構造化差分、および CSV/HTML レポートの生成。
- 画像比較を要求された場合は、`scripts/diff_local_images.py` により独立した画像差分 JSON も生成する。画像内容は `ImageBlock.data_b64` で比較し、追加、削除、変更、不変、および取得不能を区別する。
- スコープ外：ローカル文書と KGA クラウド `Document JSON` の比較。ファイル名のみが与えられた 2 件のクラウド文書の比較。添付またはローカルパスがないファイル名をローカルファイルとして推定すること。
- 該当用途分類：動作検証。

## 所有者・状態

- 対応エージェント：`SKILL.md` をサポートする Agent Skills 互換エージェント。

## 入出力例

入力：ユーザーが「添付した `MET-C_HCS-CSTD-A0-03-A-C0.xlsm` と添付した `MET-C_HCS-CSTD-A0-04-A-C0.xlsm` の差分を比較してください」と依頼する。両方の文書は明示的なローカルパスでも指定できる。

出力：構造化 CSV 差分レポート、および必要に応じて生成する HTML 差分レポート。回答では両レポートの保存先と差分の要約を案内する。

この skill は現在のワークスペースの `tools/spec2model` を使用して比較を実行する。両方の入力がファイル名のみで、添付またはローカルパスがない場合はクラウド文書として扱い、`graph_diff_documents` を使用する。

## 参考

- [SKILL.md](SKILL.md)
- [ローカル差分コマンド](../../../tools/spec2model/scripts/diff_documents.py)
- [ローカル画像差分コマンド](scripts/diff_local_images.py)
- [spec2model プロジェクト README](../../../tools/spec2model/README.md)
