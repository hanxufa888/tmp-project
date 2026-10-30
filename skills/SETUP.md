# SETUP.md — spec2model 差分 skill 導入手順（Windows / ユーザー向け）

このドキュメントは、`spec2model-local-diff` / `spec2model-cloud-diff` の 2 つの skill を各メンバーの環境で使えるようにするための **初回セットアップ手順（人が手作業で実施）** です。
**全メンバーが実施必須**です（Python の仮想環境 `.venv` はコミット・共有できないため、各自の PC で必ず構築する必要があります）。

対象環境: **Windows（PowerShell）**
※ WSL / macOS / Linux を使う場合は、パスの `\` を `/`、`.venv\Scripts\python.exe` を `.venv/bin/python` に読み替えてください。

---

## 0. 前提（用語と配置ルール）

### `.claude` ディレクトリと CWD（カレントディレクトリ）ルール

skill 内のコマンドは、すべて **使用する `.claude` ディレクトリを CWD（作業ディレクトリ）とする** 前提で書かれています。

> **注意:** `.claude` の場所はメンバーによって異なります。
> - ユーザーホーム直下: `C:\Users\<user>\.claude`
> - プロジェクトフォルダ配下: `C:\Users\<user>\<project>\.claude`
>
> 以降この手順では、あなたが使う `.claude` を **`<CLAUDE_DIR>`** と表記します。自分の実際のパスに読み替えてください。

このドキュメントの PowerShell 例では、最初に一度だけ次を実行して `$claude` に自分の `.claude` パスを入れておくと、以降のコマンドをそのままコピペできます。

```powershell
# 自分が使う .claude の実パスに置き換える（例はホーム直下／プロジェクト配下の2パターン）
$claude = "C:\Users\<user>\.claude"
# $claude = "C:\Users\<user>\<project>\.claude"

Set-Location $claude
```

### 完成後のディレクトリ構成

```
<CLAUDE_DIR>\                    ← CWD（ここを基準にコマンドが動く）
├─ skills\
│  ├─ spec2model-local-diff\   (SKILL.md, README.md)
│  └─ spec2model-cloud-diff\   (SKILL.md, README.md, scripts\...)
└─ tools\
   └─ spec2model\              ← spec2model を導入する場所
      ├─ src\spec2model\
      ├─ scripts\diff_documents.py
      ├─ pyproject.toml / requirements.txt
      └─ .venv\                ← 各自が作成する仮想環境（共有不可）
```

すべてのパスは **`<CLAUDE_DIR>` からの相対パス**（`tools\spec2model\...`, `skills\...`）です。CWD が `<CLAUDE_DIR>` になっていれば、`.claude` がどこにあっても同じコマンドで動きます。

---

## 1. 事前に必要なもの

- **Python 3.10〜3.13**（確認: `python --version`）
- **（Windows 必須）ネイティブ Cairo DLL（`libcairo-2.dll`）** … `pip` では導入されず、無いとテキスト/表差分だけでも import が失敗します。付属スクリプト **`fetch_cairo_dll.py`** で conda-forge から取得し、venv 配下（`tools\spec2model\.venv\cairo_dll`）へ配置します（**外部ダウンロードを伴うため、ネットワーク／プロキシに接続できる環境で実施**。GUI 操作・管理者権限は不要）。→ 「4-4. Windows: ネイティブ Cairo DLL の用意」を実施してください。
- （PDF・PowerPoint画像化、および Excel/Word 内 EMF/WMF 画像の差分を使う場合のみ）**Poppler** と **LibreOffice** … → 「6. システム要件」参照

---

## 2. skill を `<CLAUDE_DIR>\skills` に配置

配布された `spec2model-local-diff` / `spec2model-cloud-diff` の 2 フォルダを、`<CLAUDE_DIR>\skills\` 直下にコピーします。

```powershell
$dst = "$claude\skills"
Copy-Item ".\spec2model-local-diff" "$dst\spec2model-local-diff" -Recurse -Force
Copy-Item ".\spec2model-cloud-diff" "$dst\spec2model-cloud-diff" -Recurse -Force
```

---

## 3. tools\ 以下に「spec2model」を導入する ★重要

skill は `tools\spec2model\scripts\diff_documents.py` などソースツリーを直接参照します。
そのため、**`<CLAUDE_DIR>\tools\spec2model` に spec2model 一式を配置する必要があります。**

配布された `spec2model` フォルダを `<CLAUDE_DIR>\tools\spec2model` にコピーします。

```powershell
Set-Location $claude
New-Item -ItemType Directory -Force .\tools | Out-Null
Copy-Item "<配布された spec2model フォルダのパス>" ".\tools\spec2model" -Recurse -Force
```

配置後、`tools\spec2model\scripts\diff_documents.py` と `tools\spec2model\pyproject.toml` が存在することを確認してください。

```powershell
Test-Path "$claude\tools\spec2model\scripts\diff_documents.py"
Test-Path "$claude\tools\spec2model\pyproject.toml"
```

---

## 4. 仮想環境（venv）の作成と spec2model のインストール ★必須

CWD を `<CLAUDE_DIR>` にした状態で実行します。

```powershell
Set-Location $claude

