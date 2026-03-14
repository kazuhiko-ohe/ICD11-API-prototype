"""
Page 1: Foundation Entity 閲覧
==============================
GET /icd/entity          — トップレベル（章一覧）
GET /icd/entity/{id}     — Entity 詳細
GET /icd/entity/{id}?include=ancestor,descendant,diagnosticCriteria
"""

import json
import streamlit as st
import pandas as pd
from icd11_core import (
    get_cached_token, api_get, extract_text,
    foundation_url, show_raw_json, show_request_info,
    sidebar_lang_selector, resolve_uri_title, API_BASE,
)

st.set_page_config(page_title="Foundation Entity", layout="wide")
st.title("1. Foundation Entity")
st.caption("`GET /icd/entity/{id}` — Foundation Entity の詳細閲覧")
st.markdown("""
Foundation は ICD-11 の**基盤層**です。全ての疾病概念が多階層（polyhierarchy）で整理されており、
1つのエンティティが複数の親を持つことができます。Entity ID（数値）を指定して詳細を閲覧します。
""")

# --- Sidebar ---
lang = sidebar_lang_selector()

st.sidebar.divider()
mode = st.sidebar.radio(
    "モード",
    ["Entity ID で検索", "トップレベル（章一覧）"],
    help="Entity ID を直接指定するか、章の一覧を表示するかを選択",
)

