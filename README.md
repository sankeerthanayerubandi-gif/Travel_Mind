# TravelMind 

**TravelMind — An Autonomous Multi-Agent AI System for Personalized and Dynamic Travel Planning** is a Python + Streamlit final-year project prototype aligned with the submitted BVC Engineering College abstract.

## Abstract alignment

TravelMind accepts a destination, start date, duration, traveler count, budget level, available hours, travel pace, and interests. A small agentic workflow then performs five stages: **Supervisor** decomposes the brief, **Discovery** ranks relevant places, **Planner** creates daily route groups, **Verifier** checks timing/cost/map fields, and **Monitor/Replanner** adapts the result to a change request.

The generated itinerary contains dates, non-repeating places, recommended order, approximate start/end times, visit duration, travel time from the previous stop, food suggestions, opening-hour fields when present, entry-fee fields when present, coordinates, map links, estimated day cost, and a route map. Selecting **Today** uses the actual runtime date; custom dates and tomorrow are also supported.

## Working features

- Personalized itinerary planning for destination, date, duration, travelers, budget, interests, pace, and available time.
- Meaningful replan requests such as “remove museums,” “add beaches,” “make it cheaper,” “add food places,” or “I have only 4 hours.” Replanning produces a different ranked route when alternatives exist.
- All important actions are wired: Add to current trip carries a place into the next plan, Remove updates the current itinerary, Save stores the trip in session state, Share itinerary summary downloads a text summary, Map this place opens the real OpenStreetMap location, and Speak translation generates playable audio when the speech service is available.
- Search across a verified local catalog plus optional live OpenStreetMap/Nominatim fallback for unknown destinations.
- Real coordinates and OpenStreetMap links for every catalog place.
- Safe Wikipedia thumbnail lookup for relevant place images; if no verified image is available, the interface explains that no image was found rather than showing a random image.
- Weather through Open-Meteo when coordinates are available, Frankfurter reference currency rates, deterministic fallback rates, phrase translation for Telugu, Hindi, Japanese, French, Spanish, and English, and session-saved trips.
- Plotly globe, Streamlit route map, place details, add-to-trip state, JSON download, save trip, live-search toggle, language selector, and safe error handling.
- Telugu/Hindi/Japanese/French/Spanish translation audio through Google Text-to-Speech (`gTTS`) without storing credentials.

## Run locally

```bash
cd TravelMind3D
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://localhost:8501`.

## Streamlit Cloud deployment

1. Push the `TravelMind3D` folder to a GitHub repository.
2. Create a Streamlit Community Cloud app from that repository.
3. Set the main file to `app.py`.
4. Deploy using `requirements.txt`.
5. Optional secrets can be added in the Streamlit Cloud settings; the app remains usable without them.

## APIs and services

| Service | Purpose | Key required |
|---|---|---:|
| OpenStreetMap Nominatim | Optional live destination/place search | No, but a descriptive User-Agent is sent |
| OpenStreetMap | Map links and Streamlit map attribution | No |
| Open-Meteo | Live weather by coordinates | No |
| Frankfurter / ECB reference rates | Currency conversion | No |
| Wikipedia REST summary | Optional verified place thumbnails | No |
| Google Text-to-Speech | Playable translation audio | No |
| Local CSV catalog | Stable offline demo and test data | No |

No payment, booking, or secret API credential is included. Provider failures return safe messages or fallbacks.

## Files modified for the abstract-aligned build

- `app.py`: rebuilt the Streamlit interface with stateful planning, Today/custom dates, budget/interests/time controls, explorer, images, maps, translation, saving, export, and replan controls.
- `graph/workflow.py`: implemented personalized ranking, route timing, budget filtering, no-repeat allocation, date handling, and meaningful replanning.
- `services/places.py`: added comma-separated destination matching, live Nominatim discovery, map URLs, normalized data, and safe Wikipedia image lookup.
- `services/core.py`: added live weather, currency conversion, supported phrase translations, and safe fallbacks.
- `data/demo_places.csv`: expanded from 10 to 31 real destination records, including Kyoto, Araku, Visakhapatnam, Hyderabad, and Munnar attractions.
- `tests/test_workflow.py` and `tests/conftest.py`: added regression tests for today planning, personalization, route details, utilities, and replanning.

## Testing completed

```bash
python -m compileall -q .
pytest -q
python smoke_check.py
```

The final validation passes with **3 tests**, the smoke check, a 31-place catalog check, and a browser-level Streamlit test of the Trip Studio form and generated Kyoto route.

## Honest limitations

The abstract calls the system AI-powered, but this zero-key build uses a deterministic multi-agent workflow rather than a paid LLM. It is intentionally reproducible for a final-year demonstration. Live search and live weather are optional network integrations and can fail safely. Opening hours, entry fees, ratings, and descriptions are only shown when present in the catalog/provider response; no missing value is invented. The current translation module supports common travel phrases and clearly marks unsupported free-form translations. Persistent multi-user accounts, confirmed hotel/transport reservations, and email/WhatsApp delivery require a separate authenticated backend and provider credentials.
