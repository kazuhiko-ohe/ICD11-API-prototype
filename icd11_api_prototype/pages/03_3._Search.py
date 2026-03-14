"""
Page 3: Search (Foundation / MMS)
=================================
GET /icd/entity/search                          — Foundation 全文検索
GET /icd/release/11/{ver}/mms/search            — MMS 全文検索
"""

import streamlit as st
import pandas as pd
from icd11_core import (
    get_cached_token, api_get, extract_text,
    foundation_search_url, mms_search_url,
    show_raw_json, show_request_info,
    sidebar_lang_selector, sidebar_release_selector,
)

st.set_page_config(page_title="Search", layout="wide")
st.title("3. Search（検索）")
st.caption("Foundation / MMS の全文検索")
st.markdown("""
ICD-11 のエンティティをキーワードで検索します。
MMS 検索ではコード付きの結果が、Foundation 検索では概念レベルの結果が返されます。
""")

# --- Sidebar ---
lang = sidebar_lang_selector()
release_id = sidebar_release_selector()

st.sidebar.divider()
search_target = st.sidebar.radio(
    "検索対象",
    ["MMS（コード付き検索）", "Foundation（概念検索）"],
    help="MMS: 統計用コード体系から検索。Foundation: 基盤層の全概念から検索",
)
query = st.sidebar.text_input(
    "検索テキスト",
    value="diabetes",
    help="検索したいキーワードを入力（例: diabetes, lung cancer, 肺炎, 高血圧）",
)

st.sidebar.divider()
st.sidebar.subheader("検索オプション")
use_flexisearch = st.sidebar.checkbox("あいまい検索（Flexisearch）", value=False, help="スペルミスや省略形でもヒットしやすくなります")
flat_results = st.sidebar.checkbox("フラット表示", value=True, help="ONで一覧表示、OFFで階層グループ表示")

is_mms = search_target.startswith("MMS")
if is_mms:
    medical_coding_mode = st.sidebar.checkbox(
        "医療コーディングモード",
        value=True,
        help="ONにするとコード割当可能なエンティティのみ返されます（MMS検索時のみ有効）",
    )
else:
    medical_coding_mode = False

props_options = ["Title", "Synonym", "FullySpecifiedName", "Definition", "Exclusion"]
props_to_search = st.sidebar.multiselect(
    "検索対象プロパティ",
    options=props_options,
    default=[],
    help="空の場合は全プロパティを検索。限定する場合は選択してください",
)

highlighting = st.sidebar.checkbox("ハイライト表示", value=True, help="検索キーワードをハイライト表示します")
subtrees_filter = st.sidebar.text_input("サブツリーフィルタ（URI）", value="", help="特定のサブツリー配下に限定する場合にFoundation URIを入力")
chapter_filter = st.sidebar.text_input("章フィルタ", value="", help="特定の章に限定する場合に入力")

if not query.strip():
    st.info("サイドバーで検索テキストを入力してください")
    st.stop()

try:
    token = get_cached_token()

    if is_mms:
        base_url = mms_search_url(release_id)
    else:
        base_url = foundation_search_url()

    params = f"?q={query.strip()}"
    if use_flexisearch:
        params += "&useFlexisearch=true"
    if flat_results:
        params += "&flatResults=true"
    if highlighting:
        params += "&highlightingEnabled=true"
    if medical_coding_mode and is_mms:
        params += "&medicalCodingMode=true"
    if props_to_search:
        params += "&propertiesToBeSearched=" + ",".join(props_to_search)
    if subtrees_filter.strip():
        params += f"&subtreesFilter={subtrees_filter.strip()}"
    if chapter_filter.strip():
        params += f"&chapterFilter={chapter_filter.strip()}"

    url = base_url + params
    st.caption(f"`GET {url}`")

    data = api_get(url, token, lang=lang, use_cache=False)
    show_request_info(data)

    error = data.get("error")
    if error:
        st.error(f"検索エラー: {error}")

    word_suggestions = data.get("wordSuggestionsChosenByUser") or data.get("words") or []
    if word_suggestions:
        st.write("**関連語の提案:**", ", ".join(str(w) for w in word_suggestions))

    result_count = data.get("resultChopped", False)
    unique_entities = data.get("uniqueSearchResultsCount", "?")
    chopped_msg = "（結果が多いため一部省略）" if result_count else ""
    st.write(f"**検索結果:** {unique_entities} 件のユニークなエンティティ{chopped_msg}")

    dest_entities = data.get("destinationEntities") or []
    if dest_entities:
        st.subheader(f"検索結果（{len(dest_entities)}件）")

        rows = []
        for ent in dest_entities:
            title_text = extract_text(ent.get("title"))
            matching_pvs = ent.get("matchingPVs") or []
            matching_labels = [extract_text(pv.get("label")) for pv in matching_pvs if isinstance(pv, dict)]
            matching_str = "; ".join([l for l in matching_labels if l])

            rows.append({
                "コード": ent.get("theCode", ""),
                "タイトル": title_text,
                "スコア": ent.get("score", ""),
                "章": ent.get("chapter", ""),
                "マッチした箇所": matching_str[:100],
                "Entity ID": ent.get("id", ""),
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    else:
        st.info("検索結果が見つかりませんでした。検索テキストやオプションを変更して再試行してください。")

    show_raw_json(data)

except Exception as e:
    st.error(f"エラー: {e}")
