# Step1: チェック対象データの作成

## 目的

仕様書チェックの入力を作成する。本Stepは次の2つを用意する。

1. **変更後仕様書のマークダウン変換**: チェック対象仕様書（変更後仕様書）のローカル office ファイルを [spec2model-to-markdown](../../spec2model-to-markdown/SKILL.md) skill で Markdown 化し、`check_spec/<変更後仕様書名>/` 配下へ格納する（後続手順の入力や、Step3の参照先／影響確認先として辿るmdとなる）。詳細は「手順（変更後仕様書のマークダウン変換）」を参照。
2. **差分レコード列の作成**: 通常は差分データ(CSV)を成型して差分レコード列を作成する。差分データに現れないケースでは、チェック対象仕様書本体（`check_spec` 配下のmd）を入力として差分相当のレコードへ変換する。

差分データ(CSV)は [spec2model-cloud-diff](../../spec2model-cloud-diff/SKILL.md)（ローカル1件 + クラウド1件）または [spec2model-local-diff](../../spec2model-local-diff/SKILL.md)（ローカル2件）の出力CSVを用いる。両skillのCSVは同一形式のため同一に扱える。

**出力名・出力場所の固定（MUST）**: 両diffskillは出力先を引数（`--out-csv` / `--out-html`）で決めるため（spec2model 側では固定されていない）、speccheck-workflow から呼び出す際は、使用skillに関わらず**常に次の固定パスを `--out-csv` / `--out-html` で明示**して出力名・場所を安定させる（spec2model 側のSKILLは変更しない）。

| 種別 | 固定パス |
|---|---|
| 差分CSV | `.claude/specification_check/output/spec_diff.csv` |
| 差分HTML | `.claude/specification_check/output/spec_diff.html` |

- この固定名・場所は使用skill（cloud-diff / local-diff）に依存しない。1回のチェックで生成する差分CSVは常に `specification_check/output/spec_diff.csv` とする。
- 単一固定名のため、複数の変更後仕様書を同時にチェックする場合は差分skillを仕様書ごとに逐次実行し、都度 `spec_diff.csv` を「手順（通常: 差分データ）」でJSON化してから次の仕様書へ進む（前の `spec_diff.csv` は上書きされる前提）。

入力の与えられ方は次の2通り。いずれも最終的に差分CSVを `csv_to_diff_json.py` でJSON化して後続へ渡す。

- **差分CSVが既にある場合**: `specification_check/output/` 配下の差分CSV（`spec_diff.csv`）をそのまま「手順（通常: 差分データ）」で取り込む。
- **変更前・変更後の仕様書ファイルが与えられた場合**: 先に「手順（差分CSVの用意）」で差分skillを実行して差分CSVを生成してから、「手順（通常: 差分データ）」へ進む。

## 入力の選択（通常 / 新設・ファイル追加）

チェック対象に応じて入力を切り替える。

| ケース | 条件 | 入力 | 変換手順 |
|---|---|---|---|
| 通常 | 変更前仕様書があり、変更が差分データに現れる | 差分データ(CSV)。`.claude/specification_check/output/spec_diff.csv`（spec2model-cloud-diff / spec2model-local-diff の出力を固定パスへ出力） | 「手順（通常: 差分データ）」 |
| ①新設仕様書 | 変更前仕様書が無し（新設） | `.claude/specification_check/check_spec/<仕様書名>/` 配下のmd | 「手順（新設・ファイル追加）」 |
| ②ファイル追加 | 変更後仕様書に変更前に無いファイルが追加され、当該ファイルが差分データに現れない | 追加ファイルは `check_spec/<仕様書名>/` 配下のmd（差分データに現れる既存ファイルは通常手順を併用） | 「手順（新設・ファイル追加）」 |

- ②では、差分データに現れる既存ファイルは通常手順でJSON化し、差分データに現れない追加ファイルは新設・ファイル追加手順でJSON化して、両者のレコードを結合し後続Stepへ渡す。
- 変換後の各レコードのスキーマは通常／新設で共通（新設は `before_markdown=""`, `source="new_spec"`, `item` を追加）。
- 入力に関わらず、`check_spec/<変更後仕様書名>/` 配下のmdは「手順（変更後仕様書のマークダウン変換）」で用意する（変更後仕様書のみを変換。差分CSVの用意手順には影響しない）。

