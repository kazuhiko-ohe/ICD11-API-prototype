"""
Page 4: Autocode (Foundation / MMS)
====================================
GET /icd/entity/autocode                    — Foundation 自動コーディング
GET /icd/release/11/{ver}/mms/autocode      — MMS 自動コーディング
"""

import streamlit as st
import pandas as pd
from icd11_core import (
    get_cached_token, api_get, extract_text,
    foundation_autocode_url, mms_autocode_url,
    show_raw_json, show_request_info,
    sidebar_lang_selector, sidebar_release_selector,
)

st.set_page_config(page_title="Autocode", layout="wide")
st.title("4. Autocode（自動コーディング）")
st.caption("診断テキストからの自動コーディング — ベストマッチ1件を返す")
st.markdown("""
診断テキスト（自由記述）を入力すると、最も適合する ICD-11 エンティティを**1件**返します。
ICD-11 Coding Tool と同じアルゴリズムを使用しています。
""")

# --- Sidebar ---
lang = sidebar_lang_selector()
release_id = sidebar_release_selector()

st.sidebar.divider()
autocode_target = st.sidebar.radio(
    "対象",
    ["MMS（コード割当用）", "Foundation（概念レベル）"],
    help="MMS: 統計用コードを返す。Foundation: 概念レベルでのマッチング",
)
search_text = st.sidebar.text_area(
    "診断テキスト",
    value="Type 2 diabetes mellitus",
    help="診断名を自由に入力（例: Type 2 diabetes mellitus, Acute myocardial infarction, 肺炎）",
)
threshold = st.sidebar.slider(
    "マッチ閾値",
    min_value=0.0, max_value=1.0, value=0.5, step=0.05,
    help="値を下げると緩くマッチ（再現率↑）、上げると厳密マッチ（精度↑）",
)

if not search_text.strip():
    st.info("サイドバーで診断テキストを入力してください")
    st.stop()

try:
    token = get_cached_token()

    is_mms = autocode_target.startswith("MMS")
    if is_mms:
        base_url = mms_autocode_url(release_id)
    else:
        base_url = foundation_autocode_url()

    url = f"{base_url}?searchText={search_text.strip()}&matchThreshold={threshold}"
    st.caption(f"`GET {url}`")

    data = api_get(url, token, lang=lang, use_cache=False)
    show_request_info(data)

    st.subheader("自動コーディング結果")

    the_code = data.get("theCode")
    title = extract_text(data.get("title"))
    entity_id = data.get("id")
    score = data.get("score")
    chapter = data.get("chapter")
    is_residual = data.get("isResidual")
    foundation_uri = data.get("foundationURI")

    col1, col2 = st.columns(2)
    with col1:
        if the_code:
            st.metric("判定コード", the_code)
        st.write("**タイトル:**", title)
        if score is not None:
            st.write(f"**マッチスコア:** {score}")
        if chapter:
            st.write(f"**章:** {chapter}")

    with col2:
        st.write("**Entity ID:**", entity_id)
        if foundation_uri:
            st.write("**Foundation URI:**", foundation_uri)
        if is_residual is not None:
            residual_label = "はい（残余カテゴリ）" if is_residual else "いいえ"
            st.write(f"**残余カテゴリ:** {residual_label}")

    matching_pvs = data.get("matchingPVs") or []
    if matching_pvs:
        st.subheader("マッチしたプロパティ")
        st.markdown("入力テキストがどのプロパティ（タイトル・同義語など）にマッチしたかの詳細です。")
        rows = []
        for pv in matching_pvs:
            if isinstance(pv, dict):
                rows.append({
                    "プロパティ": pv.get("propertyId", ""),
                    "ラベル": extract_text(pv.get("label")),
                    "スコア": pv.get("score", ""),
                    "重要度": pv.get("important", ""),
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    show_raw_json(data)

except Exception as e:
    st.error(f"エラー: {e}")
