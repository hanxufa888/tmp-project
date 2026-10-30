---
name: meter-spec-common
description: "仕様書の種類の判断方法と仕様書の読み方ガイドです。仕様書分析を実施する場合は必ず利用して下さい。"
---

# 仕様書の種類の判断方法と仕様書の読み方

## 仕様書の種類の判断方法
- 以下の"仕様書の判断フロー"に従い、分析対象仕様書の種類を特定すること。
- 仕様書ファイル毎に仕様書の種類を特定すること。

```plantuml
@startuml
start
title 仕様書の判断フロー

  :仕様書内のファイル名を確認;
  if (以下の形式のファイルか？\n^MET-G_.*) then (Yes)
    :MET-G系仕様書;
    stop

  else (No)
    ' 新フォーマット判定
    if (以下の形式のファイルか？\n^MET-[A-Z]_[A-Z0-9]+-(CSTD|ORG)-[A-Z0-9]{1,2}-\d{2}-[A-Z]-C\d{1,2}(_ja|_en)?\.xlsm) then (Yes)
      :新フォーマット仕様書;
      stop

    else (No)
      '一覧系仕様書(CONTDISP/CONTBUZZのようなバリを持たない仕様書)の判定
      if (以下の形式のファイルか？\n^MET-M_[A-Z0-9]+-(CSTD|ORG)-\d{4}-C\d{1,2}) then (Yes)
        :個別仕様書;
        stop

      else (No)
        'バリを持たない仕様書以外の一覧系仕様書の判定
        if (以下のキーワードを含むファイルか？\n"MCUCONST" or "CONSTSORT" or "REMWAR") then (Yes)
          :個別仕様書;
          stop
        else (No)
          '通信仕様書(DMS)の判定
          if (以下のキーワードを含むファイルか？\n"DMS") then (Yes)
            :通信仕様書;
            stop
          'それ以外は旧フォーマットへ
          else (No)
            :旧フォーマット仕様書;
            stop
          endif
        endif

      endif
    endif

  endif

@enduml
```
## 仕様書の読み方referenceの参照方法
- 仕様書の種類の判断結果に応じ、仕様書分析に必要な仕様書の読み方のreferenceを参照すること。
  参照するreferenceは下表に従い選択すること。
  | 仕様書種類 | 参照reference |
  |---|---|
  | 全種類の仕様書 | [reference/concepts-spec-common-rules.md](reference/concepts-spec-common-rules.md)<br>[reference/concepts-spec-glossary.md](reference/concepts-spec-glossary.md) |
  | MET-G系仕様書 | [reference/guide-graphic-spec.md](reference/guide-graphic-spec.md) |
  | 新フォーマット仕様書 | [reference/guide-newformat-sheetsection.md](reference/guide-newformat-sheetsection.md)<br>[reference/guide-newformat-item.md](reference/guide-newformat-item.md)<br>[reference/guide-newformat-invalid.md](reference/guide-newformat-invalid.md) |
  | 個別仕様書 | [reference/guide-list-spec.md](reference/guide-list-spec.md) |
  | 通信仕様書 | [reference/guide-comspec.md](reference/guide-comspec.md) |
  | 旧フォーマット仕様書 | [reference/guide-oldformat.md](reference/guide-oldformat.md) |
