"""
FDIC Data Layer
Fetches data from the FDIC BankFind Suite API and caches it locally in SQLite.
Cache refreshes automatically every 90 days (aligned with quarterly Call Report releases).
"""

import io
import sqlite3
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

FDIC_BASE    = "https://api.fdic.gov/banks"
CACHE_DB     = Path(__file__).parent / "cache.db"
CACHE_TTL    = 90   # days between automatic refreshes
HISTORY_YEARS = 12  # years of financial history to fetch


# ── Cache helpers ──────────────────────────────────────────────────────────────

def _db():
    conn = sqlite3.connect(CACHE_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cache_status (
            cert INTEGER, data_type TEXT, fetched_at TEXT,
            PRIMARY KEY (cert, data_type)
        );
        CREATE TABLE IF NOT EXISTS cache_data (
            cert INTEGER, data_type TEXT, payload TEXT,
            PRIMARY KEY (cert, data_type)
        );
        CREATE TABLE IF NOT EXISTS insights_cache (
            cert INTEGER PRIMARY KEY,
            summary TEXT,
            input_hash TEXT,
            generated_at TEXT
        );
    """)
    return conn


def is_fresh(cert, data_type):
    conn = _db()
    row  = conn.execute(
        "SELECT fetched_at FROM cache_status WHERE cert=? AND data_type=?",
        (cert, data_type)
    ).fetchone()
    conn.close()
    if not row:
        return False
    return datetime.now() - datetime.fromisoformat(row[0]) < timedelta(days=CACHE_TTL)


def last_refreshed(cert, data_type):
    conn = _db()
    row  = conn.execute(
        "SELECT fetched_at FROM cache_status WHERE cert=? AND data_type=?",
        (cert, data_type)
    ).fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row else None


def _save(cert, data_type, df):
    conn = _db()
    conn.execute("INSERT OR REPLACE INTO cache_data VALUES (?,?,?)",
                 (cert, data_type, df.to_json(orient="records", date_format="iso")))
    conn.execute("INSERT OR REPLACE INTO cache_status VALUES (?,?,?)",
                 (cert, data_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def _load(cert, data_type):
    conn = _db()
    row  = conn.execute(
        "SELECT payload FROM cache_data WHERE cert=? AND data_type=?",
        (cert, data_type)
    ).fetchone()
    conn.close()
    if not row:
        return pd.DataFrame()
    return pd.read_json(io.StringIO(row[0]), orient="records")


# ── Insights cache ────────────────────────────────────────────────────────────

def get_cached_insights(cert):
    conn = _db()
    row = conn.execute(
        "SELECT summary, input_hash, generated_at FROM insights_cache WHERE cert=?",
        (cert,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"summary": row[0], "input_hash": row[1], "generated_at": row[2]}


def save_insights(cert, summary, input_hash):
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO insights_cache VALUES (?,?,?,?)",
        (cert, summary, input_hash, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# ── API helpers ────────────────────────────────────────────────────────────────

def _get(endpoint, params):
    resp = requests.get(f"{FDIC_BASE}/{endpoint}", params={**params, "format": "json"},
                        timeout=60)
    resp.raise_for_status()
    return [r["data"] for r in resp.json().get("data", [])]


def _paginate(endpoint, params):
    records, offset, limit = [], 0, 10000
    while True:
        batch = _get(endpoint, {**params, "limit": limit, "offset": offset})
        records.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return records


def _to_df(records, numeric_cols=None):
    df = pd.DataFrame(records) if records else pd.DataFrame()
    if not df.empty and numeric_cols:
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ── FDIC fetch functions ───────────────────────────────────────────────────────

def fetch_institution(cert):
    rows = _get("institutions", {
        "filters": f"CERT:{cert}",
        "fields": ("CERT,NAME,CITY,STALP,STNAME,ASSET,DEP,NETINC,ROA,ROE,NIMY,EEFFR,"
                   "OFFICES,NUMEMP,CBSA,CBSA_NO,CBSA_METRO_FLG,ESTYMD,WEBADDR,"
                   "MDI_STATUS_DESC,BKCLASS,NAMEHCR,ACTIVE,HCTMULT"),
        "limit": 1,
    })
    df = _to_df(rows, ["ASSET", "DEP", "NETINC", "ROA", "ROE", "NIMY",
                        "EEFFR", "OFFICES", "NUMEMP", "CBSA_NO"])
    return df


def fetch_financials(cert):
    start = datetime.now().year - HISTORY_YEARS
    rows  = _paginate("financials", {
        "filters": f"CERT:{cert} AND REPDTE:[{start}0101 TO 99991231]",
        "fields": ("CERT,REPDTE,ASSET,DEP,DEPDOM,COREDEP,LNLSNET,"
                   "NETINC,ROA,ROE,NIMY,EEFFR,"
                   "NTLNLSR,NCLNLSR,EQ,RBC1AAJ,IDT1RWAJR,"
                   "NUMEMP,OFFDOM,NONII,INTINC,EINTEXP"),
        "sort_by": "REPDTE", "sort_order": "ASC",
    })
    df = _to_df(rows, ["ASSET", "DEP", "DEPDOM", "COREDEP", "LNLSNET",
                        "NETINC", "ROA", "ROE", "NIMY", "EEFFR",
                        "NTLNLSR", "NCLNLSR", "EQ", "RBC1AAJ", "IDT1RWAJR",
                        "NUMEMP", "OFFDOM", "NONII", "INTINC", "EINTEXP"])
    if not df.empty and "REPDTE" in df.columns:
        df["date"] = pd.to_datetime(df["REPDTE"].astype(str), format="%Y%m%d", errors="coerce")
        df["year"] = df["date"].dt.year
        df["quarter"] = df["date"].dt.quarter
    return df


def fetch_sod(cert, start_year=2010):
    rows = _paginate("sod", {
        "filters": f"CERT:{cert} AND YEAR:[{start_year} TO 9999]",
        "fields": ("CERT,NAMEFULL,YEAR,DEPDOM,DEPSUMBR,ZIPBR,CITYBR,"
                   "CNTYNAMB,STALPBR,BRNUM,NAMEBR,ADDRESBR,"
                   "SIMS_LATITUDE,SIMS_LONGITUDE"),
        "sort_by": "YEAR", "sort_order": "ASC",
    })
    df = _to_df(rows, ["YEAR", "DEPDOM", "DEPSUMBR", "BRNUM",
                        "SIMS_LATITUDE", "SIMS_LONGITUDE"])
    # Normalise county names — FDIC sometimes changes casing across years
    # (e.g. "McIntosh" vs "Mcintosh"), which would create duplicate entries
    if not df.empty and "CNTYNAMB" in df.columns:
        df["CNTYNAMB"] = df["CNTYNAMB"].astype(str).str.title()
    return df


def fetch_locations(cert):
    rows = _paginate("locations", {
        "filters": f"CERT:{cert}",
        "fields": ("CERT,NAME,OFFNUM,OFFNAME,MAINOFF,SERVTYPE_DESC,"
                   "ADDRESS,CITY,STNAME,ZIP,COUNTY,LATITUDE,LONGITUDE,CBSA,ACQDATE"),
    })
    return _to_df(rows, ["LATITUDE", "LONGITUDE", "OFFNUM"])


def fetch_history(cert):
    rows = _paginate("history", {
        "filters": f"CERT:{cert}",
        "fields": "CERT,INSTNAME,CHANGECODE,CHANGECODE_DESC,EFFDATE,PROCDATE,OFF_NAME,OFF_PCITY",
        "sort_by": "EFFDATE", "sort_order": "ASC",
    })
    return _to_df(rows)


def fetch_peers(cert, client_assets, stalp, cbsa_no=None, min_peers=5):
    """
    Institutions within 0.25x–4x asset size.
    Tries CBSA first; falls back to state if fewer than min_peers found.
    """
    lo = client_assets * 0.25
    hi = client_assets * 4.0

    def _query(filt):
        rows = _paginate("institutions", {
            "filters": filt,
            "fields": ("CERT,NAME,CITY,STALP,ASSET,DEP,ROA,ROE,"
                       "NIMY,EEFFR,OFFICES,NUMEMP,CBSA"),
            "sort_by": "ASSET", "sort_order": "DESC",
        })
        df = _to_df(rows, ["ASSET", "DEP", "ROA", "ROE", "NIMY", "EEFFR", "OFFICES", "NUMEMP"])
        if not df.empty:
            df = df[(df["ASSET"] >= lo) & (df["ASSET"] <= hi) &
                    (df["CERT"].astype(str) != str(cert))]
        return df

    if cbsa_no:
        df = _query(f"CBSA_NO:{int(cbsa_no)} AND ACTIVE:1")
        if len(df) >= min_peers:
            df["Peer Scope"] = "CBSA"
            return df

    # Fall back to state-level
    df = _query(f"STALP:{stalp} AND ACTIVE:1")
    df["Peer Scope"] = "State"
    return df


def fetch_market_sod(sod_df, top_n_counties=None):
    """
    All banks' deposits in the same counties as the client.
    Fetches ALL counties the client operates in by default (top_n_counties=None).
    Pass an integer to limit to the top N counties by deposit volume.
    """
    if sod_df.empty:
        return pd.DataFrame()

    years   = sorted(sod_df["YEAR"].dropna().astype(int).unique())
    yr_range = f"[{min(years)} TO {max(years)}]"

    # Get all counties the client operates in; optionally limit to top N by deposit volume
    latest   = sod_df[sod_df["YEAR"] == max(years)]
    cnty_dep = (latest.groupby(["CNTYNAMB", "STALPBR"])["DEPSUMBR"]
                      .sum()
                      .sort_values(ascending=False))
    if top_n_counties:
        cnty_dep = cnty_dep.nlargest(top_n_counties)
    top_cnty = cnty_dep.reset_index()[["CNTYNAMB", "STALPBR"]]

    all_rows = []
    for _, row in top_cnty.iterrows():
        county = str(row["CNTYNAMB"]).replace('"', '')
        state  = str(row["STALPBR"])
        rows   = _paginate("sod", {
            "filters": f'CNTYNAMB:"{county}" AND STALPBR:{state} AND YEAR:{yr_range}',
            "fields":  "CERT,NAMEFULL,YEAR,DEPSUMBR,CNTYNAMB,STALPBR",
        })
        all_rows.extend(rows)

    df = _to_df(all_rows, ["YEAR", "DEPSUMBR"])
    # Normalise county names to match SOD normalisation
    if not df.empty and "CNTYNAMB" in df.columns:
        df["CNTYNAMB"] = df["CNTYNAMB"].astype(str).str.title()
    return df


# ── Master loader ──────────────────────────────────────────────────────────────

def load_client_data(cert, force_refresh=False, on_status=None):
    """
    Returns a dict of DataFrames for all data types.
    Loads from SQLite cache when fresh; hits the FDIC API otherwise.
    Pass on_status(msg) to receive progress updates.
    """
    def log(msg):
        if on_status:
            on_status(msg)

    data = {}

    steps = [
        ("institution", fetch_institution,  [cert]),
        ("financials",  fetch_financials,   [cert]),
        ("sod",         fetch_sod,          [cert]),
        ("locations",   fetch_locations,    [cert]),
        ("history",     fetch_history,      [cert]),
    ]
    for key, fn, args in steps:
        if force_refresh or not is_fresh(cert, key):
            log(f"Fetching {key}…")
            df = fn(*args)
            _save(cert, key, df)
        data[key] = _load(cert, key)

    # Peers and market SOD depend on institution data
    inst = data.get("institution", pd.DataFrame())
    if not inst.empty:
        assets  = float(inst["ASSET"].iloc[0])  if "ASSET"   in inst.columns else 0
        stalp   = inst["STALP"].iloc[0]          if "STALP"   in inst.columns else ""
        cbsa_no = inst["CBSA_NO"].iloc[0]        if "CBSA_NO" in inst.columns else None
        cbsa_no = cbsa_no if pd.notna(cbsa_no) and cbsa_no else None

        if force_refresh or not is_fresh(cert, "peers"):
            log("Fetching peer institutions…")
            _save(cert, "peers", fetch_peers(cert, assets, stalp, cbsa_no))
        data["peers"] = _load(cert, "peers")

        if force_refresh or not is_fresh(cert, "market_sod"):
            log("Fetching market deposit data (all competitors in top counties)…")
            _save(cert, "market_sod", fetch_market_sod(data["sod"]))
        data["market_sod"] = _load(cert, "market_sod")

    log("Ready.")
    return data


def cache_status_all(cert):
    types = ["institution", "financials", "sod", "locations", "history", "peers", "market_sod"]
    return {t: last_refreshed(cert, t) for t in types}
