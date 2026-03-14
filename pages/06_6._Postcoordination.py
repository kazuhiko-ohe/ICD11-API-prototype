"""
Page 6: Postcoordination
========================
MMS Entity のポストコーディネーション軸を閲覧し、
codeinfo / describe で組合せコードの検証を行う。
"""

import streamlit as st
import pandas as pd
from icd11_core import (
    get_cached_token, api_get, extract_text,
    mms_entity_url, mms_codeinfo_url, mms_describe_url,
    show_raw_json, show_request_info,
    sidebar_lang_selector, sidebar_release_selector,
    resolve_uri_title,
)

st.set_page_config(page_title="Postcoordination", layout="wide")
st.title("6. Postcoordination（ポストコーディネーション）")
st.caption("ポストコーディネーション軸の閲覧と組合せコードの検証")
st.markdown("""
**ポストコーディネーション**とは、基幹コード（Stem Code）に追加情報（重症度・部位・病因など）を付加して、
より詳細な分類を行う仕組みです。

- **Step 1**: MMS コードを入力して、利用可能なポストコーディネーション軸を確認
- **Step 2**: 組合せコードを入力して、その妥当性を検証（`codeinfo` + `describe` API）
""")

# --- Sidebar ---
lang = sidebar_lang_selector()
release_id = sidebar_release_selector()

st.sidebar.divider()
st.sidebar.subheader("Step 1: 軸の確認")
mms_code = st.sidebar.text_input(
    "MMS コード（軸の確認用）",
    value="5A11",
    help="ポストコーディネーション軸を確認したい MMS コードを入力（例: 5A11=2型糖尿病）",
)

st.sidebar.divider()
st.sidebar.subheader("Step 2: 組合せコードの検証")
combo_code = st.sidebar.text_input(
    "ポストコーディネーション付きコード",
    value="",
    help="基幹コードとポストコーディネーションを & で結合したコードを入力（例: 5A11&XS7R）",
)

try:
    token = get_cached_token()

    # ============================================================
    # Step 1: MMS Entity → postcoordinationScale
    # ============================================================
    if mms_code.strip():
        st.subheader("Step 1: ポストコーディネーション軸の確認")
        st.markdown(f"MMS コード **{mms_code.strip()}** に定義されたポストコーディネーション軸を表示します。")

        # codeinfo でURI解決
        codeinfo_url = mms_codeinfo_url(mms_code.strip(), release_id)
        codeinfo = api_get(codeinfo_url, token, lang=lang, use_cache=False)
        stem_uri = codeinfo.get("stemId")

        if stem_uri:
            entity_id = stem_uri.rstrip("/").split("/")[-1]
            url = mms_entity_url(entity_id, release_id)
            st.caption(f"`GET {url}`")
            data = api_get(url, token, lang=lang, use_cache=False)
            show_request_info(data)

            st.write(f"**コード:** {data.get('code')} — **タイトル:** {extract_text(data.get('title'))}")

            postcoord = data.get("postcoordinationScale") or []
            if postcoord:
                st.write(f"**利用可能な軸:** {len(postcoord)} 軸")
                st.markdown("各軸の詳細（必須/任意、複数値の可否、選択肢の例）を一覧表示します。")

                rows = []
                for ax in postcoord:
                    if isinstance(ax, dict):
                        axis_name = ax.get("axisName", "")
                        required = ax.get("requiredPostcoordination", False)
                        allow_multi = ax.get("allowMultipleValues", "")

                        scale_entities = ax.get("scaleEntity") or []
                        scale_strs = []
                        for se in scale_entities[:5]:
                            if isinstance(se, str):
                                title = resolve_uri_title(se, token, lang)
                                scale_strs.append(f"{title}")

                        rows.append({
                            "軸名": axis_name,
                            "必須/任意": "必須" if required else "任意",
                            "複数値": "可" if allow_multi else "不可",
                            "選択肢の例（最大5件）": "; ".join(scale_strs),
                        })

                st.dataframe(pd.DataFrame(rows), use_container_width=True)

                # Detail per axis
                with st.expander("軸の詳細（Scale Entity URI 一覧）"):
                    for ax in postcoord:
                        if isinstance(ax, dict):
                            st.markdown(f"**{ax.get('axisName', '')}**")
                            for se in (ax.get("scaleEntity") or []):
                                st.write(f"  - `{se}`")
            else:
                st.info("このエンティティにはポストコーディネーション軸が定義されていません。")

            show_raw_json(data, "MMS Entity レスポンス")
        else:
            st.error(f"コードを解決できませんでした: {mms_code}")

    # ============================================================
    # Step 2: Validate postcoordinated combination
    # ============================================================
    if combo_code.strip():
        st.divider()
        st.subheader("Step 2: 組合せコードの検証")
        st.markdown(f"""
ポストコーディネーション付きコード **{combo_code.strip()}** を `codeinfo`（柔軟モード）と `describe` で解析・検証します。
基幹コードと各ポストコーディネーション軸が正しく認識されるか確認できます。
""")

        # codeinfo (flexible)
        ci_url = mms_codeinfo_url(combo_code.strip(), release_id) + "?flexiblemode=true"
        st.caption(f"`GET {ci_url}`")
        ci_data = api_get(ci_url, token, lang=lang, use_cache=False)
        show_request_info(ci_data)

        st.markdown("**codeinfo 解析結果:**")
        st.write("**基幹コード（Stem Code）:**", ci_data.get("stemCode"))
        st.write("**Stem URI:**", ci_data.get("stemId"))

        pc = ci_data.get("postcoordination") or []
        if pc:
            st.write(f"**認識されたポストコーディネーション軸:** {len(pc)} 軸")
            for ax in pc:
                if isinstance(ax, dict):
                    st.write(f"- **{ax.get('axisName', '')}**: {ax.get('value', '')} — {extract_text(ax.get('title'))}")

        other = ci_data.get("otherPostcoordination") or {}
        if other:
            st.warning("認識されなかったポストコーディネーション要素:")
            st.markdown("以下の要素は標準的なポストコーディネーション軸として認識されませんでした。")
            st.json(other)

        show_raw_json(ci_data, "codeinfo レスポンス")

        # describe
        desc_url = f"{mms_describe_url(release_id)}?code={combo_code.strip()}&flexiblemode=true"
        st.caption(f"`GET {desc_url}`")
        desc_data = api_get(desc_url, token, lang=lang, use_cache=False)

        st.markdown("**describe 記述結果:**")
        stem_ent = desc_data.get("stemEntity") or {}
        if stem_ent:
            st.write(f"**基幹エンティティ:** {stem_ent.get('theCode')} — {extract_text(stem_ent.get('title'))}")

        pc_ents = desc_data.get("postcoordinationEntities") or []
        if pc_ents:
            st.markdown("**ポストコーディネーション要素:**")
            for p in pc_ents:
                if isinstance(p, dict):
                    st.write(f"- **{p.get('axisName', '')}**: {extract_text(p.get('title'))} (コード={p.get('theCode', '')})")

        show_raw_json(desc_data, "describe レスポンス")

except Exception as e:
    st.error(f"エラー: {e}")
