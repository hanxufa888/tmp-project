---
name: spec2model-cloud-diff
description: "「whenを使用：この skill は 1 つのローカル Office/PDF ドキュメントと 1 つのクラウド文書（KGA）との比較専用です。ローカルパスまたは添付ファイルがあるものだけをローカル文書として扱い、それ以外、つまりファイル名だけが与えられたものは常にクラウド文書として扱います。2 つのクラウド文書を比較する場合は、この skill ではなく graph_diff_documents MCP ツールを直接使用してください。たとえば、MET-C_HCS-CSTD-A0-03-A-C0.xlsm と MET-C_HCS-CSTD-A0-04-A-C0.xlsm がファイル名だけで与えられた場合は、クラウド文書同士として扱います」"
---

## 用途

この skill は次の比較のみに使用します：

- 片側がローカル Office/PDF ファイル
- もう片側がクラウドからエクスポートされた `spec2model Document JSON`

この skill が扱う入力の組み合わせは、常に「ローカル文書 1 件 + クラウド文書 1 件」です。

ローカルファイル同士の差分比較は対象外です。
ファイル名だけが提示された入力は、常にクラウド文書として扱います。
そのため、ファイル名だけの 2 文書比較はこの skill の対象外で、`graph_diff_documents` を使います。

標準出力は CSV とする。必要な場合に限り HTML を生成してもよい（MAY）。ユーザーから明示的な要求がない限り、大量の差分内容を会話に貼り付けてはならない（MUST NOT）。

背景情報：KGA はクラウド側の名称です（以下で「クラウド」と「KGA」は同一の意味で扱います）。
ユーザーの質問文で KGA と記載された場合も、常にクラウドを指すものとして解釈します。KGA の文書は統一してクラウド文書として扱います。
添付ファイルやローカルファイルパスが提示されず、ファイル名のみが提示された場合は、統一してクラウド文書として扱います。
例：`MET-C_HCS-CSTD-A0-03-A-C0.xlsm` と `MET-C_HCS-CSTD-A0-04-A-C0.xlsm` だけが与えられた場合は、ローカル vs クラウドではなく、クラウド vs クラウドです。

## 制約条件

- クラウド文書は、`graph_export_document_json` を使用して `spec2model Document JSON` としてエクスポートしなければならない（MUST）。
- ローカル文書の解析には、現在の workspace の `tools/spec2model` のみを使用しなければならない（MUST）。
- 差分は、ローカルで `compare_documents()` により実行しなければならない（MUST）。
- 比較の直前に必ず `graph_export_document_json` を実行し、その応答でローカルのクラウド `*.document.json` を更新しなければならない（MUST）。前回比較のキャッシュを再利用してはならない（MUST NOT）。
- 既存の差分結果（CSV/HTML）を入力またはキャッシュとして再利用してはならない（MUST NOT）。実行ごとに差分を再計算しなければならない（MUST）。
- クラウド `Document JSON` の代わりに、全文、Markdown、検索スニペットまたは要約を使用してはならない（MUST NOT）。
- `graph_collect_full_texts` をローカルとクラウドの差分に使用してはならない（MUST NOT）。
- `graph_diff_documents` をローカルファイルとクラウドファイルの差分に使用してはならない（MUST NOT）。同ツールはクラウド内の 2 文書比較専用である。
- 画像差分では、クラウド `Document JSON` の `kind: "image"` ノードに `data_b64`、`section`、`row`、`col`、`name`、`ext` を含めなければならない（MUST）。`data_b64` がない場合は画像内容の比較は完了できない。

標準フロー：

```text
MCP graph_export_document_json(file_name)
	-> document_json / json_text を返却（file_name / download_name / format を含む）
	-> JSON をローカル data/cloud/*.document.json に保存
	-> ローカルを tools/spec2model で解析
	-> cloud-diff スクリプト内で cloud_json を Document に復元
	-> compare_documents()
	-> CSV/HTML を出力
```

## 環境前提

リポジトリルートは現在の workspace ルートです。

ローカル環境は固定：

```text
tools/spec2model/.venv
```

解析と差分の実行には、次の環境の Python を使用しなければならない（MUST）。OS により venv 内の Python 実行ファイルのパスが異なる。

- Windows（PowerShell / cmd）：`tools\spec2model\.venv\Scripts\python.exe`
- Unix / macOS（bash）：`tools/spec2model/.venv/bin/python`

以降の手順では、この Python 実行ファイルを `<venv-python>` と表記する。実際のコマンド実行時は、使用中の OS に応じて上記いずれかのパスへ置き換えること。

外部環境（system Python / 別 venv / conda / pyenv 等）を使用してはならない（MUST NOT）。

初回利用時の環境チェック：

Windows（PowerShell）：

```powershell
if (Test-Path tools\spec2model\.venv\Scripts\python.exe) {
	"[OK] tools/spec2model/.venv is ready"
} else {
	"[MISSING] tools/spec2model/.venv"
}
```

