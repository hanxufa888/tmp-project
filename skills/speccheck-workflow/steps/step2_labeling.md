# Step2: チェック項目ラベリング

## 目的

Step1で作成したJSONの各差分レコードに対してサブエージェントを起動し、適用すべきチェック項目を `checkno` として付与する。

## 適用する選定条件ファイルの分岐【必須】

チェック項目選定条件ファイルは、**ユーザープロンプトで与えられた仕様書名**に `MET-G` を含むかで親エージェントが切り替える。

| 仕様書名 | 選定条件ファイル |
| --- | --- |
| `MET-G` を**含む**（例: `MET-G_T_SCREEN-CSTD-A1-08-A-C0.xlsx`） | [metg_check_selection.md](metg_check_selection.md) |
| `MET-G` を**含まない** | [std_ctrl_check_selection.md](std_ctrl_check_selection.md) |

以降で「選定条件ファイル」と記す箇所は、この分岐で確定した側を指す。サブエージェントへ渡すパスや原文引用も、必ず確定した側を用いる。

## 入力

- Step1で作成したJSONファイル（差分情報）
- 選定条件ファイル（上記分岐で確定した側）
- [ラベリングサブエージェントプロンプトテンプレート](../templates/labeling_subagent_prompt.md)
- 分割/マージスクリプト [scripts/checkno_split_merge.py](../scripts/checkno_split_merge.py)

## 前提

- 各差分レコードは独立してラベリング可能で、差分間に依存関係はない。
- サブエージェントは割り当てられた**1件の差分レコードのみ**を扱い、その差分に該当するチェック項目を確定する。
- 親エージェントは差分本文（`before_markdown`/`after_markdown`）を読まず、`manifest.json`（軽量メタ）とサブエージェント結果（`index`＋`checkno`）のみを扱う。差分件数が多い場合に親コンテキストが圧迫され判定精度が低下するのを防ぐため。

## 手順（通常差分フロー）

実行はプロジェクトの `.claude` を起点とする（`cd` 不要。パスは `.claude` からの相対で指定。実行環境の共通ルールは [SKILL.md](../SKILL.md) の「実行環境の注意」を参照）。

### 1. レコード分割（親コンテキスト非消費）

`checkno_split_merge.py` の `split` で、Step1出力JSONを差分レコード単位のファイル群へ分割する。

```text
python skills/speccheck-workflow/scripts/checkno_split_merge.py split --in "specification_check/output/spec_diff.json" --outdir "specification_check/output/spec_diff_records"
```

- `excluded:true` のレコードはラベリング対象外（後述の `merge` で `checkno=[]` を機械付与）。`excluded:false` のみ `rec_XXXXX.json` として出力される。
- 差分本文を含まない `manifest.json` も出力される。**親は `manifest.json` のみ読み**、対象レコードの一覧（`index`/`rec_file`/`result_file`/シート・章節メタ）を把握する。

### 2. サブエージェント並列起動（1差分＝1サブエージェント）

`manifest.json` の各エントリ（＝`excluded:false` の1差分）ごとに、[ラベリングサブエージェントプロンプトテンプレート](../templates/labeling_subagent_prompt.md) で起動し、以下を渡す。