## 入力

- 次のいずれか。
  - 差分データ(CSV形式)。`.claude/specification_check/output/spec_diff.csv`（spec2model-cloud-diff / spec2model-local-diff の出力を固定パスへ出力）に格納される。
  - 変更前・変更後の仕様書ファイル（差分skillでCSVを生成する場合）。

## 手順（変更後仕様書のマークダウン変換）

チェック対象仕様書（**変更後仕様書のみ**）のローカル office ファイルを [spec2model-to-markdown](../../spec2model-to-markdown/SKILL.md) skill で Markdown に変換し、`specification_check/check_spec/<変更後仕様書名>/` 配下へ格納する。ここで生成したmdが、「手順（新設・ファイル追加）」の入力や、Step3で参照先／影響確認先として辿る `check_spec/<変更後仕様書名>/` 配下のmdとなる。

**対象・格納先（MUST）**:

- 変換対象は **変更後仕様書のみ**。変更前仕様書（クラウド文書(KGA)／ローカルの旧ファイル）は本手順では変換しない。
- 変換元は `specification_check/check_spec/<変更後仕様書名>/` フォルダ内に格納された対応 office ファイル（`.xlsx`/`.xlsm`/`.xls`/`.docx`/`.doc`/`.pptx`）。**当該フォルダ内の対応 office ファイルはすべて変換する**（DMS等も含め、md変換段階では除外しない。下流での除外は Step1 のJSON化手順が担う）。
- 出力先は変換元と同じ `specification_check/check_spec/<変更後仕様書名>/` に固定する（`--output-dir` で明示。画像は同フォルダ配下の `images/` に出力される）。skillの標準手順に従い、出力先だけ `--output-dir "specification_check/check_spec/<変更後仕様書名>"` を必ず明示して出力名・場所を安定させる（MUST）。

**実行**:

- 変換は spec2model-to-markdown skill に委譲する。同skillは spec2model 解析を伴うため venv python（`tools/spec2model/.venv/Scripts/python.exe`、**フォワードスラッシュ表記**）を用いる（[SKILL.md](../SKILL.md) の「実行環境の注意」参照）。対象フォルダ単位で一括変換し、フォルダ内の対応 office ファイルを漏れなく変換する。

  ```text
  tools/spec2model/.venv/Scripts/python.exe skills/spec2model-to-markdown/scripts/export_to_markdown.py "specification_check/check_spec/<変更後仕様書名>" --output-dir "specification_check/check_spec/<変更後仕様書名>"
  ```

  - サブフォルダにも対応 office ファイルがある場合は `--recursive` を付与し、フォルダ配下の対応 office ファイルをすべて変換する。

**差分CSVの用意への非干渉（MUST）**:

- 本手順は 変更後仕様書 のmd化のみを行い、次節「手順（差分CSVの用意）」の入力・出力・コマンドを一切変更しない。差分skill（cloud-diff / local-diff）へ渡す「新（変更後）」側入力は従来どおりローカルの office ファイルとし、本手順で生成したmdは差分生成には使用しない。

## 手順（差分CSVの用意）

変更前・変更後の仕様書ファイルが与えられ、差分CSVがまだ無い場合に実施する。差分skillを実行して差分CSVを固定パス `specification_check/output/spec_diff.csv` へ生成する。**差分CSVが既に用意されている場合は本手順を省略**し、「手順（通常: 差分データ）」へ進む。

### 1. 差分skillの選択（変更前がクラウドにあるかで判定）

前提として、**変更後仕様書はローカルファイルで、`specification_check/check_spec/<変更後仕様書名>/` 配下に格納される**（これを差分skillの「新（変更後）」側入力に用いる）。**変更前仕様書は通常クラウド文書（KGA）**である。

変更前仕様書がクラウド文書として存在するかどうかで、使用する差分skillを切り替える。

| 変更前仕様書 | 使用skill | 差分の組み合わせ |
|---|---|---|
| クラウド文書（KGA）に存在する（既定） | [spec2model-cloud-diff](../../spec2model-cloud-diff/SKILL.md) | 変更前=クラウド, 変更後=ローカル（`check_spec/<変更後仕様書名>/`） |
| クラウド文書に存在しない | [spec2model-local-diff](../../spec2model-local-diff/SKILL.md) | 変更前=ローカル, 変更後=ローカル |

