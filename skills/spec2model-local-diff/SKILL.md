---
name: spec2model-local-diff
description: 2 つのローカル文書のみを比較し、構造化差分（CSV/HTML）を出力します。添付ファイルまたは明示的なローカルパスが与えられた入力のみをローカル文書と見なし、この skill を使用します。ローカルパスや添付がなく、ファイル名だけが与えられた入力はすべてクラウド文書として扱い、この skill は使わず、状況に応じて spec2model-cloud-diff（ローカル 1 件とクラウド 1 件の比較）または graph_diff_documents（クラウド 2 件の比較）に切り替えてください。例えば、MET-C_HCS-CSTD-A0-03-A-C0.xlsm と MET-C_HCS-CSTD-A0-04-A-C0.xlsm がファイル名のみで与えられた場合は、直接クラウド文書として扱います。
---

## 役割

- 2 つのローカル文書に対して構造化差分を実行する
- 分析可能な CSV と HTML レポートを出力する
- 既定では差分結果の生成のみを担当し、CSV/HTML の具体的な差分内容を自発的に読み取り・復述してはならない（MUST NOT）

## いつ使うか

- ユーザーがローカルの 2 ファイル（before/after）の比較を明示的に求めている
- ユーザー入力がアクセス可能なローカル入力（添付または明示的なファイルパス）である
- 両側の入力が上記条件を満たす場合にのみ、この skill を使用する
- 両側ともファイル名のみで、添付やローカルパスがない場合はクラウド文書 vs クラウド文書となるため、この skill は使用しない

## 制約条件

- 作業ディレクトリはリポジトリのルートでなければならない（MUST）。
- この skill は他の spec2model skill に依存してはならない（MUST NOT）。
- 環境の場所は spec2model プロジェクト配下の `.venv`、すなわち `<workspace-root>/tools/spec2model/.venv` に固定しなければならない（MUST）。
- リポジトリルート、`.agents/skills/`、一時ディレクトリ、またはシステム Python 上に、この skill 用の別環境を作成してはならない（MUST NOT）。
- 実行前に環境チェックを行い、`<workspace-root>/tools/spec2model/.venv` を統一して再利用しなければならない（MUST）。
- venv 内の Python 実行ファイルのパスは OS により異なる。以降ではこれを `<venv-python>` と表記し、実行時に OS 対応のパスへ置換する。
  - Windows（PowerShell / cmd）：`tools\spec2model\.venv\Scripts\python.exe`
  - Unix / macOS（bash）：`tools/spec2model/.venv/bin/python`
- 環境ポリシーは以下に固定する：
  - 上記 `<venv-python>` が存在する場合は、その環境を直接再利用しなければならない（MUST）。
  - 存在しない場合は、`uv sync --project tools/spec2model --group dev` で環境を作成しなければならない（MUST。`uv` は Windows / Unix 共通で同一コマンド）。
  - 依存ファイルに変更がなく `spec2model` を import 可能なら、依存インストールを省略してもよい（MAY）。
  - 依存ファイルの変更、環境欠落、または環境不良がある場合に限り、そのプロジェクト `.venv` 内で依存を同期しなければならない（MUST）。
- システム Python の誤用を避けるため、`<venv-python>` で直接実行することが望ましい（SHOULD）。

  現行の `spec2model` は `parsers/__init__.py` と `utils/__init__.py` から全 parser と `parse_images.py` を eager import する。`parse_images.py` はトップレベルで `lxml`、Pillow、`cairosvg` を import するため、README の extras `images` が opt-in でも、`spec2model` コードを変更しない前提ではこれらを基礎環境の作成時に導入しなければならない。画像機能を使わない場合に遅延できるのは LibreOffice / Poppler である。

  Windows で venv を新規作成した場合は、`uv sync` 後に次を実行する（MUST）：

  ```powershell
  tools\spec2model\.venv\Scripts\python.exe -m pip install "lxml>=4.9.3,<6.0.0" "cairosvg>=2.8.2,<3.0.0"
  ```

### Windows: Cairo ネイティブ DLL の導入（spec2model import に必須）

現行の `spec2model` は `parse_images.py` を import 時に読み込み、`cairosvg` は `cairocffi` 経由でネイティブの `libcairo-2.dll` を必要とする。Windows では pip がこのネイティブライブラリを提供しないため、DLL を用意しないと画像を比較しない場合でも `spec2model` の import が次のエラーで失敗する（MUST 対応）。