- **担当レコードファイルのパス**（`rec_XXXXX.json`）。サブエージェントはこの1件のみを読む。
- **選定条件ファイルのパス**（確定した側）。
- **適用フォーマット節**：対象仕様書のフォーマット種別（`meter-spec-common` の判断フローで確定した新／旧）を明記し、各選定条件の該当フォーマット節を**原文引用**する。「該当節のみ適用し、他フォーマット節の対象個所・分岐を流用禁止」と明記する。
- **章節階層マップの引き渡し**（旧フォーマット必須）：旧フォーマット仕様書では、選定条件の場所条件が親章節名（`*.イニシャル処理`／`*.通常制御`／`*.入力`／`*.出力` 等）で記載される一方、差分レコードの `chapter_new` は末端段落名（例: `4-(1)機能有無判定処理`）のみを持ち親章節を含まないことがある。この粒度差により、サブエージェントが末端段落名の文字列一致で親章節条件を誤って非該当と判断する取りこぼしが生じる（同一章節内でレコード毎に判定が割れる）。これを防ぐため、**親は `check_spec/<仕様書名>/` 配下の本体mdから章節見出しの階層を走査し、「末端段落名→親章節名」の対応マップ（例: `4-(1)機能有無判定処理 → 4.イニシャル処理`）を作成して、全ラベリングサブエージェントへ渡す**こと。差分本文は読まず見出し構造のみ参照するため親コンテキストは消費しない。
- **全種類共通reference**（`concepts-spec-common-rules.md`／`concepts-spec-glossary.md`）：(B) 担当差分・照合に関係する箇所の原文引用と、(A) 両ファイルの格納先パスの双方。
- **「要求無し」除外ルール**（新フォーマットの `excluded` 再判定用。サブエージェントは1件しか読めず宣言箇所を見られないため親が渡す）：
  - (a) 「要求無し」機能ブロック/シートの一覧（親が `check_spec/<仕様書名>/` 配下の本体mdの宣言から作成。TT＝警告灯ブロック単位 例 2-A/2-B、他＝シート単位 例 BZR/SW）。
  - (b) `guide-newformat-item.md`「要求無し***/ ■要求有り***」行の抜粋（要求有無の読み方。ファイル全体は渡さない）。
  - (c) `guide-newformat-sheetsection.md` の 機能ブロック↔特別処理指示 対応の抜粋（波及判定用。Detailed Spec `8-<X>`↔TT `2-<X>`／`9`↔BZR／`10`↔MID、Detailed Spec2 `11-*`↔Variable_MID、Detailed Spec3 `12-*`↔SW。ファイル全体は渡さない）。