Unix / macOS（bash）：

```bash
cd <workspace-root>
if [ -x tools/spec2model/.venv/bin/python ]; then
	echo "[OK] tools/spec2model/.venv is ready"
else
	echo "[MISSING] tools/spec2model/.venv"
fi
```

ローカル解析対応形式：

```text
.xlsx .xlsm .xls .docx .pptx .pdf
```

`.md` は入力文書としてサポートしません。

環境がない場合は、次の場所にのみインストールしなければならない（MUST）。

現在の `spec2model` ソースは `parsers/__init__.py` から全 parser を eager import し、`utils/__init__.py` から `parse_images.py` も eager import する。`parse_images.py` はモジュールのトップレベルで `lxml`、Pillow、`cairosvg` を import するため、README にある extras `images` の設計上は opt-in でも、現行ソースを変更しない限りこれらを後から遅延導入できない。

したがって、ユーザー要求どおり `spec2model` コードを変更しない前提では、Python の import-time 依存（Pillow、`lxml`、`cairosvg` とその依存）は基礎環境の作成時に導入する。画像機能の実行時だけ追加できるのは、EMF/WMF の実ラスタライズに使うシステムの LibreOffice / Poppler である。`requirements.txt` は画像依存と未使用 parser 依存をまとめて含むため、そのまま使わず、下記の明示的な最小実行時依存を導入する。

Windows（PowerShell）— 基礎（テキスト・表差分のみ）：

```powershell
Set-Location <workspace-root>\tools\spec2model
# python が Microsoft Store のエイリアスの場合は py ランチャーを使う
py -m venv .venv
# spec2model の eager import に必要な実行時依存。画像用の lxml / Pillow / cairosvg もここで必要になる。
.venv\Scripts\python.exe -m pip install pyyaml pandas numpy openpyxl xlrd python-docx tabulate pillow lxml cairosvg pdf2image python-pptx markdown python-dotenv azure-ai-documentintelligence beautifulsoup4 html5lib
# spec2model 本体（src レイアウト）を editable で登録する。
# 依存は上で導入済みのため --no-deps を付ける（MUST）。
# これを忘れると ModuleNotFoundError: No module named 'spec2model' になる。
.venv\Scripts\python.exe -m pip install -e . --no-deps
```

Unix / macOS（bash）— 基礎（テキスト・表差分のみ）：

```bash
cd <workspace-root>/tools/spec2model
python3 -m venv .venv
.venv/bin/python -m pip install pyyaml pandas numpy openpyxl xlrd python-docx tabulate pillow lxml cairosvg pdf2image python-pptx markdown python-dotenv azure-ai-documentintelligence beautifulsoup4 html5lib
.venv/bin/python -m pip install -e . --no-deps
```

基礎インストール後は、Windows では先に「Cairo ネイティブ DLL」の手順を完了してから、次で import できることを確認する（`<venv-python>` は OS 対応のパスへ置換）。

```text
<venv-python> -c "from spec2model import parse_document, compare_documents; from spec2model.exporters import render_diff_html; print('spec2model base ok')"
```

## 画像差分の追加インストール

画像差分（`--out-image-json` を伴う比較）を実行する場合は、原則としてシステムの LibreOffice / Poppler を追加で導入する（SHOULD）。テキスト・表差分だけの依頼ではこの追加導入を省略してよい（SHOULD）。Python の `lxml` / Pillow / `cairosvg` と Cairo は、現行ソースの eager import のため基礎環境に含める。

README の extras `images` は本来 opt-in だが、現行ソースを変更しない制約下では import-time 依存を後段へ移せない。`spec2model` コードを変更せずに依存を遅延する手順は提供しない。

**LibreOffice（+ Poppler）**は Excel/Word 内の **EMF/WMF ベクター画像**を PNG 化するため、および PowerPoint のスライド全体画像化のために必要。未導入だと EMF/WMF はプレースホルダー画像へフォールバックし、ローカル vs クラウドの画像差分が実際より大きく出る（詳細は「失敗時対応」参照）。

### システム要件: LibreOffice / Poppler（画像差分で必須）

`spec2model.utils.parse_images` は、Pillow で開けない EMF/WMF 画像を `libreoffice` / `soffice --headless --convert-to png` で PNG 化する。パスに `libreoffice`（または `soffice`）が無いと、その画像はプレースホルダー PNG になる。`.xlsx` / `.docx` に EMF/WMF が含まれる場合、これがローカル vs クラウド画像差分の乖離の主因となる。

