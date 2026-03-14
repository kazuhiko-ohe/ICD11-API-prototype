"""
Page 8: DORIS (Underlying Cause of Death)
==========================================
POST /icd/release/11/{ver}/doris — 死亡診断書からの根本死因判定
"""

import streamlit as st
from icd11_core import (
    get_cached_token, api_post, extract_text,
    doris_url, show_raw_json,
    sidebar_lang_selector, sidebar_release_selector,
)

st.set_page_config(page_title="DORIS", layout="wide")
st.title("8. DORIS（根本死因判定）")
st.caption("`POST /icd/release/11/{ver}/doris` — 死亡診断書からの根本死因判定")
st.markdown("""
**DORIS**（Digital Open Rule Integrated cause of death Selection）は、
死亡診断書に記載された死因コードから **根本死因（Underlying Cause of Death）** を自動判定する API です。

WHO の死因統計ルール（ICD-11 Mortality Rules）に基づき、Part 1（直接死因の連鎖）と Part 2（寄与した状態）の
情報を総合的に分析して根本死因を決定します。
""")

st.warning("DORIS は pre-release（プレリリース版）API です。パラメータや動作が今後変更される場合があります。")

# --- Sidebar ---
lang = sidebar_lang_selector()
release_id = sidebar_release_selector()

st.sidebar.divider()
st.sidebar.subheader("故人情報")
sex = st.sidebar.selectbox(
    "性別",
    options=["1 (男性)", "2 (女性)", "9 (不明)"],
    index=0,
    help="故人の性別を選択",
)
sex_code = sex.split(" ")[0]
estimated_age = st.sidebar.text_input(
    "推定年齢",
    value="65",
    help="故人の年齢を入力（例: 65）",
)
date_birth = st.sidebar.text_input(
    "生年月日（YYYY-MM-DD）",
    value="",
    help="任意項目。生年月日を入力（例: 1960-01-15）",
)
date_death = st.sidebar.text_input(
    "死亡日（YYYY-MM-DD）",
    value="",
    help="任意項目。死亡日を入力（例: 2025-06-01）",
)

st.divider()

st.subheader("死亡診断書 — 死因の記載")
st.markdown("""
死亡診断書の各行に **ICD-11 コード** を入力してください。

- **Part 1（直接死因の連鎖）**: Line a（直接死因）→ Line b → c → d（順に根本原因へ遡る）
- **Part 2（寄与した状態）**: 直接死因には含まれないが、死亡に寄与した状態
""")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Part 1（直接死因の連鎖）**")
    cause_a = st.text_input(
        "Line a（直接死因）",
        value="",
        help="最も直接的な死因のコードを入力（例: 5A11=2型糖尿病）",
    )
    cause_b = st.text_input(
        "Line b（上記の原因）",
        value="",
        help="Line a の原因となった状態のコードを入力（例: BA80=アテローム性動脈硬化症）",
    )
    cause_c = st.text_input(
        "Line c（上記の原因）",
        value="",
        help="Line b の原因となった状態のコードを入力",
    )
    cause_d = st.text_input(
        "Line d（上記の原因）",
        value="",
        help="Line c の原因となった状態のコードを入力（最も根本的な原因）",
    )

with col2:
    st.markdown("**Part 2（寄与した状態）**")
    cause_e = st.text_input(
        "Line e（寄与した状態）",
        value="",
        help="死亡に寄与したが直接の死因連鎖には含まれない状態（例: BA00=本態性高血圧症）",
    )

st.divider()

st.subheader("付加情報")
st.markdown("死亡の状況に関する追加情報です。根本死因の判定精度に影響します。")
col3, col4 = st.columns(2)
with col3:
    manner_of_death = st.selectbox(
        "死亡の態様",
        options=[
            "0 (疾病)", "1 (事故)", "2 (自傷行為)",
            "3 (暴行)", "4 (法的介入)", "5 (戦争)",
            "6 (判定不能)", "9 (不明/保留)"
        ],
        index=0,
        help="死亡の態様（外因死か病死かなど）を選択",
    )
    manner_code = manner_of_death.split(" ")[0]
with col4:
    surgery = st.selectbox(
        "4週間以内の手術",
        options=["9 (不明)", "1 (あり)", "2 (なし)"],
        index=0,
        help="死亡前4週間以内に手術を受けたかどうか",
    )
    surgery_code = surgery.split(" ")[0]
    autopsy = st.selectbox(
        "解剖の実施",
        options=["9 (不明)", "1 (あり)", "2 (なし)"],
        index=0,
        help="解剖（剖検）が実施されたかどうか",
    )
    autopsy_code = autopsy.split(" ")[0]

st.divider()

if st.button("DORIS を実行", type="primary"):
    if not any([cause_a.strip(), cause_b.strip(), cause_c.strip(), cause_d.strip(), cause_e.strip()]):
        st.error("少なくとも1つの死因コードを入力してください。")
        st.stop()

    try:
        token = get_cached_token()
        url = doris_url(release_id)
        st.caption(f"`POST {url}`")

        body = {
            "sex": sex_code,
            "estimatedAge": estimated_age.strip(),
            "mannerOfDeath": manner_code,
            "surgery": surgery_code,
            "autopsyRequested": autopsy_code,
        }

        if date_birth.strip():
            body["dateBirth"] = date_birth.strip()
        if date_death.strip():
            body["dateDeath"] = date_death.strip()

        # Cause of death codes
        if cause_a.strip():
            body["causeOfDeathCodeA"] = cause_a.strip()
        if cause_b.strip():
            body["causeOfDeathCodeB"] = cause_b.strip()
        if cause_c.strip():
            body["causeOfDeathCodeC"] = cause_c.strip()
        if cause_d.strip():
            body["causeOfDeathCodeD"] = cause_d.strip()
        if cause_e.strip():
            body["causeOfDeathCodeE"] = cause_e.strip()

        with st.expander("送信したリクエストボディ", expanded=False):
            st.json(body)

        data = api_post(url, token, lang=lang, json_body=body)

        # --- Result ---
        st.subheader("DORIS 判定結果")

        reject = data.get("reject", False)
        if reject:
            st.error("DORIS はこの死亡診断書を処理できませんでした（reject）")
        else:
            st.success("DORIS による根本死因判定が完了しました")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.write("**根本死因コード（Underlying Cause）:**", data.get("code"))
            st.write("**基幹コード（Stem Code）:**", data.get("stemCode"))
            st.write("**URI:**", data.get("uri"))
            st.write("**Stem URI:**", data.get("stemURI"))

        with col_r2:
            error_msg = data.get("error")
            if error_msg:
                st.error(f"エラー: {error_msg}")
            warning_msg = data.get("warning")
            if warning_msg:
                st.warning(f"警告: {warning_msg}")

        # Report
        report = data.get("report")
        if report:
            st.subheader("処理レポート")
            st.markdown("DORIS が根本死因を判定するまでの処理過程です。")
            st.text(report)

        # Tabular report
        tabular = data.get("tabularReport")
        if tabular:
            with st.expander("表形式レポート（Tabular Report）", expanded=False):
                st.text(tabular)

        show_raw_json(data)

    except Exception as e:
        st.error(f"エラー: {e}")
