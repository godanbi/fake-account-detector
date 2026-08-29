# app.py
import requests
import streamlit as st

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="AI Fake Detector", page_icon="🤖", layout="wide")
st.markdown("""
<div style='text-align:center; margin-top:10px; margin-bottom:20px;'>
    <img src="https://cdn-icons-png.flaticon.com/512/4712/4712100.png"
         width="110" style="opacity:0.95;">
</div>
""", unsafe_allow_html=True)

# -------------------------
# CSS (clean & compact)
# -------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');

.stApp { background: #1C1A27; color: #ECF0F1; font-family: 'Space Mono', monospace; }
header {visibility: hidden;}
footer {visibility: hidden;}
.main > div { padding-bottom: 140px !important; }

/* Profile picture */
.profile-pic { width:110px; height:110px; border-radius:50%; object-fit:cover; border:3px solid #8E44AD; box-shadow:0 0 12px #8E44AD; }

/* Metrics */
.metric-label { color:#BDC3C7; font-size:14px; }
.metric-value { font-size:22px; font-weight:700; margin-top:4px; }

/* Verdict card */
.verdict-card {
  background: rgba(44,62,80,0.55);
  backdrop-filter: blur(8px);
  padding:20px;
  border-radius:12px;
  border:1px solid rgba(142,68,173,0.3);
  box-shadow:0 0 20px rgba(142,68,173,0.08);
}

/* Final prediction box */
.final-box {
  margin-top:16px;
  padding:14px;
  border-radius:10px;
  text-align:center;
  font-weight:700;
  font-size:20px;
  box-shadow:0 6px 18px rgba(0,0,0,0.45);
}

/* Fixed bottom input bar */
#fixedbar {
  position: fixed; bottom:0; left:0; width:100%;
  padding:14px 0; background: rgba(23,32,42,0.92);
  backdrop-filter: blur(8px); z-index:9999; box-shadow:0 -6px 20px rgba(0,0,0,0.6);
}
#fixedbar .inner { max-width:880px; margin:auto; padding:0 12px; }
#fixedbar .stButton button { border-radius:18px; background:#8E44AD; color:#ECF0F1; font-weight:700; padding:10px 14px; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Utility functions
# -------------------------
def detect_fake_username(username: str):
    uname = username.lower().strip()
    fake_keywords = [
        "giveaway", "winner", "free", "claim", "prize", "bot",
        "officiall", "dmfor", "congrats", "scam", "hack",
        "iphonegiveaway", "shadow", "flex"
    ]
    for kw in fake_keywords:
        if kw in uname:
            return True, f"Scam keyword: '{kw}'"
    if len(uname) > 12 and sum(c.isdigit() for c in uname) > 3:
        return True, "Too many random digits"
    return False, None


def get_profile_data(username: str, timeout=10):

    username = username.strip()

    if not username:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-IG-App-ID": "936619743392459"
    }

    url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)

        if resp.status_code == 200:
            data = resp.json()

            if "data" in data and "user" in data["data"]:

                u = data["data"]["user"]

                return {
                    "exists": True,
                    "username": u.get("username", username),
                    "full_name": u.get("full_name", "Not set"),
                    "bio": u.get("biography", "") or "",
                    "followers": u["edge_followed_by"]["count"],
                    "following": u["edge_follow"]["count"],
                    "posts": u["edge_owner_to_timeline_media"]["count"],
                    "private": u.get("is_private", False),
                    "verified": u.get("is_verified", False),
                    "pic": u.get("profile_pic_url_hd", "")
                }

    except Exception:
        pass

    return {"exists": False}

def score_profile(data: dict, is_fake_uname: bool, uname_reason: str):
    if not data or not data.get("exists"):
        return 100, ["Account does not exist or is inaccessible."]

    score = 0
    reasons = []

    # Username pattern heavy weight
    if is_fake_uname:
        score += 50
        reasons.append(f"Username pattern flagged: {uname_reason}")

    # Posts
    if data.get("posts", 0) == 0:
        score += 30
        reasons.append("Zero posts — common for fakes.")

    # Followers/Following
    followers = data.get("followers", 0)
    following = data.get("following", 0)

    if followers == 0 and following < 50:
        score += 15
        reasons.append("Zero followers with low following — likely inactive/new.")

    if followers > 0 and following / max(1, followers) > 30:
        score += 15
        reasons.append(f"High following/follower ratio ({following}/{followers}).")

    # Bio checks
    fake_bio_keywords = ["dm for business", "investment", "free money", "check my story"]
    bio = (data.get("bio") or "").lower()
    for kw in fake_bio_keywords:
        if kw in bio:
            score += 10
            reasons.append(f"Bio contains suspicious phrase: '{kw}'.")
            break

    # Minimal profile
    if len(data.get("bio", "")) < 10 and data.get("posts", 0) < 5:
        score += 5
        reasons.append("Minimal bio & few posts — incomplete profile.")

    # Name check
    if not data.get("full_name") or data.get("full_name") == data.get("username"):
        score += 5
        reasons.append("Full name not set or same as username.")

    # Private account adds a small suspicion score
    if data.get("private"):
        score += 5
        reasons.append("Private account — content hidden.")

    return min(score, 100), reasons

