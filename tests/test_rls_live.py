"""
Live Row-Level-Security check against the real Supabase project.
Creates two temporary users, verifies isolation, then deletes them.

Skipped unless RUN_LIVE_TESTS=1 and a .env with SUPABASE_URL, SUPABASE_KEY and
SUPABASE_SERVICE_ROLE_KEY is present:   RUN_LIVE_TESTS=1 pytest tests/test_rls_live.py -v
"""
import os
import secrets
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1" or not ENV.get("SUPABASE_SERVICE_ROLE_KEY"),
    reason="live test: set RUN_LIVE_TESTS=1 and provide .env credentials",
)

URL = (ENV.get("SUPABASE_URL") or "").strip().rstrip("/")
ANON = (ENV.get("SUPABASE_KEY") or "").strip()
SERVICE = (ENV.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
ADMIN = {"apikey": SERVICE, "Authorization": f"Bearer {SERVICE}"}


@pytest.fixture(scope="module")
def two_users():
    from supabase import create_client
    password = secrets.token_urlsafe(16)
    users = {}
    try:
        for name in ("a", "b"):
            email = f"sentinel-e2e-{name}-{secrets.token_hex(3)}@example.com"
            r = requests.post(f"{URL}/auth/v1/admin/users", headers=ADMIN,
                              json={"email": email, "password": password, "email_confirm": True})
            r.raise_for_status()
            client = create_client(URL, ANON)
            client.auth.sign_in_with_password({"email": email, "password": password})
            users[name] = {"id": r.json()["id"], "client": client}
        users["a"]["client"].table("watchlist").insert({"ticker": "AAPL", "user_id": users["a"]["id"]}).execute()
        users["b"]["client"].table("watchlist").insert({"ticker": "INFY.NS", "user_id": users["b"]["id"]}).execute()
        yield users
    finally:
        for u in users.values():
            requests.delete(f"{URL}/rest/v1/watchlist?user_id=eq.{u['id']}", headers=ADMIN)
            requests.delete(f"{URL}/auth/v1/admin/users/{u['id']}", headers=ADMIN)


@pytest.mark.parametrize("table", ["watchlist", "market_log", "price_history"])
def test_anonymous_visitor_reads_nothing(table):
    r = requests.get(f"{URL}/rest/v1/{table}?select=*&limit=5",
                     headers={"apikey": ANON, "Authorization": f"Bearer {ANON}"})
    assert not r.ok or r.json() == []


def test_users_only_see_their_own_watchlist(two_users):
    a = two_users["a"]["client"].table("watchlist").select("ticker").execute().data
    b = two_users["b"]["client"].table("watchlist").select("ticker").execute().data
    assert [r["ticker"] for r in a] == ["AAPL"]
    assert [r["ticker"] for r in b] == ["INFY.NS"]


def test_user_cannot_write_into_or_delete_from_another_watchlist(two_users):
    a, b = two_users["a"], two_users["b"]
    with pytest.raises(Exception):
        a["client"].table("watchlist").insert({"ticker": "EVIL", "user_id": b["id"]}).execute()
    a["client"].table("watchlist").delete().eq("user_id", b["id"]).execute()
    assert len(b["client"].table("watchlist").select("id").execute().data) == 1


def test_duplicate_watchlist_entry_rejected(two_users):
    a = two_users["a"]
    with pytest.raises(Exception):
        a["client"].table("watchlist").insert({"ticker": "AAPL", "user_id": a["id"]}).execute()


def test_logged_in_user_reads_shared_market_data(two_users):
    rows = two_users["a"]["client"].table("price_history").select("ticker").eq("ticker", "AAPL").limit(1).execute().data
    assert len(rows) == 1
