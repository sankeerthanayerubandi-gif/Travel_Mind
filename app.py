from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from graph.workflow import run_agentic_workflow
from services.core import convert_currency, get_weather, save_trip, speech_audio, translate
from services.places import DemoPlaceProvider, Place, wikipedia_image
from utils.helpers import money

st.set_page_config(page_title="TravelMind 3D", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --ink:#f3f7ff; --muted:#9aacc6; --violet:#8c6dff; --cyan:#36d7e9; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:radial-gradient(circle at 15% 0%,rgba(70,56,150,.28),transparent 32%),radial-gradient(circle at 90% 10%,rgba(20,164,180,.18),transparent 30%),#07111f; color:var(--ink); }
.block-container { padding:2rem 3.5rem 4rem; max-width:1500px; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif; letter-spacing:-.03em; }
.hero h1 { font-size:clamp(2.8rem,6vw,5.9rem); line-height:.93; margin:.45rem 0 .9rem; background:linear-gradient(105deg,#fff 15%,#b9c8ff 45%,#72ebf0 90%); -webkit-background-clip:text; color:transparent; }
.hero p { color:#a8b8d2; font-size:1.08rem; max-width:700px; }
.eyebrow { color:#7ee7f2; text-transform:uppercase; letter-spacing:.18em; font-size:.72rem; font-weight:700; }
.glass { background:linear-gradient(145deg,rgba(25,43,72,.82),rgba(9,19,34,.80)); border:1px solid rgba(152,174,220,.15); border-radius:24px; padding:1.2rem; box-shadow:0 18px 60px rgba(0,0,0,.22); }
.metric { color:#90a7c8; font-size:.78rem; text-transform:uppercase; letter-spacing:.11em; }
.metric strong { display:block; color:#f6f8ff; font-family:'Space Grotesk'; font-size:1.55rem; margin-top:.3rem; }
.card-title { color:#fff; font-size:1.08rem; font-weight:700; margin-bottom:.25rem; }
.card-sub { color:#9aacc6; font-size:.88rem; line-height:1.45; }
.pill { display:inline-block; border:1px solid rgba(126,231,242,.24); color:#91edf3; border-radius:999px; padding:.25rem .65rem; font-size:.74rem; margin:.12rem; background:rgba(54,215,233,.07); }
.agent { display:flex; gap:.7rem; align-items:flex-start; padding:.6rem 0; border-bottom:1px solid rgba(255,255,255,.07); }
.dot { width:9px; height:9px; background:#58e0c2; border-radius:50%; margin-top:.35rem; box-shadow:0 0 12px #58e0c2; }
section[data-testid="stSidebar"] { background:rgba(6,15,28,.95); border-right:1px solid rgba(157,182,235,.12); }
.stButton>button,.stDownloadButton>button { border-radius:12px; border:1px solid rgba(143,114,255,.45); background:linear-gradient(135deg,#7055e9,#3b8fb5); color:#fff; font-weight:700; }
.place-card { min-height:220px; }
.small-note { color:#93a7c4; font-size:.82rem; }
</style>
""", unsafe_allow_html=True)

BASE = Path(__file__).parent
provider = DemoPlaceProvider(BASE / "data" / "demo_places.csv", enable_live_search=True)

for key, default in {
    "trip": None, "saved_trips": [], "language": "English", "page": "Command Center",
    "selected_place_ids": [], "search_query": "", "planner_destination": "Kyoto, Japan",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

TEXT = {
    "English": {"nav": "Navigate", "plan": "Plan My Trip", "explore": "Explore", "generate": "Generate itinerary", "replan": "Replan itinerary", "today": "Today", "save": "Save trip", "search": "Search", "details": "View details"},
    "Telugu": {"nav": "నావిగేషన్", "plan": "నా ప్రయాణాన్ని ప్లాన్ చేయండి", "explore": "అన్వేషించండి", "generate": "ప్రయాణ ప్రణాళిక రూపొందించండి", "replan": "ప్రణాళికను మార్చండి", "today": "ఈ రోజు", "save": "ప్రయాణాన్ని సేవ్ చేయండి", "search": "వెతకండి", "details": "వివరాలు చూడండి"},
    "Hindi": {"nav": "नेविगेशन", "plan": "मेरी यात्रा की योजना बनाएं", "explore": "अन्वेषण", "generate": "यात्रा कार्यक्रम बनाएं", "replan": "यात्रा फिर से बनाएं", "today": "आज", "save": "यात्रा सहेजें", "search": "खोजें", "details": "विवरण देखें"},
}
T = TEXT.get(st.session_state.language, TEXT["English"])

@st.cache_data(ttl=86400, show_spinner=False)
def image_for(name: str) -> str | None:
    return wikipedia_image(name)


def render_place(place: Place, key_prefix: str, allow_add: bool = True) -> None:
    with st.container(border=True):
        image = image_for(place.name)
        if image:
            st.image(image, use_container_width=True)
        else:
            st.markdown(f"<div class='glass place-card'><div class='eyebrow'>{place.category}</div><h3>{place.name}</h3><p class='card-sub'>No verified image is available; details below come from {place.source}.</p></div>", unsafe_allow_html=True)
        st.markdown(f"**{place.name}** · `{place.category}` · {place.city}, {place.country}")
        st.caption(place.description)
        st.write(f"Visit: {place.estimated_visit_duration or 'Not available'} min · Best time: {place.best_time_to_visit} · Hours: {place.opening_hours}")
        st.caption(f"Source: {place.source} · Location: {place.latitude:.4f}, {place.longitude:.4f}")
        st.link_button("Open map", place.map_url)
        if allow_add and st.button("Add to current trip", key=f"add-{key_prefix}-{place.id}"):
            if place.id not in st.session_state.selected_place_ids:
                st.session_state.selected_place_ids.append(place.id)
            st.success(f"Added {place.name} to the current trip.")


def render_itinerary(trip: dict) -> None:
    st.success(f"Workflow complete · {trip['status']}")
    added = [place for place in provider.places if place.id in st.session_state.selected_place_ids]
    if added:
        st.info("Added to this trip: " + ", ".join(place.name for place in added))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Destination", trip["destination"])
    m2.metric("Days", trip["days"])
    m3.metric("Estimated cost", money(trip["estimated_total"], trip["currency"]))
    m4.metric("Mode", "Adaptive" if "replan" in trip["status"] else "Verified")
    if trip.get("replan_reason"):
        st.info(f"Replanned because: {trip['replan_reason']}")
    for day in trip["itinerary"]:
        with st.expander(f"DAY {day['day']} · {day['date']} · {day['title']}", expanded=day["day"] == 1):
            st.write(day["notes"])
            st.caption(f"Estimated day cost: {trip['currency']} {day['estimated_day_cost']:.2f} · {day['transit']}")
            for index, stop in enumerate(day["stops"]):
                st.markdown(f"**{index + 1}. {stop['name']}** · {stop['category']} · {stop['start_time']}–{stop['end_time']}")
                st.caption(f"{stop['description']} · Visit {stop['recommended_duration_min']} min · Travel from previous stop {stop['travel_time_from_previous_min']} min")
                st.caption(f"Food suggestion: {stop['food_suggestion']} · Opening: {stop['opening_hours']} · Fee: {stop['entry_fee'] or 'Not available'} {stop['currency']}")
                map_col, remove_col = st.columns([3, 1])
                with map_col:
                    st.link_button("Map this place", stop["map_url"], key=f"map-{trip['created_at']}-{day['day']}-{index}")
                with remove_col:
                    if st.button("Remove", key=f"remove-{trip['created_at']}-{day['day']}-{index}"):
                        day["stops"].pop(index)
                        st.rerun()
    points = [stop for day in trip["itinerary"] for stop in day["stops"] if stop.get("latitude") and stop.get("longitude")]
    if points:
        st.subheader("Route map")
        st.map(pd.DataFrame(points).rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]])
    st.download_button("Download itinerary JSON", json.dumps(trip, indent=2, ensure_ascii=False), file_name="travelmind_itinerary.json", mime="application/json")
    share_text = "\n".join(
        [f"TravelMind itinerary: {trip['destination']} · {trip['days']} days"]
        + [f"Day {day['day']}: " + ", ".join(stop["name"] for stop in day["stops"]) for day in trip["itinerary"]]
    )
    st.download_button("Share itinerary summary", share_text, file_name="travelmind_share.txt", mime="text/plain")


with st.sidebar:
    st.markdown("## ◈ TravelMind 3D")
    st.caption("Autonomous multi-agent travel intelligence")
    st.session_state.language = st.selectbox("Language / భాష", ["English", "Telugu", "Hindi", "French", "Japanese"], index=["English", "Telugu", "Hindi", "French", "Japanese"].index(st.session_state.language) if st.session_state.language in ["English", "Telugu", "Hindi", "French", "Japanese"] else 0)
    pages = ["Command Center", "World Explorer", "Trip Studio", "Utilities"]
    st.session_state.page = st.radio(T["nav"], pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)
    st.markdown("---")
    st.markdown("**System status**")
    st.markdown("🟢 Planner online  \n🟢 Place provider cached  \n🟢 Live search fallback ready")
    st.caption("Demo data is labelled. Optional live services fail safely.")

page = st.session_state.page

if page == "Command Center":
    st.markdown('<div class="hero"><div class="eyebrow">Autonomous travel intelligence · abstract-aligned prototype</div><h1>PLAN.<br>EXPLORE.<br>ADAPT.</h1><p>TravelMind coordinates discovery, planning, verification, monitoring, and replanning into one personalized travel workflow.</p></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [(c1, "Places indexed", f"{len(provider.places)} demo + live search"), (c2, "Planning agents", "5"), (c3, "Plan modes", "Today + custom"), (c4, "API keys required", "0")]:
        with col: st.markdown(f'<div class="glass metric">{label}<strong>{value}</strong></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1.55, 1])
    with left:
        st.markdown('<div class="glass"><div class="card-title">🌐 World pulse</div><div class="card-sub">Verified coordinates from the local catalog.</div>', unsafe_allow_html=True)
        df = pd.DataFrame([p.to_dict() for p in provider.places])
        fig = go.Figure(go.Scattergeo(lon=df.longitude, lat=df.latitude, text=df.name, mode="markers+text", textposition="top center", marker=dict(size=10, color=df.popularity_score, colorscale=[[0, "#36d7e9"], [1, "#8c6dff"]], line=dict(width=1, color="#fff"))))
        fig.update_geos(showland=True, landcolor="#12243a", showocean=True, oceancolor="#081629", showcountries=True, countrycolor="#29405d", bgcolor="rgba(0,0,0,0)", projection_type="orthographic")
        fig.update_layout(height=450, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", font_color="#b9c8dd", showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="glass"><div class="card-title">⚡ Agent activity</div><div class="card-sub">The autonomous loop is ready to act.</div>', unsafe_allow_html=True)
        events = (st.session_state.trip or {}).get("agent_events", [{"agent": "Supervisor", "detail": "Waiting for a trip brief."}, {"agent": "Discovery", "detail": "Provider standing by."}, {"agent": "Verifier", "detail": "Constraints ready."}])
        for event in events:
            st.markdown(f'<div class="agent"><span class="dot"></span><div><b>{event["agent"]}</b><br><span class="card-sub">{event["detail"]}</span></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "World Explorer":
    st.markdown('<div class="eyebrow">Global place discovery</div><h1>World Explorer</h1>', unsafe_allow_html=True)
    query = st.text_input("Search destinations or attractions", value=st.session_state.search_query, placeholder="Try Araku, Paris, beach, museum, mountain...")
    st.session_state.search_query = query
    a, b, c = st.columns(3)
    with a: category = st.selectbox("Category", ["All"] + sorted({p.category for p in provider.places}))
    with b: country = st.selectbox("Country", ["All"] + sorted({p.country for p in provider.places}))
    with c: live = st.checkbox("Allow live OpenStreetMap search", value=True)
    provider.enable_live_search = live
    results = provider.search(query, category, country)
    st.caption(f"{len(results)} places surfaced · results without verified facts are clearly labelled")
    if not results:
        st.warning("No place found. Try a city, country, or landmark name.")
    for row in range(0, len(results), 2):
        cols = st.columns(2)
        for col, place in zip(cols, results[row:row + 2]):
            with col: render_place(place, f"explore-{row}")

elif page == "Trip Studio":
    st.markdown('<div class="eyebrow">Plan → verify → monitor → replan</div><h1>Trip Studio</h1>', unsafe_allow_html=True)
    with st.form("trip_form"):
        left, right = st.columns(2)
        with left:
            destination = st.text_input("Destination / city / country", value=st.session_state.planner_destination, help="Examples: Kyoto, Araku, Paris, Japan")
            date_mode = st.radio("Start date", ["Today", "Tomorrow", "Custom date"], horizontal=True)
            custom_date = st.date_input("Custom start date", value=date.today() + timedelta(days=7), disabled=date_mode != "Custom date")
            days = st.slider("Trip duration (days)", 1, 14, 4)
            travelers = st.number_input("Number of travelers", 1, 20, 2)
        with right:
            budget_tier = st.selectbox("Budget level", ["Low", "Medium", "High"])
            budget = st.number_input("Total budget estimate (EUR)", min_value=0.0, max_value=100000.0, value=1800.0, step=100.0)
            currency = st.selectbox("Display currency", ["EUR", "USD", "INR", "GBP"])
            pace = st.select_slider("Travel pace", options=["Relaxed", "Balanced", "Intensive"], value="Balanced")
            available_hours = st.slider("Available hours per day", 2.0, 16.0, 8.0, 0.5)
        interests = st.multiselect("Interests / preferences", ["Nature", "Culture", "Food", "Adventure", "Shopping"], default=["Nature", "Culture"])
        generate = st.form_submit_button(T["generate"], use_container_width=True)
    if generate:
        start_date = date.today() if date_mode == "Today" else date.today() + timedelta(days=1) if date_mode == "Tomorrow" else custom_date
        st.session_state.planner_destination = destination
        request = {"destination": destination, "start_date": start_date, "days": days, "travelers": travelers, "budget": budget, "budget_tier": budget_tier, "currency": currency, "pace": pace, "available_hours": available_hours, "interests": interests, "selected_place_ids": st.session_state.selected_place_ids}
        with st.spinner("Creating your personalized trip with Supervisor, Discovery, Planner, and Verifier agents..."):
            try:
                st.session_state.trip = run_agentic_workflow(request, provider)
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Planner could not complete safely: {exc}")
    trip = st.session_state.trip
    if trip:
        render_itinerary(trip)
        if st.button(T["save"], key="save-trip"):
            st.session_state.saved_trips = save_trip(trip, st.session_state.saved_trips)
            st.success("Trip saved in this session.")
        st.subheader(T["replan"])
        replan_request = st.text_area("What should change?", placeholder="Examples: remove museums, add beaches, make it cheaper, add food places, I have only 4 hours")
        if st.button(T["replan"], key="replan-trip"):
            if not replan_request.strip():
                st.warning("Describe at least one change request.")
            else:
                with st.spinner("Replanning the route around your new constraint..."):
                    try:
                        st.session_state.trip = run_agentic_workflow({**trip, "replan_request": replan_request}, provider, replan_request)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Replanning failed safely: {exc}")

else:
    st.markdown('<div class="eyebrow">Travel utility layer</div><h1>Utilities</h1>', unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        st.markdown('<div class="glass"><div class="card-title">☁ Weather snapshot</div>', unsafe_allow_html=True)
        city_place = st.selectbox("Place for weather", provider.places, format_func=lambda p: f"{p.city} · {p.name}")
        weather = get_weather(city_place.city, city_place.latitude, city_place.longitude)
        if weather["temperature"] is None: st.warning(weather["condition"])
        else: st.metric("Temperature", f"{weather['temperature']}°C", weather["condition"])
        st.caption(f"Humidity {weather['humidity'] if weather['humidity'] is not None else 'Not available'}% · Wind {weather['wind'] if weather['wind'] is not None else 'Not available'} km/h · {weather['source']}")
        st.markdown('</div><br>', unsafe_allow_html=True)
        st.markdown('<div class="glass"><div class="card-title">◎ Currency converter</div>', unsafe_allow_html=True)
        amount = st.number_input("Amount", 1.0, 100000.0, 100.0)
        x, y = st.columns(2)
        with x: src = st.selectbox("From", ["EUR", "USD", "GBP", "JPY", "INR"])
        with y: tgt = st.selectbox("To", ["EUR", "USD", "GBP", "JPY", "INR"], index=1)
        result = convert_currency(amount, src, tgt)
        st.metric("Converted", f"{result['converted']:,.2f} {tgt}", f"Rate {result['rate']} · {result['source_name']}")
        st.markdown('</div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="glass"><div class="card-title">文 Translation pocket</div>', unsafe_allow_html=True)
        text = st.text_area("Text to translate", "Where is the nearest train station?")
        lang = st.selectbox("Target language", ["Telugu", "Hindi", "Japanese", "French", "Spanish", "English"])
        st.info(translate(text, lang))
        if st.button("Speak translation"):
            translated = translate(text, lang)
            with st.spinner("Creating audio..."):
                audio = speech_audio(translated, lang)
            if audio:
                st.audio(audio, format="audio/mp3")
                st.success("Audio is ready. Press the player button to hear the translation.")
            else:
                st.warning("Audio service is unavailable. The translated text is still available above.")
        st.markdown('</div><br>', unsafe_allow_html=True)
        st.markdown('<div class="glass"><div class="card-title">▣ Saved trips</div>', unsafe_allow_html=True)
        if st.session_state.saved_trips:
            for saved in st.session_state.saved_trips:
                st.write(f"**{saved['destination']}** · {saved['days']} days · saved {saved['saved_at']}")
        else: st.caption("No saved trips yet. Generate and save a plan in Trip Studio.")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br><div style='text-align:center;color:#667b9c;font-size:.78rem'>TRAVELMIND 3D · PLAN WITH CONFIDENCE · ADAPT WITH INTELLIGENCE</div>", unsafe_allow_html=True)
