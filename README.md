# ParkSmart — Intelligent Parking Search Agent

A Python + Streamlit UI demonstrating parking-space selection and route planning with BFS, DFS, and A*.

## Features
- Interactive parking-lot grid and highlighted recommended route
- BFS, DFS, and A* pathfinding
- Occupancy toggles, blocked cells, and one-way movement rules
- Filters for vehicle type, accessibility, reserved spaces, and maximum fee
- Ranking by balanced preference, distance, fee, or estimated availability
- Candidate-space table, route directions, open/closed search diagnostics
- Responsive web UI

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (normally http://localhost:8501).

## Notes
Parking information is simulated. Connect a database, IoT sensors, or a parking API to use real occupancy data.