- **Windows**:
  ```powershell
  winget install --id TheDocumentFoundation.LibreOffice -e --accept-package-agreements --accept-source-agreements
  ```
	この MSI のシステムインストールは通常、管理者権限が必要である。管理者権限がない場合は winget を繰り返さず、組織で許可された LibreOffice Portable を `%LOCALAPPDATA%` などの書き込み可能なユーザーディレクトリへ展開する。展開後は次で `soffice.com` のあるディレクトリを現在の PowerShell セッションだけ PATH に追加する。
	```powershell
	$portableRoot = Join-Path $env:LOCALAPPDATA "LibreOfficePortable"
	$soffice = Get-ChildItem $portableRoot -Recurse -Filter "soffice.com" -File | Select-Object -First 1
	if (-not $soffice) { throw "soffice.com was not found under $portableRoot" }
	$env:PATH = $soffice.DirectoryName + ";" + $env:PATH
	& $soffice.FullName --version
	```
	Poppler が必要な場合は [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) の `bin` もユーザーディレクトリへ展開し、同じ PowerShell セッションの PATH に追加する。
- **Ubuntu / Debian**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y libreoffice poppler-utils
  ```
- **macOS (Homebrew)**:
  ```bash
  brew install --cask libreoffice
  brew install poppler
  ```

導入確認（いずれかが検出されれば EMF/WMF は実ラスタライズされる）：

Windows（PowerShell）：

```powershell
Get-Command soffice, libreoffice -ErrorAction SilentlyContinue | Select-Object -First 1 Source
```

Unix / macOS（bash）：

```bash
command -v libreoffice || command -v soffice
```

### Windows: Cairo ネイティブ DLL の導入（spec2model import に必須）

現行の `spec2model` は `parse_images.py` を import 時に読み込み、`cairosvg` は `cairocffi` 経由でネイティブの `libcairo-2.dll` を必要とする。Windows では pip がこのネイティブライブラリを提供しないため、DLL を用意しないと画像を比較しない場合でも `spec2model` の import が次のエラーで失敗する（MUST 対応）。

```text
OSError: no library called "cairo-2" was found ... libcairo-2.dll ... error 0x7e
```

対応（conda 不要。conda-forge の DLL を取得して venv 内に配置するだけ。システムには一切インストールしない）：

```powershell
Set-Location <workspace-root>\tools\spec2model
.venv\Scripts\python.exe ..\..\.agents\skills\spec2model-cloud-diff\scripts\fetch_cairo_dll.py .venv\cairo_dll
```

`scripts/fetch_cairo_dll.py` は cairo とその依存（libpng, pixman, libfreetype6→freetype.dll, fontconfig, libglib, libffi→ffi-8.dll, libharfbuzz, icu 等）の DLL を `.venv\cairo_dll` に展開し、`cairocffi` が探す名前 `libcairo-2.dll`（= `cairo.dll` のコピー）も作成する。

Unix / macOS では本スクリプトは不要。OS のパッケージマネージャで Cairo を導入する（例：`apt-get install libcairo2` / `brew install cairo`）。

インストール直後の最小確認（Windows は先に下記の環境変数を設定してから実行する）：

```powershell
$env:PATH = (Resolve-Path "tools\spec2model\.venv\cairo_dll").Path + ";" + $env:PATH
$env:CAIROCFFI_DLL_DIRECTORIES = (Resolve-Path "tools\spec2model\.venv\cairo_dll").Path
tools\spec2model\.venv\Scripts\python.exe -c "from spec2model import parse_document, compare_documents; print('spec2model import ok')"
```

Unix / macOS（bash）：

```text
<venv-python> -c "from spec2model import parse_document, compare_documents; print('spec2model import ok')"
```

### 依存不足時の確認と縮退実行

実行前に、`spec2model` の import と `soffice` / `libreoffice` の有無を確認する。依存不足を見つけた場合、agent は黙って続行せず、次の選択肢をユーザーへ提示する。

```text
画像差分の実行環境を確認しました。
- spec2model / cairosvg / Cairo: OK または NG
- LibreOffice (soffice): OK または NG

