# TT, Detailed Specシートを含むファイルの文書内関係:
ファイル内の要件は下記依存関係にある。
TTまたはDetailed Specのシートの内容を解釈する場合は、下記依存関係に基づき関連情報の取得と解釈を行うこと。

```plantuml
@startuml
class TT
    package "2.テルテール(以下TT，インジケータと同義)" as 2 {
        package "2-<I>N</I>-1.シンボル" as 2n1 {
            class "シンボル" as symbol {
                + 要求ID
                + シンボル
                + 色
                + MID有り時のTT設定要否
                + 左記の設定必要な理由
            }
        }
        package "2-<I>N</I>-2.TT要求" as 2n2 {
            class "TT要求" as tt {
                + 要求ID
                + No.
                + 要求廃止
                + TT表示状態
                + 点滅周期（msec）
                + TT表示を行う電源状態[IGR/P（IG1/2）]
                + TT表示を行う電源状態[+B, ACC, special]
                + 実施条件
                + 他:特別条件
                + 機能有無判定
                + 表示機能機能安全（ASIL）
            }
        }
        package "2-<I>N</I>-3.通信仕様　(TT分）" as 2n3 {
            class "TT通信仕様" as tt_sig {
                + 要求ID
                + No.
                + In/Out
                + データラベル名
                + 通信周期（msec）
                + 送信DMS　Ver
                + メッセージラベル
                + メータにセットする初期値
                + 通信途絶判定後にセットする値[IGR-ON中（IG2-ON中）]
                + 通信途絶判定後にセットする値[IGR-OFF中（IG2-OFF中）]
                + 途絶判定時間（msec）
                + 最大通信遅延許容時間（msec）
            }
        }
        package "2-<I>N</I>-4.ジカ線仕様　(TT分，表示電源状態，CAN入出力以外）" as 2n4 {
            class "TTジカ線仕様" as tt_line {
                + 要求ID
                + No.
                + In/Out
                + 信号名
                + 記号
                + 信号状態の説明
                + サンプリングする電源状態[IGR/P（IG1/2）]
                + サンプリングする電源状態[+B, ACC, special]
                + サンプリング条件
                + 入力確定時間（msec）
            }
        }
    }
    package "2-A.メンテナンス・点検　警告灯" as 2a {
        package "2-A-1.シンボル" as 2a1 {
            class "シンボル" as 2a_symbol {
                + 要求ID
                + シンボル
                + 色
            }
        }
        package "2-A-2.TT要求" as 2a2 {
            class "TT要求" as 2a_tt {
                + 要求ID
                + No.
                + 要求廃止
                + TT表示状態
                + 点滅周期（msec）
                + TT表示を行う電源状態[IGR/P（IG1/2）]
                + TT表示を行う電源状態[+B, ACC, special]
                + 実施条件
                + 他:特別条件
                + 機能有無判定
                + 表示機能機能安全（ASIL）
            }
        }
        package "2-A-3.通信仕様　(TT分）" as 2a3 {
            class "TT通信仕様" as 2a_tt_sig {
                + 要求ID
                + No.
                + In/Out
                + データラベル名
                + 通信周期（msec）
                + 送信DMS　Ver
                + メッセージラベル
                + メータにセットする初期値
                + 通信途絶判定後にセットする値[IGR-ON中（IG2-ON中）]
                + 通信途絶判定後にセットする値[IGR-OFF中（IG2-OFF中）]
                + 途絶判定時間（msec）
                + 最大通信遅延許容時間（msec）
            }
        }
        package "2-A-4.ジカ線仕様　(TT分，表示電源状態，CAN入出力以外）" as 2a4 {
            class "TTジカ線仕様" as 2a_tt_line {
                + 要求ID
                + No.
                + In/Out
                + 信号名
                + 記号
                + 信号状態の説明
                + サンプリングする電源状態[IGR/P（IG1/2）]
                + サンプリングする電源状態[+B, ACC, special]
                + サンプリング条件
                + 入力確定時間（msec）
            }
        }
    }
    package "2-B.停車警告灯" as 2b {
        package "2-B-1.シンボル" as 2b1 {
            class "シンボル" as 2b_symbol {
                + 要求ID
                + シンボル
                + 色
            }
        }
        package "2-B-2.TT要求" as 2b2 {
            class "TT要求" as 2b_tt {
                + 要求ID
                + No.
                + 要求廃止
                + TT表示状態
                + 点滅周期（msec）
                + TT表示を行う電源状態[IGR/P（IG1/2）]
                + TT表示を行う電源状態[+B, ACC, special]
                + 実施条件
                + 他:特別条件
                + 機能有無判定
                + 表示機能機能安全（ASIL）
            }
        }
        package "2-B-3.通信仕様　(TT分）" as 2b3 {
            class "TT通信仕様" as 2b_tt_sig {
                + 要求ID
                + No.
                + In/Out
                + データラベル名
                + 通信周期（msec）
                + 送信DMS　Ver
                + メッセージラベル
                + メータにセットする初期値
                + 通信途絶判定後にセットする値[IGR-ON中（IG2-ON中）]
                + 通信途絶判定後にセットする値[IGR-OFF中（IG2-OFF中）]
                + 途絶判定時間（msec）
                + 最大通信遅延許容時間（msec）
            }
        }
        package "2-B-4.ジカ線仕様　(TT分，表示電源状態，CAN入出力以外）" as 2b4 {
            class "TTジカ線仕様" as 2b_tt_line {
                + 要求ID
                + No.
                + In/Out
                + 信号名
                + 記号
                + 信号状態の説明
                + サンプリングする電源状態[IGR/P（IG1/2）]
                + サンプリングする電源状態[+B, ACC, special]
                + サンプリング条件
                + 入力確定時間（msec）
            }
        }
    }

Document *-- TT
TT "1" *-- "0..*" symbol
TT "1" *-- "0..1" 2a_symbol
TT "1" *-- "0..1" 2b_symbol
symbol "1" *-- "2..*" tt
2a_symbol "1" *-- "2..*" 2a_tt
2b_symbol "1" *-- "2..*" 2b_tt
tt "1" *-- "0..*" tt_sig: 実施条件
2a_tt "1" *-- "0..*" 2a_tt_sig: 実施条件
2b_tt "1" *-- "0..*" 2b_tt_sig: 実施条件
tt "1" *-- "0..*" tt_line: 実施条件
2a_tt "1" *-- "0..*" 2a_tt_line: 実施条件
2b_tt "1" *-- "0..*" 2b_tt_line: 実施条件

class "Detailed Spec" as dtel
package "8.TT表示の特別処理指示" as 8 {
    class "8-<I>N</I>.TT表示" as 8-N
    class "TT表示の特別処理要求" as ttdetl {
        + 要求ID
        + No
        + 仕様
        + 標準処理
        + 特別処理
    }
    class "8-A.TT表示 (メンテナンス・点検　警告灯)" as 8-A
    class "TT表示の特別処理要求" as ttdetl_A {
        + 要求ID
        + No
        + 仕様
        + 標準処理
        + 特別処理
    }
    class "8-B.TT表示 (停車警告灯)" as 8-B
    class "TT表示の特別処理要求" as ttdetl_B {
        + 要求ID
        + No
        + 仕様
        + 標準処理
        + 特別処理
    }
}

Document *-- dtel
dtel "1" *-- "0..*" "8-N": TT N個
"8-N" "1" *-- "11" ttdetl
dtel "1" *-- "0..1" "8-A": TT (メンテナンス・点検　警告灯)
"8-A" "1" *-- "8" ttdetl_A
dtel "1" *-- "0..1" "8-B": TT (停車警告灯)
"8-B" "1" *-- "8" ttdetl_B

2n2 -- "8-N": 他:特別条件
2a2 -- "8-A": 他:特別条件
2b2 -- "8-B": 他:特別条件

note as detailedrelation1 
通信仕様に定義されるCAN信号のルール  
# 「2-N-3」に定義されるCAN信号は、「2-N-2」に記載されている信号と「8-N」の"特別処理"欄に記載されている信号全てとなる。  
# 「2-A-3」に定義されるCAN信号は、「2-A-2」に記載されている信号と「8-A」の"特別処理"欄に記載されている信号全てとなる。  
# 「2-B-3」に定義されるCAN信号は、「2-B-2」に記載されている信号と「8-B」の"特別処理"欄に記載されている信号全てとなる。
end note  
2n2 .. detailedrelation1  
2a2 .. detailedrelation1  
2b2 .. detailedrelation1
2n3 .. detailedrelation1  
2a3 .. detailedrelation1  
2b3 .. detailedrelation1  
"8" .. detailedrelation1

note as detailedrelation2 
ジカ仕様に定義されるジカ信号のルール  
# 「2-N-4」に定義されるジカ信号は、「2-N-2」に記載されている信号と「8-N」の"特別処理"欄に記載されている信号全てとなる。 
# 「2-A-4」に定義されるジカ信号は、「2-A-2」に記載されている信号と「8-A」の"特別処理"欄に記載されている信号全てとなる。 
# 「2-B-4」に定義されるジカ信号は、「2-B-2」に記載されている信号と「8-B」の"特別処理"欄に記載されている信号全てとなる。
end note 
2n2 .. detailedrelation2 
2a2 .. detailedrelation2  
2b2 .. detailedrelation2
2n4 .. detailedrelation2  
2a4 .. detailedrelation2  
2b4 .. detailedrelation2  
"8" .. detailedrelation2

@enduml
```

