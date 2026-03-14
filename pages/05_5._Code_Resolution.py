"""
Page 5: Code Resolution
========================
GET /icd/release/11/{ver}/mms/codeinfo/{code}  — コード → Entity URI 解決
GET /icd/release/11/{ver}/mms/lookup            — Foundation URI → MMS マッピング
GET /icd/release/11/{ver}/mms/describe          — コード/URI の詳細説明
"""

import streamlit as st
import pandas as pd
from icd11_core import (
    get_cached_token, api_get, extract_text,
    mms_codeinfo_url, mms_lookup_url, mms_describe_url,
    show_raw_json, show_request_info,
    sidebar_lang_selector, sidebar_release_selector,
)

st.set_page_config(page_title="Code Resolution", layout="wide")
st.title("5. Code Resolution（コード解決）")
st.caption("codeinfo / lookup / describe — コード解決とマッピング")
st.markdown("""
ICD-11 コードや URI を使って、エンティティの特定・マッピング・詳細記述を行う3つのツールです。

- **codeinfo**: ICD-11 コード文字列 → Entity URI への変換、ポストコーディネーション構造の解析
- **lookup**: Foundation URI → MMS リニアライゼーション上の配置先を検索
- **describe**: コードまたは URI から、ポストコーディネーション情報を含む詳細な記述を取得
""")

# --- Sidebar ---
lang = sidebar_lang_selector()
release_id = sidebar_release_selector()

st.sidebar.divider()
tool = st.sidebar.radio(
    "ツール選択",
    ["codeinfo（コード解析）", "lookup（URI マッピング）", "describe（詳細記述）"],
    help="使用するコード解決ツールを選択してください",
)

# ============================================================
# codeinfo
# ============================================================
if tool.startswith("codeinfo"):
    st.subheader("codeinfo（コード解析）")
    st.caption("`GET /icd/release/11/{ver}/mms/codeinfo/{code}`")
    st.markdown("""
ICD-11 コード文字列（ポストコーディネーション含む）を解析し、**stem（基幹コード）** と **ポストコーディネーション軸** の情報を返します。
複合コード（例: `2C25.Z&XK8G&XA9HN5`）の構造を確認するのに便利です。
""")

    code = st.sidebar.text_input(
        "ICD-11 コード",
        value="5A11",
        help="解析するコードを入力（例: 5A11=2型糖尿病, 2C25.Z&XK8G&XA9HN5=複合コード）",
    )
    flexible = st.sidebar.checkbox(
        "柔軟モード（Flexible mode）",
        value=False,
        help="ONにすると不正な組合せでも部分的に結果を返します",
    )

    if not code.strip():
        st.info("サイドバーで ICD-11 コードを入力してください")
        st.stop()

    try:
        token = get_cached_token()
        url = mms_codeinfo_url(code.strip(), release_id)
        if flexible:
            url += "?flexiblemode=true"

        st.caption(f"`GET {url}`")
        data = api_get(url, token, lang=lang, use_cache=False)
        show_request_info(data)

        st.subheader("解析結果")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**基幹コード（Stem Code）:**", data.get("stemCode"))
            st.write("**Stem URI:**", data.get("stemId"))
            st.write("**Foundation URI:**", data.get("foundationURI"))

        with col2:
            chapter = data.get("chapter")
            if chapter:
                st.write("**章（Chapter）:**", chapter)
            block = data.get("block")
            if block:
                st.write("**ブロック（Block）:**", block)

        # Postcoordination axes
        axes = data.get("postcoordination") or []
        if axes:
            st.subheader("ポストコーディネーション軸")
            st.markdown("コードに含まれるポストコーディネーション（追加修飾情報）の内訳です。")
            for ax in axes:
                if isinstance(ax, dict):
                    st.write(f"- **{ax.get('axisName', '')}**: {ax.get('value', '')} ({extract_text(ax.get('title'))})")

        # Other postcoordination (flexible mode)
        other = data.get("otherPostcoordination") or {}
        if other:
            st.subheader("その他のポストコーディネーション（柔軟モード）")
            st.markdown("標準では認識されなかったポストコーディネーション要素です。")
            st.json(other)

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")