選択してください:
1. 不足依存を導入してから完全比較する（推奨）
2. 既知の制限を受け入れて実行する
3. 中止する
```

- `soffice` / `libreoffice` だけが無い場合は、ユーザーが **2** を選べば差分を続行してよい（MAY）。ただし EMF/WMF はプレースホルダー PNG へフォールバックする。テキスト・表差分および他の画像の結果は出力してよいが、EMF/WMF の `changed` / `unchanged` / `added` / `removed` 件数を原画像の確定結果として扱ってはならない。回答、ログ、またはレポート説明に次を明記する（MUST）：`LibreOffice 未導入のため EMF/WMF はプレースホルダーであり、該当画像の差分件数は参考値です。`。
- `cairosvg`、`lxml`、Cairo DLL の不足で `spec2model` の import が失敗した場合は、現行ソースでは `compare_documents()` とローカル parser を実行できない（HARD BLOCKER）。ユーザーが **2** を選んでも、画像差分や完全なローカル vs クラウド差分が完了したと報告してはならない（MUST NOT）。依存を導入するか中止する。import が成功する既存環境を別途確認できた場合に限り、画像差分を省略したテキスト・表差分を実行してよい。
- `cairosvg` の import は成功するが `soffice` が無い場合は、画像 JSON を生成し、`unavailable` とプレースホルダー由来の制限を区別して報告する。既存の `--image-compare auto` / `perceptual` の設定は変更しない。
- 依存不足を理由に `graph_collect_full_texts`、Markdown、検索スニペット、別の system Python、または未承認の別 parser へ切り替えてはならない（MUST NOT）。

## 環境検証

Windows では、`spec2model` の import と差分実行のたびに、先に Cairo DLL ディレクトリを `PATH` に追加しなければならない（MUST）。`CAIROCFFI_DLL_DIRECTORIES` だけでは `cairocffi` が依存 DLL を解決できず失敗するため、`PATH` への追加が必須である。

Windows（PowerShell）— 差分実行を含むすべての Python 呼び出しの前に設定する：

```powershell
$env:PATH = (Resolve-Path "tools\spec2model\.venv\cairo_dll").Path + ";" + $env:PATH
$env:CAIROCFFI_DLL_DIRECTORIES = (Resolve-Path "tools\spec2model\.venv\cairo_dll").Path
```

開始前に実行（`<venv-python>` は OS 対応のパスへ置換。Windows は上記の環境変数を設定済みであること）：

```text
<venv-python> -c "from spec2model import parse_document, compare_documents; from spec2model.exporters import render_diff_html; print('spec2model environment ok')"
```

`spec2model` の import が失敗した場合はハードブロッカーとして停止する。`soffice` だけが検出できない場合は、上記の確認でユーザーが既知のリスクを受け入れたときに限り、縮退実行を続行してよい。依存状態とユーザーの選択を実行結果とともに記録する（MUST）。

Windows で `no library called "cairo-2" was found`（`libcairo-2.dll` / `error 0x7e`）が出た場合は、「Windows: Cairo ネイティブ DLL の導入」の手順を実施し、`PATH` に `.venv\cairo_dll` を追加してから再実行する。

## クラウド前提

クラウド側で必要なもの：

- MCP ツール：`graph_export_document_json(file_name)`

バックエンドのダウンロード API には依存しません。権限は MCP ツールのアクセス制御に一元化されます。

## 標準手順

### 1. クラウド file_name を確認

クラウドエクスポートには完全一致する `Document.file_name` を使用しなければならない（MUST）。候補が複数ある場合は先に確認しなければならず（MUST）、推測してはならない（MUST NOT）。

### 2. クラウド Document JSON をエクスポート

比較を開始するたびに必ず実行する MCP 呼び出し：

```text
graph_export_document_json(file_name="<クラウド Document.file_name>")
```

想定返却フィールド：

```json
{
	"summary": "...",
	"file_name": "...",
	"download_name": "....document.json",
	"format": "spec2model-document-json",
	"document_json": {
		"document": { "...": "..." }
	},
	"json_text": "{...}"
}
```

`file_name`、`download_name` を記録し、`json_text`（または `document_json`）をローカル保存に使用します。

### 3. JSON をローカル保存

保存先ディレクトリには次を使用することが望ましい（SHOULD）。保存は、MCP 応答をそのまま `save_cloud_export_json.py` に渡して原子的に更新する。大きな JSON をシェル引数または heredoc に埋め込んではならない（MUST NOT）。

```text
data/cloud/
```

例：

```bash
mkdir -p data/cloud
```

MCP 応答を UTF-8 の `response.json` として Write ツールで保存した後に実行する。継続行の記号はシェルで異なる（PowerShell はバッククォート `` ` ``、bash はバックスラッシュ `\`）。

Windows（PowerShell）：

```powershell
tools\spec2model\.venv\Scripts\python.exe .agents\skills\spec2model-cloud-diff\scripts\save_cloud_export_json.py `
    "<MCP-response.json>" `
    "data/cloud/<cloud-file-stem>.document.json" `
    --expected-file-name "<cloud-file-name>"
```

Unix / macOS（bash）：

```bash
tools/spec2model/.venv/bin/python .agents/skills/spec2model-cloud-diff/scripts/save_cloud_export_json.py \
    "<MCP-response.json>" \
    "data/cloud/<cloud-file-stem>.document.json" \
    --expected-file-name "<cloud-file-name>"
```

### 4. JSON が Document に復元可能か検証

```text
<venv-python> -c "import importlib.util; from pathlib import Path; script=Path('.agents/skills/spec2model-cloud-diff/scripts/diff_local_with_cloud_json.py'); spec=importlib.util.spec_from_file_location('cloud_diff', script); m=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(m); doc=m.document_from_json_file(Path('data/cloud/<cloud-file-stem>.document.json')); print('doc_id', doc.id); print('sheets', len(doc.sheets), 'chapters', len(doc.chapters), 'contents', len(doc.contents))"
```

失敗時は JSON 形式を確認しなければならない（MUST）。full text へ切り替えてはならない（MUST NOT）。

### 5. ローカル vs クラウド差分を実行

注意：既存の `--out-csv` / `--out-html` 出力ファイルがあっても、差分手順を省略してはならない（MUST NOT）。既存結果を上書きまたは削除して再生成し、毎回 `compare_documents()` を実行しなければならない（MUST）。