### BZR, Detailed Specシートを含むファイルの文書内関係:
ファイル内の要件は下記依存関係にある。
BZRまたはDetailed Specのシートの内容を解釈する場合は、下記依存関係に基づき関連情報の取得と解釈を行うこと。

```plantuml
@startuml
class BZR
    package "3.ブザー(以下BZR)" as 3 {
        package "3-1.ブザー(BZR)要求" as 31 {
            class "BZR要求" as bzr {
                + 要求ID
                + No.
                + 要求廃止
                + BZR吹鳴状態
                + ブザー音周波数(Hz)
                + 断続吹鳴周期(sec)
                + ブザー吹鳴を行う電源状態[IGR/P（IG1/2）]
                + ブザー吹鳴を行う電源状態[+B, ACC, special]
                + 実施条件
                + 他:特別条件
                + 情報種類
                + 優先度(優先吹鳴決定用)
                + BZR吹鳴機能安全（ASIL）
            }
        }
        package "3-2.通信仕様　(BZR分）" as 32 {
            class "BZR通信仕様" as bzr_sig {
                + 要求ID
                + No.
                + In/Out
                + データラベル名
                + 通信周期（msec）
                + 送信DMS　Ver
                + メッセージラベル
                + メータにセットする初期値
                + 通信途絶判定後にセットする値[IGR-ON中（IG2-ON中）]
                + 通信途絶判定後にセットする値[IGR-OFF中（IG2-OFF中）]
                + 途絶判定時間（msec）
                + 最大通信遅延許容時間（msec）
            }
        }
        package "3-3.ジカ線仕様　(BZR分，表示電源状態，CAN入出力以外）" as 33 {
            class "BZRジカ線仕様" as bzr_line {
                + 要求ID
                + No.
                + In/Out
                + 信号名
                + 記号
                + 信号状態の説明
                + サンプリングする電源状態[IGR/P（IG1/2）]
                + サンプリングする電源状態[+B, ACC, special]
                + サンプリング条件
                + 入力確定時間（msec）
            }
        }
    }

Document *-- BZR
BZR "1" *-- "0..*" bzr
bzr "1" *-- "0..*" bzr_sig: 実施条件
bzr "1" *-- "0..*" bzr_line: 実施条件

class "Detailed Spec" as dtel
package "9.ブザー吹鳴の特別処理指示" as 9 {
    class "9.ブザー吹鳴" as 9-1
    class "BZR表示の特別処理要求" as bzrdetl {
        + 要求ID
        + No
        + 仕様
        + 標準処理
        + 特別処理
    }
}

Document *-- dtel
dtel "1" *-- "0..1" "9-1"
"9-1" "1" *-- "10" bzrdetl

31 -- "9-1": 他:特別条件

note as detailedrelation1 
通信仕様に定義されるCAN信号のルール  
# 「3-2」に定義されるCAN信号は、「3-1」に記載されている信号と「9」の"特別処理"欄に記載されている信号全てとなる。  
end note  
31 .. detailedrelation1  
32 .. detailedrelation1   
"9" .. detailedrelation1

note as detailedrelation2 
ジカ仕様に定義されるジカ信号のルール  
# 「3-3」に定義されるジカ信号は、「3-1」に記載されている信号と「9」の"特別処理"欄に記載されている信号全てとなる。 
end note 
31 .. detailedrelation2 
33 .. detailedrelation2   
"9" .. detailedrelation2

@enduml
```