```text
OSError: no library called "cairo-2" was found ... libcairo-2.dll ... error 0x7e
```

対応（conda 不要。conda-forge の DLL を取得して venv 内に配置するだけ。システムには一切インストールしない）：

```powershell
Set-Location <workspace-root>\tools\spec2model
.venv\Scripts\python.exe ..\..\.agents\skills\spec2model-local-diff\scripts\fetch_cairo_dll.py .venv\cairo_dll
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

環境チェック（venv の有無確認）：

Windows（PowerShell）：

```powershell
if (Test-Path tools\spec2model\.venv\Scripts\python.exe) {
  "[OK] tools/spec2model/.venv is ready"
} else {
  "[MISSING] tools/spec2model/.venv -> run: uv sync --project tools/spec2model --group dev"
}
```

Unix / macOS（bash）：

```bash
if [ -x tools/spec2model/.venv/bin/python ]; then
  echo "[OK] tools/spec2model/.venv is ready"
else
  echo "[MISSING] tools/spec2model/.venv -> run: uv sync --project tools/spec2model --group dev"
fi
```

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

## 基本コマンド

`<venv-python>` は OS 対応のパスへ置換する。

Windows（PowerShell）：

```powershell
tools\spec2model\.venv\Scripts\python.exe tools\spec2model\scripts\diff_documents.py <old-file> <new-file>
```

Unix / macOS（bash）：

```bash
tools/spec2model/.venv/bin/python tools/spec2model/scripts/diff_documents.py <old-file> <new-file>
```

## 画像差分

### 画像差分の追加システム要件（画像を比較する場合のみ）

テキスト・表差分だけの依頼では、この節の追加導入は不要である（SHOULD NOT）。画像差分（下記 `diff_local_images.py`）を実行する場合は、原則として LibreOffice / Poppler を導入する（SHOULD）。Python の lxml / Pillow / cairosvg と Cairo は、現行 `spec2model` の eager import のため基礎環境側で準備する。

**LibreOffice（+ Poppler）**: Excel/Word 内の **EMF/WMF ベクター画像**を PNG 化するために必要。`spec2model.utils.parse_images` は Pillow で開けない EMF/WMF を `libreoffice` / `soffice --headless --convert-to png` で変換する。パスに `libreoffice`（または `soffice`）が無いと、その画像はプレースホルダー PNG になり、画像差分の件数が実際と乖離する。
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
   - **Ubuntu / Debian**: `sudo apt-get install -y libreoffice poppler-utils`
   - **macOS (Homebrew)**: `brew install --cask libreoffice && brew install poppler`

   導入確認：

   ```powershell
   Get-Command soffice, libreoffice -ErrorAction SilentlyContinue | Select-Object -First 1 Source
   ```

   ```bash
   command -v libreoffice || command -v soffice
   ```

文書内の画像を比較する要求では、通常の CSV/HTML テキスト・表差分に加え、次のコマンドを実行しなければならない（MUST）。
このコマンドは `ImageBlock` と `TableBlock.images` の両方を収集し、画像を独立して比較する。継続行の記号はシェルで異なる（PowerShell はバッククォート `` ` ``、bash はバックスラッシュ `\`）。

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

- `soffice` / `libreoffice` だけが無い場合は、ユーザーが **2** を選べば差分を続行してよい（MAY）。EMF/WMF はプレースホルダー PNG へフォールバックするため、画像結果は参考値として扱う。回答には次を明記する（MUST）：`LibreOffice 未導入のため EMF/WMF はプレースホルダーであり、該当画像の差分件数は参考値です。`
- `cairosvg`、`lxml`、Cairo DLL の不足で `spec2model` の import が失敗した場合は、現行ソースではローカル parser と画像差分を実行できない（HARD BLOCKER）。ユーザーが **2** を選んでも、画像差分が完了したと報告してはならない（MUST NOT）。依存を導入するか中止する。import が成功する既存環境を別途確認できた場合に限り、画像差分を省略したテキスト・表差分を実行してよい。
- `cairosvg` の import は成功するが `soffice` が無い場合は、画像 JSON を生成し、`unavailable` とプレースホルダー由来の制限を区別して報告する。画像比較方式はバイト比較（`ImageBlock.data_b64` の厳密一致）のままとし、閾値による自動補正に切り替えてはならない（MUST NOT）。
- 依存不足を理由に system Python、別 parser、既存レポートの再利用へ切り替えてはならない（MUST NOT）。

Windows（PowerShell）：

```powershell
tools\spec2model\.venv\Scripts\python.exe .agents\skills\spec2model-local-diff\scripts\diff_local_images.py `
  "<old-file>" `
  "<new-file>" `
  --old-images-dir "data/output_data/images/old" `
  --new-images-dir "data/output_data/images/new" `
  --out-json "data/output_data/local_image_diff.json"
```