- 既定は spec2model-cloud-diff。変更前仕様書がクラウドに無い場合に限り spec2model-local-diff を用いる（この場合は変更前もローカルファイルとして用意する）。

### 2. 差分CSVの生成

選択した差分skillの手順に従い、変更前を旧・変更後を新として差分を実行し、差分CSVを固定パスへ出力する。**使用skill（cloud-diff / local-diff）に関わらず、`--out-csv` / `--out-html` に次の固定パスを必ず明示する（MUST）**：`--out-csv "specification_check/output/spec_diff.csv"`、`--out-html "specification_check/output/spec_diff.html"`。変更後（新）側の入力は `specification_check/check_spec/<変更後仕様書名>/` 配下のローカルファイルとする。生成後、その `spec_diff.csv` を「手順（通常: 差分データ）」の入力とする。

- 上記は**変更前・変更後がそれぞれ単一ファイル**（本体のみ）の場合。1つの仕様書が複数ファイル（本体＋1つ以上の添付資料 等）で構成される場合は、次節「### 3. 変更前後が複数ファイル構成の場合」に従う。

### 3. 変更前後が複数ファイル構成の場合（ペアごとにdiff → JSON化時に統合）

1つの仕様書が**本体＋1つ以上の添付資料**の複数ファイルで構成されることがある。**本体・添付資料のフォーマット（拡張子）は限定しない**（本体が旧フォーマット .doc/.docx／新フォーマット .xlsm、添付資料が .xlsx/.docx/.pdf 等、いずれの組み合わせもあり得る）。

差分skill（cloud-diff / local-diff）が呼ぶ `diff_documents.py`（`parse_document`）は**単一ファイル対単一ファイル**の比較のみ対応し、拡張子で `.xlsx/.xlsm/.xls`・`.docx/.doc`・`.pptx`・`.pdf` を自動判定する（ディレクトリ入力や複数ファイルの一括束ねは不可）。このため、**変更前後で同一ドキュメント（同一の役割・対応関係）に当たるファイルどうしをペアにして差分skillを個別に複数回実行**し、ペアごとの差分CSVを固定名で出力する。CSV自体は結合せず、**JSON化（「手順（通常: 差分データ）」の `csv_to_diff_json.py`）でレコードを統合**する（CSVレベルで結合しない理由：差分CSVの本文セル `before_markdown`/`after_markdown` には改行が埋め込まれるため、物理行の単純連結はレコードを壊す。JSON配列の連結は安全）。

**ファイルのペアリングと対象/除外（MUST）**:

- 変更前フォルダと変更後フォルダの中身を突き合わせ、**変更前後で同一ドキュメントに対応するファイルどうしをペア**にする（本体は本体と、各添付資料は対応する添付資料と）。拡張子はペアの両側で一致するのが通常だが、フォーマット種別（新／旧）は問わない。
- **DMSファイル（通信仕様書。ファイル名に "DMS" トークンを含む）はdiff対象から除外する**（既存の変換・チェック除外ルールと整合。片側フォルダにしか無い場合も除外）。
- 添付資料は0個・1個・複数個（2〜3個等）いずれもあり得る。存在するペアすべてを対象とする。
- 片側にしか存在しないファイル（DMS以外で新規追加・削除されたファイル）は差分では扱えないため、「手順（新設・ファイル追加）」側で扱う。

**ペアごとの固定出力名（MUST）**: ペアの差分CSV／HTMLは、後段のグロブ取り込みが一意になるよう次の固定名で `specification_check/output/` へ出力する（`--out-csv` / `--out-html` に明示）。**本体・添付資料の拡張子に関わらず本固定名を用いる**（出力名は入力の拡張子に依存させない）。

| ペア種別 | 差分CSV（固定名） | 差分HTML（固定名） |
|---|---|---|
| 本体（フォーマット・拡張子問わず） | `spec_diff_body.csv` | `spec_diff_body.html` |
| 添付資料（1個目） | `spec_diff_appendix_1.csv` | `spec_diff_appendix_1.html` |
| 添付資料（n個目） | `spec_diff_appendix_<n>.csv` | `spec_diff_appendix_<n>.html` |

