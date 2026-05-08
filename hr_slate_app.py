import streamlit as st
import pandas as pd
import numpy as np
import math, datetime, traceback
from io import StringIO

st.set_page_config(page_title="HR Slate Analyzer", layout="wide", page_icon="⚾")

try:
    import pybaseball as pb
    from pybaseball import batting_stats, pitching_stats
    pb.cache.enable()
    HAS_PB = True
except Exception:
    HAS_PB = False

try:
    from curl_cffi import requests as _r
    def _get(u, **k): return _r.get(u, impersonate="chrome110", timeout=30, **k)
except Exception:
    import requests as _r2
    def _get(u, **k): return _r2.get(u, timeout=30, **k)

SEASON          = 2026
SEASON_FALLBACK = 2025

PARK = {
    "COL":1.18,"CIN":1.10,"PHI":1.09,"BOS":1.08,"NYY":1.07,"MIL":1.05,
    "HOU":1.04,"ATL":1.04,"CHC":1.03,"TEX":1.03,"LAD":1.02,"STL":1.01,
    "ARI":1.01,"MIN":1.00,"TOR":1.00,"DET":1.00,"WSH":0.99,"MIA":0.98,
    "NYM":0.98,"ATH":0.97,"SEA":0.97,"SFG":0.96,"SF":0.96,"PIT":0.96,
    "CLE":0.96,"BAL":0.95,"TBR":0.95,"TB":0.95,"KCR":0.95,"KC":0.95,
    "LAA":0.94,"CHW":0.94,"SDP":0.93,"SD":0.93,"OAK":0.97,
}
PITCH_NAMES = {
    "FF":"4-Seam FB","SI":"Sinker","FC":"Cutter","SL":"Slider",
    "CU":"Curveball","CH":"Changeup","FS":"Splitter",
    "KC":"Knuckle-Curve","ST":"Sweeper","SV":"Slurve","KN":"Knuckleball",
}
PITCH_COLORS = {
    "FF":"#dc2626","SI":"#b91c1c","FC":"#ea580c",
    "SL":"#2563eb","ST":"#1d4ed8","SV":"#0891b2",
    "CU":"#7c3aed","KC":"#6d28d9",
    "CH":"#16a34a","FS":"#15803d","KN":"#6b7280",
}