### MID, Detailed Specシートを含むファイルの文書内関係:
ファイル内の要件は下記依存関係にある。
MIDまたはDetailed Specのシートの内容を解釈する場合は、下記依存関係に基づき関連情報の取得と解釈を行うこと。

```plantuml
@startuml
class MID
    package "4.割込み固定表示(以下固定MID)" as 4 {
        package "4-1.割込み固定表示(固定MID)　要求" as 41 {
            class "MID要求" as mid {
                + 要求ID
                + No.
                + 要求廃止
                + 固定MID表示[日本語]
                + 固定MID表示[英語]
                + 固定MID表示を行う電源状態[IGR/P（IG1/2）]
                + 固定MID表示を行う電源状態[+B, ACC, special]
                + 実施条件
                + 他:特別条件
                + 情報種類
                + 優先度(優先表示決定用)
                + 機能有無判定
                + M/Cランプ連動 点灯・点滅
                + M/Cブザー有無
                + 表示機能機能安全（ASIL）
            }
        }
        package "4-2.通信仕様　(固定MID分）" as 42 {
            class "MID通信仕様" as mid_sig {
                + 要求ID
                + No.
                + In/Out
                + データラベル名
                + 通信周期（msec）
                + 送信DMS　Ver
                + メッセージラベル
                + メータにセットする初期値
                + 通信途絶判定後にセットする値[IGR-ON中（IG2-ON中）]
                + 通信途絶判定後にセットする値[IGR-OFF中（IG2-OFF中）]
                + 途絶判定時間（msec）
                + 最大通信遅延許容時間（msec）
            }
        }
        package "4-3.ジカ線仕様　(固定MID分，表示電源状態，CAN入出力以外）" as 43 {
            class "MIDジカ線仕様" as mid_line {
                + 要求ID
                + No.
                + In/Out
                + 信号名
                + 記号
                + 信号状態の説明
                + サンプリングする電源状態[IGR/P（IG1/2）]
                + サンプリングする電源状態[+B, ACC, special]
                + サンプリング条件
                + 入力確定時間（msec）
            }
        }
        package "4-4.積算値・学習値の固定MID内での表示有無とバッテリ再接続後の値リセット有無" as 44 {
            class "学習値要求" as mid_reset {
                + 要求ID
                + 表示/リセット有無
            }
        }
    }

Document *-- MID
MID "1" *-- "0..*" mid
mid "1" *-- "0..*" mid_sig: 実施条件
mid "1" *-- "0..*" mid_line: 実施条件
mid *-- mid_reset

class "Detailed Spec" as dtel
package "10.固定MID表示の特別処理指示" as 10 {
    class "10.MID表示" as 10-1
    class "MID表示の特別処理要求" as middetl {
        + 要求ID
        + No
        + 仕様
        + 標準処理
        + 特別処理
    }
}

Document *-- dtel
dtel "1" *-- "0..1" "10-1"
"10-1" "1" *-- "8" middetl

41 -- "10-1": 他:特別条件

note as detailedrelation1 
通信仕様に定義されるCAN信号のルール  
# 「4-2」に定義されるCAN信号は、「4-1」に記載されている信号と「10」の"特別処理"欄に記載されている信号全てとなる。  
end note  
41 .. detailedrelation1  
42 .. detailedrelation1   
"10" .. detailedrelation1

note as detailedrelation2 
ジカ仕様に定義されるジカ信号のルール  
# 「4-3」に定義されるジカ信号は、「4-1」に記載されている信号と「10」の"特別処理"欄に記載されている信号全てとなる。 
end note 
41 .. detailedrelation2 
43 .. detailedrelation2   
"10" .. detailedrelation2

@enduml
```