# -------------------------
# UI render helpers
# -------------------------
def display_profile_header(data: dict):
    left, right = st.columns([1, 4])
    with left:
        if data.get("pic"):
            st.markdown(f'<img src="{data["pic"]}" class="profile-pic" />', unsafe_allow_html=True)
        else:
            st.markdown('<div class="profile-pic" style="display:flex;align-items:center;justify-content:center;background:#2C2A36;">👤</div>', unsafe_allow_html=True)
    with right:
        st.markdown(f"### @{data.get('username', '')}")
        if data.get("full_name") and data.get("full_name") != "Not set":
            st.markdown(f"*Name:* {data.get('full_name')}")
        if data.get("verified"):
            st.markdown("<span style='color:#2ecc71;font-weight:700;'>✅ VERIFIED</span>", unsafe_allow_html=True)
        elif data.get("private"):
            st.markdown("<span style='color:#f1c40f;font-weight:700;'>🔒 PRIVATE</span>", unsafe_allow_html=True)
        st.markdown(f"*Bio:* {(data.get('bio') or 'No bio provided')}", unsafe_allow_html=True)


def display_metrics(data: dict):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="metric-label">Followers</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{data.get("followers",0):,}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-label">Following</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{data.get("following",0):,}</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-label">Posts</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{data.get("posts",0):,}</div>', unsafe_allow_html=True)


def display_verdict(score: int, reasons: list):
    # Primary verdict card
    if score >= 70:
        color = "#e74c3c"
        icon = "🚨"
        title = "HIGHLY SUSPICIOUS (SCAM / BOT)"
    elif score >= 40:
        color = "#f39c12"
        icon = "⚠"
        title = "MODERATELY SUSPICIOUS (INCOMPLETE PROFILE)"
    else:
        color = "#2ecc71"
        icon = "✅"
        title = "LOW RISK (AUTHENTIC)"

    st.markdown(f"""
    <div class="verdict-card" style="border-color:{color}30;">
      <h3 style="color:{color}; margin:0;">{icon} FAKE SCORE: {score}%</h3>
      <p style="color:{color}; font-weight:700; margin-top:6px;">{title}</p>
      <hr style="border-top:1px solid {color}30;">
      <p style="color:#BDC3C7; margin-bottom:6px;"><strong>Analysis Report:</strong></p>
      <ul style="color:#BDC3C7;">
        {''.join([f'<li>• {r}</li>' for r in reasons])}
      </ul>
    </div>
    """, unsafe_allow_html=True)

    # --- FINAL PREDICTION BOX ---
    final_label = ""
    final_color = ""
    final_icon = ""

    if score >= 70:
        final_label = "FAKE ACCOUNT DETECTED"
        final_color = "#e74c3c"
        final_icon = "❌"
    elif score >= 40:
        final_label = "SUSPICIOUS / POSSIBLY FAKE"
        final_color = "#f39c12"
        final_icon = "⚠"
    else:
        final_label = "AUTHENTIC ACCOUNT"
        final_color = "#2ecc71"
        final_icon = "✅"

    st.markdown(f"""
    <div class="final-box" style="border: 2px solid {final_color}; color:{final_color}; background: rgba(0,0,0,0.18);">
        {final_icon} {final_label}
    </div>
    """, unsafe_allow_html=True)

# -------------------------
# App main layout
# -------------------------
st.markdown("<h1 style='text-align:center; margin-bottom:2px;'>NEURAL SCAN — INSTAGRAM ANALYST</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#BDC3C7; margin-top:4px;'>AI-Powered Fake Profile Detection System</p>", unsafe_allow_html=True)

# session state for result
if "scan_result" not in st.session_state:
    st.session_state.scan_result = None

# Display result card or placeholder
if st.session_state.scan_result:
    res = st.session_state.scan_result
    st.markdown('<div style="margin-top:18px;">', unsafe_allow_html=True)
    if not res.get("exists"):
        st.error("❌ TARGET OFFLINE: Account not found or inaccessible.")
        if res.get("is_fake_uname"):
            st.warning(f"⚠ Username flagged: {res.get('uname_reason')}")
    else:
        data = res["data"]
        score = res["score"]
        reasons = res["reasons"]

        st.subheader("📊 PROFILE DATA MATRIX")
        display_profile_header(data)
        st.markdown("<hr style='border-top:1px solid #9B59B650;'>", unsafe_allow_html=True)
        display_metrics(data)
        st.markdown("<hr style='border-top:1px solid #9B59B650;'>", unsafe_allow_html=True)
        display_verdict(score, reasons)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown('<div style="margin-top:18px;" class="verdict-card">', unsafe_allow_html=True)
    st.markdown("### ✅ SYSTEM READY", unsafe_allow_html=True)
    st.markdown("<p style='color:#BDC3C7;'>Enter an Instagram username in the input bar below to run a neural scan.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# Scan logic
# -------------------------
def run_scan():
    username = st.session_state.username_enter.strip()
    if not username:
        return

    is_fake_uname, uname_reason = detect_fake_username(username)
    pdata = get_profile_data(username)

    # Prepare session result
    if not pdata or not pdata.get("exists"):
        st.session_state.scan_result = {
            "exists": False,
            "is_fake_uname": is_fake_uname,
            "uname_reason": uname_reason
        }
    else:
        score, reasons = score_profile(pdata, is_fake_uname, uname_reason)
        st.session_state.scan_result = {
            "exists": True,
            "data": pdata,
            "score": score,
            "reasons": reasons
        }

    # clear input (keeps focus neat)
    st.session_state.username_enter = ""

    # rerun to show results
    st.session_state["trigger_rerun"] = True
    
()

if st.session_state.get("trigger_rerun"):
    st.session_state["trigger_rerun"] = False
    st.rerun()


# -------------------------
# Fixed bottom input bar
# -------------------------
st.markdown("""
<div id="fixedbar">
  <div class="inner">
""", unsafe_allow_html=True)

cols = st.columns([7,1])
with cols[0]:
    st.text_input("Enter Instagram username", key="username_enter", placeholder="Type username (without @) and press Enter or Scan", label_visibility="collapsed", on_change=run_scan)
with cols[1]:
    st.button("SCAN", on_click=run_scan)

st.markdown("</div></div>", unsafe_allow_html=True)