Unix / macOS（bash）：

```bash
tools/spec2model/.venv/bin/python .agents/skills/spec2model-local-diff/scripts/diff_local_images.py \
  "<old-file>" \
  "<new-file>" \
  --old-images-dir "data/output_data/images/old" \
  --new-images-dir "data/output_data/images/new" \
  --out-json "data/output_data/local_image_diff.json"
```

- 画像コンテンツの変更判定は `ImageBlock.data_b64` の厳密一致を使用する（MUST）。ファイル名、UUID、パスの変更だけを内容変更として報告してはならない（MUST NOT）。
- 対応付けは一意な画像内容、`section/row/col` の論理位置、`name/ext` の順に行う。
- 出力 JSON の `status` は `added`、`removed`、`changed`、`moved`、`unchanged`、または `unavailable` である。
- `moved` は画像内容が一致し（バイトが同一）、シート・行・列の位置だけが変化したものを指す。行の挿入で下方の画像がずれた場合などが該当し、`added`＋`removed` の重複報告にはしない（MUST NOT）。
- Base64 データが取得できない画像は `unavailable` として報告し、変更なしと扱ってはならない（MUST NOT）。
- 画像差分 JSON はテキスト差分 CSV を置き換えない。両方を出力しなければならない（MUST）。

## 代表例

継続行の記号はシェルで異なる（PowerShell はバッククォート `` ` ``、bash はバックスラッシュ `\`）。

Windows（PowerShell）：

```powershell
tools\spec2model\.venv\Scripts\python.exe tools\spec2model\scripts\diff_documents.py `
  "data/before/spec.xlsx" `
  "data/after/spec.xlsx" `
  --out-csv "data/output_data/local_diff.csv" `
  --out-html "data/output_data/local_diff.html"
```

```powershell
tools\spec2model\.venv\Scripts\python.exe tools\spec2model\scripts\diff_documents.py `
  "data/before/spec.docx" `
  "data/after/spec.docx" `
  --text-similarity 0.5 `
  --row-similarity 0.5 `
  --char-level-diff
```

Unix / macOS（bash）：

```bash
tools/spec2model/.venv/bin/python tools/spec2model/scripts/diff_documents.py \
  "data/before/spec.xlsx" \
  "data/after/spec.xlsx" \
  --out-csv "data/output_data/local_diff.csv" \
  --out-html "data/output_data/local_diff.html"
```

```bash
tools/spec2model/.venv/bin/python tools/spec2model/scripts/diff_documents.py \
  "data/before/spec.docx" \
  "data/after/spec.docx" \
  --text-similarity 0.5 \
  --row-similarity 0.5 \
  --char-level-diff
```

## オプション

- `--out-csv`: CSV 出力パス（デフォルトは `diff_result.csv`）
- `--out-html`: HTML 出力パス（任意）
- `--text-similarity`: テキストブロックの対応付けしきい値
- `--row-similarity`: 表行の対応付けしきい値
- `--word-level-diff` / `--char-level-diff`: 行内差分の粒度
- `--normalize-mode`: テキスト正規化モード
- `--no-summary`: 端末サマリーの出力を無効化

## 結果報告

- 比較の完了後、CSV 出力ファイルが生成されたことを確認しなければならない（MUST）。
- ユーザーが HTML を要求した、または `--out-html` を指定した場合は、HTML 出力ファイルが生成されたことも確認しなければならない（MUST）。
- 回答では CSV の保存先を明示しなければならない（MUST）。HTML を生成した場合は、その保存先も明示しなければならない（MUST）。
- `--no-summary` を指定していない場合は、端末サマリーの総行数と `change_type` 分布を報告しなければならない（MUST）。
- CSV/HTML の差分詳細を読み取り、復述または再掲してはならない（MUST NOT）。ただし、ユーザーが明示的に要求した場合はこの限りではない（MAY）。

