"""
Page 7: ICD-10
==============
GET /icd/release/10                         — ICD-10 リリース一覧
GET /icd/release/10/{releaseId}             — ICD-10 章一覧
GET /icd/release/10/{releaseId}/{code}      — ICD-10 コード詳細
"""

import streamlit as st
import pandas as pd
from icd11_core import (
    get_cached_token, api_get, extract_text,
    show_raw_json, show_request_info,
    sidebar_lang_selector, API_BASE,
)

st.set_page_config(page_title="ICD-10", layout="wide")
st.title("7. ICD-10（旧版参照）")
st.caption("`GET /icd/release/10/{ver}/{code}` — ICD-10 コード検索")
st.markdown("""
WHO ICD API では ICD-11 だけでなく、**ICD-10**（旧版）のコード情報も参照できます。
ICD-10 → ICD-11 への移行作業や、旧コードの確認に利用します。
""")

# --- Sidebar ---
lang = sidebar_lang_selector()

st.sidebar.divider()
mode = st.sidebar.radio(
    "モード",
    ["コード検索", "リリース一覧", "リリース章一覧"],
    help="ICD-10 のコード検索、利用可能なリリース一覧、またはリリース内の章一覧を選択",
)

# ============================================================
# Release List
# ============================================================
if mode == "リリース一覧":
    st.subheader("ICD-10 リリース一覧")
    st.markdown("WHO ICD API で利用可能な ICD-10 のリリースバージョン一覧です。")
    url = f"{API_BASE}/icd/release/10"
    st.caption(f"`GET {url}`")

    try:
        token = get_cached_token()
        data = api_get(url, token, lang=lang, use_cache=False)
        show_request_info(data)

        releases = data.get("release") or []
        if releases:
            st.write(f"**利用可能なリリース数:** {len(releases)}")
            for r in releases:
                st.write(f"- `{r}`")
        else:
            st.info("リリースが見つかりませんでした。")

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")

# ============================================================
# Release Chapters
# ============================================================
elif mode == "リリース章一覧":
    release_id = st.sidebar.selectbox(
        "ICD-10 リリース版",
        options=["2019", "2016", "2010", "2008"],
        index=0,
        help="ICD-10 のリリースバージョンを選択",
    )

    st.subheader(f"ICD-10 リリース: {release_id} — 章一覧")
    st.markdown("選択したリリースバージョンに含まれる全章（Chapter）の一覧です。")
    url = f"{API_BASE}/icd/release/10/{release_id}"
    st.caption(f"`GET {url}`")

    try:
        token = get_cached_token()
        data = api_get(url, token, lang=lang, use_cache=False)
        show_request_info(data)

        children = data.get("child") or []
        st.write(f"**章の数:** {len(children)}")

        rows = []
        for uri in children:
            code_part = uri.rstrip("/").split("/")[-1]
            try:
                child_data = api_get(uri, token, lang=lang)
                title = extract_text(child_data.get("title"))
            except Exception:
                title = "（取得エラー）"
            rows.append({"コード": code_part, "タイトル": title, "URI": uri})

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")

# ============================================================
# Code Lookup
# ============================================================
else:
    release_id = st.sidebar.selectbox(
        "ICD-10 リリース版",
        options=["2019", "2016", "2010", "2008"],
        index=0,
        help="ICD-10 のリリースバージョンを選択",
    )
    icd10_code = st.sidebar.text_input(
        "ICD-10 コード",
        value="E11",
        help="ICD-10 コードを入力（例: E11=2型糖尿病, J18=肺炎, C34=肺悪性新生物）",
    )

    if not icd10_code.strip():
        st.info("サイドバーで ICD-10 コードを入力してください")
        st.stop()

    url = f"{API_BASE}/icd/release/10/{release_id}/{icd10_code.strip()}"
    st.caption(f"`GET {url}`")

    try:
        token = get_cached_token()
        data = api_get(url, token, lang=lang, use_cache=False)
        show_request_info(data)

        st.subheader("ICD-10 コード詳細")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**コード:**", data.get("code"))
            st.write("**タイトル:**", extract_text(data.get("title")))
            st.write("**Entity URI:**", data.get("@id"))

        with col2:
            definition = extract_text(data.get("definition"))
            if definition:
                st.write("**定義:**")
                st.info(definition)

        # Inclusions
        inclusions = data.get("inclusion") or []
        if inclusions:
            st.subheader(f"包含項目（Inclusion）（{len(inclusions)}件）")
            st.markdown("この分類に含まれる診断用語です。")
            for inc in inclusions:
                if isinstance(inc, dict):
                    st.write(f"- {extract_text(inc.get('label'))}")

        # Exclusions
        exclusions = data.get("exclusion") or []
        if exclusions:
            st.subheader(f"除外項目（Exclusion）（{len(exclusions)}件）")
            st.markdown("この分類には含まず、別のコードに分類される項目です。")
            for exc in exclusions:
                if isinstance(exc, dict):
                    st.write(f"- {extract_text(exc.get('label'))}")

        # Children
        children = data.get("child") or []
        if children:
            st.subheader(f"子コード（{len(children)}件）")
            st.markdown("このコードの配下にあるより細分化されたコードです。")
            rows = []
            for uri in children[:50]:
                code_part = uri.rstrip("/").split("/")[-1]
                try:
                    child_data = api_get(uri, token, lang=lang)
                    title = extract_text(child_data.get("title"))
                except Exception:
                    title = "（取得エラー）"
                rows.append({"コード": code_part, "タイトル": title, "URI": uri})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

        # Parent
        parent = data.get("parent") or []
        if parent:
            st.subheader("親コード")
            st.markdown("このコードが属する上位の分類です。")
            for uri in parent:
                code_part = uri.rstrip("/").split("/")[-1]
                st.write(f"- `{code_part}` (`{uri}`)")

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")
