"""
Page 2: MMS Linearization Entity 閲覧
=====================================
GET /icd/release/11/{ver}/mms            — MMS リリース情報（章一覧）
GET /icd/release/11/{ver}/mms/{id}       — MMS Entity 詳細
"""

import streamlit as st
import pandas as pd
from icd11_core import (
    get_cached_token, api_get, extract_text,
    mms_release_url, mms_entity_url, mms_codeinfo_url,
    show_raw_json, show_request_info,
    sidebar_lang_selector, sidebar_release_selector,
    resolve_uri_title, DEFAULT_RELEASE_ID,
)

st.set_page_config(page_title="MMS Linearization", layout="wide")
st.title("2. MMS Linearization")
st.caption("`GET /icd/release/11/{ver}/mms/{id}` — MMS Linearization Entity の閲覧")
st.markdown("""
MMS（Mortality and Morbidity Statistics）は、死因・疾病統計のために Foundation から派生した**単一階層コード体系**です。
ICD-11 コード（例: `6A00`, `5A11`）を入力すると、コード体系に沿ったエンティティ情報を閲覧できます。
""")

# --- Sidebar ---
lang = sidebar_lang_selector()
release_id = sidebar_release_selector()

st.sidebar.divider()
mode = st.sidebar.radio("モード", ["MMS コードで検索", "リリース情報（章一覧）"])

if mode == "リリース情報（章一覧）":
    st.subheader(f"MMS リリース: {release_id} — 章一覧")
    st.markdown("選択したリリースバージョンに含まれる全章（Chapter）の一覧です。")
    url = mms_release_url(release_id)
    st.caption(f"`GET {url}`")

    try:
        token = get_cached_token()
        data = api_get(url, token, lang=lang)
        show_request_info(data)

        children = data.get("child") or []
        st.write(f"**章の数:** {len(children)}")

        rows = []
        for uri in children:
            title = resolve_uri_title(uri, token, lang)
            entity_id = uri.rstrip("/").split("/")[-1]
            rows.append({"Entity ID": entity_id, "タイトル": title, "URI": uri})

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")