st.markdown("""<style>
.block-container{padding-top:2rem !important; padding-bottom:2rem !important}

/* ── HEADER ── */
.app-header{
  display:flex;align-items:center;gap:16px;flex-wrap:wrap;
  padding:12px 0 10px;margin-bottom:4px;
  border-bottom:2px solid #1e293b;}
.app-title{
  font-size:1.7rem;font-weight:800;letter-spacing:-.01em;
  color:#f1f5f9;line-height:1.2;white-space:nowrap;}
.app-title span{color:#f59e0b;}
.app-season{
  font-size:.75rem;font-weight:600;color:#64748b;
  background:#1e293b;border:1px solid #334155;
  padding:3px 9px;border-radius:6px;white-space:nowrap;}

/* ── DATE NAV ── */
.date-nav-bar{
  display:flex;align-items:center;gap:6px;
  background:#1e293b;border:1px solid #334155;
  border-radius:10px;padding:5px 8px;width:fit-content;margin-bottom:12px}
.date-nav-bar .date-lbl{
  font-family:monospace;font-size:.82rem;color:#e2e8f0;
  min-width:90px;text-align:center;font-weight:600;}

/* ── GAME CHIPS ── */
.game-chips-wrap{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;}
.game-chip{
  display:inline-flex;flex-direction:column;align-items:center;
  padding:10px 16px;border-radius:10px;cursor:pointer;
  border:1.5px solid #334155;background:#1e293b;
  transition:all .15s;min-width:120px;text-align:center;}
.game-chip:hover{border-color:#3b82f6;background:#1e3a5f;}
.game-chip.selected{border-color:#f59e0b !important;
  background:linear-gradient(135deg,#1e293b 0%,#1a2535 100%) !important;
  box-shadow:0 0 0 2px rgba(245,158,11,.2);}
.game-chip-teams{font-size:.92rem;font-weight:700;color:#f1f5f9;letter-spacing:.01em;white-space:nowrap;}
.game-chip-time{font-size:.65rem;color:#64748b;margin-top:3px;font-family:monospace;}
.game-chip.selected .game-chip-teams{color:#f59e0b;}
.game-chip.selected .game-chip-time{color:#ca8a04;}

/* ── PILLS ── */
.pill{display:inline-flex;align-items:center;justify-content:center;
      padding:3px 11px;border-radius:999px;font-size:.76rem;font-weight:600;
      color:#fff !important;min-width:50px;white-space:nowrap}
.pill-g{background:#16a34a !important}
.pill-y{background:#ca8a04 !important}
.pill-r{background:#dc2626 !important}
.pill-b{background:#2563eb !important}

/* ── HEAT CELLS ── */
.hc{display:inline-block;padding:2px 7px;border-radius:5px;font-weight:600;
    font-size:.79rem;min-width:44px;text-align:center;white-space:nowrap}
.hc-g{background:#dcfce7;color:#15803d}
.hc-y{background:#fef9c3;color:#92400e}
.hc-r{background:#fee2e2;color:#991b1b}
.hc-b{background:#dbeafe;color:#1d4ed8}
.hc-n{background:#f1f5f9;color:#64748b}

/* ── MAIN TABLE ── */
.slate-tbl{width:100%;border-collapse:collapse;font-size:.81rem}
.slate-tbl th{background:#1e293b;color:#94a3b8;padding:6px 8px;text-align:center;
  font-size:.64rem;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap;
  border-bottom:2px solid #334155}
.slate-tbl th:first-child,.slate-tbl th:nth-child(2){text-align:left}
.slate-tbl td{padding:5px 8px;text-align:center;border-bottom:1px solid #f1f5f9;
  white-space:nowrap;vertical-align:middle}
.slate-tbl td:first-child{text-align:left;font-weight:600;font-size:.84rem;padding-left:8px}
.slate-tbl td:nth-child(2){text-align:left;font-size:.76rem;color:#6b7280}
.slate-tbl tr:hover td{background:#f0f9ff;cursor:pointer}
.slate-tbl tr.selected td{background:#eff6ff !important;border-left:3px solid #2563eb}
.col-mix{background:#f0f9ff}
.col-plat{background:#f0fff4}
.tbl-section-mix{background:#1e3a5f !important;color:#93c5fd !important}
.tbl-section-plat{background:#14532d !important;color:#86efac !important}

/* ── PITCHER BAR ── */
.sp-bar{background:#1e293b;border-radius:10px;padding:10px 16px;margin-bottom:10px;
  display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.sp-name{font-size:1rem;font-weight:700;color:#fff;white-space:nowrap}
.sp-stat{text-align:center;min-width:42px}
.sp-val{font-size:.87rem;font-weight:700;color:#f8fafc;display:block}
.sp-lbl{font-size:.58rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;display:block}
.ac{display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:5px;
  font-size:.72rem;border:1px solid;margin:2px}

/* ── STAT ROWS ── */
.stat-row{display:flex;justify-content:space-between;align-items:center;
  padding:4px 0;border-bottom:1px solid #e5e7eb}
.stat-lbl{font-size:.81rem;color:#374151}

/* ── MINI STATS ── */
.mini-stat{display:inline-block;text-align:center;min-width:48px;
  padding:3px 5px;border-radius:6px;margin:2px}
.mini-label{font-size:.6rem;color:#6b7280;display:block;margin-bottom:1px}
.mini-val{font-size:.83rem;font-weight:700}

/* ── DETAIL PANEL ── */
.detail-panel{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
  padding:14px 16px;margin-top:6px;margin-bottom:12px}

/* ── PLATOON TABLE ── */
.plat-tbl{width:100%;border-collapse:collapse;font-size:.8rem}
.plat-tbl th{background:#f8fafc;padding:4px 6px;text-align:center;font-size:.63rem;
  color:#6b7280;text-transform:uppercase;border-bottom:1px solid #e2e8f0;letter-spacing:.04em}
.plat-tbl td{padding:4px 6px;text-align:center;border-bottom:1px solid #f1f5f9}
.plat-hl{background:#f0fdf4 !important;font-weight:600}

/* ── PITCH TABLE ── */
.pitch-row-tbl{width:100%;border-collapse:collapse;font-size:.78rem}
.pitch-row-tbl th{background:#1e293b;color:#94a3b8;padding:4px 7px;text-align:center;
  font-size:.62rem;text-transform:uppercase;border-bottom:1px solid #334155}
.pitch-row-tbl th:first-child{text-align:left}
.pitch-row-tbl td{padding:4px 7px;text-align:center;border-bottom:1px solid #f1f5f9}
.pitch-row-tbl td:first-child{text-align:left}
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════

def _norm(df):
    return df.rename(columns={c: c.lower().replace(" ","_").replace("%","_pct")
                                .replace("/","_per_").replace("-","_") for c in df.columns})
def _std_id(df):
    for col in ("player_id","mlbam_id","batter","pitcher","xmlbamid","mlbamid","playerid","xMLBAMID"):
        if col in df.columns:
            df["player_id"] = df[col].astype(str).str.replace(r"\.0$","",regex=True); return df
    return df

def _scale_pct(df, cols):
    for c in cols:
        if c in df.columns:
            try:
                s = pd.to_numeric(df[c], errors="coerce")
                if 0 < s.dropna().max() <= 1.1: df[c] = s*100
            except: pass
    return df

def _fv(row, col, default=None):
    if not isinstance(row, dict): return default
    v = row.get(col)
    if v is None: return default
    try:
        f = float(v); return default if (math.isnan(f) or math.isinf(f)) else f
    except: return default

def _heat(v, lo, hi, invert=False):
    if v is None: return "pill-y"
    p = max(0.0, min(1.0, (v-lo)/(hi-lo) if hi!=lo else 0.5))
    if invert: p = 1-p
    return "pill-g" if p>=0.65 else ("pill-y" if p>=0.45 else "pill-r")

def _fmt(v, dec=1, suf=""):
    if v is None: return "—"
    try: return f"{float(v):.{dec}f}{suf}"
    except: return "—"

def _score(val, lo, hi, hib):
    if val is None: return None
    val = max(lo, min(hi, val))
    r = (val-lo)/(hi-lo) if hi!=lo else 0.5
    return r*100 if hib else (1-r)*100

def pill(v, lo, hi, hib, suf=""):
    cls = _heat(v,lo,hi,not hib) if v is not None else "pill-b"
    return f"<span class='pill {cls}'>{_fmt(v)}{suf if v is not None else ''}</span>"

def hc(v, lo, hi, hib=True, dec=1, suf=""):
    if v is None: return "<span class='hc hc-n'>—</span>"
    p = max(0.0, min(1.0, (v-lo)/(hi-lo) if hi!=lo else 0.5))
    if not hib: p = 1-p
    cls = "hc-g" if p>=0.65 else ("hc-y" if p>=0.35 else "hc-r")
    return f"<span class='hc {cls}'>{v:.{dec}f}{suf}</span>"

def hcn(v,lo,hi,h=True): return hc(v,lo,hi,h,3)
def hcp(v,lo,hi,h=True): return hc(v,lo,hi,h,1,"%")
def hcv(v,lo,hi,h=True): return hc(v,lo,hi,h,1," mph")
def nb(v,dec=0):
    if v is None: return "<span class='hc hc-n'>—</span>"
    return f"<span class='hc hc-b'>{v:.{dec}f}</span>"

def score_pill(s):
    if s is None: return "<span class='pill pill-b'>—</span>"
    cls = "pill-g" if s>=65 else ("pill-y" if s>=45 else "pill-r")
    return f"<span class='pill {cls}'>{s}</span>"

def mbadge(label, val, fmt=".3f", lo=None, hi=None, hib=True):
    if val is None:
        return (f"<div class='mini-stat' style='background:#f3f4f6'>"
                f"<span class='mini-label'>{label}</span>"
                f"<span class='mini-val' style='color:#9ca3af'>—</span></div>")
    disp = f"{val:{fmt}}"
    if lo is not None:
        cls = _heat(val,lo,hi,not hib)
        bg = {"pill-g":"#dcfce7","pill-y":"#fef9c3","pill-r":"#fee2e2"}.get(cls,"#f3f4f6")
        tc = {"pill-g":"#15803d","pill-y":"#92400e","pill-r":"#991b1b"}.get(cls,"#374151")
    else:
        bg, tc = "#f3f4f6","#374151"
    return (f"<div class='mini-stat' style='background:{bg}'>"
            f"<span class='mini-label'>{label}</span>"
            f"<span class='mini-val' style='color:{tc}'>{disp}</span></div>")

# ═══════════════════════════════════════════════════════
# SCHEDULE / ROSTER / WEATHER
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def get_games(date_str):
    try:
        url = (f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"
               f"&hydrate=team,venue,probablePitcher(note)")
        data = _get(url).json()
        out = []
        for dt in data.get("dates",[]):
            for g in dt.get("games",[]):
                aw=g["teams"]["away"]; hm=g["teams"]["home"]
                out.append({
                    "game_pk":g["gamePk"],
                    "away":aw["team"]["abbreviation"],"home":hm["team"]["abbreviation"],
                    "venue":g.get("venue",{}).get("name",""),
                    "away_sp_id":aw.get("probablePitcher",{}).get("id"),
                    "away_sp_name":aw.get("probablePitcher",{}).get("fullName","TBD"),
                    "home_sp_id":hm.get("probablePitcher",{}).get("id"),
                    "home_sp_name":hm.get("probablePitcher",{}).get("fullName","TBD"),
                })
        return out
    except Exception: traceback.print_exc(); return []

@st.cache_data(ttl=1800, show_spinner=False)
def get_roster(team_abbr):
    try:
        teams = _get(f"https://statsapi.mlb.com/api/v1/teams?sportId=1&season={SEASON}").json().get("teams",[])
        tid = next((t["id"] for t in teams if t.get("abbreviation")==team_abbr), None)
        if not tid: return []
        r = _get(f"https://statsapi.mlb.com/api/v1/teams/{tid}/roster?rosterType=active&season={SEASON}").json()
        out = []
        for p in r.get("roster",[]):
            pid = p["person"]["id"]
            bh  = p.get("person",{}).get("batSide",{}).get("code","")
            if not bh:
                try:
                    pd2 = _get(f"https://statsapi.mlb.com/api/v1/people/{pid}").json()
                    bh  = pd2.get("people",[{}])[0].get("batSide",{}).get("code","R")
                except: bh="R"
            out.append({"id":pid,"name":p["person"]["fullName"],
                        "pos":p.get("position",{}).get("abbreviation",""),"bat_hand":bh})
        return out
    except Exception: traceback.print_exc(); return []

@st.cache_data(ttl=3600, show_spinner=False)
def get_pitcher_hand(pitcher_id):
    if not pitcher_id: return "R"
    try:
        d = _get(f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}").json()
        return d.get("people",[{}])[0].get("pitchHand",{}).get("code","R")
    except: return "R"

@st.cache_data(ttl=1800, show_spinner=False)
def get_weather(venue, date_str):
    COORDS = {
        "Yankee Stadium":(40.8296,-73.9262),"Fenway Park":(42.3467,-71.0972),
        "Wrigley Field":(41.9484,-87.6553),"Dodger Stadium":(34.0739,-118.24),
        "Coors Field":(39.7559,-104.994),"Oracle Park":(37.7786,-122.389),
        "Great American Ball Park":(39.0979,-84.5082),"Globe Life Field":(32.7473,-97.083),
        "Truist Park":(33.8908,-84.4678),"Citizens Bank Park":(39.9061,-75.1665),
        "Busch Stadium":(38.6226,-90.1928),"American Family Field":(43.028,-87.9712),
        "Petco Park":(32.7076,-117.157),"Chase Field":(33.4455,-112.067),
        "T-Mobile Park":(47.5914,-122.332),"Guaranteed Rate Field":(41.83,-87.6339),
        "Target Field":(44.9817,-93.2783),"Progressive Field":(41.4962,-81.6852),
        "Comerica Park":(42.339,-83.0485),"Kauffman Stadium":(39.0517,-94.4803),
        "Minute Maid Park":(29.7573,-95.3555),"Angel Stadium":(33.8003,-117.883),
        "Nationals Park":(38.873,-77.0074),"loanDepot park":(25.7781,-80.2197),
        "PNC Park":(40.4469,-80.0057),"Citi Field":(40.7571,-73.8458),
        "Camden Yards":(39.2838,-76.6216),"Tropicana Field":(27.7683,-82.6534),
    }
    try:
        lat,lon = COORDS.get(venue,(40.7128,-74.006))
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&hourly=temperature_2m,precipitation_probability,windspeed_10m,winddirection_10m"
               f"&temperature_unit=fahrenheit&windspeed_unit=mph&timezone=auto&forecast_days=1")
        h = _get(url).json().get("hourly",{})
        return {"temp":h.get("temperature_2m",[72])[13],"rain":h.get("precipitation_probability",[0])[13],
                "wind":h.get("windspeed_10m",[0])[13],"wdir":h.get("winddirection_10m",[0])[13]}
    except: return {"temp":72,"rain":0,"wind":0,"wdir":0}

def wind_label(spd,deg):
    dirs=["N","NE","E","SE","S","SW","W","NW"]
    return f"{spd:.0f} mph {dirs[round(deg/45)%8]}"

def weather_score(w):
    s = 50 + max(-20,min(20,(w["temp"]-65)*0.5)) - w["rain"]*0.4
    bonus = 0.8 if (w["wdir"]<90 or w["wdir"]>270) else -0.8
    return max(0,min(100, s + max(-15,min(15,w["wind"]*bonus))))

# ═══════════════════════════════════════════════════════
# SAVANT DATA
# ═══════════════════════════════════════════════════════

def _savant_csv(player_id, player_type, season):
    """
    Fetch true pitch-by-pitch Savant CSV (no grouping).
    Returns DataFrame with columns: pitch_type, launch_speed, launch_angle,
    barrel, events, description, estimated_ba/woba, p_throws, game_date, etc.
    """
    pid = str(player_id).replace(".0","")
    lookup_param = "pitchersLookup" if player_type=="pitcher" else "battersLookup"
    # type=details with NO group_by gives pitch-level rows with all Statcast columns
    url = (f"https://baseballsavant.mlb.com/statcast_search/csv?"
           f"hfSea={season}%7C&player_type={player_type}&"
           f"{lookup_param}%5B%5D={pid}&"
           f"type=details&")
    try:
        resp = _get(url)
        if resp.status_code != 200: return None
        text = resp.text.strip()
        if not text or text.startswith("<!") or len(text) < 100: return None
        df = pd.read_csv(StringIO(text), low_memory=False)
        if df.empty or len(df.columns) < 10: return None
        return df
    except: return None

@st.cache_data(ttl=21600, show_spinner=False)
def _get_batter_raw_df(batter_id, season):
    """Cache the full raw pitch-by-pitch DataFrame for a batter (expensive fetch)."""
    pid = str(batter_id).replace(".0","")
    for s in (season, SEASON_FALLBACK):
        df = _savant_csv(pid, "batter", s)
        if df is not None and "pitch_type" in df.columns:
            df["_season"] = s
            return df
        # pybaseball statcast fallback — pulls full pitch log with all columns
        if HAS_PB:
            try:
                start = f"{s}-03-01"; end = f"{s}-11-01"
                df = pb.statcast_batter(start, end, player_id=int(pid))
                if df is not None and not df.empty:
                    df["_season"] = s
                    return df
            except: pass
    return None

AB_EVENTS = {"single","double","triple","home_run","field_out","grounded_into_double_play",
             "strikeout","strikeout_double_play","force_out","field_error","fielders_choice",
             "fielders_choice_out","double_play","triple_play","sac_fly","sac_bunt"}

def _is_barrel(ev, la):
    """
    Official Baseball Savant barrel definition:
    Exit velo >= 98 mph AND launch angle in the sweet spot range that scales with velo.
    At 98 mph: 26-30°. Each additional mph widens range by ~1° per side up to 116 mph.
    """
    if ev is None or la is None or np.isnan(ev) or np.isnan(la): return False
    if ev < 98: return False
    if ev >= 116:
        return 8 <= la <= 50
    max_la = 30 + (ev - 98) * 1.0
    min_la = 26 - (ev - 98) * 1.0
    min_la = max(min_la, 8)
    return min_la <= la <= max_la

def _stats_from_grp(grp):
    """Compute counting stats dict from a raw Savant pitch DataFrame group."""
    ev  = grp["events"].dropna() if "events" in grp.columns else pd.Series(dtype=str)
    dsc = grp["description"].dropna() if "description" in grp.columns else pd.Series(dtype=str)
    ab  = ev[ev.isin(AB_EVENTS)].count()
    sng = ev[ev=="single"].count(); dbl=ev[ev=="double"].count()
    trp = ev[ev=="triple"].count(); hr =ev[ev=="home_run"].count()
    bb  = ev[ev=="walk"].count();   hbp=ev[ev=="hit_by_pitch"].count()
    hits= sng+dbl+trp+hr; pa=ab+bb+hbp
    swings = dsc[dsc.isin({"swinging_strike","swinging_strike_blocked","foul","foul_tip",
                            "hit_into_play","hit_into_play_no_out","hit_into_play_score"})].count()
    whiffs = dsc[dsc.isin({"swinging_strike","swinging_strike_blocked"})].count()

    # Batted ball metrics — only non-NaN on contact
    ev_col = grp["launch_speed"]  if "launch_speed"  in grp.columns else pd.Series(dtype=float)
    la_col = grp["launch_angle"]  if "launch_angle"  in grp.columns else pd.Series(dtype=float)
    xba_s  = grp["estimated_ba_using_speedangle"].dropna()   if "estimated_ba_using_speedangle"   in grp.columns else pd.Series(dtype=float)
    xw_s   = grp["estimated_woba_using_speedangle"].dropna() if "estimated_woba_using_speedangle" in grp.columns else pd.Series(dtype=float)

    # Only rows with valid EV = batted balls
    bbl_mask = ev_col.notna()
    ev_s = ev_col[bbl_mask]
    la_s_clean = la_col[bbl_mask].dropna()
    n_bbl = int(bbl_mask.sum())

    # Hard hit %
    hard_pct = round((ev_s >= 95).sum() / n_bbl * 100, 1) if n_bbl > 0 else None
    avg_ev   = round(float(ev_s.mean()), 1) if n_bbl > 0 else None
    avg_la   = round(float(la_col.dropna().mean()), 1) if la_col.notna().any() else None

    # Barrel %: use Savant 'barrel' column if present, otherwise compute from EV+LA
    brl_pct = None
    if n_bbl > 0:
        if "barrel" in grp.columns:
            brl_col = pd.to_numeric(grp["barrel"], errors="coerce")
            n_barrels = int((brl_col >= 1).sum())
            brl_pct = round(n_barrels / n_bbl * 100, 1)
        elif "launch_speed" in grp.columns and "launch_angle" in grp.columns:
            # Compute barrel from EV + LA using official definition
            bbl_rows = grp[bbl_mask][["launch_speed","launch_angle"]].dropna()
            n_barrels = int(bbl_rows.apply(
                lambda r: _is_barrel(r["launch_speed"], r["launch_angle"]), axis=1).sum())
            if len(bbl_rows) > 0:
                brl_pct = round(n_barrels / len(bbl_rows) * 100, 1)

    return {
        "pa":int(pa),"ab":int(ab),"hr":int(hr),
        "ba":   round(hits/ab,3)   if ab>0  else None,
        "slg":  round((sng+2*dbl+3*trp+4*hr)/ab,3) if ab>0 else None,
        "obp":  round((hits+bb+hbp)/pa,3) if pa>0 else None,
        "iso":  round((sng+2*dbl+3*trp+4*hr-hits)/ab,3) if ab>0 else None,
        "woba": round((0.69*bb+0.72*hbp+0.89*sng+1.27*dbl+1.62*trp+2.10*hr)/pa,3) if pa>0 else None,
        "xba":  round(float(xba_s.mean()),3)  if len(xba_s)>0  else None,
        "xwoba":round(float(xw_s.mean()),3)   if len(xw_s)>0   else None,
        "whiff_pct": round(whiffs/swings*100,1) if swings>0 else None,
        "hard_pct":  hard_pct,
        "avg_ev":    avg_ev,
        "avg_la":    avg_la,
        "brl_pct":   brl_pct,
    }

@st.cache_data(ttl=21600, show_spinner=False)
def get_batter_pitch_splits(batter_id, season):
    """
    Returns {pitch_type: stats_dict} — hitter's stats vs each pitch type LEAGUE-WIDE.

    Method 1: Raw Savant pitch-by-pitch CSV — gives brl%, hard%, EV, LA, wOBA, whiff.
    Method 2: pybaseball statcast_batter_pitch_arsenal — fallback for wOBA/whiff only.
    """
    pid = str(batter_id).replace(".0","")

    # ── Method 1: raw Savant/pybaseball pitch-by-pitch (has brl%, EV, LA) ───
    for s in (season, SEASON_FALLBACK):
        df = _get_batter_raw_df(batter_id, s)
        if df is None or "pitch_type" not in df.columns: continue
        out = {}
        for pt, grp in df.groupby("pitch_type"):
            ptu = str(pt).strip().upper()
            if ptu in ("NAN","NA","","PO","IN","AB"): continue
            stats = _stats_from_grp(grp)
            stats["season"] = s
            out[ptu] = stats
        if out: return out

    # ── Method 2: pybaseball statcast_batter_pitch_arsenal (wOBA/whiff only) ─
    if HAS_PB:
        for s in (season, SEASON_FALLBACK):
            try:
                df = pb.statcast_batter_pitch_arsenal(s, minPA=0)
                if df is None or df.empty: continue
                df_norm = _norm(df)
                id_col = next((c for c in ("batter","player_id","mlbam_id") if c in df_norm.columns), None)
                pt_col = next((c for c in ("pitch_type","pitch_name") if c in df_norm.columns), None)
                if not id_col or not pt_col: continue
                sub = df_norm[df_norm[id_col].astype(str).str.replace(r"\.0$","",regex=True)==pid]
                if sub.empty: continue
                out = {}
                for _, row in sub.iterrows():
                    pt = str(row[pt_col]).strip().upper()
                    if not pt or pt in ("NAN","NA","","PO","IN","AB"): continue
                    def gv(keys):
                        for k in keys:
                            v = row.get(k)
                            if v is not None:
                                try:
                                    f = float(v)
                                    if not math.isnan(f): return f
                                except: pass
                        return None
                    pa_v    = gv(["pa","pa_x","pa_y"])
                    woba_v  = gv(["woba","woba_value"])
                    xwoba_v = gv(["est_woba","estimated_woba_using_speedangle","xwoba"])
                    whiff_v = gv(["whiff_percent","whiff_pct"])
                    hard_v  = gv(["hard_hit_percent","hard_hit_pct","hard_pct"])
                    hr_v    = gv(["home_run","hr"])
                    # These fields are NOT in pitch arsenal — will be None
                    brl_v   = None
                    ev_v    = None
                    la_v    = None
                    if whiff_v is not None and 0 < whiff_v <= 1.0: whiff_v *= 100
                    if hard_v  is not None and 0 < hard_v  <= 1.0: hard_v  *= 100
                    out[pt] = {
                        "pa":       int(pa_v)       if pa_v    is not None else None,
                        "hr":       int(hr_v)       if hr_v    is not None else None,
                        "woba":     round(woba_v,3)  if woba_v  else None,
                        "xwoba":    round(xwoba_v,3) if xwoba_v else None,
                        "whiff_pct":round(whiff_v,1) if whiff_v else None,
                        "hard_pct": round(hard_v,1)  if hard_v  else None,
                        # Power fields unavailable from this source
                        "brl_pct":None,"avg_ev":None,"avg_la":None,
                        "ba":None,"slg":None,"xba":None,
                        "season": s,
                    }
                if out: return out
            except Exception: traceback.print_exc()

    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def get_recent_form(batter_id, season, n_games=10):
    """
    Returns recent form: last N games HR, hits, wOBA trend from Savant.
    Uses game_date grouping to get per-game results.
    """
    for s in (season, SEASON_FALLBACK):
        df = _get_batter_raw_df(batter_id, s)
        if df is None: continue
        if "game_date" not in df.columns: continue
        try:
            df["game_date"] = pd.to_datetime(df["game_date"])
            df = df.sort_values("game_date")
            recent = df[df["game_date"] >= df["game_date"].max() - pd.Timedelta(days=14)]
            if recent.empty: continue
            games_grouped = recent.groupby("game_date")
            game_stats = []
            for gdate, grp in games_grouped:
                gs = _stats_from_grp(grp)
                gs["date"] = gdate.strftime("%m/%d")
                game_stats.append(gs)
            game_stats = game_stats[-n_games:]  # last N games only
            if not game_stats: continue
            # Rolling totals
            total = _stats_from_grp(recent)
            total["season"] = s
            total["games"] = len(game_stats)
            total["game_log"] = game_stats
            # Hot/cold: compare last 7 days vs season
            last7 = recent[recent["game_date"] >= recent["game_date"].max() - pd.Timedelta(days=14)]
            total["last14"] = _stats_from_grp(last7) if not last7.empty else {}
            return total
        except Exception: traceback.print_exc()
    return {}
    """
    Returns {pitch_type: stats_dict} — hitter's stats vs each pitch type LEAGUE-WIDE
    (all pitchers, not just one SP). Tries pybaseball first, then raw Savant CSV.
    """
    pid = str(batter_id).replace(".0","")

    # Method 1: pybaseball statcast_batter_pitch_arsenal — league-wide pitch splits
    if HAS_PB:
        for s in (season, SEASON_FALLBACK):
            try:
                df = pb.statcast_batter_pitch_arsenal(s, minPA=0)
                if df is None or df.empty: continue
                df_norm = _norm(df)
                # find batter id column
                id_col = next((c for c in ("batter","player_id","mlbam_id") if c in df_norm.columns), None)
                pt_col = next((c for c in ("pitch_type","pitch_name") if c in df_norm.columns), None)
                if not id_col or not pt_col: continue
                sub = df_norm[df_norm[id_col].astype(str).str.replace(r"\.0$","",regex=True)==pid]
                if sub.empty: continue
                out = {}
                for _, row in sub.iterrows():
                    pt = str(row[pt_col]).strip().upper()
                    if not pt or pt in ("NAN","NA","","PO","IN","AB"): continue
                    # map pybaseball column names to our standard keys
                    def gv(keys):
                        for k in keys:
                            v = row.get(k)
                            if v is not None:
                                try:
                                    f = float(v)
                                    if not math.isnan(f): return f
                                except: pass
                        return None
                    pa_v = gv(["pa","pa_x","pa_y"])
                    ba_v = gv(["ba","batting_avg","avg"])
                    slg_v= gv(["slg","slg_percent"])
                    woba_v=gv(["woba","woba_value"])
                    xba_v =gv(["est_ba","estimated_ba_using_speedangle","xba"])
                    xwoba_v=gv(["est_woba","estimated_woba_using_speedangle","xwoba"])
                    whiff_v=gv(["whiff_percent","whiff_pct"])
                    hard_v =gv(["hard_hit_percent","hard_hit_pct","hard_pct"])
                    hr_v   =gv(["home_run","hr"])
                    # scale 0-1 fields to 0-100
                    if whiff_v is not None and 0 < whiff_v <= 1.0: whiff_v *= 100
                    if hard_v  is not None and 0 < hard_v  <= 1.0: hard_v  *= 100
                    out[pt] = {
                        "pa": int(pa_v) if pa_v is not None else None,
                        "hr": int(hr_v) if hr_v is not None else None,
                        "ba": round(ba_v,3) if ba_v else None,
                        "slg":round(slg_v,3) if slg_v else None,
                        "woba":round(woba_v,3) if woba_v else None,
                        "xba": round(xba_v,3) if xba_v else None,
                        "xwoba":round(xwoba_v,3) if xwoba_v else None,
                        "whiff_pct":round(whiff_v,1) if whiff_v else None,
                        "hard_pct": round(hard_v,1)  if hard_v  else None,
                        "season": s,
                    }
                if out: return out
            except Exception: traceback.print_exc()

    return {}

@st.cache_data(ttl=21600, show_spinner=False)
def get_platoon_splits(batter_id, season):
    """
    Returns {"R": stats, "L": stats} — hitter's splits vs RHP and LHP.
    Uses pybaseball batting_stats_bref or raw Savant CSV.
    """
    pid = str(batter_id).replace(".0","")
    result = {}

    # Method 1: raw pitch-by-pitch filtered by p_throws
    for s in (season, SEASON_FALLBACK):
        df = _get_batter_raw_df(batter_id, s)
        if df is None or "p_throws" not in df.columns: continue
        for hand in ("R","L"):
            grp = df[df["p_throws"]==hand]
            if grp.empty: continue
            stats = _stats_from_grp(grp); stats["season"]=s; result[hand]=stats
        if result: return result

    # Method 2: pybaseball get_splits if available
    if HAS_PB:
        for s in (season, SEASON_FALLBACK):
            try:
                # Try to get FanGraphs batter splits page via pybaseball
                splits = pb.batting_stats_bref(s)
                if splits is None or splits.empty: continue
                splits = _norm(splits)
                id_col = next((c for c in ("mlbid","player_id","mlbam_id") if c in splits.columns), None)
                if not id_col: continue
                sub = splits[splits[id_col].astype(str).str.replace(r"\.0$","",regex=True)==pid]
                if sub.empty: continue
                # bref splits don't have hand directly but we can approximate from season totals
                # This is a fallback only — just return season totals for both hands as estimate
                row = sub.iloc[0].to_dict()
                stats = {
                    "pa": int(_fv(row,"pa") or 0), "hr": int(_fv(row,"hr") or 0),
                    "ba":  _fv(row,"ba") or _fv(row,"batting_avg"),
                    "obp": _fv(row,"obp"), "slg": _fv(row,"slg"),
                    "iso": _fv(row,"iso"),
                    "woba":_fv(row,"woba"),
                    "xba":None,"xwoba":None,"hard_pct":None,
                    "season":s,
                }
                # Return same stats for both hands as placeholder
                result = {"R": stats, "L": stats}
                return result
            except: pass

    return result

@st.cache_data(ttl=21600, show_spinner=False)
def get_arsenal(pitcher_id, season):
    """Returns {pitch_type: pct} — tries multiple methods."""
    if not pitcher_id: return {}
    pid = str(pitcher_id).replace(".0","")
    # Method 1: raw Savant pitch-by-pitch CSV grouped by pitch_type
    for s in (season, SEASON_FALLBACK):
        df = _savant_csv(pid, "pitcher", s)
        if df is None or "pitch_type" not in df.columns: continue
        counts = df.groupby("pitch_type").size().reset_index(name="n")
        total = counts["n"].sum()
        if total == 0: continue
        out = {}
        for _, row in counts.iterrows():
            pt = str(row["pitch_type"]).strip().upper()
            if pt in ("NAN","NA","","AB","PO","IN"): continue
            out[pt] = round(row["n"]/total*100, 1)
        if out: return out
    # Method 2: Savant leaderboard CSV
    for s in (season, SEASON_FALLBACK):
        try:
            resp = _get(f"https://baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats?"
                        f"type=pitcher&pitchType=&year={s}&team=&min=1&csv=true")
            if resp.status_code != 200: continue
            df = pd.read_csv(StringIO(resp.text))
            df.columns = [c.strip().lower() for c in df.columns]
            id_col = next((c for c in ("pitcher_id","mlbam_id","player_id","id") if c in df.columns), None)
            pt_col = next((c for c in ("pitch_type","pitch_name") if c in df.columns), None)
            pc_col = next((c for c in ("run_frequency_formatted","pitch_percent","pitch_usage") if c in df.columns), None)
            if not id_col or not pt_col: continue
            sub = df[df[id_col].astype(str).str.replace(r"\.0$","",regex=True)==pid]
            if sub.empty: continue
            out = {}
            for _, row in sub.iterrows():
                pt = str(row[pt_col]).strip().upper()
                if not pt or pt in ("NAN","NA",""): continue
                if pc_col:
                    try:
                        pct = float(str(row[pc_col]).replace("%",""))
                        if 0 < pct <= 1.0: pct *= 100
                        if pct > 0: out[pt] = round(pct,1)
                    except: pass
            if out: return out
        except: pass
    # Method 3: pybaseball
    if HAS_PB:
        for s in (season, SEASON_FALLBACK):
            try:
                adf = pb.statcast_pitcher_pitch_arsenal(s, minP=1)
                if adf is None or adf.empty: continue
                id_col = next((c for c in ("pitcher","player_id","mlbam_id") if c in adf.columns), None)
                if not id_col: continue
                sub = adf[adf[id_col].astype(str).str.replace(r"\.0$","",regex=True)==pid]
                if sub.empty: continue
                out = {}
                if "pitch_type" in adf.columns:
                    for _, row in sub.iterrows():
                        pt = str(row.get("pitch_type","")).strip().upper()
                        if not pt or pt in ("NAN","NA",""): continue
                        for k in ("pitch_usage","pitch_percent","pitch_pct","percent"):
                            v = row.get(k)
                            if v is not None:
                                try:
                                    pct=float(v)
                                    if 0<abs(pct)<=1.0: pct*=100
                                    if pct>0: out[pt]=round(pct,1); break
                                except: pass
                    if out: return out
                row = sub.iloc[0].to_dict()
                _PA = {"FF","SI","FC","SL","CU","CH","FS","KC","ST","SV","KN"}
                for cn in adf.columns:
                    if cn.strip().upper() not in _PA: continue
                    try:
                        pct=float(row.get(cn,0))
                        if pct>0:
                            if 0<pct<=1.0: pct*=100
                            out[cn.strip().upper()]=round(pct,1)
                    except: pass
                if out: return out
            except: pass
    return {}

def pitch_mix_composite(splits, arsenal):
    if not arsenal or not splits: return {}
    tw = sum(arsenal.values())
    if tw==0: return {}
    # Power/contact keys — same ones the user wants displayed
    keys = ["brl_pct","hard_pct","avg_ev","avg_la","pull_pct_pm","fb_pct_pm",
            "woba","xwoba","whiff_pct"]
    acc={k:0.0 for k in keys}; wts={k:0.0 for k in keys}
    for pt,pct in arsenal.items():
        hvp = splits.get(pt,{}); w=pct/tw
        # map split keys to composite keys
        kmap = {
            "brl_pct":"brl_pct","hard_pct":"hard_pct","avg_ev":"avg_ev",
            "avg_la":"avg_la","woba":"woba","xwoba":"xwoba","whiff_pct":"whiff_pct",
        }
        for src,dst in kmap.items():
            if hvp.get(src) is not None:
                acc[dst]+=hvp[src]*w; wts[dst]+=w
    dec = {"brl_pct":1,"hard_pct":1,"avg_ev":1,"avg_la":1,
           "pull_pct_pm":1,"fb_pct_pm":1,"whiff_pct":1,"woba":3,"xwoba":3}
    return {k:round(acc[k]/wts[k], dec.get(k,1)) if wts[k]>0 else None for k in keys}

# ═══════════════════════════════════════════════════════
# SEASON STATS (pybaseball)
# ═══════════════════════════════════════════════════════

@st.cache_data(ttl=21600, show_spinner=False)
def build_hitter_master():
    if not HAS_PB: return None
    for s in (SEASON, SEASON_FALLBACK):
        try:
            sc = pb.statcast_batter_exitvelo_barrels(s, minBBE=0)
            fg = batting_stats(s, qual=0)
            if sc is not None and not sc.empty:
                sc = _norm(sc).rename(columns={
                    "brl_percent":"barrel_pct","avg_hit_speed":"avg_ev",
                    "avg_hit_angle":"avg_la","anglesweetspotpercent":"sweet_spot_pct",
                    "ev95percent":"hard_hit_pct"})
                sc = _std_id(sc)
            else: sc=None
            if fg is not None and not fg.empty:
                fg = _norm(fg)
                fg = _scale_pct(fg,["pull_pct","fb_pct","gb_pct","ld_pct","o_contact_pct",
                                    "z_contact_pct","o_swing_pct","z_swing_pct","k_pct",
                                    "bb_pct","hard_hit_pct","barrel_pct","hr_per_fb",
                                    "iffb_pct","swstr_pct"])
                for ic in ["xmlbamid","mlbamid","playerid"]:
                    if ic in fg.columns:
                        fg["player_id"] = fg[ic].astype(str).str.replace(r"\.0$","",regex=True); break
                fg = _std_id(fg)
            else: fg=None
            if sc is not None and fg is not None and "player_id" in fg.columns:
                sc["player_id"]=sc["player_id"].astype(str)
                fg["player_id"]=fg["player_id"].astype(str)
                return sc.merge(fg,on="player_id",how="outer",suffixes=("","_fg"))
            return sc if sc is not None else fg
        except Exception: traceback.print_exc()
    return None

@st.cache_data(ttl=21600, show_spinner=False)
def build_pitcher_master():
    if not HAS_PB: return None
    for s in (SEASON, SEASON_FALLBACK):
        try:
            sc = pb.statcast_pitcher_exitvelo_barrels(s, minBBE=0)
            fg = pitching_stats(s, qual=0)
            if sc is not None and not sc.empty:
                sc = _norm(sc).rename(columns={
                    "brl_percent":"p_brl_pct","avg_hit_speed":"p_avg_ev",
                    "ev95percent":"p_hard_hit_pct","avg_hit_angle":"p_avg_la"})
                sc = _std_id(sc)
            else: sc=None
            if fg is not None and not fg.empty:
                fg = _norm(fg)
                fg = _scale_pct(fg,["k_pct","bb_pct","fb_pct","gb_pct","ld_pct",
                                    "hr_per_fb","o_swing_pct","z_swing_pct"])
                for ic in ["xmlbamid","mlbamid","playerid","idfg"]:
                    if ic in fg.columns:
                        fg["player_id"] = fg[ic].astype(str).str.replace(r"\.0$","",regex=True); break
                skip={"player_id","name","playername","team","season","playerid","g","gs","ip","w","l","sv","era","fip","xfip","war","age"}
                fg = fg.rename(columns={c:"p_"+c for c in fg.columns if c not in skip and not c.startswith("p_")})
                fg = _std_id(fg)
            else: fg=None
            if sc is not None and fg is not None and "player_id" in fg.columns:
                sc["player_id"]=sc["player_id"].astype(str)
                fg["player_id"]=fg["player_id"].astype(str)
                return sc.merge(fg,on="player_id",how="outer",suffixes=("","_fg"))
            return sc if sc is not None else fg
        except Exception: traceback.print_exc()
    return None

def get_row(df, pid):
    if df is None or pid is None: return {}
    s = str(pid).replace(".0","")
    for col in ("player_id","mlbam_id","batter","pitcher"):
        if col in df.columns:
            sub = df[df[col].astype(str).str.replace(r"\.0$","",regex=True)==s]
            if not sub.empty: return sub.iloc[0].to_dict()
    return {}

# ═══════════════════════════════════════════════════════
# SCORING — MLB-calibrated 0-100 scores
# ═══════════════════════════════════════════════════════
#
# Ranges are set to realistic MLB percentile bounds:
#   lo = ~10th pct (below avg),  hi = ~90th pct (elite)
# _score() linearly maps value → 0-100 within [lo, hi]
# hib=True  means higher value is better for the hitter
# hib=False means lower value is better for the hitter

def calc_hitter_score(h_row):
    """
    Hitter power/contact quality score 0-100.
    Weights emphasise barrel% and hard hit% (best HR predictors),
    then exit velo, launch angle sweet spot, K% suppression.
    Requires at least 40 weight-points of data to return a score.
    """
    metrics = [
        # col            lo    hi   hib   wt
        ("barrel_pct",    3,   18,  True, 28),  # 3% = avg, 18% = elite
        ("hard_hit_pct", 30,   55,  True, 22),  # 30% = avg, 55% = elite
        ("avg_ev",       86,   95,  True, 18),  # mph — avg ~88.5, elite ~93+
        ("avg_la",        8,   18,  True,  8),  # ideal 10-18° for HRs
        ("sweet_spot_pct",25,  42,  True,  8),  # 8-32° sweet spot %
        ("fb_pct",       22,   45,  True,  7),  # fly ball tendencies
        ("pull_pct",     28,   50,  True,  5),  # pull tendency adds HR
        ("k_pct",         6,   30, False,  4),  # lower K = better contact
    ]
    total_w = 0; total_s = 0
    for col,lo,hi,hib,w in metrics:
        v = _fv(h_row, col)
        if v is None: continue
        s = _score(v, lo, hi, hib)
        if s is not None: total_s += s*w; total_w += w
    return round(total_s / total_w) if total_w >= 40 else None


def calc_pitcher_hr_risk(p_row):
    """
    Pitcher HR vulnerability score 0-100.
    Higher score = pitcher is MORE likely to give up HRs today.
    Key signals: barrel% allowed (best), HR/FB, hard hit% allowed, K% (inverse).

    When a pitcher has no data (new pitcher, TBD, etc.) we substitute 2024-2025
    MLB league-average values so the score degrades gracefully to ~50 instead
    of returning None and breaking the HR Score calculation.

    2024-25 MLB league averages used as fallbacks:
      brl_pct      ~6.5%    hard_hit_pct ~37%
      hr_per_fb    ~12%     k_pct        ~22%
      fb_pct       ~35%     avg_ev       ~88 mph
    """
    # League-average fallbacks — mid-range values produce a ~50 risk score
    MLB_AVG = {
        "p_brl_pct":      6.5,
        "p_hr_per_fb":   12.0,
        "p_hard_hit_pct":37.0,
        "p_k_pct":       22.0,
        "p_fb_pct":      35.0,
        "p_avg_ev":      88.0,
    }
    metrics = [
        # col              lo    hi   hib   wt
        ("p_brl_pct",      2,   14,  True,  30),
        ("p_hr_per_fb",    5,   20,  True,  25),
        ("p_hard_hit_pct",28,   50,  True,  20),
        ("p_k_pct",       14,   35, False,  15),
        ("p_fb_pct",      20,   50,  True,   7),
        ("p_avg_ev",      82,   93,  True,   3),
    ]
    total_w = 0; total_s = 0
    used_fallback = False
    for col,lo,hi,hib,w in metrics:
        v = _fv(p_row, col) if p_row else None
        if v is None:
            v = MLB_AVG[col]   # substitute league average
            used_fallback = True
        s = _score(v, lo, hi, hib)
        if s is not None: total_s += s*w; total_w += w
    if total_w == 0: return 50   # absolute fallback
    score = round(total_s / total_w)
    # Tag score as estimate when all/most data was league average
    return score


def calc_hr_score(h_row, p_row, ws, pf, splits, platoon, sp_hand, arsenal):
    """
    Final HR Score 0-100.

    Weights prioritise the TODAY'S MATCHUP over raw season-long hitter quality:
      28% Pitcher HR Risk    — who they're facing (biggest single-day driver)
      25% Pitch Mix wOBA     — hitter vs this specific arsenal (league-wide splits)
      22% Hitter Quality     — season-long power/contact profile
      18% Platoon wOBA       — hitter vs pitcher handedness this season
       5% Park factor        — ballpark HR environment
       2% Weather            — temp/wind/conditions
    Weights are re-normalised when components are missing.
    """
    hs         = calc_hitter_score(h_row)
    pr         = calc_pitcher_hr_risk(p_row)
    comp       = pitch_mix_composite(splits, arsenal)
    plat       = platoon.get(sp_hand, {})

    # Pitch mix wOBA → 0-100  (0.220 = replacement, 0.420 = elite)
    pm_woba    = comp.get("woba")
    pm_score   = max(0, min(100, (pm_woba - 0.220) / (0.420 - 0.220) * 100)) if pm_woba else None

    # Platoon wOBA → 0-100
    plat_woba  = plat.get("woba")
    plat_score = max(0, min(100, (plat_woba - 0.220) / (0.420 - 0.220) * 100)) if plat_woba else None

    # Park factor: 1.00 = neutral = 50 pts
    pf_score   = max(0, min(100, 50 + (pf - 1.0) * 100))

    # Weather: already 0-100
    ws_score   = max(0, min(100, ws))

    components = []
    if pr          is not None: components.append((pr,          0.28))  # matchup-first
    if pm_score    is not None: components.append((pm_score,    0.25))  # vs this arsenal
    if hs          is not None: components.append((hs,          0.22))  # raw power profile
    if plat_score  is not None: components.append((plat_score,  0.18))  # handedness edge
    components.append((pf_score,  0.05))
    components.append((ws_score,  0.02))

    total_w = sum(w for _,w in components)
    if total_w == 0: return None
    raw = sum(s*w for s,w in components) / total_w
    return max(0, min(100, round(raw)))

def pull_air(row):
    p=_fv(row,"pull_pct"); f=_fv(row,"fb_pct")
    if p is None or f is None: return None
    return round(p*f/100, 1)




# ═══════════════════════════════════════════════════════
# SESSION STATE + HEADER + GAME SELECTOR
# ═══════════════════════════════════════════════════════

for k,v in [("date",datetime.date.today()),("game_idx",0),
            ("sort_col","hr_score"),("sort_asc",False),
            ("selected_hitter",None),("selected_team_key","")]:
    if k not in st.session_state: st.session_state[k]=v

# ═══════════════════════════════════════════════════════
# HEADER + DATE NAV
# ═══════════════════════════════════════════════════════

st.markdown(
    f"<div class='app-header'>"
    f"<div class='app-title'>⚾ HR <span>Slate</span> Analyzer</div>"
    f"<div class='app-season'>Season {SEASON}</div>"
    f"</div>",
    unsafe_allow_html=True)

d=st.session_state.date
date_str=d.strftime("%Y-%m-%d")


c1,c2,c3,c4=st.columns([1,1,1,3])
with c1:
    if st.button("◀  Yesterday", use_container_width=True):
        st.session_state.date-=datetime.timedelta(days=1); st.session_state.game_idx=0; st.session_state.selected_hitter=None; st.rerun()
with c2:
    if st.button("📅  Today", use_container_width=True):
        st.session_state.date=datetime.date.today(); st.session_state.game_idx=0; st.session_state.selected_hitter=None; st.rerun()
with c3:
    if st.button("Tomorrow  ▶", use_container_width=True):
        st.session_state.date+=datetime.timedelta(days=1); st.session_state.game_idx=0; st.session_state.selected_hitter=None; st.rerun()
with c4:
    pk=st.date_input("", value=d, label_visibility="collapsed")
    if pk!=d: st.session_state.date=pk; st.session_state.game_idx=0; st.session_state.selected_hitter=None; st.rerun()

date_str=st.session_state.date.strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════
# GAME SELECTOR — styled chip cards
# ═══════════════════════════════════════════════════════

with st.spinner("Loading schedule…"):
    games=get_games(date_str)
if not games: st.warning("No games found for this date."); st.stop()

# Build chip grid — up to 8 per row, wraps to as many rows as needed
CHIPS_PER_ROW = 8
game_rows = [games[i:i+CHIPS_PER_ROW] for i in range(0, len(games), CHIPS_PER_ROW)]
for row_games in game_rows:
    chip_cols = st.columns(len(row_games))
    for col, (g, local_i) in zip(chip_cols, [(g, games.index(g)) for g in row_games]):
        i = local_i
        is_sel = (st.session_state.game_idx == i)
        label = f"{'★ ' if is_sel else ''}{g['away']} @ {g['home']}"
        if col.button(
            label,
            key=f"game_chip_{i}",
            use_container_width=True,
            type="primary" if is_sel else "secondary"
        ):
            if not is_sel:
                st.session_state.game_idx=i; st.session_state.selected_hitter=None; st.rerun()

game=games[min(st.session_state.game_idx, len(games)-1)]

away,home,venue=game["away"],game["home"],game.get("venue","")
away_sp_id,away_sp_name=game.get("away_sp_id"),game.get("away_sp_name","TBD")
home_sp_id,home_sp_name=game.get("home_sp_id"),game.get("home_sp_name","TBD")
pf=PARK.get(home,1.00)

w=get_weather(venue,date_str); ws=weather_score(w)
wc1,wc2,wc3,wc4,wc5=st.columns(5)
wc1.metric("🌡️ Temp",f"{w['temp']:.0f}°F")
wc2.metric("💨 Wind",wind_label(w['wind'],w['wdir']))
wc3.metric("🌧️ Rain",f"{w['rain']:.0f}%")
wc4.metric("🏟️ Park",f"{pf:.2f}× ({home})")
wc5.metric("☀️ Weather",f"{ws:.0f}/100")
st.markdown("---")

# ═══════════════════════════════════════════════════════
# MASTER DATA
# ═══════════════════════════════════════════════════════

with st.spinner(f"Loading {SEASON}/{SEASON_FALLBACK} season stats…"):
    hdf=build_hitter_master(); pdf=build_pitcher_master()

away_sp_hand=get_pitcher_hand(away_sp_id)
home_sp_hand=get_pitcher_hand(home_sp_id)
HAND={"R":"RHP","L":"LHP","S":"S/P"}

away_p_row=get_row(pdf,home_sp_id); home_p_row=get_row(pdf,away_sp_id)

with st.spinner("Fetching pitch arsenals…"):
    away_arsenal=get_arsenal(home_sp_id,SEASON)
    home_arsenal=get_arsenal(away_sp_id,SEASON)

# ═══════════════════════════════════════════════════════
# RENDER FUNCTION
# ═══════════════════════════════════════════════════════

def render_team(bat_team, opp_sp_id, opp_sp_name, opp_sp_hand, p_row, arsenal, tab_key):
    if not opp_sp_id:
        st.info(f"No probable pitcher listed yet for {opp_sp_name}"); return

    # ── Pitcher header ─────────────────────────────────────────────────────
    era=_fv(p_row,"era"); fip=_fv(p_row,"p_fip") or _fv(p_row,"fip")
    xfip=_fv(p_row,"xfip"); kpct=_fv(p_row,"p_k_pct"); bbpct=_fv(p_row,"p_bb_pct")
    gbpct=_fv(p_row,"p_gb_pct"); fbpct=_fv(p_row,"p_fb_pct") or _fv(p_row,"p_fb_pct1")
    hrfb=_fv(p_row,"p_hr_per_fb"); ip=_fv(p_row,"ip")
    pr=calc_pitcher_hr_risk(p_row)
    pr_cls="pill-r" if pr and pr>=65 else ("pill-y" if pr and pr>=45 else "pill-g")

    # Detect if we have real data or fell back to league averages
    has_real_data = p_row and any(_fv(p_row, c) is not None
        for c in ("p_brl_pct","p_hard_hit_pct","p_k_pct","p_hr_per_fb","era"))
    avg_note = ("" if has_real_data else
        " <span style='font-size:.63rem;color:#f59e0b;background:rgba(245,158,11,.12);"
        "padding:1px 6px;border-radius:4px;border:1px solid rgba(245,158,11,.3)'>★ lg avg</span>")

    stats_html="".join(
        f"<div class='sp-stat'><span class='sp-val'>{v}</span><span class='sp-lbl'>{l}</span></div>"
        for l,v in [("IP",_fmt(ip,1)),("ERA",_fmt(era)),("FIP",_fmt(fip)),("xFIP",_fmt(xfip)),
                    ("K%",_fmt(kpct,1,"%")),("BB%",_fmt(bbpct,1,"%")),
                    ("GB%",_fmt(gbpct,1,"%")),("HR/FB",_fmt(hrfb,1,"%")),("Park",f"{pf:.2f}×")])

    arsenal_chips="".join(
        f"<span class='ac' style='color:{PITCH_COLORS.get(pt,'#6b7280')};border-color:{PITCH_COLORS.get(pt,'#6b7280')}44;background:{PITCH_COLORS.get(pt,'#6b7280')}11'>"
        f"<b>{PITCH_NAMES.get(pt,pt)}</b> {pct:.0f}%</span>"
        for pt,pct in sorted(arsenal.items(),key=lambda x:-x[1])) if arsenal else "<span style='color:#64748b;font-size:.75rem'>No arsenal data</span>"

    st.markdown(
        f"<div class='sp-bar'>"
        f"<div><div class='sp-name'>{opp_sp_name}</div>"
        f"<div style='display:flex;align-items:center;gap:8px;margin-top:3px'>"
        f"<span style='font-size:.7rem;color:#94a3b8'>{HAND.get(opp_sp_hand,'RHP')} · vs {bat_team} · {venue}</span>"
        f"<span style='font-size:.7rem;color:#94a3b8'>HR Risk:</span>"
        f"<span class='pill {pr_cls}' style='font-size:.7rem;padding:1px 8px'>{pr or '—'}</span>"
        f"<span style='font-size:.63rem;color:#64748b'>{'🔴 volatile' if pr and pr>=65 else ('🟡 average' if pr and pr>=45 else '🟢 safe') if pr else ''}</span>"
        f"{avg_note}"
        f"</div></div>{stats_html}</div>"
        f"<div style='margin-bottom:12px;display:flex;align-items:center;gap:4px;flex-wrap:wrap'>"
        f"<span style='font-size:.72rem;color:#64748b;font-weight:600;margin-right:2px'>ARSENAL:</span>"
        f"{arsenal_chips}</div>",
        unsafe_allow_html=True)

    # ── Roster + data ──────────────────────────────────────────────────────
    with st.spinner(f"Loading {bat_team} roster…"):
        roster=get_roster(bat_team)
    hitters=[h for h in roster if h.get("pos","") not in ("P","")]
    if not hitters: st.warning("Roster unavailable."); return

    # ── Sort controls ──────────────────────────────────────────────────────
    sort_opts={
        "hr_score":"⚾ HR Score","hitter_score":"🏏 Hitter Score",
        "plat_woba":"⚡ Platoon wOBA","l14_brl":"🔥 L14 Barrel%",
        "l14_hard":"🔥 L14 Hard%","l14_ev":"🔥 L14 Exit Velo",
        "barrel_pct":"💥 Barrel%","hard_hit_pct":"💪 Hard Hit%","avg_ev":"🚀 Exit Velo"
    }
    sc_cols=st.columns(len(sort_opts))
    for col,(k,lbl) in zip(sc_cols,sort_opts.items()):
        active=(st.session_state.sort_col==k)
        icon="▼ " if active and not st.session_state.sort_asc else ("▲ " if active else "")
        if col.button(f"{icon}{lbl}",key=f"sort_{k}_{tab_key}",use_container_width=True):
            if st.session_state.sort_col==k: st.session_state.sort_asc=not st.session_state.sort_asc
            else: st.session_state.sort_col=k; st.session_state.sort_asc=False
            st.rerun()

    # ── Build row data ─────────────────────────────────────────────────────
    rows=[]
    prog=st.progress(0,text="Loading hitter data…")
    for i,h in enumerate(hitters):
        prog.progress((i+1)/len(hitters), text=f"Loading {h['name']}…")
        hid=str(h["id"]); h_row=get_row(hdf,hid)
        splits=get_batter_pitch_splits(hid,SEASON)
        platoon=get_platoon_splits(hid,SEASON)
        form=get_recent_form(hid,SEASON)
        plat=platoon.get(opp_sp_hand,{})
        hs=calc_hitter_score(h_row)
        hrs=calc_hr_score(h_row,p_row,ws,pf,splits,platoon,opp_sp_hand,arsenal)
        # Last 14 days stats — use the full 14-day window totals
        l14=form if form else {}
        rows.append({
            "id":hid,"name":h["name"],"team":bat_team,
            "pos":h.get("pos",""),"bat_hand":h.get("bat_hand","R"),
            "hr_score":hrs,"hitter_score":hs,
            "barrel_pct":_fv(h_row,"barrel_pct"),
            "hard_hit_pct":_fv(h_row,"hard_hit_pct"),
            "avg_ev":_fv(h_row,"avg_ev"),"avg_la":_fv(h_row,"avg_la"),
            "pull_pct":_fv(h_row,"pull_pct"),"fb_pct":_fv(h_row,"fb_pct"),
            "pull_air":pull_air(h_row),"sweet_spot_pct":_fv(h_row,"sweet_spot_pct"),
            "k_pct":_fv(h_row,"k_pct"),"bb_pct":_fv(h_row,"bb_pct"),
            "swstr_pct":_fv(h_row,"swstr_pct"),
            # Last 14 days columns (replaces league-wide pitch mix)
            "l14_brl":   l14.get("brl_pct"),
            "l14_hard":  l14.get("hard_pct"),
            "l14_ev":    l14.get("avg_ev"),
            "l14_la":    l14.get("avg_la"),
            "l14_swstr": l14.get("whiff_pct"),   # whiff_pct from raw Savant ≈ SwStr%
            "l14_hr":    l14.get("hr"),
            "l14_woba":  l14.get("woba"),
            "l14_games": l14.get("games"),
            "plat_pa":plat.get("pa"),"plat_hr":plat.get("hr"),
            "plat_ba":plat.get("ba"),"plat_obp":plat.get("obp"),
            "plat_slg":plat.get("slg"),"plat_iso":plat.get("iso"),
            "plat_woba":plat.get("woba"),"plat_xwoba":plat.get("xwoba"),
            "_splits":splits,"_platoon":platoon,"_h_row":h_row,"_form":form,
        })
    prog.empty()

    # Store rows in session state so score breakdown panels can access them
    st.session_state[f"rows_{tab_key}"] = rows

    # Sort
    sk=st.session_state.sort_col
    rows.sort(key=lambda r:(r.get(sk) is None,-(r.get(sk) or 0) if not st.session_state.sort_asc else (r.get(sk) or 0)))

    # ── TABLE with inline click buttons ────────────────────────────────────
    sel_hid=st.session_state.selected_hitter
    hand_lbl=HAND.get(opp_sp_hand,"RHP")

    hdr=(f"<div style='overflow-x:auto'><table class='slate-tbl'><thead>"
         f"<tr>"
         f"<th rowspan='2' style='text-align:left'>HITTER</th>"
         f"<th rowspan='2' style='text-align:left'>POS</th>"
         f"<th rowspan='2'>HR<br>SCORE</th>"
         f"<th rowspan='2'>HITTER<br>SCORE</th>"
         f"<th rowspan='2'>BARREL<br>%</th>"
         f"<th rowspan='2'>HARD<br>HIT%</th>"
         f"<th rowspan='2'>EXIT<br>VELO</th>"
         f"<th rowspan='2'>LAUNCH<br>ANG</th>"
         f"<th rowspan='2'>PULL<br>%</th>"
         f"<th rowspan='2'>FB<br>%</th>"
         f"<th rowspan='2'>K%</th>"
         f"<th rowspan='2'>BB%</th>"
         f"<th rowspan='2'>SwStr<br>%</th>"
         f"<th colspan='6' class='tbl-section-mix'>── LAST 14 DAYS ──</th>"
         f"<th colspan='7' class='tbl-section-plat'>── PLATOON vs {hand_lbl} ──</th>"
         f"</tr>"
         f"<tr>"
         f"<th class='tbl-section-mix'>BRL%</th>"
         f"<th class='tbl-section-mix'>HARD%</th>"
         f"<th class='tbl-section-mix'>EXIT VELO</th>"
         f"<th class='tbl-section-mix'>LAUNCH</th>"
         f"<th class='tbl-section-mix'>SwStr%</th>"
         f"<th class='tbl-section-mix'>HR</th>"
         f"<th class='tbl-section-plat'>wOBA</th>"
         f"<th class='tbl-section-plat'>SLG</th>"
         f"<th class='tbl-section-plat'>OBP</th>"
         f"<th class='tbl-section-plat'>AVG</th>"
         f"<th class='tbl-section-plat'>ISO</th>"
         f"<th class='tbl-section-plat'>PA</th>"
         f"<th class='tbl-section-plat'>HR</th>"
         f"</tr></thead><tbody>")

    tbody=""
    for r in rows:
        is_sel=(r["id"]==sel_hid and st.session_state.selected_team_key==tab_key)
        sel_cls="selected" if is_sel else ""
        bh=r["bat_hand"]
        hand_badge=f"<span style='font-size:.63rem;color:#94a3b8;margin-left:2px'>{bh}</span>"
        hrs=r["hr_score"]
        hrs_cls="pill-g" if hrs and hrs>=65 else ("pill-y" if hrs and hrs>=45 else "pill-r") if hrs else "pill-b"
        tbody+=(f"<tr class='{sel_cls}'>"
                f"<td>{r['name']}{hand_badge}</td>"
                f"<td>{r['pos']}</td>"
                f"<td><span class='pill {hrs_cls}'>{hrs if hrs is not None else '—'}</span></td>"
                f"<td>{hc(r['hitter_score'],25,80,True,0)}</td>"
                f"<td>{hcp(r['barrel_pct'],4,15,True)}</td>"
                f"<td>{hcp(r['hard_hit_pct'],32,52,True)}</td>"
                f"<td>{hcv(r['avg_ev'],86,94,True)}</td>"
                f"<td>{hc(r['avg_la'],8,18,True,1,'°')}</td>"
                f"<td>{hcp(r['pull_pct'],30,48,True)}</td>"
                f"<td>{hcp(r['fb_pct'],22,42,True)}</td>"
                f"<td>{hcp(r['k_pct'],8,28,False)}</td>"
                f"<td>{hcp(r['bb_pct'],5,14,True)}</td>"
                f"<td>{hcp(r['swstr_pct'],5,14,False)}</td>"
                f"<td class='col-mix'>{hcp(r['l14_brl'],4,15,True)}</td>"
                f"<td class='col-mix'>{hcp(r['l14_hard'],32,52,True)}</td>"
                f"<td class='col-mix'>{hcv(r['l14_ev'],86,94,True)}</td>"
                f"<td class='col-mix'>{hc(r['l14_la'],8,18,True,1,'°')}</td>"
                f"<td class='col-mix'>{hcp(r['l14_swstr'],5,14,False)}</td>"
                f"<td class='col-mix'>{nb(r['l14_hr'])}</td>"
                f"<td class='col-plat'>{hcn(r['plat_woba'],.290,.390,True)}</td>"
                f"<td class='col-plat'>{hcn(r['plat_slg'],.320,.520,True)}</td>"
                f"<td class='col-plat'>{hcn(r['plat_obp'],.305,.385,True)}</td>"
                f"<td class='col-plat'>{hcn(r['plat_ba'],.215,.305,True)}</td>"
                f"<td class='col-plat'>{hcn(r['plat_iso'],.100,.220,True)}</td>"
                f"<td class='col-plat'>{nb(r['plat_pa'])}</td>"
                f"<td class='col-plat'>{nb(r['plat_hr'])}</td>"
                f"</tr>")
    st.markdown(hdr+tbody+"</tbody></table></div>", unsafe_allow_html=True)

    # ── Per-row click buttons rendered below the table ─────────────────────
    # Each hitter gets a button; clicking sets selected_hitter and reruns
    st.markdown("<div style='margin-top:6px;margin-bottom:2px;font-size:.74rem;color:#64748b'>👇 Click a hitter to open full breakdown</div>", unsafe_allow_html=True)

    btn_cols = st.columns(min(len(rows), 8))
    extra_rows = rows[8:]  # overflow into second row
    for i, r in enumerate(rows[:8]):
        is_sel = (r["id"]==sel_hid and st.session_state.selected_team_key==tab_key)
        label = f"{'✓ ' if is_sel else ''}{r['name'].split()[-1]}"  # last name only to fit
        if btn_cols[i % 8].button(label, key=f"btn_{r['id']}_{tab_key}", use_container_width=True,
                                   type="primary" if is_sel else "secondary"):
            if is_sel:
                st.session_state.selected_hitter = None
                st.session_state.selected_team_key = ""
            else:
                st.session_state.selected_hitter = r["id"]
                st.session_state.selected_team_key = tab_key
            st.rerun()

    if extra_rows:
        btn_cols2 = st.columns(min(len(extra_rows), 8))
        for i, r in enumerate(extra_rows):
            is_sel = (r["id"]==sel_hid and st.session_state.selected_team_key==tab_key)
            label = f"{'✓ ' if is_sel else ''}{r['name'].split()[-1]}"
            if btn_cols2[i % 8].button(label, key=f"btn2_{r['id']}_{tab_key}", use_container_width=True,
                                        type="primary" if is_sel else "secondary"):
                if is_sel:
                    st.session_state.selected_hitter = None
                    st.session_state.selected_team_key = ""
                else:
                    st.session_state.selected_hitter = r["id"]
                    st.session_state.selected_team_key = tab_key
                st.rerun()

    # ── Detail panel ───────────────────────────────────────────────────────
    if sel_hid and st.session_state.selected_team_key==tab_key:
        det=next((r for r in rows if r["id"]==sel_hid),None)
        if det:
            bh_str="L" if det["bat_hand"]=="L" else "R" if det["bat_hand"]=="R" else "S"
            hrs_val=det["hr_score"]; hs_val=det["hitter_score"]
            hrs_cls2="pill-g" if hrs_val and hrs_val>=65 else ("pill-y" if hrs_val and hrs_val>=45 else "pill-r") if hrs_val else "pill-b"

            st.markdown(
                f"<div style='border-top:3px solid #2563eb;margin:8px 0 12px'></div>"
                f"<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px'>"
                f"<span style='font-size:1rem;font-weight:700;color:#111'>{det['name']}</span>"
                f"<span style='font-size:.78rem;color:#64748b;background:#f1f5f9;padding:2px 8px;border-radius:4px'>{det['pos']} · Bats {bh_str}</span>"
                f"<span style='font-size:.75rem;color:#64748b'>HR Score</span>"
                f"<span class='pill {hrs_cls2}'>{hrs_val or '—'}</span>"
                f"<span style='font-size:.75rem;color:#64748b'>Hitter Score</span>"
                f"{score_pill(hs_val)}"
                f"</div>",
                unsafe_allow_html=True)

            # ── ROW 1: Season Stats (left) | Recent Form (right) ──────────
            r1a, r1b = st.columns([1, 1])

            with r1a:
                st.markdown("**📊 Season Stats**")
                h=det["_h_row"]
                # Two sub-columns inside for compact display
                sa, sb = st.columns(2)
                left_stats = [
                    ("AVG",          "avg",          .215,.300, True, 3,""),
                    ("OBP",          "obp",          .305,.385, True, 3,""),
                    ("SLG",          "slg",          .340,.520, True, 3,""),
                    ("OPS",          "ops",          .700,.900, True, 3,""),
                    ("HR",           "hr",           3,   35,   True, 0,""),
                    ("Barrel%",      "barrel_pct",   4,   15,   True, 1,"%"),
                    ("Hard Hit%",    "hard_hit_pct", 32,  52,   True, 1,"%"),
                    ("Exit Velo",    "avg_ev",       86,  94,   True, 1," mph"),
                    ("Launch Angle", "avg_la",       8,   18,   True, 1,"°"),
                    ("Pull%",        "pull_pct",     30,  48,   True, 1,"%"),
                ]
                right_stats = [
                    ("FB%",         "fb_pct",         22,  42,  True, 1,"%"),
                    ("Sweet Spot%", "sweet_spot_pct", 25,  40,  True, 1,"%"),
                    ("Pull Air%",   None,              8,   20,  True, 1,"%"),
                    ("K%",          "k_pct",           8,   28, False, 1,"%"),
                    ("BB%",         "bb_pct",          5,   14,  True, 1,"%"),
                    ("SwStr%",      "swstr_pct",       5,   14, False, 1,"%"),
                    ("O-Contact%",  "o_contact_pct",  45,   70, False, 1,"%"),
                    ("Z-Contact%",  "z_contact_pct",  72,   92,  True, 1,"%"),
                    ("O-Swing%",    "o_swing_pct",    22,   38, False, 1,"%"),
                    ("ISO",         "iso",            .100, .250, True, 3,""),
                ]
                for side, stats in [(sa, left_stats), (sb, right_stats)]:
                    with side:
                        for lbl,col,lo,hi,hib,dec,suf in stats:
                            v=pull_air(h) if col is None else _fv(h,col)
                            st.markdown(
                                f"<div class='stat-row'><span class='stat-lbl'>{lbl}</span>"
                                f"{hc(v,lo,hi,hib,dec,suf)}</div>",
                                unsafe_allow_html=True)

            with r1b:
                st.markdown("**🔥 Recent Form**")
                with st.spinner("Loading…"):
                    form = get_recent_form(det["id"], SEASON)

                if not form:
                    st.caption("No recent game data available")
                else:
                    yr_note = f" ({form.get('season','')})" if form.get("season")==SEASON_FALLBACK else ""
                    g_count = form.get("games",0)
                    st.caption(f"Last 14 days · {g_count} games{yr_note}")

                    l7 = form.get("last14",{})
                    if l7 and l7.get("pa",0) > 0:
                        l7_woba = l7.get("woba")
                        l7_cls = _heat(l7_woba,.280,.380) if l7_woba else "pill-b"
                        bg7 = {"pill-g":"#dcfce7","pill-y":"#fef9c3","pill-r":"#fee2e2"}.get(l7_cls,"#f8fafc")
                        tc7 = {"pill-g":"#15803d","pill-y":"#92400e","pill-r":"#991b1b"}.get(l7_cls,"#374151")
                        st.markdown(
                            f"<div style='background:{bg7};border-radius:8px;padding:8px 10px;margin-bottom:8px'>"
                            f"<div style='font-size:.68rem;font-weight:600;color:#64748b;margin-bottom:4px'>LAST 14 DAYS</div>"
                            f"<div style='display:flex;gap:14px;flex-wrap:wrap'>"
                            f"<div><span style='font-size:.63rem;color:#64748b'>PA</span><br><b style='color:{tc7}'>{l7.get('pa','—')}</b></div>"
                            f"<div><span style='font-size:.63rem;color:#64748b'>HR</span><br><b style='color:{tc7}'>{l7.get('hr','—')}</b></div>"
                            f"<div><span style='font-size:.63rem;color:#64748b'>AVG</span><br><b style='color:{tc7}'>{_fmt(l7.get('ba'),3)}</b></div>"
                            f"<div><span style='font-size:.63rem;color:#64748b'>wOBA</span><br><b style='color:{tc7}'>{_fmt(l7_woba,3)}</b></div>"
                            f"<div><span style='font-size:.63rem;color:#64748b'>SLG</span><br><b style='color:{tc7}'>{_fmt(l7.get('slg'),3)}</b></div>"
                            f"<div><span style='font-size:.63rem;color:#64748b'>EV</span><br><b style='color:{tc7}'>{_fmt(l7.get('avg_ev'),1)}</b></div>"
                            f"</div></div>",
                            unsafe_allow_html=True)

                    game_log = form.get("game_log",[])
                    if game_log:
                        gl_html = ("<table style='width:100%;border-collapse:collapse;font-size:.76rem'>"
                                   "<thead><tr style='background:#f8fafc'>"
                                   "<th style='padding:3px 5px;text-align:left;font-size:.62rem;color:#64748b'>DATE</th>"
                                   "<th style='padding:3px 5px;text-align:center;font-size:.62rem;color:#64748b'>PA</th>"
                                   "<th style='padding:3px 5px;text-align:center;font-size:.62rem;color:#64748b'>HR</th>"
                                   "<th style='padding:3px 5px;text-align:center;font-size:.62rem;color:#64748b'>AVG</th>"
                                   "<th style='padding:3px 5px;text-align:center;font-size:.62rem;color:#64748b'>wOBA</th>"
                                   "<th style='padding:3px 5px;text-align:center;font-size:.62rem;color:#64748b'>EV</th>"
                                   "<th style='padding:3px 5px;text-align:center;font-size:.62rem;color:#64748b'>BRL%</th>"
                                   "</tr></thead><tbody>")
                        for g in reversed(game_log):
                            woba_g = g.get("woba")
                            bg_g = ""
                            if g.get("hr",0) > 0: bg_g="background:#fef9c3;"
                            elif woba_g and woba_g >= 0.380: bg_g="background:#dcfce7;"
                            elif woba_g and woba_g < 0.250: bg_g="background:#fee2e2;"
                            gl_html += (f"<tr style='{bg_g}border-bottom:1px solid #f1f5f9'>"
                                        f"<td style='padding:3px 5px;font-weight:500'>{g.get('date','')}</td>"
                                        f"<td style='padding:3px 5px;text-align:center'>{g.get('pa','—')}</td>"
                                        f"<td style='padding:3px 5px;text-align:center;font-weight:700'>{'💥' if g.get('hr',0)>0 else '—'}</td>"
                                        f"<td style='padding:3px 5px;text-align:center'>{_fmt(g.get('ba'),3)}</td>"
                                        f"<td style='padding:3px 5px;text-align:center'>{_fmt(woba_g,3)}</td>"
                                        f"<td style='padding:3px 5px;text-align:center'>{_fmt(g.get('avg_ev'),1)}</td>"
                                        f"<td style='padding:3px 5px;text-align:center'>{_fmt(g.get('brl_pct'),1,'%')}</td>"
                                        f"</tr>")
                        gl_html += "</tbody></table>"
                        st.markdown(gl_html, unsafe_allow_html=True)

                    st.markdown(
                        f"<div style='margin-top:6px;padding:5px 8px;background:#f8fafc;"
                        f"border-radius:6px;font-size:.74rem;color:#374151'>"
                        f"<b>WINDOW:</b> &nbsp;"
                        f"PA {form.get('pa','—')} · HR {form.get('hr','—')} · "
                        f"AVG {_fmt(form.get('ba'),3)} · wOBA {_fmt(form.get('woba'),3)} · "
                        f"EV {_fmt(form.get('avg_ev'),1,' mph')} · "
                        f"HH% {_fmt(form.get('hard_pct'),1,'%')} · "
                        f"BRL% {_fmt(form.get('brl_pct'),1,'%')}"
                        f"</div>", unsafe_allow_html=True)

            st.markdown("<div style='margin:10px 0;border-top:1px solid #e2e8f0'></div>", unsafe_allow_html=True)

            # ── ROW 2: vs Pitch Mix (wider) | Platoon Splits ──────────────
            r2a, r2b = st.columns([1.6, 1])

            with r2a:
                st.markdown(f"**🎯 vs {opp_sp_name}'s Pitch Mix**")
                st.caption("SP% = pitcher's usage · Stats = hitter's league-wide results vs that pitch type · Top bar = last 14 days summary")
                # Debug: show raw split keys + barrel column info
                if splits:
                    first_pt = next(iter(splits))
                    with st.expander(f"🔧 Debug splits ({first_pt})", expanded=False):
                        st.write("Split values:", splits[first_pt])
                        # Show barrel-related columns from raw data
                        raw_df = _get_batter_raw_df(det["id"], SEASON)
                        if raw_df is not None:
                            brl_cols = [c for c in raw_df.columns if "barrel" in c.lower() or "brl" in c.lower()]
                            st.write("Barrel columns found:", brl_cols)
                            if brl_cols:
                                st.write("Sample values:", raw_df[brl_cols].dropna().head(5))
                splits=det["_splits"]
                if not arsenal:
                    st.info("No arsenal data available")
                else:
                    tbl=("<table class='pitch-row-tbl'><thead><tr>"
                         "<th style='text-align:left'>Pitch</th><th>SP%</th>"
                         "<th>PA</th><th>HR</th><th>BRL%</th><th>HARD%</th>"
                         "<th>EV</th><th>LA</th><th>wOBA</th><th>xwOBA</th><th>Whiff%</th>"
                         "</tr></thead><tbody>")
                    for pt,pct in sorted(arsenal.items(),key=lambda x:-x[1]):
                        nm=PITCH_NAMES.get(pt,pt); color=PITCH_COLORS.get(pt,"#6b7280")
                        bw=min(55,int(pct*0.55))
                        usage=(f"<div style='display:flex;align-items:center;gap:3px'>"
                               f"<div style='width:{bw}px;height:8px;background:{color};border-radius:2px'></div>"
                               f"<span style='font-weight:600;font-size:.76rem'>{pct:.0f}%</span></div>")
                        hvp=splits.get(pt,{})
                        yr="" if hvp.get("season")!=SEASON_FALLBACK else f"<sup style='color:#9ca3af'>{SEASON_FALLBACK}</sup>"
                        tbl+=(f"<tr><td><b style='color:{color}'>{nm}</b>{yr}</td>"
                              f"<td>{usage}</td>"
                              f"<td>{nb(hvp.get('pa'))}</td>"
                              f"<td>{nb(hvp.get('hr'))}</td>"
                              f"<td>{hcp(hvp.get('brl_pct'),4,15,True)}</td>"
                              f"<td>{hcp(hvp.get('hard_pct'),32,52,True)}</td>"
                              f"<td>{hcv(hvp.get('avg_ev'),86,94,True)}</td>"
                              f"<td>{hc(hvp.get('avg_la'),8,18,True,1,'°')}</td>"
                              f"<td>{hcn(hvp.get('woba'),.280,.400,True)}</td>"
                              f"<td>{hcn(hvp.get('xwoba'),.280,.400,True)}</td>"
                              f"<td>{hcp(hvp.get('whiff_pct'),18,35,False)}</td>"
                              f"</tr>")
                    tbl+="</tbody></table>"
                    st.markdown(tbl,unsafe_allow_html=True)

                    # Weighted composite
                    st.markdown(
                        f"<div style='margin-top:6px;padding:7px 10px;background:#eff6ff;"
                        f"border-radius:7px;border-left:3px solid #2563eb;font-size:.78rem'>"
                        f"<b style='color:#1d4ed8'>LAST 14 DAYS SUMMARY:</b> &nbsp;"
                        f"Brl% {hcp(det['l14_brl'],4,15,True)} &nbsp;"
                        f"Hard% {hcp(det['l14_hard'],32,52,True)} &nbsp;"
                        f"EV {hcv(det['l14_ev'],86,94,True)} &nbsp;"
                        f"LA {hc(det['l14_la'],8,18,True,1,'°')} &nbsp;"
                        f"SwStr% {hcp(det['l14_swstr'],5,14,False)} &nbsp;"
                        f"HR {nb(det['l14_hr'])} &nbsp;"
                        f"wOBA {hcn(det['l14_woba'],.290,.390,True)}"
                        f"</div>",unsafe_allow_html=True)

                    # Score breakdown
                    pr_val=calc_pitcher_hr_risk(p_row)
                    # Pitch mix wOBA still used internally in HR score calc
                    comp_for_score=pitch_mix_composite(det["_splits"],arsenal)
                    pm_woba_val=comp_for_score.get("woba")
                    plat_woba_val=det["plat_woba"]
                    pm_s = round(max(0,min(100,(pm_woba_val-0.220)/(0.420-0.220)*100))) if pm_woba_val else None
                    pl_s = round(max(0,min(100,(plat_woba_val-0.220)/(0.420-0.220)*100))) if plat_woba_val else None
                    st.markdown(
                        f"<div style='margin-top:6px;padding:7px 10px;background:#f8fafc;"
                        f"border-radius:7px;border-left:3px solid #64748b;font-size:.75rem;color:#374151'>"
                        f"<b>HR SCORE:</b> &nbsp;"
                        f"Hitter {score_pill(hs_val)} 35% &nbsp;"
                        f"P.Risk {score_pill(pr_val)} 25% &nbsp;"
                        f"Mix {score_pill(pm_s)} 20% &nbsp;"
                        f"Platoon {score_pill(pl_s)} 12% &nbsp;"
                        f"Park <b>{pf:.2f}×</b> · Weather <b>{ws:.0f}</b>"
                        f"</div>",unsafe_allow_html=True)

            with r2b:
                st.markdown("**⚡ Platoon Splits**")
                platoon=det["_platoon"]
                if platoon:
                    tbl2=("<table class='plat-tbl'><thead><tr>"
                          "<th>vs</th><th>PA</th><th>HR</th><th>AVG</th>"
                          "<th>OBP</th><th>SLG</th><th>ISO</th><th>wOBA</th><th>xwOBA</th>"
                          "</tr></thead><tbody>")
                    for hand in ("R","L"):
                        sp=platoon.get(hand,{})
                        hl="plat-hl" if hand==opp_sp_hand else ""
                        lbl=f"{'★ ' if hand==opp_sp_hand else ''}{'RHP' if hand=='R' else 'LHP'}"
                        yr=f" <sup style='color:#9ca3af'>{sp.get('season','')}</sup>" if sp.get("season")==SEASON_FALLBACK else ""
                        tbl2+=(f"<tr class='{hl}'>"
                               f"<td><b>{lbl}</b>{yr}</td>"
                               f"<td>{sp.get('pa','—')}</td>"
                               f"<td>{sp.get('hr','—')}</td>"
                               f"<td>{hcn(sp.get('ba'),.215,.305,True)}</td>"
                               f"<td>{hcn(sp.get('obp'),.305,.385,True)}</td>"
                               f"<td>{hcn(sp.get('slg'),.320,.520,True)}</td>"
                               f"<td>{hcn(sp.get('iso'),.100,.220,True)}</td>"
                               f"<td>{hcn(sp.get('woba'),.290,.390,True)}</td>"
                               f"<td>{hcn(sp.get('xwoba'),.290,.390,True)}</td>"
                               f"</tr>")
                    tbl2+="</tbody></table>"
                    st.markdown(tbl2,unsafe_allow_html=True)
                else:
                    st.caption("No platoon data available")
                st.caption(f"Source: Savant {SEASON}→{SEASON_FALLBACK} fallback")

# ═══════════════════════════════════════════════════════
# TEAM TABS
# ═══════════════════════════════════════════════════════

tab_away,tab_home=st.tabs([
    f"🏃 {away}  vs  {home_sp_name}  ({HAND.get(home_sp_hand,'RHP')})",
    f"🏠 {home}  vs  {away_sp_name}  ({HAND.get(away_sp_hand,'RHP')})",
])

with tab_away:
    render_team(away, home_sp_id, home_sp_name, home_sp_hand, away_p_row, away_arsenal, "away")

with tab_home:
    render_team(home, away_sp_id, away_sp_name, away_sp_hand, home_p_row, home_arsenal, "home")

# ═══════════════════════════════════════════════════════
# PITCHER BREAKDOWN TAB
# ═══════════════════════════════════════════════════════

st.markdown("---")
with st.expander("⚔️ Pitcher Score Breakdown", expanded=False):
    for sp_id,sp_name,sp_arsenal,sp_p_row,bat_against in [
        (home_sp_id,home_sp_name,away_arsenal,away_p_row,away),
        (away_sp_id,away_sp_name,home_arsenal,home_p_row,home),
    ]:
        st.markdown(f"### {sp_name} · faces {bat_against}")
        pb1,pb2=st.columns(2)
        with pb1:
            risk=calc_pitcher_hr_risk(sp_p_row) if sp_p_row else calc_pitcher_hr_risk(None)
            has_data = sp_p_row and any(_fv(sp_p_row,c) is not None
                for c in ("p_brl_pct","p_hard_hit_pct","p_k_pct","era"))
            avg_tag = "" if has_data else " <span style='font-size:.63rem;color:#f59e0b;background:rgba(245,158,11,.1);padding:1px 6px;border-radius:4px;border:1px solid rgba(245,158,11,.25)'>★ league avg used</span>"
            rc="pill-r" if risk and risk>=65 else ("pill-y" if risk and risk>=45 else "pill-g")
            st.markdown(f"**HR Risk Score:** <span class='pill {rc}'>{risk or '—'}</span>{avg_tag}",unsafe_allow_html=True)
            st.markdown("")
            for lbl,col,lo,hi,hib,suf in [
                # hib=True here means "higher value = more HR risk = red for pitcher"
                ("Barrel% allowed",   "p_brl_pct",       2,  14,  True, "%"),
                ("Hard Hit% allowed", "p_hard_hit_pct",  28,  50,  True, "%"),
                ("Exit Velo allowed", "p_avg_ev",         83,  92,  True, " mph"),
                ("K%",                "p_k_pct",          14,  35, False, "%"),  # high K = green
                ("BB%",               "p_bb_pct",          4,  12,  True, "%"),
                ("FB% allowed",       "p_fb_pct",         20,  48,  True, "%"),
                ("HR/FB%",            "p_hr_per_fb",       5,  20,  True, "%"),
                ("GB%",               "p_gb_pct",         35,  55, False, "%"),  # high GB = green
            ]:
                v=_fv(sp_p_row,col) if sp_p_row else None
                sc2=_score(v,lo,hi,hib); cls=_heat(v,lo,hi,not hib)
                rv=round(sc2) if sc2 is not None else None
                st.markdown(
                    f"<div class='stat-row'><span class='stat-lbl'>{lbl}</span>"
                    f"<div style='display:flex;gap:6px;align-items:center'>"
                    f"<span class='pill {cls}'>{_fmt(v)}{suf if v is not None else ''}</span>"
                    f"<span class='hc hc-b' style='min-width:32px'>{rv if rv is not None else '—'}</span>"
                    f"</div></div>",unsafe_allow_html=True)
        with pb2:
            st.markdown("**🎯 Arsenal**")
            if sp_arsenal:
                for pt,pct in sorted(sp_arsenal.items(),key=lambda x:-x[1]):
                    nm=PITCH_NAMES.get(pt,pt); color=PITCH_COLORS.get(pt,"#6b7280")
                    bar=min(100,int(pct))
                    st.markdown(
                        f"<div style='margin-bottom:7px'>"
                        f"<div style='display:flex;justify-content:space-between;font-size:.84rem;margin-bottom:2px'>"
                        f"<span><b style='color:{color}'>{nm}</b> <span style='color:#9ca3af;font-size:.7rem'>{pt}</span></span>"
                        f"<span style='font-weight:700'>{pct:.1f}%</span></div>"
                        f"<div style='background:#e5e7eb;border-radius:3px;height:8px'>"
                        f"<div style='background:{color};border-radius:3px;height:8px;width:{bar}%'></div></div></div>",
                        unsafe_allow_html=True)
            else:
                st.info("No arsenal data")
        st.markdown("---")

# ═══════════════════════════════════════════════════════
# SCORE BREAKDOWN + METHODOLOGY PANELS
# ═══════════════════════════════════════════════════════

st.markdown("---")

# Shared CSS for these panels
st.markdown("""<style>
.info-panel{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px 18px;margin-bottom:10px}
.info-section-title{
  font-family:'Barlow Condensed',sans-serif;font-size:.68rem;font-weight:700;
  letter-spacing:.1em;color:#64748b;text-transform:uppercase;margin-bottom:10px}
.score-formula-row{
  display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  padding:8px 0;border-bottom:1px solid #334155}
.score-formula-row:last-child{border-bottom:none}
.sf-metric{flex:1;min-width:140px}
.sf-metric-name{font-size:.82rem;font-weight:600;color:#e2e8f0}
.sf-metric-val{
  font-family:'Courier New',monospace;font-size:.78rem;
  padding:2px 9px;border-radius:5px;white-space:nowrap;font-weight:600}
.sf-raw{font-size:.75rem;color:#94a3b8;margin-left:4px}
.sf-weight{font-size:.72rem;color:#64748b;text-align:right;min-width:36px}
.sf-bar-wrap{flex:2;min-width:80px;display:flex;align-items:center;gap:6px}
.sf-bar-bg{background:#0f172a;border-radius:3px;height:8px;flex:1}
.sf-bar-fill{height:8px;border-radius:3px}
.wt-chip{
  display:inline-block;background:#0f172a;border:1px solid #334155;
  border-radius:5px;font-size:.68rem;color:#64748b;padding:1px 7px;white-space:nowrap}
.meth-table{width:100%;border-collapse:collapse;font-size:.8rem}
.meth-table th{
  background:#0f172a;color:#64748b;padding:6px 10px;text-align:left;
  font-size:.65rem;text-transform:uppercase;letter-spacing:.06em;
  border-bottom:1px solid #334155}
.meth-table td{padding:6px 10px;border-bottom:1px solid #1e293b;vertical-align:top}
.meth-table tr:last-child td{border-bottom:none}
.meth-table tr:hover td{background:#0f172a}
.dir-g{color:#4ade80;font-weight:700} .dir-r{color:#f87171;font-weight:700}
.range-lbl{font-family:'Courier New',monospace;font-size:.74rem;color:#94a3b8}
.src-tag{
  display:inline-block;font-size:.62rem;padding:1px 6px;border-radius:4px;
  font-weight:600;white-space:nowrap}
.src-sc{background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.3)}
.src-fg{background:rgba(34,197,94,.12);color:#4ade80;border:1px solid rgba(34,197,94,.25)}
.src-sv{background:rgba(245,158,11,.12);color:#fbbf24;border:1px solid rgba(245,158,11,.25)}
.src-mlb{background:rgba(168,85,247,.12);color:#c084fc;border:1px solid rgba(168,85,247,.25)}
</style>""", unsafe_allow_html=True)

info_c1, info_c2 = st.columns(2)

# ── Panel 1: Score Breakdown ──────────────────────────────────────────────────
with info_c1:
    with st.expander("📊 Score Breakdown — How Scores Are Calculated", expanded=False):

        def score_bar_html(score, color):
            if score is None: return "<span style='color:#64748b'>—</span>"
            pct = max(0, min(100, score))
            cls = "#22c55e" if pct>=65 else ("#eab308" if pct>=45 else "#ef4444")
            return (f"<div class='sf-bar-wrap'>"
                    f"<div class='sf-bar-bg'><div class='sf-bar-fill' "
                    f"style='width:{pct}%;background:{cls}'></div></div>"
                    f"<span style='font-family:monospace;font-size:.78rem;color:{cls};min-width:28px'>{pct}</span>"
                    f"</div>")

        def val_chip(v, lo, hi, hib, dec=1, suf=""):
            if v is None: return "<span class='sf-metric-val' style='background:#0f172a;color:#64748b'>—</span>"
            import math
            p = max(0.0, min(1.0, (v-lo)/(hi-lo) if hi!=lo else 0.5))
            if not hib: p = 1-p
            bg = "#14532d" if p>=0.65 else ("#713f12" if p>=0.35 else "#7f1d1d")
            tc = "#4ade80" if p>=0.65 else ("#fbbf24" if p>=0.35 else "#f87171")
            return f"<span class='sf-metric-val' style='background:{bg};color:{tc}'>{v:.{dec}f}{suf}</span>"

        # ── Hitter Score ─────────────────────────────────────────
        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='info-section-title'>🏏 Hitter Score (0–100)</div>", unsafe_allow_html=True)

        # Get selected hitter if one is open
        sel_id = st.session_state.get("selected_hitter")
        sel_key = st.session_state.get("selected_team_key","")
        sel_hitter_row = {}
        sel_hitter_name = "No hitter selected"
        if sel_id:
            all_cached = st.session_state.get('rows_away',[]) + st.session_state.get('rows_home',[])
            for team_rows in [all_cached]:
                for r in team_rows:
                    if str(r.get("id","")) == str(sel_id):
                        sel_hitter_row = r.get("_h_row", {})
                        sel_hitter_name = r.get("name","")
                        break

        if sel_id and sel_hitter_name != "No hitter selected":
            st.caption(f"Showing: **{sel_hitter_name}** · Select a different hitter in the table to update")
        else:
            st.caption("Select a hitter in the table above to see their breakdown")

        HITTER_METRICS = [
            ("Barrel %",       "barrel_pct",       3,  18,  True, 1, "%", 28),
            ("Hard Hit %",     "hard_hit_pct",     30,  55,  True, 1, "%", 22),
            ("Exit Velocity",  "avg_ev",           86,  95,  True, 1, " mph", 18),
            ("Launch Angle",   "avg_la",            8,  18,  True, 1, "°", 8),
            ("Sweet Spot %",   "sweet_spot_pct",   25,  42,  True, 1, "%", 8),
            ("Fly Ball %",     "fb_pct",           22,  45,  True, 1, "%", 7),
            ("Pull %",         "pull_pct",         28,  50,  True, 1, "%", 5),
            ("K %",            "k_pct",             6,  30, False, 1, "%", 4),
        ]

        total_hs = None; total_w_h = 0; total_s_h = 0.0
        rows_html = ""
        for lbl, col, lo, hi, hib, dec, suf, wt in HITTER_METRICS:
            v = _fv(sel_hitter_row, col)
            s = _score(v, lo, hi, hib)
            if s is not None: total_s_h += s*wt; total_w_h += wt
            component = round(s) if s is not None else None
            rows_html += (
                f"<div class='score-formula-row'>"
                f"<div class='sf-metric'>"
                f"<div class='sf-metric-name'>{lbl}</div>"
                f"<div>{val_chip(v,lo,hi,hib,dec,suf)} "
                f"<span class='wt-chip'>×{wt}wt</span></div>"
                f"</div>"
                f"{score_bar_html(component, '#3b82f6')}"
                f"</div>")
        if total_w_h >= 40: total_hs = round(total_s_h/total_w_h)

        rows_html += (f"<div style='padding:10px 0 4px;display:flex;justify-content:space-between;align-items:center'>"
                      f"<span style='font-size:.82rem;font-weight:700;color:#e2e8f0'>HITTER SCORE</span>"
                      f"{score_bar_html(total_hs,'#22c55e')}</div>")
        st.markdown(rows_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Pitcher HR Risk ───────────────────────────────────────
        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='info-section-title'>⚾ Pitcher HR Risk Score (0–100)</div>", unsafe_allow_html=True)
        st.caption("🟢 Green = low risk pitcher (good for pitcher, fewer HRs) · 🔴 Red = high risk (bad for pitcher, more HRs expected) · Bar shows component contribution to overall score")

        # Determine which pitcher to show based on active team tab
        active_tab = st.session_state.get("selected_team_key","away")
        sp_name_show = home_sp_name if active_tab=="away" else away_sp_name
        p_row_show   = away_p_row   if active_tab=="away" else home_p_row
        has_data = p_row_show and any(_fv(p_row_show,c) is not None
            for c in ("p_brl_pct","p_hard_hit_pct","p_k_pct"))
        st.caption(f"Pitcher: **{sp_name_show}**" + (" · ★ league avg used for missing metrics" if not has_data else ""))

        MLB_AVG_DISPLAY = {
            "p_brl_pct":6.5,"p_hr_per_fb":12.0,"p_hard_hit_pct":37.0,
            "p_k_pct":22.0,"p_fb_pct":35.0,"p_avg_ev":88.0
        }
        PITCHER_METRICS = [
            ("Barrel % Allowed",   "p_brl_pct",      2, 14, True,  1, "%", 30),
            ("HR / FB %",          "p_hr_per_fb",     5, 20, True,  1, "%", 25),
            ("Hard Hit % Allowed", "p_hard_hit_pct", 28, 50, True,  1, "%", 20),
            ("K %",                "p_k_pct",        14, 35, False, 1, "%", 15),
            ("FB % Allowed",       "p_fb_pct",       20, 50, True,  1, "%", 7),
            ("Exit Velo Allowed",  "p_avg_ev",       82, 93, True,  1, " mph", 3),
        ]

        total_pr = None; total_w_p = 0; total_s_p = 0.0
        rows_html_p = ""
        for lbl, col, lo, hi, hib, dec, suf, wt in PITCHER_METRICS:
            v_real = _fv(p_row_show, col) if p_row_show else None
            v = v_real if v_real is not None else MLB_AVG_DISPLAY[col]
            is_avg = v_real is None
            s = _score(v, lo, hi, hib)
            if s is not None: total_s_p += s*wt; total_w_p += wt
            component = round(s) if s is not None else None
            avg_mark = " <span style='font-size:.6rem;color:#f59e0b'>★avg</span>" if is_avg else ""
            rows_html_p += (
                f"<div class='score-formula-row'>"
                f"<div class='sf-metric'>"
                f"<div class='sf-metric-name'>{lbl}{avg_mark}</div>"
                f"<div>{val_chip(v,lo,hi,hib,dec,suf)} "
                f"<span class='wt-chip'>×{wt}wt</span></div>"
                f"</div>"
                f"{score_bar_html(component, '#3b82f6')}"
                f"</div>")
        if total_w_p > 0: total_pr = round(total_s_p/total_w_p)

        rows_html_p += (f"<div style='padding:10px 0 4px;display:flex;justify-content:space-between;align-items:center'>"
                        f"<span style='font-size:.82rem;font-weight:700;color:#e2e8f0'>PITCHER RISK SCORE</span>"
                        f"{score_bar_html(total_pr,'#ef4444')}</div>")
        st.markdown(rows_html_p, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Final HR Score ────────────────────────────────────────
        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='info-section-title'>💥 HR Score Formula (0–100)</div>", unsafe_allow_html=True)
        st.caption("Weighted combination of all components — weights re-normalised when data is missing")

        pf_val = PARK.get(home, 1.00)
        ws_val = weather_score(w) if 'w' in dir() and w else 50
        pf_score_val = max(0, min(100, 50+(pf_val-1.0)*100))

        # Get pm_woba for selected hitter if available
        pm_woba_disp = None
        plat_woba_disp = None
        if sel_id and sel_hitter_name != "No hitter selected":
            for r in st.session_state.get('rows_away',[]) + st.session_state.get('rows_home',[]):
                if str(r.get("id","")) == str(sel_id):
                    pm_woba_disp = r.get("pm_woba") or r.get("l14_woba")
                    plat_woba_disp = r.get("plat_woba")
                    break

        pm_score_disp = round(max(0,min(100,(pm_woba_disp-0.220)/(0.420-0.220)*100))) if pm_woba_disp else None
        pl_score_disp = round(max(0,min(100,(plat_woba_disp-0.220)/(0.420-0.220)*100))) if plat_woba_disp else None

        HR_COMPONENTS = [
            ("⚾ Pitcher HR Risk", total_pr,      0.28, "barrel% allowed, HR/FB, hard hit%, K%"),
            ("🎯 Pitch Mix wOBA",  pm_score_disp, 0.25, "hitter's wOBA vs pitcher's arsenal weighted by pitch usage"),
            ("🏏 Hitter Quality",  total_hs,      0.22, "barrel%, hard hit%, EV, launch, FB%, K%"),
            ("⚡ Platoon wOBA",    pl_score_disp, 0.18, f"hitter vs {'RHP' if (active_tab=='away' and home_sp_hand=='R') or (active_tab=='home' and away_sp_hand=='R') else 'LHP'} this season"),
            ("🏟️ Park Factor",    round(pf_score_val), 0.05, f"{home} · {pf_val:.2f}× factor"),
            ("☀️ Weather",        round(ws_val),  0.02, f"{w['temp']:.0f}°F · {wind_label(w['wind'],w['wdir'])} · {w['rain']:.0f}% rain" if 'w' in dir() and w else "unavailable"),
        ]

        # Compute actual weighted score
        comps_present = [(s,wt) for _,s,wt,_ in HR_COMPONENTS if s is not None]
        tw = sum(w2 for _,w2 in comps_present)
        final_hr = round(sum(s*w2 for s,w2 in comps_present)/tw) if tw>0 else None

        for comp_name, comp_score, comp_wt, comp_desc in HR_COMPONENTS:
            filled = comp_wt / 0.80 * 100  # normalize to show relative weight
            bar_w = int(comp_wt * 400)  # scale for visual
            wt_pct = f"{comp_wt*100:.0f}%"
            st.markdown(
                f"<div class='score-formula-row'>"
                f"<div class='sf-metric'>"
                f"<div class='sf-metric-name'>{comp_name} <span style='color:#64748b;font-size:.7rem'>({wt_pct})</span></div>"
                f"<div style='font-size:.7rem;color:#64748b;margin-top:2px'>{comp_desc}</div>"
                f"</div>"
                f"{score_bar_html(comp_score, '#3b82f6')}"
                f"</div>",
                unsafe_allow_html=True)

        st.markdown(
            f"<div style='padding:10px 0 4px;display:flex;justify-content:space-between;align-items:center'>"
            f"<span style='font-size:.82rem;font-weight:700;color:#e2e8f0'>FINAL HR SCORE</span>"
            f"{score_bar_html(final_hr,'#f59e0b')}</div>",
            unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ── Panel 2: Methodology ─────────────────────────────────────────────────────
with info_c2:
    with st.expander("📖 Data Methodology — How All Stats Are Derived", expanded=False):

        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='info-section-title'>🏏 Hitter Metrics</div>", unsafe_allow_html=True)
        st.markdown("""<table class='meth-table'>
<thead><tr><th>Metric</th><th>Source</th><th>Range</th><th>Green = Good When</th><th>Used In</th></tr></thead>
<tbody>
<tr><td><b>Barrel %</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>4% → 15%</td><td><span class='dir-g'>↑ Higher</span></td><td>Hitter Score (28wt), HR Score</td></tr>
<tr><td><b>Hard Hit %</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>32% → 52%</td><td><span class='dir-g'>↑ Higher</span></td><td>Hitter Score (22wt)</td></tr>
<tr><td><b>Exit Velocity</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>86 → 94 mph</td><td><span class='dir-g'>↑ Higher</span></td><td>Hitter Score (18wt)</td></tr>
<tr><td><b>Launch Angle</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>8° → 18°</td><td><span class='dir-g'>↑ Higher</span> (in range)</td><td>Hitter Score (8wt)</td></tr>
<tr><td><b>Sweet Spot %</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>25% → 42%</td><td><span class='dir-g'>↑ Higher</span></td><td>Hitter Score (8wt)</td></tr>
<tr><td><b>Fly Ball %</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>22% → 42%</td><td><span class='dir-g'>↑ Higher</span></td><td>Hitter Score (7wt)</td></tr>
<tr><td><b>Pull %</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>28% → 48%</td><td><span class='dir-g'>↑ Higher</span></td><td>Hitter Score (5wt)</td></tr>
<tr><td><b>K %</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>8% → 28%</td><td><span class='dir-r'>↓ Lower</span></td><td>Hitter Score (4wt)</td></tr>
<tr><td><b>BB %</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>5% → 14%</td><td><span class='dir-g'>↑ Higher</span></td><td>Display only</td></tr>
<tr><td><b>SwStr %</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>5% → 14%</td><td><span class='dir-r'>↓ Lower</span></td><td>Display + Last 14 Days</td></tr>
<tr><td><b>AVG / OBP / SLG</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>Standard</td><td><span class='dir-g'>↑ Higher</span></td><td>Display only</td></tr>
<tr><td><b>wOBA / xwOBA</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>.290 → .390</td><td><span class='dir-g'>↑ Higher</span></td><td>Pitch mix score, platoon score</td></tr>
</tbody></table>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='info-section-title'>⚾ Pitcher Metrics</div>", unsafe_allow_html=True)
        st.markdown("""<table class='meth-table'>
<thead><tr><th>Metric</th><th>Source</th><th>Range</th><th>Red = Pitcher Danger When</th><th>Weight</th></tr></thead>
<tbody>
<tr><td><b>Barrel % Allowed</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>2% → 14%</td><td><span class='dir-r'>↑ High</span></td><td>30 — strongest predictor</td></tr>
<tr><td><b>HR / FB %</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>5% → 20%</td><td><span class='dir-r'>↑ High</span></td><td>25</td></tr>
<tr><td><b>Hard Hit % Allowed</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>28% → 50%</td><td><span class='dir-r'>↑ High</span></td><td>20</td></tr>
<tr><td><b>K %</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>14% → 35%</td><td><span class='dir-r'>↓ Low</span> (hitters make contact)</td><td>15</td></tr>
<tr><td><b>FB % Allowed</b></td><td><span class='src-tag src-fg'>FanGraphs</span></td><td class='range-lbl'>20% → 50%</td><td><span class='dir-r'>↑ High</span> (more fly balls)</td><td>7</td></tr>
<tr><td><b>Exit Velo Allowed</b></td><td><span class='src-tag src-sc'>Statcast</span></td><td class='range-lbl'>82 → 93 mph</td><td><span class='dir-r'>↑ High</span></td><td>3</td></tr>
<tr><td colspan='5' style='color:#64748b;font-size:.74rem;padding-top:6px'>★ When a pitcher has no data, 2024-25 MLB league averages are substituted to ensure a score is always produced (~50 = league average risk)</td></tr>
</tbody></table>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='info-section-title'>💥 HR Score Weights & Data Sources</div>", unsafe_allow_html=True)
        st.markdown("""<table class='meth-table'>
<thead><tr><th>Component</th><th>Weight</th><th>How Derived</th><th>Source</th></tr></thead>
<tbody>
<tr><td><b>Hitter Quality</b></td><td>22%</td><td>Weighted composite of barrel%, hard hit%, EV, launch angle, sweet spot%, FB%, pull%, K% — each scaled 0-100 within MLB percentile range</td><td><span class='src-tag src-sc'>Statcast</span> <span class='src-tag src-fg'>FanGraphs</span></td></tr>
<tr><td><b>Pitcher HR Risk</b></td><td>28%</td><td>Barrel% allowed, HR/FB, hard hit% allowed, K%, FB%, EV allowed — weighted composite, league avg fallback when missing</td><td><span class='src-tag src-sc'>Statcast</span> <span class='src-tag src-fg'>FanGraphs</span></td></tr>
<tr><td><b>Pitch Mix wOBA</b></td><td>25%</td><td>Hitter's wOBA vs each pitch type (league-wide) weighted by SP's arsenal usage %. Scaled: .220 = 0pts, .420 = 100pts</td><td><span class='src-tag src-sv'>Savant</span></td></tr>
<tr><td><b>Platoon wOBA</b></td><td>18%</td><td>Hitter's wOBA vs RHP or LHP this season. Scaled same as above. ★ = today's matchup hand</td><td><span class='src-tag src-sv'>Savant</span></td></tr>
<tr><td><b>Park Factor</b></td><td>5%</td><td>Multi-year park HR factor. 1.00 = neutral (50pts). Each 0.01 above/below neutral = ±1pt. COL=1.18 (best), SDP=0.93 (worst)</td><td>Historical</td></tr>
<tr><td><b>Weather</b></td><td>2%</td><td>Temperature (warm = good), wind direction/speed (blowing out = good), rain probability (penalty). Open-Meteo hourly forecast at game time</td><td><span class='src-tag src-mlb'>Open-Meteo</span></td></tr>
</tbody></table>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='info-section-title'>🔥 Last 14 Days Section</div>", unsafe_allow_html=True)
        st.markdown("""<table class='meth-table'>
<thead><tr><th>Column</th><th>What It Shows</th><th>Source</th></tr></thead>
<tbody>
<tr><td><b>BRL %</b></td><td>Barrel rate over last 14 days — computed from raw pitch-by-pitch exit velo + launch angle using official Savant barrel formula (≥98 mph in sweet spot range)</td><td><span class='src-tag src-sv'>Savant</span></td></tr>
<tr><td><b>HARD %</b></td><td>% of batted balls with exit velocity ≥ 95 mph over last 14 days</td><td><span class='src-tag src-sv'>Savant</span></td></tr>
<tr><td><b>EXIT VELO</b></td><td>Average exit velocity on all batted balls over last 14 days</td><td><span class='src-tag src-sv'>Savant</span></td></tr>
<tr><td><b>LAUNCH</b></td><td>Average launch angle over last 14 days. 10-25° = optimal HR range</td><td><span class='src-tag src-sv'>Savant</span></td></tr>
<tr><td><b>SwStr %</b></td><td>Swinging strike rate (whiffs ÷ total swings) over last 14 days — lower = better contact</td><td><span class='src-tag src-sv'>Savant</span></td></tr>
<tr><td><b>HR</b></td><td>Home runs hit in the last 14 days — direct count from event log</td><td><span class='src-tag src-sv'>Savant</span></td></tr>
</tbody></table>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='info-panel'>", unsafe_allow_html=True)
        st.markdown("<div class='info-section-title'>📡 Data Sources</div>", unsafe_allow_html=True)
        st.markdown("""<table class='meth-table'>
<thead><tr><th>Source</th><th>Data Provided</th><th>Refresh</th></tr></thead>
<tbody>
<tr><td><span class='src-tag src-sc'>Statcast</span> Baseball Savant</td><td>Barrel%, hard hit%, exit velo, launch angle, sweet spot%, wOBA, xwOBA, pitch-by-pitch splits, last 14 days raw data, arsenal usage</td><td>Daily</td></tr>
<tr><td><span class='src-tag src-fg'>FanGraphs</span> via pybaseball</td><td>K%, BB%, SwStr%, pull%, FB%, GB%, HR/FB%, ISO, standard slash line, pitcher ERA/FIP/xFIP</td><td>Daily</td></tr>
<tr><td><span class='src-tag src-mlb'>MLB Stats API</span></td><td>Game schedule, rosters, probable pitchers, pitcher handedness, venue</td><td>Real-time</td></tr>
<tr><td><span class='src-tag src-mlb'>Open-Meteo</span></td><td>Hourly weather forecast at each ballpark (temp, wind speed/direction, precipitation)</td><td>Hourly</td></tr>
</tbody></table>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption(f"HR Slate Analyzer · {SEASON}/{SEASON_FALLBACK} · Savant pitch splits · FanGraphs/Statcast via pybaseball · Weather: Open-Meteo · MLB Stats API")