次のスクリプトを使用する。`<venv-python>` は OS 対応のパスへ置換。継続行の記号がシェルで異なる点に注意（PowerShell はバッククォート `` ` ``、bash はバックスラッシュ `\`）。

Windows（PowerShell）：

```powershell
tools\spec2model\.venv\Scripts\python.exe .agents\skills\spec2model-cloud-diff\scripts\diff_local_with_cloud_json.py `
	"<local-file>" `
	"<cloud-ref>" `
	--cloud-source json `
	--local-side new `
	--cloud-name "<cloud-file-name>" `
	--local-name "<local-file-name>" `
	--out-csv "data/output_data/local_cloud_diff.csv" `
	--out-html "data/output_data/local_cloud_diff.html" `
	--out-image-json "data/output_data/local_cloud_image_diff.json"
```

Unix / macOS（bash）：

```bash
tools/spec2model/.venv/bin/python .agents/skills/spec2model-cloud-diff/scripts/diff_local_with_cloud_json.py \
	"<local-file>" \
	"<cloud-ref>" \
	--cloud-source json \
	--local-side new \
	--cloud-name "<cloud-file-name>" \
	--local-name "<local-file-name>" \
	--out-csv "data/output_data/local_cloud_diff.csv" \
	--out-html "data/output_data/local_cloud_diff.html" \
	--out-image-json "data/output_data/local_cloud_image_diff.json"
```

`<cloud-ref>` には、ローカルに保存済みの JSON `data/cloud/<cloud-file-stem>.document.json` を使用しなければならない（MUST）。

表ヘッダまたは markdown roundtrip の差異が確認できた場合に限り、明示的な有効化を検討することが望ましい（SHOULD）。

```bash
--normalize-as-graph
```

スクリプト既定値：

```text
--local-parser auto
```

ローカル parser の生出力差異を調査する場合に限り、一時的に無効化してもよい（MAY）。

```bash
--no-project-local-as-graph
```

`--local-side` の意味：

- `new`: クラウドが旧版、ローカルが新版
- `old`: ローカルが旧版、クラウドが新版

出力ディレクトリには次を使用することが望ましい（SHOULD）。

```text
data/output_data/
```

### 5.1 画像差分

上記スクリプトはテキスト・表の CSV/HTML に加え、画像差分 JSON を生成する。`--out-image-json` を省略した場合は `--out-csv` と同じ場所に `<csv-stem>.images.json` を生成する。

- ローカル文書は parser が抽出した `ImageBlock` と `TableBlock.images` を対象とする。
- クラウド側は `graph_export_document_json` の構造化 JSON に含まれる `kind: "image"` を対象とする。全文や Markdown の画像リンクで代用してはならない（MUST NOT）。
- 対応付けは一意な画像内容、`section/row/col` の論理位置、`name/ext` の順で行う。
- `changed` / `unchanged` は画像内容の比較結果のみで判定する。UUID、パス、ファイル名の違いだけを内容変更として報告してはならない（MUST NOT）。
- `moved` は画像内容が一致し、位置（シート・行・列）だけが変化したものを指す。行の挿入などで画像がずれた場合、`added`＋`removed` に分裂させず `moved` として報告する（MUST NOT を分裂報告に適用）。
- `added`、`removed`、`changed`、`moved`、`unchanged`、`unavailable` を区別して報告する。`unavailable` は未比較であり、差異なしではない。

#### AI による逐張視覚核対（跨プラットフォーム誤判の最終判定）

知覚比較（32x32、閾値 8.0）は、跨プラットフォームのフォント描画差（Windows/macOS の Cairo・フォント vs クラウド Linux）を吸収するための **粗いフィルタ**である。テキストボックス内の **微小な文字増減**（例：「を参照」の削除）と、フォント描画ノイズは、画素・知覚指標では **物理的に分離できない**。実測では、真の文字削除の知覚平均差 ≈ 6.3 に対し、描画ノイズ ≈ 5.8 と重なり、フル解像度の変化画素率はノイズ側の方が高くなることもある。したがって、スクリプトの `changed` / `unchanged` を最終結論として無検証で採用してはならない（MUST NOT）。

agent は、画像差分 JSON（`--out-image-json`）に基づき、次のポリシーで画像を **逐張で視覚核対** しなければならない（MUST）。核対対象は次に限定し、大規模文書での全数核対による膨張を避ける（SHOULD）。核対の**目的は status ごとに異なる**点に注意する。