else:
    mms_code = st.sidebar.text_input(
        "MMS コード",
        value="6A00",
        help="ICD-11 MMS コードを入力（例: 6A00=アルコール使用による障害, 5A11=2型糖尿病, 1A00=コレラ）",
    )
    include_opts = st.sidebar.multiselect(
        "追加情報の取得（Include）",
        options=["ancestor", "descendant", "diagnosticCriteria"],
        help="ancestor=祖先一覧、descendant=子孫一覧、diagnosticCriteria=診断基準",
    )
    resolve_titles = st.sidebar.checkbox("親子エンティティのタイトルを表示", value=True, help="ONにするとAPI呼出が増え表示が遅くなる場合があります")

    if not mms_code.strip():
        st.info("サイドバーで MMS コードを入力してください")
        st.stop()

    try:
        token = get_cached_token()

        codeinfo_url = mms_codeinfo_url(mms_code.strip(), release_id)
        st.caption(f"Step 1 — コード解決: `GET {codeinfo_url}`")
        codeinfo = api_get(codeinfo_url, token, lang=lang, use_cache=False)
        show_request_info(codeinfo)

        stem_uri = codeinfo.get("stemId")
        if not stem_uri:
            st.error(f"codeinfo でコードを解決できませんでした: {mms_code}")
            show_raw_json(codeinfo, "codeinfo レスポンス")
            st.stop()

        with st.expander("codeinfo レスポンス（コード→URI変換結果）", expanded=False):
            st.json(codeinfo)

        entity_id = stem_uri.rstrip("/").split("/")[-1]
        url = mms_entity_url(entity_id, release_id)
        if include_opts:
            url += "?include=" + ",".join(include_opts)

        st.caption(f"Step 2 — エンティティ取得: `GET {url}`")
        data = api_get(url, token, lang=lang, use_cache=False)
        show_request_info(data)

        # --- Basic Info ---
        st.subheader("基本情報")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**コード:**", data.get("code"))
            st.write("**タイトル:**", extract_text(data.get("title")))
            class_kind = data.get("classKind")
            kind_labels = {"chapter": "章", "block": "ブロック", "category": "カテゴリ", "window": "ウィンドウ"}
            if class_kind:
                st.write("**分類種別:**", f"{class_kind}（{kind_labels.get(class_kind, '')}）")
            st.write("**コード範囲:**", data.get("codeRange"))
            st.write("**ブロック ID:**", data.get("blockId"))
            st.write("**Entity URI:**", data.get("@id"))
            source = data.get("source")
            if source:
                st.write("**Foundation ソース:**", source)
            if data.get("browserUrl"):
                st.write("**WHO ブラウザ:**", data.get("browserUrl"))

        with col2:
            definition = extract_text(data.get("definition"))
            if definition:
                st.write("**定義:**")
                st.info(definition)
            long_def = extract_text(data.get("longDefinition"))
            if long_def:
                st.write("**詳細定義:**")
                st.info(long_def)

        coding_note = extract_text(data.get("codingNote"))
        if coding_note:
            st.subheader("コーディングノート")
            st.warning(coding_note)

        exclusions = data.get("exclusion") or []
        if exclusions:
            st.subheader(f"除外項目（Exclusion）（{len(exclusions)}件）")
            st.markdown("この分類には含まず、別のコードに分類される項目です。")
            exc_rows = []
            for exc in exclusions:
                if isinstance(exc, dict):
                    exc_rows.append({
                        "ラベル": extract_text(exc.get("label")),
                        "Foundation 参照": exc.get("foundationReference"),
                        "Linearization 参照": exc.get("linearizationReference"),
                    })
            st.dataframe(pd.DataFrame(exc_rows), use_container_width=True)

        inclusions = data.get("inclusion") or []
        if inclusions:
            st.subheader(f"包含項目（Inclusion）（{len(inclusions)}件）")
            for inc in inclusions:
                if isinstance(inc, dict):
                    st.write(f"- {extract_text(inc.get('label'))}")

        parents = data.get("parent") or []
        children = data.get("child") or []

        if parents:
            st.subheader(f"親エンティティ（{len(parents)}件）")
            for uri in parents[:30]:
                if resolve_titles:
                    title = resolve_uri_title(uri, token, lang)
                    st.write(f"- {title} (`{uri}`)")
                else:
                    st.write(f"- `{uri}`")

        if children:
            st.subheader(f"子エンティティ（{len(children)}件）")
            for uri in children[:50]:
                if resolve_titles:
                    title = resolve_uri_title(uri, token, lang)
                    st.write(f"- {title} (`{uri}`)")
                else:
                    st.write(f"- `{uri}`")

        fce = data.get("foundationChildElsewhere") or []
        if fce:
            st.subheader(f"他所に配置された Foundation 子エンティティ（{len(fce)}件）")
            st.markdown("Foundation では子だが、MMS では別の場所に分類されているエンティティです。")
            for item in fce[:20]:
                if isinstance(item, dict):
                    st.write(f"- {extract_text(item.get('label'))} (`{item.get('foundationReference')}`)")

        postcoord = data.get("postcoordinationScale") or []
        if postcoord:
            st.subheader(f"ポストコーディネーション軸（{len(postcoord)}軸）")
            for ax in postcoord:
                if isinstance(ax, dict):
                    req_label = "必須" if ax.get('requiredPostcoordination', False) else "任意"
                    st.write(f"- **{ax.get('axisName')}**（{req_label}）| 複数値: {ax.get('allowMultipleValues', '')}")

        index_terms = data.get("indexTerm") or []
        if index_terms:
            st.subheader(f"索引語（{len(index_terms)}件）")
            for it in index_terms[:30]:
                if isinstance(it, dict):
                    st.write(f"- {extract_text(it.get('label'))}")
            if len(index_terms) > 30:
                st.caption(f"... 他 {len(index_terms) - 30} 件")

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")