回答には少なくとも次の項目を含めなければならない（MUST）。

- CSV: `<csv-output-path>`
- HTML: `<html-output-path>`（生成した場合）
- Image JSON: `<image-diff-json-path>`（画像差分を実行した場合）
- Summary: `<total-rows-and-change_type-distribution>`（`--no-summary` を指定していない場合）

## 使い分け

- ローカルファイル vs ローカルファイル：この skill を使用する
- この skill はローカルファイル vs クラウド Document JSON を扱ってはならない（MUST NOT）。
- 添付やファイルパスがなく、ファイル名のみが与えられた場合は、一律クラウド文書入力として扱わなければならない（MUST）。この skill は使用せず、cloud-diff skill に切り替える。
- 2 つの入力がどちらもファイル名のみ（例：MET-C_HCS-CSTD-A0-03-A-C0.xlsm と MET-C_HCS-CSTD-A0-04-A-C0.xlsm）の場合は、クラウド文書 vs クラウド文書と直接判定し、`graph_diff_documents` を使用しなければならない（MUST）。
- 差分結果が大きい場合は、ファイルを生成するだけに留めることが望ましい（SHOULD）。要約のために出力内容を再読込してはならない（MUST NOT）。
- 出力ファイルを読み、差分詳細を復述してもよいのは、ユーザーが明示的に要求した場合のみである（MAY）。

## 失敗時対応

### `ModuleNotFoundError`（cairosvg / lxml）または `spec2model` import 失敗

現行ソースでは `parse_images.py` を eager import するため、画像差分を実行しない場合でも `lxml` と `cairosvg` が必要になる。依存を導入できない場合は完全なローカル差分を続行できない。ユーザー確認の **2** は、import が成功する既存環境で画像差分を省略する縮退実行に限る。

### Windows: `no library called "cairo-2" was found` / `libcairo-2.dll` / `error 0x7e`

Cairo ネイティブ DLL が無い、または `PATH` に追加されていない。次を実施する（MUST）：

1. `scripts/fetch_cairo_dll.py` で `.venv\cairo_dll` に DLL を展開する。
2. Python 呼び出しの前に `PATH` へ `.venv\cairo_dll` を追加する（`CAIROCFFI_DLL_DIRECTORIES` だけでは不十分）。

`error 0x7e`（ERROR_MOD_NOT_FOUND）は DLL 自体ではなく依存 DLL が見つからない状態を示す。`fetch_cairo_dll.py` は `freetype.dll`（libfreetype6）と `ffi-8.dll`（libffi）を含む依存一式を取得するため、これらの取得漏れが原因のことが多い。

## 禁止事項

- ローカルファイルとクラウド `Document JSON` の差分にこの skill を使用してはならない（MUST NOT）。この場合は `spec2model-cloud-diff` を使用する。
- 添付または明示的なローカルパスがないファイル名を、ローカルファイルとして扱ってはならない（MUST NOT）。
- 既存の CSV/HTML 差分ファイルを根拠に、文書の比較手順を省略してはならない（MUST NOT）。
- `.agents/skills/`、一時ディレクトリまたはシステム Python に、この skill 用の仮想環境を作成してはならない（MUST NOT）。

## 例示

### 正例：2 件のローカル文書の比較

ユーザーが `test_data/MET-C_HCS-CSTD-A0-03-A-C0.xlsm` と `test_data/MET-C_HCS-CSTD-A0-04-A-C0.xlsm` のローカルパスを提示し、差分比較を依頼する。この場合は本 skill を使用して比較し、CSV を出力する。必要に応じて HTML レポートも出力する。

### 反例：ファイル名のみの 2 文書比較

ユーザーが `MET-C_HCS-CSTD-A0-03-A-C0.xlsm` と `MET-C_HCS-CSTD-A0-04-A-C0.xlsm` のみを提示し、添付または明示的なローカルパスがない場合、両方をクラウド文書として扱わなければならない（MUST）。本 skill を使用してはならず（MUST NOT）、直接 `graph_diff_documents` を使用する。

## 参考

- [README.md](README.md)
- [ローカル差分コマンド](../../../tools/spec2model/scripts/diff_documents.py)
- [Cairo DLL 取得スクリプト（Windows）](scripts/fetch_cairo_dll.py)
- [spec2model プロジェクト README](../../../tools/spec2model/README.md)