- **`changed`、および `unchanged` で知覚平均差が境界帯（既定 4.0 以上 8.0 未満）のペア（MUST）**：目的は **実変化か描画ノイズかの判別**。新旧画像を並べて読み、意味内容が変化したかを判定する。
- **`added` / `removed`（MUST）**：目的は 2 つ。(a) ユーザーの「増減した画像の内容」の問いに答えるための **内容記述**（片側にしか無いため、その 1 枚を読んで何の図かを説明する）。(b) **pairing 誤判の検証**。ローカル vs クラウドの対応付けは知覚閾値に依存するため、内容が同一でも跨プラットフォーム描画差が大きい図は対応付けに失敗し、本来 `unchanged` / `moved` であるべきものが `added`＋`removed` に割れることがある。この「孤児」が対側の他の画像に視覚的に近い相手を持たないかを確認し、持つ場合は実態を `unchanged` / `moved`（誤判による偽の増減）として報告する（MUST）。
- **視覚核対を省略してよい（MAY）**：知覚平均差が ≈ 0（画素ほぼ一致）の `unchanged`、および対応付いたうえで差異が大きく別画像と明白な `changed`（例：知覚平均差 > 30）。これらは誤判の余地が小さい。

視覚核対の手順（MUST）：

1. 対象画像の内容を、各 `ImageBlock` の base64（ローカルは parser 出力、クラウドは `data_b64`）から一時 PNG へ復元し、画像として読み取る。`changed` と境界帯 `unchanged` は新旧ペアを、`added` / `removed` は当該 1 枚（および pairing 検証のため対側の候補）を読む。
2. **文字列・記号・図形の意味内容** が変化したか（または `added` / `removed` が何の図か）を判断する。フォントの太さ・アンチエイリアス・PNG エンコード差だけの相違は「変化なし」とみなす（MUST）。
3. スクリプトの判定と視覚核対が食い違う場合は、**視覚核対の結果を最終結論とする**（MUST）。例：スクリプト `changed` でも内容同一なら「描画差のみ・実変化なし」、スクリプト `unchanged` でも文字が増減していれば「実変化あり」、スクリプト `added`＋`removed` でも同一内容の孤児同士なら「対応付け失敗による偽の増減（実態は unchanged / moved）」と報告する。
4. 復元した一時 PNG は `data/output_data/` 配下に保存してよい（MAY）。会話に画像を大量に貼り付けてはならない（MUST NOT）。

ローカル同士の比較（`spec2model-local-diff`）はバイト厳密一致で判定され、同一プラットフォームのため描画ノイズが発生しない。したがって、この視覚核対要件はローカル vs クラウド（本 skill）にのみ適用し、ローカル vs ローカルには適用しない（MUST NOT）。

#### 画像内容の比較方式（バイト比較 / 知覚比較）

クラウド側の画像は Linux 上の spec2model が生成したものであり、ローカル（Windows / macOS）で生成した画像とは **バイト列が一致しない**。したがって、ローカル vs クラウドではバイト比較を使用してはならない（MUST NOT）。

スクリプトの `--image-compare` で方式を選択する。

```text
--image-compare auto        # 既定。クラウド側が Document JSON のときは perceptual を選ぶ
--image-compare bytes       # 常に base64 の完全一致
--image-compare perceptual  # 常に知覚比較
```

知覚比較は、両画像を 32x32 のグレースケールへ縮小し、画素あたりの平均絶対差が閾値以下なら「同一」と判定する。判定だけでなく **対応付け（pairing）にも同じ指標を使う**。対応付けの第 1 段階は本来「内容が一致する画像」を探すが、跨プラットフォームではバイト一致が 0 件になるため、これを知覚一致に置き換えないとほぼ全画像が `added` / `removed` に落ちる。

計測結果（同一文書 `MET-M_CONTDISP-CSTD-0063-C2.xlsx` をローカル解析とクラウド JSON で比較、画像 396 件）：

```text
バイト一致                   0 件
画素は完全一致・バイトのみ相違  340 件（PNG/zlib のエンコード差）
画素が相違                    53 件（フォント描画差）
サイズまたはモードが相違        3 件
知覚平均差                    全 396 件が閾値 8.0 未満（358 件は 2.0 未満）
```

対応付けの第 1 段階では、閾値内の候補が複数あっても **平均差が最小の候補が唯一のときだけ** 採用する。バイト一致による対応付けと同じ「一意性」を保つためであり、これを緩めると類似画像の集合内で誤った相手を選び、後段の座標一致（行番号がずれるため信頼できない）へ落ちてしまう。

検証結果（旧 = `0063` クラウド JSON、新 = `0064` ローカル解析）。ローカル同士をバイト比較した結果を正解とすると、知覚比較は集計値が完全一致する。

```text
                matched  unchanged  changed  added  removed
正解（バイト）      390        383        7     17        6
知覚比較            390        383        7     17        6
```

ローカル同士の比較ではバイト比較のままとする（MUST）。同一プラットフォームで描画されるため、同一図形は必ずバイト一致し、閾値による誤判定を持ち込む必要がない。


### 6. 結果報告

標準では、次のみを報告することが望ましい（SHOULD）。

- 保存した JSON パス
- CSV パス
- HTML パス
- 端末サマリーの総行数と change_type 分布

CSV/HTML 差分レポートを生成した後は、CSV と HTML の保存先パスをユーザーに明示しなければならない（MUST）。

