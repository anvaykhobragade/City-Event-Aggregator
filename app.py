"""
app.py — City Event Aggregator · Streamlit UI
Run: streamlit run app.py
"""

import streamlit as st
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# ── Page config (must be FIRST Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="🏙️ City Event Aggregator",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Fonts */
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

  /* Main App Background - Removed to let Streamlit handle light/dark natively */
  
  /* Header gradient */
  .hero-banner {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    padding: 3rem 2rem;
    border-radius: 20px;
    margin-bottom: 2rem;
    text-align: center;
    color: white;
    box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.5);
  }
  .hero-banner h1 { font-size: 3.2rem; font-weight: 700; margin: 0; letter-spacing: -1px; }
  .hero-banner p  { font-size: 1.2rem; opacity: 0.9; margin-top: 0.8rem; font-weight: 300; }

  /* Event cards */
  .event-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.05);
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  }
  .event-card:hover { 
    transform: translateY(-5px); 
    box-shadow: 0 15px 35px 0 rgba(0, 0, 0, 0.15); 
    background: var(--background-color);
  }
  .event-title { font-size: 1.25rem; font-weight: 700; color: var(--text-color); line-height: 1.3; }
  .event-meta  { font-size: 0.9rem; color: var(--text-color); opacity: 0.7; margin-top: 0.5rem; font-weight: 500; }
  .badge       { display: inline-block; background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%); color: #4338ca;
                  padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }
  .score-pill  { display: inline-block; background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%); color: #15803d;
                  padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }

  /* Weather card */
  .weather-card {
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
    color: white; border-radius: 20px; padding: 2rem;
    box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.5);
  }
  .weather-temp { font-size: 3.5rem; font-weight: 700; line-height: 1; margin: 0.5rem 0; }
  .weather-desc { font-size: 1.1rem; opacity: 0.9; font-weight: 500; }
  .forecast-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.18);
    border-radius: 16px;
    padding: 1.1rem 0.9rem;
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    overflow: hidden;
  }
  .forecast-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px -6px rgba(0,0,0,0.12); }
  .forecast-card.best-day { border-color: #22c55e; border-width: 2px; }
  .forecast-card.worst-day { border-color: #ef4444; border-width: 2px; }
  .forecast-dow   { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #6366f1; margin-bottom: 2px; }
  .forecast-date  { font-size: 0.82rem; color: var(--text-color); opacity: 0.65; margin-bottom: 0.5rem; }
  .forecast-emoji { font-size: 2.2rem; line-height: 1; margin: 0.3rem 0; }
  .forecast-cond  { font-size: 0.75rem; color: var(--text-color); opacity: 0.8; margin-bottom: 0.4rem; }
  .forecast-temp  { font-size: 1rem; font-weight: 700; color: var(--text-color); margin-bottom: 0.3rem; }
  .forecast-rain  { font-size: 0.72rem; color: #3b82f6; margin-bottom: 0.6rem; }
  .suit-badge     { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; }
  .suit-great  { background: #dcfce7; color: #15803d; }
  .suit-good   { background: #d1fae5; color: #065f46; }
  .suit-fair   { background: #fef9c3; color: #854d0e; }
  .suit-poor   { background: #fee2e2; color: #991b1b; }

  /* Metric cards */
  .metric-row { display: flex; gap: 1rem; margin: 1rem 0; flex-wrap: wrap; }
  .metric-box {
    background: var(--secondary-background-color); border-radius: 16px; padding: 1.2rem;
    flex: 1; min-width: 120px; text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.2);
  }
  .metric-value { font-size: 1.8rem; font-weight: 700; background: linear-gradient(to right, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .metric-label { font-size: 0.85rem; color: var(--text-color); opacity: 0.7; margin-top: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

  /* Judge scores */
  .judge-bar-bg  { background: rgba(128, 128, 128, 0.2); border-radius: 8px; height: 8px; margin: 8px 0; overflow: hidden; }
  .judge-bar-fill{ background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899); border-radius: 8px; height: 100%; transition: width 1s ease-out; }

  /* Section headers */
  .section-header {
    font-size: 1.5rem; font-weight: 700; color: var(--text-color);
    border-left: 5px solid #6366f1; padding-left: 16px; margin: 2.5rem 0 1.5rem;
    line-height: 1.2;
  }

  /* Timeline */
  .timeline-item {
    border-left: 3px solid rgba(128, 128, 128, 0.3); padding-left: 1.5rem;
    margin-bottom: 1.5rem; padding-bottom: 0.5rem; position: relative;
  }
  .timeline-item::before {
    content: ''; position: absolute; left: -7.5px; top: 0; width: 12px; height: 12px;
    background: #6366f1; border-radius: 50%; border: 2px solid var(--background-color);
  }
  .timeline-time { font-size: 0.85rem; color: #6366f1; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
  .timeline-act  { font-weight: 700; color: var(--text-color); font-size: 1.1rem; margin-top: 0.2rem; }
  .timeline-tip  { font-size: 0.95rem; color: var(--text-color); opacity: 0.7; margin-top: 0.3rem; }

  /* Sidebar - Removed background to let Streamlit handle it */

  /* Buttons */
  div.stButton > button:first-child {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white; border: none; border-radius: 12px; font-weight: 600; padding: 0.5rem 1rem;
    transition: all 0.3s ease;
  }
  div.stButton > button:first-child:hover {
    transform: translateY(-2px); box-shadow: 0 10px 20px -10px rgba(99, 102, 241, 0.6);
  }

  /* Progress */
  .stage-status { font-size: 1rem; padding: 4px 0; font-weight: 500; }

  /* Grade badge */
  .grade-a-plus { color: #166534; background: #dcfce7; padding: 8px 16px; border-radius: 12px; font-weight: 800; font-size: 1.8rem; display: inline-block; box-shadow: 0 4px 10px rgba(22, 101, 52, 0.1); }
  .grade-a      { color: #15803d; background: #dcfce7; padding: 8px 16px; border-radius: 12px; font-weight: 800; font-size: 1.8rem; display: inline-block; box-shadow: 0 4px 10px rgba(21, 128, 61, 0.1); }
  .grade-b      { color: #c2410c; background: #ffedd5; padding: 8px 16px; border-radius: 12px; font-weight: 800; font-size: 1.8rem; display: inline-block; box-shadow: 0 4px 10px rgba(194, 65, 12, 0.1); }
  .grade-c      { color: #b91c1c; background: #fee2e2; padding: 8px 16px; border-radius: 12px; font-weight: 800; font-size: 1.8rem; display: inline-block; box-shadow: 0 4px 10px rgba(185, 28, 28, 0.1); }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "result"       not in st.session_state: st.session_state.result       = None
if "running"      not in st.session_state: st.session_state.running      = False
if "orchestrator" not in st.session_state: st.session_state.orchestrator = None


# ── Lazy orchestrator init ────────────────────────────────────────────────────
def get_orchestrator():
    if st.session_state.orchestrator is None:
        from orchestrator import CityEventOrchestrator
        st.session_state.orchestrator = CityEventOrchestrator()
    return st.session_state.orchestrator


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏙️ Configure Your Search")
    st.markdown("---")

    try:
        orch = get_orchestrator()
        cities     = orch.get_supported_cities()
        categories = orch.get_supported_categories()
    except Exception:
        cities     = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune",
                       "Kolkata", "Jaipur", "Goa", "Nagpur", "London", "New York"]
        categories = ["all", "Music Concerts", "Food Festivals", "Art Exhibitions",
                       "Sports Events", "Cultural Festivals", "Comedy Shows"]

    city = st.selectbox("📍 Select City", cities, index=0)

    # Allow custom city
    custom_city = st.text_input("✏️  Or type a city name", placeholder="e.g. Nashik, Kolkata…")
    if custom_city.strip():
        city = custom_city.strip().title()

    category = st.selectbox("🎭 Event Category", categories, index=0)

    st.markdown("#### 📅 Date Range")
    import datetime as dt
    today = dt.date.today()
    forecast_limit = today + dt.timedelta(days=15)
    date_to = st.date_input(
        "Find events until:",
        value=today + dt.timedelta(days=6),
        min_value=today,
        max_value=forecast_limit,
    )
    st.caption("Weather forecast is available for up to 16 days.")

    st.markdown("#### 👤 Your Preferences")

    interests_options = ["Music", "Food", "Art", "Sports", "Culture", "Comedy", "Theatre", "Outdoor"]
    interests = st.multiselect("Interests", interests_options, default=["Music", "Food"])

    budget = st.select_slider(
        "Budget", options=["Free", "Budget", "Moderate", "Premium", "Luxury"], value="Moderate"
    )
    group_type = st.selectbox(
        "Going as…", ["Solo", "Couple", "Friends", "Family", "Corporate"]
    )

    st.markdown("#### ⚙️ Settings")
    run_judge = st.toggle("🤖 Run LLM-as-Judge", value=True)

    st.markdown("---")
    search_btn = st.button(
        "🔍 Find Events", type="primary", use_container_width=True,
        disabled=st.session_state.running
    )

    # API key status
    st.markdown("#### 🔑 System Status")
    try:
        from config import validate_keys
        keys = validate_keys()
        for name, ok in keys.items():
            icon = "✅" if ok else "❌"
            st.markdown(f"{icon} `{name.upper()}`")
    except Exception:
        st.warning("Add your API keys to .env")


# ── Hero banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <h1>🏙️ City Event Aggregator</h1>
  <p>Real-time events · Live weather · Personalised day plans · AI-powered recommendations</p>
</div>
""", unsafe_allow_html=True)


# ── Run pipeline on button click ──────────────────────────────────────────────
if search_btn:
    st.session_state.running = True
    preferences = {
        "interests":  [i.lower() for i in interests],
        "budget":     budget.lower(),
        "group_type": group_type.lower(),
    }

    progress_placeholder = st.empty()

    with progress_placeholder.container():
        st.markdown(f"### 🔄 Searching for events in **{city}**…")
        progress_bar = st.progress(0)
        stage_status = st.empty()

        stages = [
            ("🔍 Discovering events…",           20),
            ("🌤️  Fetching live weather…",        40),
            ("✂️  Curating & ranking events…",    60),
            ("🎯 Generating personalised plan…", 80),
            ("⚖️  Running quality evaluation…",  100),
        ]
        for msg, pct in stages:
            stage_status.markdown(f"**{msg}**")
            progress_bar.progress(pct)
            time.sleep(0.3)

    try:
        orch = get_orchestrator()
        
        date_from_str = today.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d") if date_to else None

        result = orch.run(
            city=city,
            category=category,
            preferences=preferences,
            run_judge=run_judge,
            date_from=date_from_str,
            date_to=date_to_str
        )
        st.session_state.result = result
        if result and date_to_str:
            result["date_to"] = date_to_str
    except Exception as exc:
        st.error(f"Pipeline error: {exc}")
        result = None

    progress_placeholder.empty()
    st.session_state.running = False


# ── Render results ────────────────────────────────────────────────────────────
result = st.session_state.result

if result:
    pipeline     = result.get("pipeline", {})
    weather_data = pipeline.get("weather", {})
    curation     = pipeline.get("curation", {})
    reco         = pipeline.get("recommendations", {})
    judge        = pipeline.get("evaluation", {})
    timing       = result.get("timing", {})
    errors       = result.get("errors", [])

    current_weather = weather_data.get("current", {})
    curated_events  = curation.get("curated_events", [])
    forecast        = weather_data.get("forecast", [])

    # ── Errors / warnings ────────────────────────────────────────────────────
    if errors:
        with st.expander(f"⚠️ {len(errors)} warning(s)", expanded=False):
            for e in errors:
                st.warning(e)

    # ── Quick stats ──────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    total_time = timing.get("total", 0)
    with col1:
        st.metric("📍 City", result.get("city", "—"))
    with col2:
        st.metric("🎟️ Events Found", len(curated_events))
    with col3:
        outdoor = current_weather.get("outdoor_score", "?")
        st.metric("🌿 Outdoor Score", f"{outdoor}/10")
    with col4:
        grade = judge.get("grade", "—") if judge else "—"
        score = judge.get("overall_score", "—") if judge else "—"
        st.metric("⚖️ Judge Score", f"{score}/10")
    with col5:
        st.metric("⏱️ Total Time", f"{total_time}s")

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎉 Events", "🌤️ Weather", "🗓️ Day Plan", "⚖️ AI Judge"
    ])

    # ── TAB 1: Events ────────────────────────────────────────────────────────
    with tab1:
        curator_insight = curation.get("insights", "")
        if curator_insight:
            st.info(f"✂️ **Curator's Note:** {curator_insight}")

        if not curated_events:
            st.warning("No events found. Try a different city or category.")
        else:
            top_pick = curation.get("top_pick")
            if top_pick:
                st.markdown('<div class="section-header">🏆 Top Pick</div>', unsafe_allow_html=True)
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### {top_pick.get('badge', '🎟️')} {top_pick.get('title', '')}")
                        st.markdown(f"📅 {top_pick.get('date', 'TBD')} &nbsp;|&nbsp; 📍 {top_pick.get('venue', '')} &nbsp;|&nbsp; 💰 {top_pick.get('price', 'TBD')}")
                        st.markdown(top_pick.get("description", ""))
                        if top_pick.get("why_go"):
                            st.success(f"✨ **Why go:** {top_pick['why_go']}")
                        if top_pick.get("weather_tip"):
                            st.info(f"🌤️ **Weather tip:** {top_pick['weather_tip']}")
                    with c2:
                        score = top_pick.get("relevance_score", 0)
                        st.markdown(f"""
                        <div style='text-align:center;background:#f0f4ff;border-radius:12px;padding:1.5rem'>
                          <div style='font-size:2.5rem;font-weight:700;color:#3b5bdb'>{score}</div>
                          <div style='font-size:0.8rem;color:#666'>Relevance Score</div>
                          <div style='font-size:1.4rem;margin-top:0.5rem'>{top_pick.get('badge','🎟️')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if top_pick.get("url"):
                            st.link_button("🔗 View Event", top_pick["url"])

            st.markdown('<div class="section-header">🎟️ All Curated Events</div>', unsafe_allow_html=True)

            # Category filter
            all_cats = list({e.get("category", "Other") for e in curated_events})
            filter_cat = st.multiselect("Filter by category", all_cats, default=all_cats)
            filtered = [e for e in curated_events if e.get("category", "Other") in filter_cat]

            cols_per_row = 2
            for i in range(0, len(filtered), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(filtered):
                        event = filtered[i + j]
                        with col:
                            st.markdown(f"""
                            <div class="event-card">
                              <div class="event-title">{event.get('badge','🎟️')} {event.get('title','')}</div>
                              <div class="event-meta">
                                📅 {event.get('date','TBD')} &nbsp;·&nbsp;
                                📍 {event.get('venue','')} &nbsp;·&nbsp;
                                💰 {event.get('price','TBD')}
                              </div>
                              <div style="margin-top:0.5rem;font-size:0.9rem;color:#888">{event.get('description','')}</div>
                              {"<div style='margin-top:0.5rem;font-size:0.82rem;color:var(--text-color);opacity:0.8;background:rgba(128, 128, 128, 0.1);padding:6px 10px;border-radius:6px;border-left:3px solid #8b5cf6'>☂️ " + event.get('weather_tip','') + "</div>" if event.get('weather_tip') else ""}
                              <div style="margin-top:0.6rem">
                                <span class="badge">{event.get('category','Other')}</span>
                                <span class="score-pill" style="margin-left:6px">Score: {event.get('relevance_score',0)}</span>
                              </div>
                            </div>
                            """, unsafe_allow_html=True)
                            if event.get("url"):
                                st.link_button("🔗 Details", event["url"], use_container_width=True)

    # ── TAB 2: Weather ───────────────────────────────────────────────────────
    with tab2:
        if not current_weather or "error" in current_weather:
            st.warning("Live current weather is unavailable right now.")
        else:
            # Current weather card
            col_w1, col_w2 = st.columns([2, 3])
            with col_w1:
                st.markdown(f"""
                <div class="weather-card">
                  <div style="font-size:1rem;opacity:0.8">{current_weather.get('city','')} {current_weather.get('country','')}</div>
                  <div class="weather-temp">{current_weather.get('emoji','')} {current_weather.get('temperature','')}°C</div>
                  <div class="weather-desc">{current_weather.get('description','')}</div>
                  <div style="margin-top:1rem;font-size:0.85rem;opacity:0.85">
                    Feels like {current_weather.get('feels_like','')}°C &nbsp;·&nbsp;
                    {current_weather.get('temp_min','')}° / {current_weather.get('temp_max','')}°
                  </div>
                  <div style="font-size:0.82rem;opacity:0.8;margin-top:0.3rem">
                    💧 Humidity: {current_weather.get('humidity','')}% &nbsp;·&nbsp;
                    💨 Wind: {current_weather.get('wind_speed','')} km/h
                  </div>
                  <div style="font-size:0.82rem;opacity:0.8">
                    🌅 {current_weather.get('sunrise','')} → 🌇 {current_weather.get('sunset','')}
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with col_w2:
                advice = weather_data.get("advice", "")
                if advice:
                    st.markdown("#### 🤖 AI Weather Analysis")
                    st.info(advice)

                # Outdoor score gauge
                outdoor_score = current_weather.get("outdoor_score", 5)
                st.markdown("#### 🌿 Outdoor Event Suitability")
                st.progress(outdoor_score / 10)
                colour = "🟢" if outdoor_score >= 7 else ("🟡" if outdoor_score >= 5 else "🔴")
                st.markdown(f"{colour} **{outdoor_score}/10** — {weather_data.get('quick_summary','')}")

                # Event type recs
                event_recs = weather_data.get("event_recommendations", {})
                if event_recs:
                    st.markdown("#### 🎟️ Event Type Suitability")
                    for etype, label in event_recs.items():
                        st.markdown(f"**{etype.replace('_',' ').title()}**: {label}")

        if forecast:
            # ── Compute suitability for every day ────────────────────────────
            def _day_suit(day: dict):
                rain = day.get("rain_chance", 0)
                tmax = day.get("temp_max", 25)
                desc = day.get("description", "").lower()
                bad  = any(w in desc for w in ["storm", "heavy rain", "snow", "fog"])
                if bad or rain > 60:   return "poor",  "🔴", "Poor — stay indoors"
                if rain > 35:         return "fair",  "🟡", "Fair — carry umbrella"
                if tmax > 38:         return "fair",  "🟡", "Fair — very hot"
                if rain <= 15:        return "great", "🟢", "Great for events!"
                return "good", "🔵", "Good — enjoy yourself"

            # best-day set from agent or compute from suitability
            best_days_set = set(weather_data.get("best_days", []))

            try:
                date_to_selected = result.get("date_to", "")
                nice_until = datetime.strptime(date_to_selected, "%Y-%m-%d").strftime("%b %d, %Y") if date_to_selected else ""
            except Exception:
                nice_until = ""

            header_text = f"📅 Day-by-Day Weather Forecast"
            if nice_until:
                header_text = f"📅 Day-by-Day Forecast &nbsp;<small style='font-size:0.9rem;font-weight:400;opacity:0.6'>until {nice_until}</small>"
            st.markdown(f'<div class="section-header">{header_text}</div>', unsafe_allow_html=True)

            # ── Build event date → title lookup for event-weather linking ─────
            event_date_lookup: dict = {}
            for ev in curated_events:
                ev_date = ev.get("date", "")
                ev_title = ev.get("title", "")
                if ev_date and ev_title:
                    # normalise date key loosely (take first 10 chars if ISO)
                    short = ev_date[:10] if len(ev_date) >= 10 else ev_date
                    event_date_lookup.setdefault(short, []).append(ev_title)

            # ── Render cards in rows of up to 5 ──────────────────────────────
            for row_start in range(0, len(forecast), 5):
                chunk   = forecast[row_start : row_start + 5]
                row_cols = st.columns(len(chunk))
                for col, day in zip(row_cols, chunk):
                    suit_key, suit_dot, suit_label = _day_suit(day)
                    day_date   = day.get("date", "")          # YYYY-MM-DD
                    day_label  = day.get("day", day_date)     # e.g. "Monday, Apr 28"
                    # split into weekday / date parts for cleaner display
                    parts = day_label.split(",") if "," in day_label else [day_label, ""]
                    dow   = parts[0].strip()
                    dnum  = parts[1].strip() if len(parts) > 1 else ""
                    is_best  = any(bd in day_label for bd in best_days_set)
                    card_cls = "forecast-card" + (" best-day" if is_best else "")
                    # events on that day
                    ev_on_day = event_date_lookup.get(day_date, [])
                    ev_html   = ""
                    if ev_on_day:
                        ev_html = f"<div style='margin-top:6px;font-size:0.65rem;color:#6366f1;font-weight:600'>🎟️ {ev_on_day[0][:28]}{'…' if len(ev_on_day[0])>28 else ''}</div>"
                        if len(ev_on_day) > 1:
                            ev_html += f"<div style='font-size:0.6rem;color:#6366f1'>+{len(ev_on_day)-1} more</div>"
                    best_ribbon = "<div style='position:absolute;top:0;right:0;background:#22c55e;color:white;font-size:0.55rem;font-weight:700;padding:2px 7px;border-radius:0 16px 0 8px;letter-spacing:0.5px'>BEST DAY</div>" if is_best else ""
                    with col:
                        st.markdown(f"""
                        <div class="{card_cls}">
                          {best_ribbon}
                          <div class="forecast-dow">{dow}</div>
                          <div class="forecast-date">{dnum}</div>
                          <div class="forecast-emoji">{day.get('emoji','🌡️')}</div>
                          <div class="forecast-cond">{day.get('description','')}</div>
                          <div class="forecast-temp">{day.get('temp_max','--')}° / {day.get('temp_min','--')}°</div>
                          <div class="forecast-rain">💧 Rain {day.get('rain_chance',0)}%</div>
                          <span class="suit-badge suit-{suit_key}">{suit_label}</span>
                          {ev_html}
                        </div>
                        """, unsafe_allow_html=True)

            # ── Best-day call-out ─────────────────────────────────────────────
            best_days = weather_data.get("best_days", [])
            if best_days:
                st.success(f"🌟 **Best days for outdoor events this period:** {' · '.join(best_days)}")

    # ── TAB 3: Day Plan ──────────────────────────────────────────────────────
    with tab3:
        note = reco.get("personalised_note", "")
        if note:
            st.success(f"👋 {note}")

        day_plan = reco.get("day_plan", "")
        if day_plan:
            st.markdown('<div class="section-header">🗓️ Your Personalised Day Plan</div>', unsafe_allow_html=True)
            # Render as clean paragraphs
            for para in day_plan.split("\n\n"):
                if para.strip():
                    st.markdown(para)

        # Itinerary timeline
        itinerary = reco.get("itinerary", [])
        if itinerary:
            st.markdown('<div class="section-header">⏰ Hour-by-Hour Itinerary</div>', unsafe_allow_html=True)
            for item in itinerary:
                st.markdown(f"""
                <div class="timeline-item">
                  <div class="timeline-time">🕐 {item.get('time','')} ({item.get('duration','')})</div>
                  <div class="timeline-act">{item.get('activity','')}</div>
                  <div class="timeline-tip">📍 {item.get('location','')} — {item.get('tip','')}</div>
                </div>
                """, unsafe_allow_html=True)

        # Dining & Transport
        col_d, col_t = st.columns(2)
        with col_d:
            dining = reco.get("dining_tips", "")
            if dining:
                st.markdown('<div class="section-header">🍽️ Dining Tips</div>', unsafe_allow_html=True)
                st.markdown(dining)
        with col_t:
            transport = reco.get("transport_tips", "")
            if transport:
                st.markdown('<div class="section-header">🚇 Getting Around</div>', unsafe_allow_html=True)
                st.markdown(transport)

    # ── TAB 4: AI Judge ──────────────────────────────────────────────────────
    with tab4:
        if not judge:
            st.info("Enable 'Run LLM-as-Judge' in the sidebar to see quality evaluation.")
        else:
            overall_score = judge.get("overall_score", 0)
            grade         = judge.get("grade", "?")
            summary       = judge.get("judge_summary", "")
            scores        = judge.get("scores", {})
            strengths     = judge.get("strengths", [])
            improvements  = judge.get("improvements", [])

            col_g1, col_g2 = st.columns([1, 3])
            with col_g1:
                grade_class = "grade-a-plus" if grade == "A+" else ("grade-a" if "A" in grade else ("grade-b" if "B" in grade else "grade-c"))
                st.markdown(f"""
                <div style="text-align:center;padding:2rem">
                  <div class="{grade_class}">{grade}</div>
                  <div style="font-size:2.5rem;font-weight:700;margin-top:1rem">{overall_score}<span style="font-size:1rem;color:#888">/10</span></div>
                  <div style="font-size:0.85rem;color:#666">Overall Quality</div>
                </div>
                """, unsafe_allow_html=True)
            with col_g2:
                st.markdown("#### ⚖️ Judge's Verdict")
                if summary:
                    st.info(summary)

                # Dimension bars
                if scores:
                    st.markdown("#### 📊 Dimension Scores")
                    for dim, data in scores.items():
                        s   = data.get("score", 0)
                        fb  = data.get("feedback", "")
                        pct = int(s * 10)
                        st.markdown(f"""
                        <div style="margin-bottom:0.8rem">
                          <div style="display:flex;justify-content:space-between">
                            <span style="font-weight:600">{dim.replace('_',' ').title()}</span>
                            <span style="color:#4776e6;font-weight:700">{s}/10</span>
                          </div>
                          <div class="judge-bar-bg">
                            <div class="judge-bar-fill" style="width:{pct}%"></div>
                          </div>
                          <div style="font-size:0.8rem;color:#666">{fb}</div>
                        </div>
                        """, unsafe_allow_html=True)

            # Strengths & improvements
            if strengths or improvements:
                col_s, col_i = st.columns(2)
                with col_s:
                    st.markdown("#### ✅ Strengths")
                    for s in strengths:
                        st.success(s)
                with col_i:
                    if improvements:
                        st.markdown("#### 🔧 Improvement Areas")
                        for imp in improvements:
                            st.warning(imp)

            # Rubric reference
            with st.expander("📋 Full Evaluation Rubric"):
                try:
                    from agents.judge_agent import JudgeAgent
                    rubric_items = JudgeAgent.__new__(JudgeAgent).get_rubric_display()
                except Exception:
                    rubric_items = []
                if rubric_items:
                    for item in rubric_items:
                        st.markdown(f"**{item['dimension']}** ({item['weight']}) — {item['description']}")

    # ── Export button ─────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("📥 Export Results as JSON"):
        json_str = json.dumps(result, indent=2, default=str)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_str,
            file_name=f"city_events_{result.get('city','city')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
        )

else:
    # Empty state
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#888">
      <div style="font-size:4rem">🏙️</div>
      <h3 style="color:#555">Ready to discover your city</h3>
      <p>Select a city and hit <strong>Find Events</strong> to get started.<br>
      The AI will search for events, check the weather, and build you a personalised day plan.</p>
    </div>
    """, unsafe_allow_html=True)

    # Feature showcase
    col1, col2, col3, col4, col5 = st.columns(5)
    features = [
        ("🔍", "Search Engine", "Event Discovery", "Real-time web search for local events"),
        ("🌤️", "Data API", "Weather Intel",   "Current conditions & 5-day forecast"),
        ("✂️", "AI Engine", "Event Curator",   "Intelligent ranking & enrichment"),
        ("🎯", "AI Engine", "Day Planner",     "Personalised itineraries & tips"),
        ("⚖️", "AI Evaluator", "Quality Check",   "Automated rubric-based scoring"),
    ]
    for col, (emoji, label, title, desc) in zip([col1, col2, col3, col4, col5], features):
        with col:
            st.markdown(f"""
            <div style="text-align:center;padding:1.2rem;background:#f8f9fa;border-radius:12px;height:100%">
              <div style="font-size:2rem">{emoji}</div>
              <div style="font-size:0.7rem;color:#4776e6;font-weight:600;margin:4px 0">{label}</div>
              <div style="font-weight:700;font-size:0.9rem">{title}</div>
              <div style="font-size:0.78rem;color:#777;margin-top:4px">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
