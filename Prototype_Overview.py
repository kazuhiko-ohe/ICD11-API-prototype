"""
ICD-11 API Prototype — Prototype Overview
==========================================
WHO ICD-11 API を網羅的に実演する Streamlit マルチページアプリケーション。
"""

import streamlit as st

st.set_page_config(page_title="ICD-11 API Prototype", layout="wide")

st.title("ICD-11 API Prototype")
st.markdown("""
WHO ICD-11 API の各機能を実演するプロトタイプツールです。
左のサイドバーからページを選択してください。

各ページでは、実際の API リクエスト URL とレスポンス JSON を確認できます。
""")

st.divider()

st.subheader("対応 API エンドポイント一覧")

endpoints = [
    ("1. Foundation Entity", "GET /icd/entity/{id}",
     "ICD-11 の基盤となる Foundation Entity の詳細閲覧。定義・除外・親子階層を確認できます。"),
    ("2. MMS Linearization", "GET .../mms/{id}",
     "死因・疾病統計用の MMS コードから Linearization Entity を閲覧。コード体系に沿った情報を確認できます。"),
    ("3. Search（検索）", "GET .../search",
     "Foundation / MMS の全文検索。あいまい検索（Flexisearch）やフィルタにも対応しています。"),
    ("4. Autocode（自動コーディング）", "GET .../autocode",
     "診断テキスト（自由記述）を入力すると、最も適合する ICD-11 コードを自動判定します。"),
    ("5. Code Resolution（コード解決）", "GET .../codeinfo, lookup, describe",
     "コードから URI への変換、Foundation→MMS マッピング、ポストコーディネーション解析を行います。"),
    ("6. Postcoordination", "GET .../mms/{id}",
     "ポストコーディネーション（付加情報の軸）を確認し、組合せコードの妥当性を検証します。"),
    ("7. ICD-10", "GET /icd/release/10/{ver}/{code}",
     "旧版 ICD-10 のコード検索・詳細表示。ICD-11 との比較に利用できます。"),
    ("8. DORIS（死因判定）", "POST .../doris",
     "死亡診断書の情報から WHO ルールに基づいて根本死因を自動判定します（pre-release）。"),
]

for page, endpoint, desc in endpoints:
    with st.container():
        col1, col2, col3 = st.columns([1.2, 1.5, 2])
        with col1:
            st.markdown(f"**{page}**")
        with col2:
            st.code(endpoint, language=None)
        with col3:
            st.caption(desc)

st.divider()

st.subheader("セットアップ -- 本Webページを使うだけの場合には不要です。自分のPCにオンプレミスで本HPと同じWebアプリを導入する場合の作業手順です。作業にはパッケージが必要ですので管理者までお知らせください。")
st.markdown("""
```bash
# 1. 依存パッケージのインストール
pip install -r requirements.txt

# 2. .env ファイルに WHO ICD API の認証情報を設定
#    ICD_CLIENT_ID=<あなたの Client ID>
#    ICD_CLIENT_SECRET=<あなたの Client Secret>

# 3. アプリケーション起動
streamlit run app.py
```

API の認証情報は [icd.who.int/icdapi](https://icd.who.int/icdapi) で無料取得できます。
""")

st.divider()

st.subheader("用語ガイド")
st.markdown("""
| 用語 | 説明 |
|---|---|
| **Foundation** | ICD-11 の基盤層。多階層（polyhierarchy）でエンティティが整理されている |
| **MMS (Linearization)** | 死因・疾病統計用に Foundation から派生した単一階層のコード体系 |
| **Entity** | 疾病や症状などの個々の概念（エンティティ） |
| **Exclusion** | 「この分類には含まない」とされる除外項目 |
| **Inclusion** | 「この分類に含む」とされる包含項目 |
| **Postcoordination** | 重症度・部位・原因などの付加情報を組合せてコードを精緻化する仕組み |
| **Autocode** | 自由記述テキストから最適な ICD-11 コードを自動判定する機能 |
| **DORIS** | 死亡診断書から根本死因を判定する WHO の自動ルールエンジン |
""")

st.divider()
st.caption("ICD-11 API Prototype | WHO ICD-11 API v2 | Release 2025-01")