回答には少なくとも次の行を含めなければならない（MUST）。

- CSV: `<csv-output-path>`
- HTML: `<html-output-path>`
- Image JSON: `<image-diff-json-path>`

画像差分を実行した場合は、**ユーザーへの報告は「AI による逐張視覚核対」後の真実の結論を最終結果としなければならない（MUST）**。スクリプトの `added` / `removed` / `changed` / `moved` / `unchanged` の集計値は中間の参考情報であり、視覚核対と食い違う場合はそれを最終結果として報告してはならない（MUST NOT）。具体的には次を守る。

- 「どの画像が変化したか」「増減した画像の内容は何か」は、スクリプトの集計値ではなく **視覚核対の結果に基づいて回答する**（MUST）。
- スクリプト判定と視覚核対が食い違ったペアは、実態を明示する（MUST）。例：スクリプト `changed` → 実態「描画差のみ・実変化なし」、スクリプト `unchanged` → 実態「文字増減あり」、スクリプト `added`＋`removed` → 実態「対応付け失敗による偽の増減（unchanged / moved）」。
- スクリプトの集計値も併記してよいが、その際は「スクリプト初判定（視覚核対前）」と明記し、最終結論と区別する（SHOULD）。

既定では、完全な CSV/HTML の内容を読み取り、復述または再掲してはならない（MUST NOT）。

## 失敗時対応

### MCP ツールが存在しない

クラウド版と MCP が更新済みであることを確認しなければならない（MUST）。`graph_collect_full_texts` に置き換えてはならない（MUST NOT）。

### MCP 返却に document_json/json_text がない

MCP のみを使用するエクスポート実装へ更新済みであることを確認しなければならない（MUST）。バックエンドのダウンロード API へ戻してはならない（MUST NOT）。

### JSON は取得できるがローカルで Document に復元できない

ファイル先頭が JSON オブジェクトか、トップレベル `document` フィールドがあるか確認してください。

### 差分スクリプトがローカル入力未対応を表示

ローカルファイル拡張子が次か確認：

```text
.xlsx .xlsm .xls .docx .pptx .pdf
```

### `ModuleNotFoundError: No module named 'spec2model'`

`pip install -e . --no-deps` を実行して `spec2model` 本体を登録したか確認する（MUST）。`tools/spec2model/spec2model`（空ディレクトリ）が名前空間として干渉している場合があるため、`src/spec2model` を editable 登録することで解決する。

### `ModuleNotFoundError`（pdf2image / pptx / azure など）

`spec2model.parsers` は全 parser を eager import するため、xlsx 差分だけでも次を導入する（MUST）：`pdf2image python-pptx markdown beautifulsoup4 html5lib python-dotenv azure-ai-documentintelligence`。

### `ModuleNotFoundError`（cairosvg / lxml）または画像抽出がスキップされる

画像差分を実行するのに extras `images` を導入していない。まず「画像差分の追加インストール」の手順で `lxml` と `cairosvg` を導入する。現行ソースでは不足時に import 自体が失敗するため、依存を導入できない場合は完全な差分を続行できない。ユーザー確認の **2** は、import が成功する別の既存環境での縮退実行に限る。

### EMF/WMF 画像がプレースホルダーになる（`LibreOffice が見つからないため EMF/WMF はプレースホルダーへフォールバックします`）

`.xlsx` / `.docx` に含まれる EMF/WMF ベクター画像は Pillow で開けないため、`spec2model.utils.parse_images` は `libreoffice` / `soffice` で PNG 化する。パスに `libreoffice`（または `soffice`）が無いと、その画像はプレースホルダー PNG に置き換わる。あわせて `openpyxl` が `wmf image format is not supported so the image is being dropped` を警告することがある。

対応: 「システム要件: LibreOffice / Poppler」の手順で LibreOffice を導入し、`soffice` を PATH に通す（SHOULD）。導入できない場合は、ユーザーが既知のリスクを受け入れたときに限り差分を続行してよい。ローカル側は EMF/WMF がプレースホルダー、クラウド側は実ラスタライズ画像となり、画像差分が実際より大きく出るため、結果を参考値として報告する。

### Windows: `no library called "cairo-2" was found` / `libcairo-2.dll` / `error 0x7e`

Cairo ネイティブ DLL が無い、または `PATH` に追加されていない。次を実施する（MUST）：

1. `scripts/fetch_cairo_dll.py` で `.venv\cairo_dll` に DLL を展開する。
2. Python 呼び出しの前に `PATH` へ `.venv\cairo_dll` を追加する（`CAIROCFFI_DLL_DIRECTORIES` だけでは不十分）。

`error 0x7e`（ERROR_MOD_NOT_FOUND）は DLL 自体ではなく依存 DLL が見つからない状態を示す。`fetch_cairo_dll.py` は `freetype.dll`（libfreetype6）と `ffi-8.dll`（libffi）を含む依存一式を取得するため、これらの取得漏れが原因のことが多い。