# 4-1) venv 作成（tools\spec2model\.venv に固定）
python -m venv tools\spec2model\.venv

# 4-2) pip 更新
tools\spec2model\.venv\Scripts\python.exe -m pip install --upgrade pip

# 4-3) spec2model 本体＋全依存をインストール（editable install）
#      ※ requirements.txt 単独では不足・本体未インストールになるため必ず -e . を使う
#      ※ images extra（lxml/cairosvg）はコア import でも実質必須のため必ず [images] を付ける
#         （utils/__init__.py が無条件で cairosvg を import するため、付けないと手順5が [NG] になる）
Set-Location "$claude\tools\spec2model"
.\.venv\Scripts\python.exe -m pip install -e ".[images]"
Set-Location $claude
```

### 4-4) Windows: ネイティブ Cairo DLL の用意
（`fetch_cairo_dll.py` で取得）

`spec2model` は `utils/__init__.py` → `parse_images.py` を**無条件で import** し、`cairosvg`→`cairocffi` がネイティブの `libcairo-2.dll`（＋依存DLL）を要求します。**手順 4-3 の `pip install -e ".[images]"` は Python 側（cairosvg/cairocffi）しか入れず、ネイティブ DLL は入れません**。DLL が無いと、画像を使わないテキスト/表差分だけでも手順 5 の import が次で失敗します。

```text
OSError: no library called "cairo-2" was found ... libcairo-2.dll ... error 0x7e
```

付属の取得スクリプト `fetch_cairo_dll.py`（`skills\spec2model-cloud-diff\scripts\`）を実行し、conda-forge（win-64）から Cairo とその依存 DLL 一式をダウンロードして `tools\spec2model\.venv\cairo_dll` へ展開します。`conda` のインストールは不要で、パッケージアーカイブを取得・解凍するだけです（システムには一切インストールしません）。

1. **DLL を取得する**（CWD=`<CLAUDE_DIR>`）。

   ```powershell
   Set-Location $claude
   tools\spec2model\.venv\Scripts\python.exe skills\spec2model-cloud-diff\scripts\fetch_cairo_dll.py tools\spec2model\.venv\cairo_dll
   ```

   末尾に `libcairo-2.dll present: True` と表示されれば取得成功です。

2. **実行時に DLL フォルダを解決させる。** `libcairo-2.dll` はシステム PATH ではなく venv 配下（`tools\spec2model\.venv\cairo_dll`）に置くため、import／差分実行の前に、当該フォルダを `PATH` と `CAIROCFFI_DLL_DIRECTORIES` に追加します。

   ```powershell
   $env:PATH = (Resolve-Path "tools\spec2model\.venv\cairo_dll").Path + ";" + $env:PATH
   $env:CAIROCFFI_DLL_DIRECTORIES = (Resolve-Path "tools\spec2model\.venv\cairo_dll").Path
   ```

   - この 2 行は **PowerShell セッション（ウィンドウ）ごと**に必要です（新しい PowerShell を開いたら再度設定）。`CAIROCFFI_DLL_DIRECTORIES` だけでは依存 DLL を解決できないため、`PATH` への追加も必須です。
   - 最終確認は手順 5 の import 検証（`[OK]` になること）で兼ねられます。

> **LibreOffice について:** LibreOffice は Excel/Word 内の EMF/WMF ベクター画像を PNG 化する用途（画像差分の精度向上）で有用ですが、**Cairo 本体は上記 `fetch_cairo_dll.py` で用意**します。画像差分まで行う場合は「6. システム要件」も参照。

---

## 5. 動作確認（import 検証）

CWD=`<CLAUDE_DIR>` で以下を実行し、両方 `[OK]` になれば成功です。

```powershell
Set-Location $claude
# 手順 4-4 で取得した Cairo DLL フォルダを解決させる（セッションごとに必要）
$env:PATH = (Resolve-Path "tools\spec2model\.venv\cairo_dll").Path + ";" + $env:PATH
$env:CAIROCFFI_DLL_DIRECTORIES = (Resolve-Path "tools\spec2model\.venv\cairo_dll").Path
@'
def t(name, fn):
    try:
        fn(); print(f"[OK] {name}")
    except Exception as e:
        print(f"[NG] {name}: {repr(e)}")