- 添付資料が1個でも `_1` を付す（`spec_diff_appendix_1.csv`）。番号 `<n>` は 1,2,3… と採番する（添付資料の個数分）。
- 複数ファイル構成では、単一ファイル構成用の `spec_diff.csv`（無印）は使用しない（`spec_diff.json` へはJSON化時に統合するため。「手順（通常: 差分データ）」参照）。
- **差分0件のペアはCSVが生成されない**点に注意（`diff_documents.py` は差分0件のとき CSV を出力せず early return する）。未生成のCSVは後段のグロブ取り込みで自動的にスキップされる（存在しないパターンは警告のうえスキップ）。

## 手順（通常: 差分データ）

実行はプロジェクトの `.claude` を起点とする（`cd` 不要。スクリプトパス・入出力パスはすべて `.claude` からの相対で指定。実行環境の共通ルールは [SKILL.md](../SKILL.md) の「実行環境の注意」を参照）。以降のコマンドも同様。

### 1. 差分CSVの取り込み・JSON変換

`specification_check/output/` 配下の差分CSV（固定名 `spec_diff.csv`）を、同梱スクリプト [scripts/csv_to_diff_json.py](../scripts/csv_to_diff_json.py) で後続手順の入力JSONへ変換する。

- 事前準備: 追加の依存パッケージは不要（標準ライブラリのみで動作）。対象CSVのパスを確認する。
- 実行（単一ファイル構成）:

  ```text
  python skills/speccheck-workflow/scripts/csv_to_diff_json.py --in "specification_check/output/spec_diff.csv" --out "specification_check/output/spec_diff.json"
  ```

  - **複数ファイル構成の場合（「手順（差分CSVの用意）」の「### 3.」でペアごとに差分CSVを出力したとき）**: `--in` を複数回指定してペア別CSVを1つの `spec_diff.json` へ統合する。`--in` の各値は**グロブパターン**として展開されるため、添付資料が複数でも `spec_diff_appendix_*.csv` の1パターンでまとめて取り込める。CSV自体は結合せず、本スクリプトがJSONレコードを連結する。差分0件でCSV未生成のペア（グロブ0件一致）は警告のうえ自動スキップされる。

    ```text
    python skills/speccheck-workflow/scripts/csv_to_diff_json.py --in "specification_check/output/spec_diff_body.csv" --in "specification_check/output/spec_diff_appendix_*.csv" --out "specification_check/output/spec_diff.json"
    ```

  - 出力先は `specification_check/output/` とする。
  - 入力CSVは spec2model diff の共通スキーマ（列名で対応付け。順不同・欠落は空文字扱い）。主な列：

    `file_old`, `file_new`, `sheet_name`, `chapter_key`, `chapter_title_old`, `chapter_title_new`, `paragraph_key`, `paragraph_title_old`, `paragraph_title_new`, `before_markdown`, `after_markdown` ほか

  - スクリプトは各行を8キーへ対応付ける：

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

  - CSVの1行=変更ブロック単位（TextBlock/TableRow）の差分。行の抽出・破棄・要約・改変は行わない。出力された各JSONを後続手順の入力とする。
  - **末端段落ノード単位のTextBlock統合（既定ON）**: spec2model diff は TextBlock（段落）単位で差分を出すため、1つの末端段落に対する1回の編集（例: プレースホルダ `T.B.D` → 複数行の記載）が「削除1＋追加N」等の複数レコードに過分割されることがある。`csv_to_diff_json.py` は既定で、`block_type=="text"` の行のうち同一末端段落ノード（`(file_old, file_new, sheet_name, chapter_key, order_path親)` が一致）を1レコードへ統合する（`before`/`after` を `order_path`/`block_order` 順に**原文のまま改行連結**。要約・改変・並べ替えはしない）。
    - 統合キーに `order_path` 親（末端段落ノード）を用いるため、同名末端段落が親章節配下に複数存在しても（例: メータ演算タイプ／EFI演算タイプの各「(3)リセット処理」）、実際に変更のあった出現のみが統合され、他出現（別ノード）や独立した変更は**巻き込まず分割保持**される。`block_type!="text"`（TableRow 等）や `order_path` に親が無い行は統合対象外（各1レコード）。
    - この統合は**末端段落ノード単位＝変更単位**であり、下記禁止事項の「章節単位への集約」には当たらない（許容）。統合を無効化して1行=1レコードに戻す場合のみ `--no-coalesce` を付与する。

### 2. 無効差分の除外（Step2 ラベリングサブエージェントへ委譲）