### 画像差分がほぼすべて `changed` / `added` / `removed` になる

バイト比較のまま、ローカル vs クラウドを比較している。`--image-compare` を `auto`（既定）または `perceptual` にする（MUST）。`bytes` を明示している場合は外す。

クラウド側の画像はローカルとバイト一致しない。原因は spec2model のバージョン差ではなく、Python パッケージの外側にある：

1. `spec2model.utils.parse_images._resolve_font_path` は `fc-match` を呼ぶ。Windows には存在しないため `FileNotFoundError` となり `None` を返し、`ImageFont.load_default()`（CJK 非対応のビットマップフォント）へ退避する。これはバージョン差ではなくプラットフォーム分岐である。
2. フォント実体（Noto Sans CJK JP / IPAexGothic 等）は pip パッケージに含まれず、Windows には存在しない。
3. cairo / pixman / freetype / zlib のバージョンとビルド差により、アンチエイリアスと PNG 圧縮結果が一致しない。
4. EMF/WMF ベクター画像は、ローカルに LibreOffice が無いとプレースホルダー PNG になる。クラウド（Linux）側は LibreOffice で実ラスタライズされるため、同じ図でも内容が食い違う。この場合は「システム要件: LibreOffice / Poppler」の手順で LibreOffice を導入すると乖離が縮小する。

3 は描画結果が同一でもバイト列を変えるため、フォント問題を解決してもバイト一致は達成できない（計測では 86% が「画素一致・バイト相違」）。バイト一致を要求するなら、クラウドと同一のコンテナイメージをローカルで動かす必要がある。知覚比較（`--image-compare auto`）は 1〜3 のレンダリング差は吸収するが、4 のプレースホルダー化（内容そのものが別画像）は吸収できないため、EMF/WMF を含む文書では LibreOffice の導入が必要である。

### テキストボックスの `changed` / `unchanged` が実態と食い違う（境界帯の誤判）

テキストボックス内の微小な文字増減（例：「を参照」の削除）は、跨プラットフォームのフォント描画ノイズと知覚平均差が重なるため、知覚比較の閾値だけでは分離できない。実測では真の文字削除 ≈ 6.3、描画ノイズ ≈ 5.8 と接近し、フル解像度の変化画素率はノイズ側が高い場合すらある。

対応: **閾値を調整して自動分離しようとしてはならない（MUST NOT）**。いかなる単一の画素・知覚閾値も、この 2 者を頑健には分離できない（閾値を下げると描画ノイズを `changed` と誤り、上げると真の微小変化を `unchanged` と見逃す）。代わりに「AI による逐張視覚核対」を実施し、対象ペアの新旧画像内容を読み取って最終判定する（MUST）。境界帯（知覚平均差 4.0〜8.0）の `unchanged` と、すべての `changed` / `added` / `removed` が核対対象である。

### 差分結果が空

次を確認：

- `--local-side` の選択が正しいか
- ローカル JSON が想定 `file_name` の `graph_export_document_json` 結果から保存されたか
- ローカルファイルとクラウド文書がもともと一致していないか

## 禁止事項

- `graph_collect_full_texts` をローカルとクラウドの差分に使用してはならない（MUST NOT）。
- Markdown、full text、search snippet または summary で `Document` を復元してはならない（MUST NOT）。
- 画像内容の比較に画像ファイル名、IMAGE_REF、UUID、またはパスだけを使用してはならない（MUST NOT）。
- 既存の CSV/HTML 差分ファイルに基づいて差分手順を省略してはならない（MUST NOT）。
- 大きな JSON を会話コンテキストに貼り付けてはならない（MUST NOT）。
- `.agents/skills/` またはシステム Python に一時仮想環境を作成してはならない（MUST NOT）。

## 例示

### 正例：ローカル文書と KGA 文書の比較

ユーザーが添付または明示的なローカルパス `test_data/MET-C_HCS-CSTD-A0-03-A-C0.xlsm` を提供し、KGA 文書 `MET-C_HCS-CSTD-A0-04-A-C0.xlsm` との差分比較を依頼する。この場合は本 skill を使用し、KGA 文書を `Document JSON` としてエクスポートし、ローカルで差分を再計算して CSV と HTML レポートを出力する。

### 反例：2 つの文書名のみを提示

ユーザーが `MET-C_HCS-CSTD-A0-03-A-C0.xlsm` と `MET-C_HCS-CSTD-A0-04-A-C0.xlsm` のみを提示し、添付または明示的なローカルパスがない場合、両方をクラウド文書として扱わなければならない（MUST）。本 skill を使用してはならず（MUST NOT）、直接 `graph_diff_documents` を使用する。

## 参考

- [README.md](README.md)
- [ローカルとクラウドの差分スクリプト](scripts/diff_local_with_cloud_json.py)
- [Cairo DLL 取得スクリプト（Windows）](scripts/fetch_cairo_dll.py)
- [spec2model プロジェクト README](../../../tools/spec2model/README.md)