# ============================================================
# lookup
# ============================================================
elif tool.startswith("lookup"):
    st.subheader("lookup（URI マッピング）")
    st.caption("`GET /icd/release/11/{ver}/mms/lookup?foundationUri=...`")
    st.markdown("""
Foundation Entity の URI を指定すると、その概念が **MMS Linearization（統計用コード体系）** のどこに配置されているかを返します。
Foundation は多階層構造のため、1つの概念が MMS では別の場所にマッピングされることがあります。
""")

    foundation_uri = st.sidebar.text_input(
        "Foundation URI",
        value="http://id.who.int/icd/entity/455013390",
        help="Foundation Entity の URI を入力（例: http://id.who.int/icd/entity/455013390 = Diabetes mellitus）",
    )

    if not foundation_uri.strip():
        st.info("サイドバーで Foundation URI を入力してください")
        st.stop()

    try:
        token = get_cached_token()
        url = f"{mms_lookup_url(release_id)}?foundationUri={foundation_uri.strip()}"

        st.caption(f"`GET {url}`")
        data = api_get(url, token, lang=lang, use_cache=False)
        show_request_info(data)

        st.subheader("MMS マッピング結果")
        st.markdown("指定した Foundation Entity が MMS 上でどのコード・位置に対応するかの情報です。")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**コード:**", data.get("code"))
            st.write("**タイトル:**", extract_text(data.get("title")))
            st.write("**Entity URI:**", data.get("@id"))

        with col2:
            class_kind = data.get("classKind")
            kind_labels = {"chapter": "章", "block": "ブロック", "category": "カテゴリ", "window": "ウィンドウ"}
            if class_kind:
                st.write("**分類種別:**", f"{class_kind}（{kind_labels.get(class_kind, '')}）")
            st.write("**Foundation ソース:**", data.get("source"))

        definition = extract_text(data.get("definition"))
        if definition:
            st.write("**定義:**")
            st.info(definition)

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")

# ============================================================
# describe
# ============================================================
else:
    st.subheader("describe（詳細記述）")
    st.caption("`GET /icd/release/11/{ver}/mms/describe?code=...` or `?uri=...`")
    st.markdown("""
ICD-11 コードまたは URI を入力して、**ポストコーディネーション情報を含む詳細な記述**を取得します。
基幹エンティティ（Stem）と各ポストコーディネーション軸のタイトル・コードが返されます。
""")

    describe_mode = st.sidebar.radio(
        "入力方式",
        ["コードで指定", "URI で指定"],
        help="コードまたは URI のどちらで入力するかを選択",
    )
    if describe_mode == "コードで指定":
        code = st.sidebar.text_input(
            "ICD-11 コード",
            value="5A11",
            help="例: 5A11, 5A11&XS7R（ポストコーディネーション付き）",
        )
        uri_input = ""
    else:
        code = ""
        uri_input = st.sidebar.text_input(
            "Entity URI",
            value="",
            help="MMS または Foundation の URI を入力",
        )

    flexible = st.sidebar.checkbox(
        "柔軟モード（Flexible mode）",
        value=False,
        help="ONにすると不正な組合せでも部分的に結果を返します",
    )
    simplify = st.sidebar.checkbox(
        "簡易表示（Simplify）",
        value=False,
        help="ONにすると簡略化された結果を返します",
    )

    if not code.strip() and not uri_input.strip():
        st.info("サイドバーでコードまたは URI を入力してください")
        st.stop()

    try:
        token = get_cached_token()
        base = mms_describe_url(release_id)
        params = []
        if code.strip():
            params.append(f"code={code.strip()}")
        if uri_input.strip():
            params.append(f"uri={uri_input.strip()}")
        if flexible:
            params.append("flexiblemode=true")
        if simplify:
            params.append("simplify=true")

        url = base + "?" + "&".join(params)
        st.caption(f"`GET {url}`")
        data = api_get(url, token, lang=lang, use_cache=False)
        show_request_info(data)

        st.subheader("記述結果")

        # Stem entity
        stem = data.get("stemEntity") or {}
        if stem:
            st.markdown("**基幹エンティティ（Stem Entity）**")
            st.write("**コード:**", stem.get("theCode"))
            st.write("**タイトル:**", extract_text(stem.get("title")))
            st.write("**URI:**", stem.get("id"))

        # Postcoordination sets
        pc_entities = data.get("postcoordinationEntities") or []
        if pc_entities:
            st.subheader(f"ポストコーディネーション要素（{len(pc_entities)}件）")
            st.markdown("基幹エンティティに付加されたポストコーディネーション（追加修飾情報）の詳細です。")
            for pc in pc_entities:
                if isinstance(pc, dict):
                    st.write(f"- **{pc.get('axisName', '')}**: {extract_text(pc.get('title'))} (コード={pc.get('theCode', '')})")

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")