通常差分フローでは、無効差分の除外判定（`excluded` の付与）は**全フォーマットで Step2 のラベリングサブエージェントが担う**（判定基準は [step2_labeling.md](step2_labeling.md) および [ラベリングサブエージェントプロンプトテンプレート](../templates/labeling_subagent_prompt.md) の「除外フラグ（excluded）の判定」節を参照）。
Step1の親エージェントは差分本文を読み込まないため、`excluded` を付与せず（＝JSONに `excluded` が無い状態で）後続Stepへ渡す。`excluded` の確定はStep2の `merge` で行われる。

## 手順（新設・ファイル追加）

変更前仕様書が無い新設仕様書（ケース①）、または変更後に追加され差分データに現れないファイル（ケース②）は、差分が存在しないため、`.claude/specification_check/check_spec/<仕様書名>/` 配下の変換済みmd（仕様書本体／添付資料）を入力とし、全内容を「追加（変更前なし）」の差分相当レコードへ変換する。

### 仕様書フォーマットによるスクリプト選択（必須）

変換スクリプトは仕様書フォーマットで使い分ける（フォーマットは [meter-spec-common](../../meter-spec-common/SKILL.md) の判断フローで特定。**ファイル単位**で判定する）。Step2の `checkno` 付与は、いずれのフォーマットもサブエージェントで行う（[step2_labeling.md](step2_labeling.md)）。

- **新フォーマット仕様書（.xlsm 由来md）**: [scripts/newformat_md_to_newspec_json.py](../scripts/newformat_md_to_newspec_json.py)。以下「0.〜4.」の手順に従う。
- **旧フォーマット仕様書（.doc/.docx 由来md）**: [scripts/oldformat_md_to_newspec_json.py](../scripts/oldformat_md_to_newspec_json.py)。旧フォーマットmdは `# 目次`・`## 章節`・`### 段落` のみでシート見出し(`# <シート>`)を持たず、新フォーマット用スクリプトでは表が捕捉されないため、旧フォーマット専用スクリプトでStep1（章節単位レコード化）を実行する。仕様書ごとに作り分ける必要はなく `--spec-dir` を渡す。

  ```text
  python skills/speccheck-workflow/scripts/oldformat_md_to_newspec_json.py --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
  ```

  - 章節（`##`）単位でレコード化し（`### 段落` は章節本文に含める）、変更履歴章節は `excluded:true`、DMSファイルは除外する。本スクリプトは `checkno` を付与しない（機械判定を行わない）。
  - Step2で適用する選定条件節は「■ 旧フォーマットの場合」。

### 本体と添付資料が混在する場合のフォーマット別ルーティング（必須）

1つの仕様書フォルダ（`check_spec/<仕様書名>/`）内に、本体（新フォーマット .xlsm 由来md）と**添付資料**（`_Appendix`/`_Attachment`/`添付` トークンを含むファイル。新旧スクリプトの `ATTACH` 正規表現で共通判定）が混在することがある。この場合、**本体は新フォーマット、添付資料は旧フォーマット**として別々に変換し、同一JSONへ結合する。

1. 本体を新フォーマットで変換（`newformat_md_to_newspec_json.py` は DMS と添付資料を自動スキップし、本体のみをレコード化する）。

   ```text
   python skills/speccheck-workflow/scripts/newformat_md_to_newspec_json.py --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
   ```

2. 添付資料を旧フォーマットで変換し、1.のJSONへ追記結合する（`--attachment-only` で添付資料のみ、`--append` で既存JSON末尾へ追記）。

   ```text
   python skills/speccheck-workflow/scripts/oldformat_md_to_newspec_json.py --attachment-only --append --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
   ```

- 添付資料mdが `## 章節` を持たず `# シート見出し`＋表のみの場合、`oldformat_md_to_newspec_json.py` は `#` 見出し（目次を除く）を章節とみなして1レコード化する。結合後の添付資料レコードは `sheet_new=""`・`chapter_new=<# 見出し>`・`source="new_spec"` を持つ。
- 結合後の `<仕様書名>_newspec.json` を、そのままStep2（`mark_invalid_items.py` → `split` → サブエージェント → `merge`）の入力とする。`split`/`merge` は配列の位置indexで動作するため、本体レコードの後に添付資料レコードが結合されていても整合する。
- Step2で各レコードへ適用する選定条件節は**レコードのフォーマット別**とする（本体レコード＝「■ 新フォーマットの場合」、添付資料レコード＝「■ 旧フォーマットの場合」。判別はレコードの `file_new` の添付資料トークンの有無で行う）。