if mode == "トップレベル（章一覧）":
    # ============================================================
    # GET /icd/entity — 章一覧
    # ============================================================
    st.subheader("Foundation トップレベル（章一覧）")
    st.markdown("Foundation の最上位にある章（Chapter）の一覧を表示します。各章の Entity ID をコピーして「Entity ID で検索」モードで詳細を閲覧できます。")

    url = f"{API_BASE}/icd/entity"
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
    # ============================================================
    # GET /icd/entity/{id} — Entity 詳細
    # ============================================================
    entity_id = st.sidebar.text_input(
        "Entity ID",
        value="455013390",
        help="Foundation Entity の数値 ID を入力（例: 455013390 = Diabetes mellitus）",
    )
    include_opts = st.sidebar.multiselect(
        "追加情報の取得（Include）",
        options=["ancestor", "descendant", "diagnosticCriteria"],
        help="ancestor=祖先一覧、descendant=子孫一覧、diagnosticCriteria=診断基準",
    )
    expand_children = st.sidebar.checkbox("子エンティティのタイトルを表示", value=False, help="ONにするとAPI呼出が増え表示が遅くなる場合があります")
    expand_parents = st.sidebar.checkbox("親エンティティのタイトルを表示", value=True)

    if not entity_id.strip():
        st.info("サイドバーで Entity ID を入力してください")
        st.stop()

    try:
        token = get_cached_token()

        # Build URL
        url = foundation_url(entity_id.strip())
        if include_opts:
            url += "?include=" + ",".join(include_opts)

        st.caption(f"`GET {url}`")
        data = api_get(url, token, lang=lang, use_cache=False)
        show_request_info(data)

        # --- Basic Info ---
        st.subheader("基本情報")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**タイトル:**", extract_text(data.get("title")))
            fsn = extract_text(data.get("fullySpecifiedName"))
            if fsn:
                st.write("**完全修飾名:**", fsn)
            class_kind = data.get("classKind")
            kind_labels = {"chapter": "章", "block": "ブロック", "category": "カテゴリ", "window": "ウィンドウ"}
            if class_kind:
                st.write("**分類種別:**", f"{class_kind}（{kind_labels.get(class_kind, '')}）")
            st.write("**Entity URI:**", data.get("@id"))
            if data.get("browserUrl"):
                st.write("**WHO ブラウザ:**", data.get("browserUrl"))

        with col2:
            definition = extract_text(data.get("definition"))
            if definition:
                st.write("**定義（Definition）:**")
                st.info(definition)
            long_def = extract_text(data.get("longDefinition"))
            if long_def:
                st.write("**詳細定義（Long Definition）:**")
                st.info(long_def)

        # --- Coding Note ---
        coding_note = extract_text(data.get("codingNote"))
        if coding_note:
            st.subheader("コーディングノート")
            st.markdown("コーディング時の注意事項・ガイドラインです。")
            st.warning(coding_note)

        # --- Synonyms ---
        synonyms = data.get("synonym") or []
        if synonyms:
            st.subheader("同義語（Synonym）")
            st.markdown("この概念を指す別の用語一覧です。")
            syn_labels = [extract_text(s.get("label")) for s in synonyms if isinstance(s, dict)]
            syn_labels = [s for s in syn_labels if s]
            for s in syn_labels:
                st.write(f"- {s}")

        # --- Inclusions ---
        inclusions = data.get("inclusion") or []
        if inclusions:
            st.subheader(f"包含項目（Inclusion）（{len(inclusions)}件）")
            st.markdown("この分類に含まれる診断用語です。")
            for inc in inclusions:
                if isinstance(inc, dict):
                    st.write(f"- {extract_text(inc.get('label'))}")

        # --- Exclusions ---
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

        # --- Parents ---
        parents = data.get("parent") or []
        if parents:
            st.subheader(f"親エンティティ（Parent）（{len(parents)}件）")
            st.markdown("Foundation では1つのエンティティが複数の親を持つことがあります（多階層構造）。")
            if expand_parents:
                for uri in parents[:30]:
                    title = resolve_uri_title(uri, token, lang)
                    st.write(f"- {title} (`{uri}`)")
            else:
                for uri in parents[:30]:
                    st.write(f"- `{uri}`")

        # --- Children ---
        children = data.get("child") or []
        if children:
            st.subheader(f"子エンティティ（Child）（{len(children)}件）")
            if expand_children:
                for uri in children[:50]:
                    title = resolve_uri_title(uri, token, lang)
                    st.write(f"- {title} (`{uri}`)")
            else:
                for uri in children[:50]:
                    st.write(f"- `{uri}`")
                if len(children) > 50:
                    st.caption(f"... 他 {len(children) - 50} 件")

        # --- Ancestors (if requested) ---
        ancestors = data.get("ancestor") or []
        if ancestors:
            st.subheader(f"祖先（Ancestor）（{len(ancestors)}件）")
            st.markdown("ルートまでの全ての上位エンティティです（include=ancestor 指定時）。")
            for uri in ancestors[:30]:
                title = resolve_uri_title(uri, token, lang)
                st.write(f"- {title} (`{uri}`)")

        # --- Descendants (if requested) ---
        descendants = data.get("descendant") or []
        if descendants:
            st.subheader(f"子孫（Descendant）（{len(descendants)}件）")
            st.markdown("配下の全てのエンティティです（include=descendant 指定時）。")
            for uri in descendants[:20]:
                title = resolve_uri_title(uri, token, lang)
                st.write(f"- {title} (`{uri}`)")
            if len(descendants) > 20:
                st.caption(f"... 他 {len(descendants) - 20} 件")

        # --- Diagnostic Criteria (if requested) ---
        diag = data.get("diagnosticCriteria")
        if diag:
            st.subheader("診断基準（Diagnostic Criteria）")
            st.markdown("この疾病の診断基準です（include=diagnosticCriteria 指定時）。")
            st.info(extract_text(diag))

        # --- Postcoordination Scale ---
        postcoord = data.get("postcoordinationScale") or []
        if postcoord:
            st.subheader(f"ポストコーディネーション軸（{len(postcoord)}軸）")
            st.markdown("このエンティティに付加できる追加情報（重症度・部位など）の軸です。")
            for ax in postcoord:
                if isinstance(ax, dict):
                    axis_name = ax.get("axisName", "")
                    required = ax.get("requiredPostcoordination", False)
                    allow_multi = ax.get("allowMultipleValues", "")
                    req_label = "必須" if required else "任意"
                    st.write(f"- **{axis_name}**（{req_label}）| 複数値: {allow_multi}")

        # --- Index Terms ---
        index_terms = data.get("indexTerm") or []
        if index_terms:
            st.subheader(f"索引語（Index Term）（{len(index_terms)}件）")
            st.markdown("検索でヒットさせるための索引用語です。")
            for it in index_terms[:30]:
                if isinstance(it, dict):
                    st.write(f"- {extract_text(it.get('label'))}")
            if len(index_terms) > 30:
                st.caption(f"... 他 {len(index_terms) - 30} 件")

        # --- Language Fallback Note ---
        fb = data.get("_lang_fallback")
        if fb:
            st.warning(f"言語フォールバック: 日本語（{fb.get('requested')}）でのリクエストが失敗したため、英語（{fb.get('used')}）で取得しました（ステータス: {fb.get('reason_status')}）")

        # --- Raw JSON ---
        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")
