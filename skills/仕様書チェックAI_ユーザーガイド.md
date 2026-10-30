# 仕様書チェックAI ユーザーガイド

- 最終更新：2026-08-07

本書は、仕様書チェックAIの**概要**と**使い方（前提・準備・入力プロンプト例）** を、利用者向けにまとめた説明書である。
内部構成（各 SKILL の役割・仕様書チェックAIの処理フロー・スクリプト仕様など）は、開発者向けドキュメント [仕様書チェックAI_開発者向けガイド.md](仕様書チェックAI_開発者向けガイド.md) を参照すること。

---

## 目次

- [仕様書チェックAI ユーザーガイド](#仕様書チェックai-ユーザーガイド)
  - [目次](#目次)
  - [1. 仕様書チェックAIの概要](#1-仕様書チェックaiの概要)
  - [2. 仕様書チェックAIの設定](#2-仕様書チェックaiの設定)
    - [2.1 前提](#21-前提)
    - [2.2 必要資料の配置とディレクトリ構成](#22-必要資料の配置とディレクトリ構成)
    - [2.3 初回セットアップ（spec2model 差分スキルの導入）](#23-初回セットアップspec2model-差分スキルの導入)
  - [3. 仕様書チェックAIの使い方](#3-仕様書チェックaiの使い方)
    - [3.1 前準備（入力の準備）](#31-前準備入力の準備)
    - [3.2 入力プロンプト例](#32-入力プロンプト例)
      - [【暫定対応】変更前仕様書もローカルに配置して比較する場合](#暫定対応変更前仕様書もローカルに配置して比較する場合)
      - [【参考】影響範囲確認先の仕様書カテゴリを限定する場合](#参考影響範囲確認先の仕様書カテゴリを限定する場合)
    - [3.3 出力](#33-出力)

---

## 1. 仕様書チェックAIの概要
仕様書チェックAIは、客先からDR依頼のあった **正式発効前のメータ仕様書(標準制御仕様書、標準GFX仕様書)** について、あらかじめ定義されたチェック項目（CHK-*）に従い、**内容の不備・不足や他仕様書への影響**を確認し、問題を検出してレポートするAIエージェントである。

- 分析対象は、ナレッジグラフエージェント（KGA）に格納された仕様書群(tagに登録されている各仕様書の最新Ver.)と、ユーザーが与えるチェック対象仕様書(正式発効前の仕様書)である。
- チェックは「仕様書の変更前後の**差分**」を単位に行い、各差分に対して適用すべきチェック項目を選定 → チェック項目毎に問題有無を判定 → 結果を集約してレポート（Markdown＋Excel）を出力する。

---

## 2. 仕様書チェックAIの設定

仕様書チェックAIを実行するための **前提** と、**環境構築（必要資料の配置・初回セットアップ）** を示す。

### 2.1 前提

- **Claude Code** および **KGA（ナレッジグラフエージェント）** を使用できること。
  - Claude Code の導入方法は [こちらのページ](https://aip01.dndev.net/wiki/pages/viewpage.action?pageId=359201832) を参照すること。
  - KGAの導入については、DN担当(吉田M)に問い合わせください。

### 2.2 必要資料の配置とディレクトリ構成

仕様書チェックAIを利用するには、利用者が **配布された一式を配置し、以下の構成になるように作業ディレクトリ（`.claude/`）を整える** 必要がある。**`data/` と `specification_check/output/` 配下（いずれも実行時に自動生成）を除き、基本的に以下のすべてを利用者が配置する。**

利用者が配置するもの：

- **配布物一式**：`CLAUDE.md` / `settings.json` / 各ガイド（開発者・ユーザー）/ `SETUP.md` / すべての skill（`general-rule` / `meter-spec-common` / `speccheck-workflow` / `spec2model-cloud-diff` / `spec2model-local-diff` / `spec2model-to-markdown`）/ 差分生成エンジン `tools/spec2model` 一式 を、それぞれ所定の位置（下記ツリー参照）へ配置する。
  - うち **差分スキル**（`spec2model-cloud-diff` / `spec2model-local-diff`）・**md変換スキル**（`spec2model-to-markdown`）と **差分生成エンジン**（`tools/spec2model`）は、配置後に初回セットアップ（Python 仮想環境の構築等）が必要（いずれも `tools/spec2model/.venv` を共用。「2.3 初回セットアップ」を参照）。
- **チェック対象仕様書**（本体・Appendix。DMSも含む）：`specification_check/check_spec/<仕様書名>/` へ配置する（チェック実行のたびに用意）。**md変換版（.md）は利用者が用意する必要はない**（Step1がAIで自動生成し同フォルダへ格納）。詳細は「3.1 前準備（入力の準備）」を参照。


> 以下は暫定対応ではあるが、担当者から指示があるまでは本対応を適用すること。
- **【暫定対応】チェック対象仕様書の前Ver.**（本体・Appendix。DMSも含む:`specification_check/check_spec/<チェック対象仕様書の前Ver.名>/` へ配置する（チェック実行のたびに用意）。通常、変更前仕様書は KGA（クラウド）に登録された最新Ver. を用いて差分を取得するが、ローカルに配置した前Ver. と比較したい場合は暫定対応として配置する（この場合、差分取得には `spec2model-local-diff` を使用する。詳細は「3.2 入力プロンプト例」を参照）。

> `data/` および `specification_check/output/` 配下は実行時に自動生成されるため、利用者が用意する必要はない（それ以外は利用者が配置する）。

```text
.claude/                             ← ルート（作業ディレクトリ）
│
├── CLAUDE.md                        ← システムプロンプト（スキル読み込み順などを規定）
├── settings.json                    ← ハーネス設定（allow権限・環境変数・フック等）
│
├── data/
│   ├── cloud/                       KGAからエクスポートした変更前仕様書の構造化JSON（spec2model-cloud-diff が比較に使用）※実行時生成
│   └── output_data/                 差分生成スキル（spec2model-*-diff）を単体実行した場合の既定出力先（差分CSV／HTML）※実行時生成／仕様書チェック実行時は使用せず specification_check/output/ へ固定出力
│
├── specification_check/             ← 仕様書チェックの入出力データ
│   ├── check_spec/                  入力: チェック対象仕様書（<仕様書名>/ 配下に本体 .xlsm/.docx・Appendix・DMSを配置。md変換版 .md はStep1がAI自動生成し同フォルダへ格納）
│   └── output/                      出力: 仕様書チェック実行時の差分生成スキル（spec2model-*-diff）の出力（差分CSV／HTML）・差分JSON・レコード分割・チェック結果・レポート(.md/.xlsx)
│
├── tools/
│   └── spec2model/                  ← 差分生成スキル（spec2model-*-diff）が `scripts/diff_documents.py` を通じて利用するスクリプト
└── skills/                          ← 各SKILL
    ├── 仕様書チェックAI_開発者向けガイド.md  ← 開発者向けガイド（SKILLS概要／内部構成）
    ├── 仕様書チェックAI_ユーザーガイド.md    ← 本書（ユーザー向け・概要／使い方）
    ├── SETUP.md    ← ユーザー向け(`spec2model-local-diff` / `spec2model-cloud-diff`のスキルを使用するための初回セットアップ方法)
    │
    ├── general-rule/                ← 基本ルール
    │   └── SKILL.md
    │
    ├── meter-spec-common/         ← 種類判定・読み方ガイド
    │   ├── SKILL.md
    │   └── reference/
    │       ├── concepts-spec-common-rules.md      （全種類共通: 仕様書共通ルール）
    │       ├── concepts-spec-glossary.md          （全種類共通: 仕様書専門用語）
    │       ├── guide-graphic-spec.md              （MET-G系仕様書）
    │       ├── guide-list-spec.md                 （一覧系仕様書）
    │       ├── guide-comspec.md                   （通信仕様書）
    │       ├── guide-oldformat.md                 （旧フォーマット仕様書）
    │       ├── guide-newformat-sheetsection.md    （新フォーマット: シート章節間の読み方）
    │       ├── guide-newformat-item.md            （新フォーマット: 項目毎の読み方）
    │       └── guide-newformat-invalid.md         （新フォーマット: 無効情報一覧）
    │
    ├── speccheck-workflow/         ← チェック本体（Step1〜4）
    │   ├── SKILL.md
    │   ├── steps/                       手順（各Stepの詳細・選定条件）
    │   │   ├── step1_prep_checkdata.md
    │   │   ├── step2_labeling.md
    │   │   ├── step3_check.md
    │   │   ├── step4_report.md
    │   │   ├── std_ctrl_check_selection.md   （標準制御仕様書のCHK選定条件）
    │   │   └── metg_check_selection.md        （標準GFX仕様書のCHK選定条件）
    │   ├── templates/                   サブエージェント指示・レポート様式
    │   │   ├── labeling_subagent_prompt.md
    │   │   ├── subagent_prompt.md
    │   │   └── report_format.md
    │   ├── scripts/                     変換・集約スクリプト（Python）
    │   │   ├── csv_to_diff_json.py
    │   │   ├── newformat_md_to_newspec_json.py
    │   │   ├── oldformat_md_to_newspec_json.py
    │   │   ├── mark_invalid_items.py
    │   │   ├── checkno_split_merge.py
    │   │   ├── merge_results_to_report.py
    │   │   ├── report_md_to_xlsx.py
    │   │   └── README.md                （各スクリプトの実行方法・仕様補足）
    │   ├── check/                       標準制御仕様書用チェック項目（CHK-*.md）
    │   ├── MET-G_check/                 標準GFX仕様書用チェック項目（CHK-*.md）
    │   └── .gitignore                   （生成物・キャッシュを Git 管理対象外に指定）
    │
    ├── spec2model-cloud-diff/       ← 差分生成（ローカル×クラウド）
    │   ├── SKILL.md
    │   ├── README.md                    （スキル概要・ユースケース）
    │   └── scripts/
    │       ├── diff_local_with_cloud_json.py   （ローカル×クラウドJSON 差分本体）
    │       ├── save_cloud_export_json.py       （KGAエクスポート応答をローカルJSONへ保存）
    │       ├── fetch_cairo_dll.py              （Windows: Cairo DLL 取得スクリプト）
    │       └── image_diff.py                   （画像差分の補助モジュール）
    │
    ├── spec2model-local-diff/       ← 差分生成（ローカル×ローカル）
    │   ├── SKILL.md
    │   ├── README.md                    （スキル概要・ユースケース）
    │   └── scripts/diff_local_images.py     （ローカル×ローカルの画像差分）
    │
    └── spec2model-to-markdown/      ← md変換（変更後仕様書のローカルoffice文書→md）
        ├── SKILL.md
        ├── README.md                    （スキル概要・ユースケース）
        └── scripts/export_to_markdown.py
```

### 2.3 初回セットアップ（spec2model 差分スキルの導入）

差分生成（変更前後の仕様書比較）を担う `spec2model-cloud-diff` / `spec2model-local-diff` を使用するには、事前に差分生成エンジン `spec2model` 一式を `tools/spec2model/` 配下へ配置し、各自の環境で初回セットアップ（Python 仮想環境の構築＋インストール）を行う必要がある。Python 仮想環境（`.venv`）はコミット・共有できないため、**全メンバーが各自の PC で実施必須**である（初回のみ）。

**要点（詳細な手順・PowerShell コマンドは [SETUP.md](SETUP.md) を参照）：**

1. 差分スキル（`spec2model-cloud-diff` / `spec2model-local-diff`）を `skills/` 配下に配置する。
2. `spec2model` 一式を `tools/spec2model/` 配下に配置する（skill が `scripts/diff_documents.py` などソースツリーを直接参照するため）。
3. `tools/spec2model/.venv` に Python 仮想環境を作成し、`pip install -e ".[images]"` で本体＋全依存を導入する。
4. **（Windows）ネイティブ Cairo DLL を用意する。** `spec2model` は `cairosvg`→`cairocffi` を通じてネイティブ `libcairo-2.dll` を要求するが、これは `pip` では導入されない。付属の取得スクリプト `fetch_cairo_dll.py`（`skills/spec2model-cloud-diff/scripts/`）を実行し、conda-forge から Cairo とその依存 DLL 一式をダウンロードして `tools/spec2model/.venv/cairo_dll` へ配置する（SETUP.md 手順4-4）。実行時は当該フォルダを `PATH` と環境変数 `CAIROCFFI_DLL_DIRECTORIES` に追加する（詳細コマンドは SETUP.md 参照）。**この取得は外部（conda-forge）へのダウンロードを伴うため、ネットワーク／プロキシに接続できる環境で実施する（初回のみ）。** 未取得だと手順5の import 検証が `cairo-2` エラーで失敗する。
5. import 検証（SETUP.md 手順5）が `[OK]` になれば完了。
6. （PDF / PowerPoint 画像化、または Excel/Word 内の EMF/WMF 画像差分を使う場合のみ）Poppler / LibreOffice を別途導入する。

**補足：Claude Code にセットアップを実行させることも可能。** `.venv` の作成 → `pip install -e ".[images]"` → 手順4（Cairo DLL の取得：`fetch_cairo_dll.py` の実行）→ import 検証 は、`SETUP.md` を参照させて Claude Code に実行させてもよい。ただし、**Python の導入・手順1・2 のファイル配置は、Claude Code では実施できないため事前に人手で済ませておくこと**。
入力プロンプト例：

```text
SETUP.mdに即してvenvを作成し、spec2modelを使用できるように環境を整えてください。
```

> **更新時の `.venv` の扱い**：`.venv` の作成は初回のみでよい。`spec2model` 更新時は **`.venv` を残したまま中身（ソース・config 等）を更新する** 運用とし、venv の再作成は原則不要（editable install（`pip install -e .`）のためソースコード変更は自動反映される）。依存パッケージ（`pyproject.toml` / `requirements.txt`）が変わった場合のみ、既存 venv で `pip install -e .` を再実行する。
>
> `spec2model` のバージョン更新・差し替え時の追従作業（bitbucket 登録者向け）は、開発者向けドキュメント [仕様書チェックAI_開発者向けガイド.md](仕様書チェックAI_開発者向けガイド.md) の「spec2model 更新時の処置」を参照。

---

## 3. 仕様書チェックAIの使い方
仕様書チェックの入力準備から実行・出力までを示す（前提・環境構築は「2. 仕様書チェックAIの設定」を参照）。

### 3.1 前準備（入力の準備）
1. **チェック対象仕様書の格納**
   - `specification_check/check_spec/<仕様書名>/` 配下に、チェック対象仕様書（発行前仕様書。`.xlsm` / `.docx` 等の原本。本体に加え、AppendixやDMSも格納する。）を配置する。
   - **旧バイナリの `.doc` / `.xls` は格納しない**。標準環境では解析に失敗するため、Word / Excel の「名前を付けて保存」等で事前に `.docx` / `.xlsx` へ変換し、変換後のみを配置すること（変更前・変更後の双方）。`.xlsx` / `.xlsm` / `.docx` / `.pptx` はそのまま配置してよい。
2. **プロンプトの入力**
   - 仕様書チェックAIフォルダ配下の `.claude`（例: `C:\Users\<ユーザー名>\仕様書チェックAI\.claude`）をワークスペースとして VSCode で開く。
   - Claude Code のチャット欄に、変更前仕様書と変更後仕様書のファイル名を次節の例の形式で記載してプロンプトを入力する。

### 3.2 入力プロンプト例

```text
以下の仕様書チェックを実施してください。

[変更前仕様書]
MET-H_SOHDSP-CSTD-0-06-Z-C0.xlsm
MET-H_SOHDSP-CSTD-0-06-Z-C0_Appendix.docx

[変更後仕様書]
MET-H_SOHDSP-CSTD-0-07-A-C0.xlsm
MET-H_SOHDSP-CSTD-0-07-A-C0_Appendix.docx
```
> チェック対象仕様書にDMSファイルが添付されている場合、[変更後仕様書]にはDMSファイル名は記載不要である。

#### 【暫定対応】変更前仕様書もローカルに配置して比較する場合
> 担当者から指示があるまでは、本暫定対応を適用すること。
通常、変更前仕様書は KGA（クラウド）の最新Ver. を用いて差分を取得するが、ローカルに配置した前Ver.（「2.2」参照）と比較したい場合は、変更前・変更後仕様書がともにローカル（`specification_check/check_spec` 配下）に格納済みである旨と、`spec2model-local-diff` で差分を取得する指示を明記する。

```text
以下の仕様書チェックを実施してください。
変更前仕様書と変更後仕様書はともに
\.claude\specification_check\check_spec に格納済みであるため、spec2model-local-diff/ で差分を取得すること。

[変更前仕様書]
MET-H_SOHDSP-CSTD-0-06-Z-C0.xlsm
MET-H_SOHDSP-CSTD-0-06-Z-C0_Appendix.docx

[変更後仕様書]
MET-H_SOHDSP-CSTD-0-07-A-C0.xlsm
MET-H_SOHDSP-CSTD-0-07-A-C0_Appendix.docx
```

#### 【参考】影響範囲確認先の仕様書カテゴリを限定する場合

精度検証等で、MCP（`graph_*`）による影響範囲確認先（別仕様書）の探索対象を特定のカテゴリに絞りたい場合は、以下のようにカテゴリを限定する指示を冒頭に加えるとよい。（`「***(カテゴリ名)」` は実際のカテゴリ名に置き換えること）。

```text
以下の仕様書について仕様書チェックを実施してください。
但し、今回の仕様書チェックでは、MCP（graph_*）で別仕様書を探索する際、対象をカテゴリ「***(カテゴリ名)」に限定すること。この制約は各チェックのサブエージェントプロンプトにも必ず引き継ぐこと。

また、変更前仕様書と変更後仕様書はともに
\.claude\specification_check\check_specに格納済みであるため、spec2model-local-diff/で差分を取得すること。

[変更前仕様書]
MET-H_SOHDSP-CSTD-0-06-Z-C0.xlsm
MET-H_SOHDSP-CSTD-0-06-Z-C0_Appendix.docx

[変更後仕様書]
MET-H_SOHDSP-CSTD-0-07-A-C0.xlsm
MET-H_SOHDSP-CSTD-0-07-A-C0_Appendix.docx
```

### 3.3 出力
- チェック結果は `specification_check/output/` 配下に出力される。
- 最終レポートは **Markdown（`.md`）と Excel（`.xlsx`）** の2形式で生成され、各チェック項目について **問題あり／なし／要確認** の判定が確認できる。