### Variable_MID, Detailed Spec2シートを含むファイルの文書内関係:
ファイル内の要件は下記依存関係にある。
Variable_MIDまたはDetailed Spec2のシートの内容を解釈する場合は、下記依存関係に基づき関連情報の取得と解釈を行うこと。

```plantuml
@startuml
class Variable_MID
package "5-1.基本画面の表示 要求" as 51 {
    class "基本画面表示要求" as BS {
        + 要求ID
        + 基本画面No.
        + 要求廃止
        + 基本画面の意匠例
        + 基本画面表示を行う電源状態[IGR/P（IG1/2）]
        + 基本画面表示を行う電源状態[+B, ACC, special]
        + 実施条件
        + 他:特別条件
        + 情報種類
        + 優先度(優先表示決定用)
        + 機能有無判定
        + M/Cランプ連動点灯・点滅
        + M/Cブザー有無
        + 表示機能機能安全（ASIL）
    }
}
package "5-2.通信仕様　(基本画面表示要求分）" as 52 {
    class "基本画面通信仕様" as sig {
        + 要求ID
        + No.
        + In/Out
        + データラベル名
        + 通信周期（msec）
        + 送信DMS　Ver
        + メッセージラベル
        + メータにセットする初期値
        + 通信途絶時にセットする値[IGR-ON中（IG2-ON中）]
        + 通信途絶時にセットする値[IGR-OFF中（IG2-OFF中）]
        + 途絶判定時間（msec）
        + 最大通信遅延許容時間（msec）
    }
}
Variable_MID "1" *-- "0..*" BS
BS "1" *-- "0..*" sig: 実施条件

package "5-3.各基本画面の詳細表示 要求" as 53 {
    package "5-3-<I>N</I>.各表示エリアの表示 要求" as 53n {
        class "表示グループ" as gp {
            + 要求ID
            + No.
            + 要求廃止
            + 基本画面No.
            + 表示エリアNo割付
            + グループNo.
            + 表示変化グループ
            + アニメーション有無
            + 最大アニメーション許容時間(msec)
            + 他:特別条件
        }

        package "G<I>N</I>-1.グループ<I>M</I> 表示要求" as gn1m {
            class "グループ表示要求" as gd {
                + 要求ID
                + No.
                + 要求廃止
                + 表示種類
                + 表示コンテンツ[シンボル / 日本語MSG]
                + 表示コンテンツ[英語MSG]
                + 表示効果[効果の種類]
                + 表示効果[点滅周期(msec)]
                + 表示効果[色]
                + 表示効果[変化パターン]
                + 可変MID表示を行う電源状態[IGR/P（IG1/2）
                + 可変MID表示を行う電源状態[+B, ACC, special]
                + 実施条件
                + 他:特別条件
            }

        }
        package "G<I>N</I>-2.グループ<I>M</I> 通信仕様" as gn2m {
            class "グループ通信仕様" as gsig{
                + 要求ID
                + No.
                + In/Out
                + データラベル名
                + 通信周期（msec）
                + 送信DMS　Ver
                + メッセージラベル
                + メータにセットする初期値
                + 通信途絶時にセットする値[IGR-ON中（IG2-ON中）]
                + 通信途絶時にセットする値[IGR-OFF中（IG2-OFF中）]
                + 途絶判定時間（msec）
                + 最大通信遅延許容時間（msec）
            }

        }

        gp *-- gd: グループNo.<I>M</I>
        gd *-- gsig: 実施条件
        gd *-- gd: No.<I>n-m</I>
    }
}

BS "1" *-- "0..*" gp: 基本画面No.<I>N</I>
note "# 基本画面No.Nと表示グループNo.Mの関係 \n\
基本画面No.Nの表示構成要素として表示グループNo.Mが規定される。\n\
各表示グループNo.Mの要件は、基本画面No.Nの表示条件が成立していることが前提。 \n\
一方で、基本画面No.Nの表示条件成立時に、表示される内容は表示グループの実施条件参照が必要。 \n\
したがって、基本画面または表示グループを正しく把握するためには、どちらも参照する必要がある。" as vmidnote1
BS .. vmidnote1
gp .. vmidnote1

package "5-4.積算値・学習値の可変MID内での表示有無とバッテリ再接続後の値リセット有無" as 54 {
    class "学習値要求" as rst {
        + 要求ID
        + No.
        + 基本画面No.
        + グループNo.
        + 表示/リセット有無
    }
}

gp *-- rst: 基本画面No.+グループNo.

class "Detailed Spec2" as dtel2
package "11.可変MID表示の特別処理指示" as 11 {
    class "11-<I>N</I>.基本画面No.<I>N</I>" as 11-N
    class "可変MID表示の特別処理要求" as vmiddetl {
        + 要求ID
        + No
        + 仕様
        + 標準処理
        + 特別処理
    }
}

dtel2 "1" *-- "0..*" "11-N": 基本画面N個
"11-N" "1" *-- "12" vmiddetl

Document *-- Variable_MID
Document *-- dtel2

51 -- "11-N": 他:特別条件
53n -- "11-N": 他:特別条件
gn1m -- "11-N": 他:特別条件

note as detailedrelation 
通信仕様に定義されるCAN信号のルール  
# 「5-2」に定義されるCAN信号は、「5-1」に記載されている信号と「11-N」の"特別処理"欄に記載されている信号全てとなる。 
# 「GN-2」に定義されるCAN信号は、「GN-1」に記載されている信号と「11-N」の"特別処理"欄に記載されている信号全てとなる。   
end note  
51 .. detailedrelation 
52 .. detailedrelation
gn1m .. detailedrelation 
gn2m .. detailedrelation   
"11" .. detailedrelation

@enduml
```