- **添付資料の有無／新設か否か**（CHK-046-2判定用・全フロー必須）：添付資料自体に差分が無いと差分にも `manifest.json` にも現れず、レコード単体からは有無を判別できない。そのため親は `manifest.json` の `file_new` だけで判断せず、`check_spec/<仕様書名>/` 配下のファイル名一覧を確認し、`_Appendix`/`_Attachment`/`添付` トークンを含むmd（本体・DMS以外の補足資料）の有無から判別して渡す。通常差分フローでも省略しない（CHK-046-2 のラベリング漏れに直結する）。
- **MCP探索カテゴリ制約の引き継ぎ**：[SKILL.md](../SKILL.md) の「MCP（graph_*）探索スコープのカテゴリ制約」で確定した探索対象カテゴリ（ユーザプロンプトでカテゴリ指定があればそれ、無ければ既定の「MET_COMMON」）を各サブエージェントへ引き継ぐ。ラベリングでMCP（graph_*）探索を行う場合は当該カテゴリに限定し、他カテゴリは探索しない旨を明記する。
- **結果ファイルの出力先パス**（`rec_XXXXX.checkno.json`。`manifest.json` の `result_file` に対応）。Read用途の入力パスは絶対パス（`\`／`/` いずれ）でも可。

サブエージェントは、まず担当レコードが無効情報（除外対象）か否かを判定し `excluded`（boolean）を確定する（判定基準はテンプレートの「除外フラグ（excluded）の判定」節。全フォーマット共通＝変更履歴シート・章節、新フォーマットのみ＝無効情報一覧の無効シート・無効章節および「要求無し」宣言セクション）。`excluded=true` なら `checkno=[]`、`excluded=false` なら詳細項目まで照合して `checkno` を確定し、結果ファイル `{"index":.., "excluded":<bool>, "checkno":[..]}` を出力する。これは通常差分・新設/ファイル追加の双方に適用し、スクリプトが `excluded:true` を付けなかったレコードはサブエージェントが再判定する（付与忘れ防止のセーフティネット）。

### 3. マージ（親コンテキスト非消費での書き戻し）

全結果ファイル出力後、`merge` で各レコードへ `checkno`／`excluded` を機械的に書き戻す。

```text
python skills/speccheck-workflow/scripts/checkno_split_merge.py merge --in "specification_check/output/spec_diff.json" --resultsdir "specification_check/output/spec_diff_records" --out "specification_check/output/spec_diff.json"
```

- サブエージェント結果の `excluded` を書き戻し、`excluded=true` は `checkno=[]` を機械付与する。Step1でスクリプトが `excluded:true` を付与済みのレコード（新設・ファイル追加）はサブエージェント起動対象外のため `checkno=[]` が維持される。`checkno`・`excluded` 以外の既存項目は改変・要約せず保持する。
- 結果ファイルが見つからないレコードは未処理indexとして警告される。**警告が出たら該当サブエージェントを再実行して結果ファイルを出力し、再度 `merge` してから次Stepへ進む**。

## 新設・ファイル追加（new_spec レコード）の場合

Step1で生成したレコード（`source="new_spec"`, `before_markdown=""`, `item="(章節全体)"`）も、同じ「1レコード＝1サブエージェント」でラベリングする。全内容が「追加」であるため、各選定条件の「追加があった場合」が一律に成立する点に注意する。

手順は上記 1.分割 → 2.サブエージェント → 3.マージ と同じ。ただし**新フォーマットでは分割前に列除外アノテータ [mark_invalid_items.py](../scripts/mark_invalid_items.py) を実行**し、各レコードへ無効列 `invalid_items` を付与する（サブエージェントが場所条件照合から無効列を除外するため）。入力JSONは `<仕様書名>_newspec.json`。

```text
python skills/speccheck-workflow/scripts/mark_invalid_items.py --io "specification_check/output/<仕様書名>_newspec.json"
python skills/speccheck-workflow/scripts/checkno_split_merge.py split --in "specification_check/output/<仕様書名>_newspec.json" --outdir "specification_check/output/<仕様書名>_records"
（各レコードをサブエージェントでラベリング → 結果ファイル出力）
python skills/speccheck-workflow/scripts/checkno_split_merge.py merge --in "specification_check/output/<仕様書名>_newspec.json" --resultsdir "specification_check/output/<仕様書名>_records" --out "specification_check/output/<仕様書名>_newspec.json"
```

`invalid_items` は分割時に各 `rec_XXXXX.json` へ引き継がれる（`checkno_split_merge.py` の改修は不要）。

新設・ファイル追加のサブエージェントには、通常フローの引き渡しに加えて以下を渡す。

- **新設か否か／添付資料の有無／担当レコードが添付資料か**（CHK-046-2判定用。親は `manifest.json` の `file_new` 群から判別）。
- **レコード単位のフォーマット別適用**：フォーマットは**ファイル単位**で判定する。本体（新フォーマット .xlsm 由来）レコードには「■ 新フォーマットの場合」節を、添付資料（`file_new` に `_Appendix`/`_Attachment`/`添付` を含む .docx 由来）レコードには「■ 旧フォーマットの場合」節を原文引用する。同一フォルダの新設仕様書でも本体と添付資料で適用節が異なる点に注意する。
- 全内容が「追加」であるため、`after_markdown`（章節/シートの表全体）の各行・各項目を対象に詳細項目照合を行う。

また `excluded` の扱いは以下による（付与忘れ防止のセーフティネット）。

- スクリプトが `excluded:true` を付けなかった（`excluded:false` で分割された）レコードはサブエージェントが再判定し、除外相当なら結果の `excluded=true` が `merge` で書き戻される。
- Step1でスクリプトが `excluded:true` を付与済みのレコードは `split` が事前除外し、`merge` で `checkno=[]` が維持される（サブエージェント起動対象外）。

### 旧フォーマット仕様書（.doc/.docx 由来md）の新設・ファイル追加

Step1で [oldformat_md_to_newspec_json.py](../scripts/oldformat_md_to_newspec_json.py) を用いた場合も、`checkno` 付与は上記のサブエージェント手順（split→サブエージェント→merge）で行う。

```text
python skills/speccheck-workflow/scripts/oldformat_md_to_newspec_json.py --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
```

- 適用する選定条件節は「■ 旧フォーマットの場合」で、各サブエージェントへ原文引用する。
- `excluded:true`／空章節は `merge` で `checkno=[]` となる。添付資料の有無・新設か否かのコンテキストも渡す（CHK-046-2判定用）。

## 選定条件・照合ルールの所在

- チェック項目選定条件：確定した側のファイル（`MET-G` 含む→metg／含まない→std）。
- 詳細項目レベルの照合ルール（【再発防止策1】詳細項目の1対1照合、【再発防止策2】通常差分での仕様行抽出）：[ラベリングサブエージェントプロンプトテンプレート](../templates/labeling_subagent_prompt.md)。

## 禁止事項

- 親エージェントがStep2でMCP（`graph_*` 等の外部ツール）を呼び出すこと。親の責務は `split`・`manifest.json` 参照・配布・`merge` に限定される（仕様書本文の参照はサブエージェントの責務。Step3準備等を名目としたカテゴリ一覧取得も含め不要かつ禁止）。
- 親エージェントが差分本文（`before_markdown`/`after_markdown`）を読んでラベリングすること。
- 旧フォーマットで章節階層マップ（末端段落名→親章節名）を渡さず、末端段落名と親章節条件（`*.イニシャル処理` 等）の突合をサブエージェントの推論のみに委ねること。
- `manifest.json` の対象レコードの一部でサブエージェント起動をスキップすること。
- 選定条件に無い独自の絞り込み（「軽微だから対象外」等の主観判断）を加えること、または技術的合理性・設計意図の推論で該当差分を対象外とすること。
- 詳細項目限定を持つCHK（CHK-060-3/066/089-1/089-2/111 等）を、シート・章節レベルの一致のみで該当判定し詳細項目照合を省くこと。変更行の「仕様」値と詳細項目を語の部分一致・類似で対応付けること（1対1の機械照合を要する）。
- `merge` の未処理index警告を無視して次Stepへ進むこと（該当サブエージェントの再実行と再マージを必須とする）。

## 自己チェック

- [ ] 親は差分本文を読まず、`split`・`manifest.json` のみで進めたか？
- [ ] 仕様書名の `MET-G` 判定で選定条件ファイルを正しく確定したか？
- [ ] `manifest.json` の全対象レコード（`split` が出力した全レコード）でサブエージェントを起動したか？
- [ ] 各サブエージェントに、担当レコード・選定条件（確定した側）・適用フォーマット節（原文引用）・共通reference（(B)引用＋(A)パス）・CHK-046-2用コンテキスト・結果出力先を渡したか？
- [ ] 旧フォーマットでは、`check_spec` の本体mdから章節階層マップ（末端段落名→親章節名）を作成し、全ラベリングサブエージェントへ渡したか？
- [ ] 各サブエージェントが `excluded`（変更履歴＝全共通／無効シート・章節＝新フォーマットのみ）を判定し、`excluded=true` は `checkno=[]` としたか？
- [ ] 詳細項目限定CHKで対象行の「仕様」値と詳細項目の1対1照合表を作成し、機械的に一致を確認したか？（語の部分一致で判定していないか）
- [ ] `merge` で `excluded`・`checkno` を書き戻し、未処理index警告が無いことを確認したか？（あれば再実行・再マージ）
- [ ] `checkno`・`excluded` 以外の項目を、Step1の内容を改変・要約せず保持したか？