### 0. 変換対象ファイルの限定（DMSファイルの除外）

- DMSファイル（通信仕様書）は差分相当レコードへの変換対象から**除外する**。
- 識別: ファイル名に "DMS" トークンを含むもの（例: `*_DMS_*`, `*(DMS(In))*`, `*(DMS(Out))*`）。
- 変換スクリプト（`newformat_md_to_newspec_json.py`／旧は `oldformat_md_to_newspec_json.py`）は `--spec-dir` 配下のmdのうちDMSファイルを自動でスキップする（スキップ対象はログ出力）。

### 1. md → レコードJSONへの変換

`newformat_md_to_newspec_json.py`（旧フォーマットは `oldformat_md_to_newspec_json.py`）を、対象仕様書フォルダ単位で1回実行する。

```text
python skills/speccheck-workflow/scripts/newformat_md_to_newspec_json.py --spec-dir "specification_check/check_spec/<仕様書名>" --out "specification_check/output/<仕様書名>_newspec.json"
```

- `--spec-dir` 配下の全md（DMSファイルを除く）を取り込む（仕様書本体・添付資料を含む）。
- 各レコードは通常差分JSONと互換のキー（`file_old`/`sheet_old`/`chapter_old`/`file_new`/`sheet_new`/`chapter_new`/`before_markdown`/`after_markdown`）に加え、`item`（章節内の項目名）, `source`（"new_spec"）, `excluded` を持つ。
- 新設・追加では変更前が存在しないため `before_markdown=""`、`after_markdown=` 当該箇所の原文 とする。原文は要約・改変しない。

### 2. 分解粒度（シート×章節）

- 1レコード = （シート × 章節(段落)）とする。`after_markdown` は当該章節の表（複数表がある場合は連結）を原文のまま保持する。`item` は互換用に `"(章節全体)"` 固定。
- 章節見出しを持たないシート（添付資料 English translations 等）は、シート全体を1レコードとする。
- 項目(列)単位の無効情報（"Ver"・各種"数"・参考列・R/R・"特別処理が必要な理由" 等）は、章節レコード内では原文として保持されるが、Step2のチェック項目選定時に当該列を選定対象から除外する（[scripts/mark_invalid_items.py](../scripts/mark_invalid_items.py) が `guide-newformat-invalid.md` 由来の定義で `invalid_items` を付与し、サブエージェントが当該列を除外）。
- **空章節のドロップ**（レコード化しない＝Step2ラベリング／Step3チェック対象外。ただし `excluded:true` とは別）: 識別子列（要求ID/Ver/No）以外に非空セルが無い章節はレコード化しない。
  - **Detailed Spec系（Detailed Spec/Detailed Spec2/Detailed Spec3）は、content 判定を作成者記載欄「特別処理」列で行う**（[guide-newformat-item.md](../../meter-spec-common/reference/guide-newformat-item.md) で 仕様/標準処理 は「フォーマット定義項目＝作成者が記載する箇所ではない」ため）。「特別処理」列が全行空（"-" 含む）の章節は「作成者記載なし」としてドロップする。
  - これは `excluded:true`（無効情報＝要求無し等。参照先でも不在扱い）**とは別**の扱いである。ドロップした章節は newspec.json に現れずラベリング・チェック対象にならないが、`excluded:true` ではないため、Step3で参照先/影響確認先として `check_spec` の md を辿った場合は**有効な内容**（標準処理は特別処理が無ければ仕様として適用）として扱う（不在＝無効にはしない）。

### 3. 無効差分の除外（新設・ファイル追加：スクリプトの機械付与＋Step2サブエージェントの再判定）

新設・ファイル追加フローでは、まず変換スクリプトが除外フラグを機械付与する。スクリプトは [guide-newformat-invalid.md](../../meter-spec-common/reference/guide-newformat-invalid.md) と `変更履歴情報の扱いルール` に基づき、無効シート（MSG/Variable_MSG/SW_MSG/Revision history）・無効章節（1.システム内容説明 等）・無効項目（"Ver"・各種"数"・参考列・R/R 等）・"特別処理が必要な理由" 列に `excluded:true` を付与する。それ以外は `excluded:false` とする。