t("core", lambda: __import__("spec2model", fromlist=["parse_document", "compare_documents"]))
t("exporters.render_diff_html", lambda: __import__("spec2model.exporters", fromlist=["render_diff_html"]))
'@ | tools\spec2model\.venv\Scripts\python.exe -
```

> **注（Windows）:** この検証の前に、手順 4-4 の **`fetch_cairo_dll.py` による Cairo DLL 取得**を済ませ、上のコードブロックのとおり **`PATH` と `CAIROCFFI_DLL_DIRECTORIES` に `tools\spec2model\.venv\cairo_dll` を追加**しておくこと。未取得・未設定だと、Python 依存（`.[images]`）が入っていても import は `cairo-2` エラーで失敗します。環境変数の設定は **PowerShell セッションごと**に必要です。

### `[NG]` が出たときの切り分け

| `[NG]` のメッセージ | 原因 / 対処 |
|---|---|
| `no library called "cairo-2"` / `libcairo-2.dll` / `error 0x7e` | **ネイティブ Cairo DLL 不足**（`pip` では入らない）。手順 4-4 の `fetch_cairo_dll.py` で DLL を取得し、`PATH` と `CAIROCFFI_DLL_DIRECTORIES` に `tools\spec2model\.venv\cairo_dll` を追加してから再検証する（設定は PowerShell セッションごとに必要） |
| `No module named 'cairosvg'` | images extra 未導入。手順 4-3 を `pip install -e ".[images]"` で入れ直す（コア import でも必須） |
| `No module named 'spec2model'` | 手順 4-3 の `-e .`（editable install）を未実施。venv の場所が `tools\spec2model\.venv` か確認 |
| `No module named 'pdf2image'` / `'pptx'` 等 | `requirements.txt` だけで済ませている。`pip install -e ".[images]"` で全依存を入れ直す |

---

## 6. システム要件（PDF / PowerPoint画像化を使う場合のみ）

Excel / Word の差分だけなら不要です。PDF を扱う、または PowerPoint のスライド全体画像化を使う場合のみ、以下が必要です。

- **Poppler（`pdf2image` が使用）**
  [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) からバイナリを入手し、`bin` フォルダを環境変数 `PATH` に追加。
- **LibreOffice（PowerPointスライド画像化）**
  [LibreOffice 公式](https://www.libreoffice.org/download/download/) からインストール。

> PowerPoint 画像化を無効化する場合は、設定 YAML で `pptx.whole_slide_image.enabled: false` に設定します。
> 詳細は `tools/spec2model/README.md`（「システム要件のインストール」）を参照。

---

## 7. 使い方の入口

導入後、CWD=`<CLAUDE_DIR>` で各 skill のコマンドを実行します。

> **（Windows）差分実行の前に、手順 4-4 手順2 の環境変数（`PATH` / `CAIROCFFI_DLL_DIRECTORIES` への `tools\spec2model\.venv\cairo_dll` 追加）を、その PowerShell セッションで設定しておくこと**（未設定だと `cairo-2` エラーになります）。

- 2 件のローカル文書の差分:
  ```powershell
  tools\spec2model\.venv\Scripts\python.exe tools\spec2model\scripts\diff_documents.py `
    "<old-file>" "<new-file>" `
    --out-csv "data\output_data\local_diff.csv" `
    --out-html "data\output_data\local_diff.html"
  ```
- ローカル + クラウド（KGA）の差分は `spec2model-cloud-diff\SKILL.md` を参照。

---

## 8. トラブルシュート

| 症状 | 原因 / 対処 |
|---|---|
| `no library called "cairo-2"` / `libcairo-2.dll` / `error 0x7e` | **ネイティブ Cairo DLL 不足**（`pip` では入らない）。手順 4-4 の `fetch_cairo_dll.py` で DLL を取得し、`PATH` と `CAIROCFFI_DLL_DIRECTORIES` に `tools\spec2model\.venv\cairo_dll` を追加してから再実行（設定は PowerShell セッションごと）。`error 0x7e` は依存 DLL 不足を示すが、本スクリプトは依存 DLL 一式（freetype/ffi 等）も取得する |
| `No module named 'spec2model'` | 手順 4-3 の `pip install -e ".[images]"` を実施していない。venv の場所が `tools\spec2model\.venv` か確認 |
| `No module named 'cairosvg'` | images extra 未導入。`pip install -e ".[images]"` で入れ直す（コア import でも必須） |
| `No module named 'pdf2image'` 等の依存不足 | `requirements.txt` だけで済ませている。`pip install -e .` で全依存を入れ直す |
| PDF 変換で失敗 / 画像が出ない | Poppler / LibreOffice 未導入（手順 6） |
| `python` が見つからない | Python 未インストール、または PATH 未設定。`py --version` も試す |
| 相対パスが見つからない | CWD が `<CLAUDE_DIR>` になっていない。`Set-Location $claude` を実行 |

---

## チェックリスト（各メンバー）

- [ ] Python 3.10〜3.13 がある
- [ ] 自分の `.claude`（`<CLAUDE_DIR>`）の場所を把握し、`$claude` に設定した
- [ ] `<CLAUDE_DIR>\skills` に 2 つの skill を配置した（手順 2）
- [ ] `<CLAUDE_DIR>\tools\spec2model` に spec2model を配置した（手順 3）
- [ ] `tools\spec2model\.venv` を作成した（手順 4）
- [ ] `pip install -e ".[images]"` で本体＋依存（images extra 含む）を入れた（手順 4-3）
- [ ] （Windows）`fetch_cairo_dll.py` で Cairo DLL を取得し、`PATH`／`CAIROCFFI_DLL_DIRECTORIES` に `tools\spec2model\.venv\cairo_dll` を追加した（手順 4-4／import 検証 `[OK]` で確認）
- [ ] import 検証が `[OK]`（手順 5）
- [ ] （必要時）Poppler / LibreOffice を導入した（手順 6）