### SW, Detailed Spec3シートを含むファイルの文書内関係:
ファイル内の要件は下記依存関係にある。
SWまたはDetailed Spec3のシートの内容を解釈する場合は、下記依存関係に基づき関連情報の取得と解釈を行うこと。

```plantuml
@startuml
class SW
    package "6.ソフトSW /カスタマイズSW　表示" as 6 {
        package "6-1.SW表示要求" as 6-1 {
            package "6-1-<I>N</I>.SW状態表示" as 61n {
                class "SW状態表示" as sw {
                    + 要求ID
                    + No.
                    + 要求廃止
                    + シンボル/意匠例
                    + 走行中操作可否
                    + SW機能
                    + 補助文言（ガイド文）[日本語]
                    + 補助文言（ガイド文）[英語]
                }
                package "S<I>N</I>.SW制御" as sn {
                    package "S<I>N</I>-1.機能有無判別" as sn1 {
                        class "機能有無" as func {
                            + 要求ID
                            + No.
                            + 要求廃止
                            + 有無判別結果
                            + 有無判別後の処理
                            + 実施条件
                            + 他:特別条件
                            + 機能有無判定時間（msec）
                            + クリア条件[Phase4]
                            + クリア条件[Phase5]
                        }
                    }
                    package "S<I>N</I>-2.ステアリングSW押下制御　（メータ送信）" as sn2 {
                        class "SWメータ送信" as send {
                            + 要求ID
                            + No.
                            + 要求廃止
                            + ステアリングSWの状態
                            + 実施条件
                            + 他:特別条件
                        }
                    }
                    package "S<I>N</I>-3.SW状態応答要求(システム側ECU送信)" as sn3 {
                        class "SWメータ受信" as recieve {
                            + 要求ID
                            + No.
                            + 要求廃止
                            + 表示種類
                            + SW状態表示[日本語 / 画像]
                            + SW状態表示[英語]
                            + 実施条件
                            + 他:特別条件
                        }
                    }
                    package "S<I>N</I>-4.通信仕様" as sn4 {
                        class "SW通信仕様" as sw_sig {
                            + 要求ID
                            + No.
                            + In/Out
                            + データラベル名
                            + 通信周期（msec）
                            + 送信DMS　Ver
                            + メッセージラベル
                            + メータにセットする初期値
                            + 通信途絶判定後にセットする値[IGR-ON中（IG2-ON中）]
                            + 通信途絶判定後にセットする値[IGR-OFF中（IG2-OFF中）]
                            + 途絶判定時間（msec）
                            + 最大通信遅延許容時間（msec）
                        }
                    }
                }
            }
        }
    }

Document *-- SW
SW "1" *-- "0..*" sw
sw "1" *-- "0..1" func: 機能有無
sw "1" *-- "0..*" send: メータ送信
sw "1" *-- "0..*" recieve: メータ受信
func "1" *-- "0..*" sw_sig: 実施条件
send "1" *-- "0..*" sw_sig: 実施条件
recieve "1" *-- "0..*" sw_sig: 実施条件

class "Detailed Spec3" as dtel3
package "12.ソフトSW/カスタマイズSW表示の特別処理指示" as 12 {
    class "12-<I>N</I>. SW制御" as 12-N
    class "SW表示の特別処理要求" as swdetl {
        + 要求ID
        + No
        + 仕様
        + 標準処理
        + 特別処理
    }
}

Document *-- dtel3
dtel3 "1" *-- "0..*" "12-N": SW N個
"12-N" "1" *-- "12" swdetl

sn1 -- "12-N": 他:特別条件
sn2 -- "12-N": 他:特別条件
sn3 -- "12-N": 他:特別条件

note as detailedrelation 
通信仕様に定義されるCAN信号のルール  
# 「S1-4」に定義されるCAN信号は、「S1-1」、「S1-2」、「S1-3」に記載されている信号と「12-N」の"特別処理"欄に記載されている信号全てとなる。    
end note  
sn1 .. detailedrelation 
sn2 .. detailedrelation
sn3 .. detailedrelation 
sn4 .. detailedrelation   
"12" .. detailedrelation

@enduml
```

