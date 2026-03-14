"""
icd11_core.py — ICD-11 API 共通モジュール
==========================================
認証・API呼出・キャッシュ・テキスト抽出を集約。
各 Streamlit ページから import して使う。
"""

import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List, Tuple

# ============================================================
# Config
# ============================================================

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
API_BASE = "https://id.who.int"
DEFAULT_RELEASE_ID = "2025-01"

load_dotenv()
CLIENT_ID = os.environ.get("ICD_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ICD_CLIENT_SECRET")

# ============================================================
# OAuth2 Token
# ============================================================

def get_token() -> str:
    """OAuth2 Client Credentials でアクセストークンを取得"""
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("ICD_CLIENT_ID / ICD_CLIENT_SECRET が .env に設定されていません")

    r = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "icdapi_access",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


@st.cache_data(ttl=3000, show_spinner=False)
def get_cached_token() -> str:
    """トークンをキャッシュ（50分TTL、有効期限60分のため余裕をもって更新）"""
    return get_token()

# ============================================================
# API GET 共通
# ============================================================

_ENTITY_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}


def _normalize_url(url: str) -> str:
    if not isinstance(url, str):
        url = str(url)
    return url.replace("http://", "https://", 1)


def _build_headers(token: str, lang: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Language": lang,
        "API-Version": "v2",
    }


def api_get(url: str, token: str, lang: str = "en", use_cache: bool = True) -> Dict[str, Any]:
    """
    GET 共通（キャッシュ + 日本語フォールバック）
    返り値は JSON dict。_raw_request に {method, url, headers, status_code} を付与。
    """
    url = _normalize_url(url)
    key = (url, lang)

    if use_cache and key in _ENTITY_CACHE:
        return _ENTITY_CACHE[key]

    headers = _build_headers(token, lang)
    r = requests.get(url, headers=headers, timeout=30)

    # 日本語フォールバック
    if lang.lower().startswith("ja") and r.status_code in (400, 404, 406):
        headers_en = _build_headers(token, "en")
        r2 = requests.get(url, headers=headers_en, timeout=30)
        if r2.status_code == 200:
            data = r2.json()
            if isinstance(data, dict):
                data = dict(data)
                data["_lang_fallback"] = {"requested": lang, "used": "en", "reason_status": r.status_code}
                data["_raw_request"] = {"method": "GET", "url": url, "lang": "en (fallback)", "status": r2.status_code}
            if use_cache:
                _ENTITY_CACHE[(url, "en")] = data
                _ENTITY_CACHE[key] = data
            return data

    if r.status_code != 200:
        body = (r.text or "")[:500]
        raise requests.HTTPError(f"{r.status_code} Error: {url} (lang={lang}) body={body}", response=r)

    data = r.json()
    if isinstance(data, dict):
        data["_raw_request"] = {"method": "GET", "url": url, "lang": lang, "status": r.status_code}

    if use_cache:
        _ENTITY_CACHE[key] = data
    return data


def api_post(url: str, token: str, lang: str = "en",
             data: Optional[Dict] = None, json_body: Optional[Dict] = None) -> Dict[str, Any]:
    """POST 共通"""
    url = _normalize_url(url)
    headers = _build_headers(token, lang)
    r = requests.post(url, headers=headers, data=data, json=json_body, timeout=60)

    if r.status_code != 200:
        body = (r.text or "")[:500]
        raise requests.HTTPError(f"{r.status_code} Error: {url} (lang={lang}) body={body}", response=r)

    result = r.json()
    if isinstance(result, dict):
        result["_raw_request"] = {"method": "POST", "url": url, "lang": lang, "status": r.status_code}
    return result

# ============================================================
# JSON-LD テキスト抽出
# ============================================================