- **「要求無し」宣言セクションの除外**: スクリプトは [guide-newformat-item.md](../../meter-spec-common/reference/guide-newformat-item.md) の項目「要求無し***/ ■要求有り***」の行に従い、「要求無し」宣言セクション配下のレコードへ `excluded:true` を付与する（TT＝警告灯ブロック単位／他シート＝シート全体。区別の詳細は当該行およびスクリプト実装が正）。加えて、[guide-newformat-sheetsection.md](../../meter-spec-common/reference/guide-newformat-sheetsection.md) の 機能ブロック↔特別処理指示 の対応に従い、要求無しの機能ブロックに対応する**特別処理指示シートの章節も波及して除外**する（Detailed Spec `8-<X>`←TT `2-<X>`／`9`←BZR／`10`←MID、Detailed Spec2 `11-*`←Variable_MID、Detailed Spec3 `12-*`←SW。要求有りブロックに対応する章節は残す）。
- **付与忘れ防止のセーフティネット（Step2で再判定）**: スクリプトが `excluded:true` を付けなかった `excluded:false` レコードは、Step2の `split` でラベリング対象として分割され、サブエージェントが [ラベリングサブエージェントプロンプトテンプレート](../templates/labeling_subagent_prompt.md) の「除外フラグ（excluded）の判定」節に従い `excluded` を再判定する。除外相当と判定した場合は結果の `excluded=true` がStep2の `merge` で書き戻される（`excluded:true` を付与済みのレコードは `split` が事前除外するためサブエージェント起動対象外）。

### 4. ②（ファイル追加）で既存ファイルの差分も併存する場合

既存ファイルは「手順（通常: 差分データ）」でJSON化し、追加ファイル（DMSファイルを除く）は本手順でJSON化したうえで、両JSONのレコードを結合して後続Step（Step2以降）の入力とする。

## 禁止事項

- 無効差分の除外は、無効箇所として明記された箇所のみとし、それ以外の差分を除外すること。
- CSVから取り込んだ各列の値を、要約・集約・言い換え・意訳して保持すること。
- 複数の独立した変更を「同種」「同趣旨」「軽微」等の理由で1件に統合すること。
- 章節単位の差分内に含まれる複数の変更箇所を、章節単位の1件に集約すること（変更単位での分割保持を強制）。
  - ただし `csv_to_diff_json.py` の**末端段落ノード単位のTextBlock統合（既定ON）**は、1つの末端段落に対する1回の編集が複数ブロックに過分割されたものを`order_path`親（末端段落ノード）で束ね直す**変更単位の統合**であり、本禁止事項の「章節単位への集約」には**該当しない**（別ノード・独立変更は巻き込まない）。
- 原文中の表データを、列省略・行統合・セル文言短縮などで改変すること。

## 自己チェック

- [ ] 変更後仕様書（のみ）を spec2model-to-markdown で `check_spec/<変更後仕様書名>/` 配下へmd変換したか？（`--output-dir` に当該フォルダを固定し、フォルダ内の対応 office ファイルをすべて変換したか。変更前仕様書は変換していないか。差分CSVの用意手順は変更していないか）
- [ ] 差分CSVを固定パス `specification_check/output/spec_diff.csv` に出力し、そのJSON変換（`spec_diff.json`）を実行したか？（複数ファイル構成の場合は、ペアごとに `spec_diff_body.csv`／`spec_diff_appendix_<n>.csv` を出力し、DMSを除外し、`csv_to_diff_json.py` の `--in` 複数指定で1つの `spec_diff.json` へ統合したか）
- [ ] 8キーすべてを保持してJSON化したか？
- [ ] 差分の原文を改変・要約せずに保持しているか？
- [ ] 通常差分フローでは Step1で `excluded` を付与せず（＝除外判定はStep2ラベリングサブエージェントへ委譲）、後続Stepへ渡したか？
- [ ] 新設・ファイル追加フローでは、変換スクリプトが明確な無効シート・章節（新フォーマット無効情報／変更履歴）に `excluded:true` を機械付与したか？（スクリプトが付けなかった `excluded:false` レコードは、Step2でサブエージェントが再判定・書き戻す＝セーフティネットが働くことを前提とする）