def extract_text(obj: Any) -> Optional[str]:
    """ICD JSON-LD のテキスト抽出（多層ネスト対応）"""
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        if "@value" in obj and isinstance(obj["@value"], str):
            return obj["@value"]
        for k in ("ja", "en"):
            v = obj.get(k)
            if isinstance(v, str):
                return v
        if "label" in obj:
            return extract_text(obj.get("label"))
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return str(obj)
    if isinstance(obj, list):
        parts = [extract_text(x) for x in obj]
        parts = [p for p in parts if p]
        return "; ".join(parts) if parts else None
    return str(obj)

# ============================================================
# URL ヘルパー
# ============================================================

def foundation_url(entity_id: str) -> str:
    return f"{API_BASE}/icd/entity/{entity_id}"


def mms_release_url(release_id: str = DEFAULT_RELEASE_ID) -> str:
    return f"{API_BASE}/icd/release/11/{release_id}/mms"


def mms_entity_url(entity_id: str, release_id: str = DEFAULT_RELEASE_ID) -> str:
    return f"{API_BASE}/icd/release/11/{release_id}/mms/{entity_id}"


def mms_search_url(release_id: str = DEFAULT_RELEASE_ID) -> str:
    return f"{API_BASE}/icd/release/11/{release_id}/mms/search"


def mms_autocode_url(release_id: str = DEFAULT_RELEASE_ID) -> str:
    return f"{API_BASE}/icd/release/11/{release_id}/mms/autocode"


def mms_codeinfo_url(code: str, release_id: str = DEFAULT_RELEASE_ID) -> str:
    return f"{API_BASE}/icd/release/11/{release_id}/mms/codeinfo/{code}"


def mms_lookup_url(release_id: str = DEFAULT_RELEASE_ID) -> str:
    return f"{API_BASE}/icd/release/11/{release_id}/mms/lookup"


def mms_describe_url(release_id: str = DEFAULT_RELEASE_ID) -> str:
    return f"{API_BASE}/icd/release/11/{release_id}/mms/describe"


def foundation_search_url() -> str:
    return f"{API_BASE}/icd/entity/search"


def foundation_autocode_url() -> str:
    return f"{API_BASE}/icd/entity/autocode"


def icd10_release_url(release_id: str = "2019") -> str:
    return f"{API_BASE}/icd/release/10/{release_id}"


def doris_url(release_id: str = DEFAULT_RELEASE_ID) -> str:
    return f"{API_BASE}/icd/release/11/{release_id}/doris"

# ============================================================
# UI ヘルパー
# ============================================================

def show_raw_json(data: Any, title: str = "API レスポンス JSON（様式確認用）"):
    """Expander 内に生 JSON を表示"""
    display_data = data
    if isinstance(data, dict):
        display_data = {k: v for k, v in data.items() if not k.startswith("_")}
    with st.expander(title, expanded=False):
        st.code(json.dumps(display_data, ensure_ascii=False, indent=2), language="json")


def show_request_info(data: Dict[str, Any]):
    """リクエスト情報を表示"""
    req = data.get("_raw_request")
    if req:
        st.caption(f"`{req.get('method', 'GET')} {req.get('url', '')}` | lang={req.get('lang')} | status={req.get('status')}")


def sidebar_lang_selector() -> str:
    return st.sidebar.selectbox(
        "言語 / Language",
        options=["en", "ja"],
        index=0,
        help="API レスポンスの言語。日本語未対応のエンティティは自動で英語にフォールバックします",
    )


def sidebar_release_selector() -> str:
    return st.sidebar.selectbox(
        "リリース版 / Release ID",
        options=["2025-01", "2024-01", "2023-01", "2022-02", "2021-05", "2020-09", "2019-04"],
        index=0,
        help="ICD-11 のリリースバージョンを選択",
    )


def resolve_uri_title(uri: str, token: str, lang: str) -> str:
    """URI からタイトルを解決"""
    try:
        e = api_get(uri, token, lang=lang)
        t = extract_text(e.get("title"))
        return t or uri
    except Exception:
        return uri
