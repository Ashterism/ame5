import streamlit as st
import json
import pandas as pd

st.set_page_config(page_title="My Balkans Trip", page_icon="🧭")

with open("plan.json") as f:
    plan = json.load(f)

st.title(plan["title"])
st.write(plan["summary"])
st.caption(f"Last updated: {plan['last_updated']}")

st.header("Route map")
map_data = pd.DataFrame([
    {"lat": stop["lat"], "lon": stop["lon"]} for stop in plan["stops"]
])


import folium
from streamlit_folium import st_folium

st.header("Route map")
m = folium.Map(location=[44.5, 17.5], zoom_start=6)

coords = [(stop["lat"], stop["lon"]) for stop in plan["stops"]]
for stop, (lat, lon) in zip(plan["stops"], coords):
    folium.Marker([lat, lon], popup=stop["place"]).add_to(m)

folium.PolyLine(coords, color="blue", weight=3, opacity=0.7).add_to(m)

st_folium(m, width=700, height=450)

st.header("Itinerary")
for stop in plan["stops"]:
    with st.expander(f"{stop['place']} — {stop['nights']} nights"):
        st.write(stop["notes"])

if plan.get("open_questions"):
    st.header("Open questions")
    for q in plan["open_questions"]:
        st.write(f"- {q}")

st.header("Leave feedback")
feedback = st.text_area("What do you like, dislike, or want more detail on?")

st.header("Get real recommendations")
st.caption("Uses web search - costs a few cents per request, only when you click this.")
stop_names = [s["place"] for s in plan["stops"]]
selected_stop = st.selectbox("Which stop?", stop_names)
what_to_find = st.text_input("What do you want recommendations for? (e.g. 'budget hotels', 'cafes', 'kayaking tour operators')")

if st.button("Find recommendations"):
    with open(FEEDBACK_FILE) as f:
        existing = json.load(f)
    existing.append({"type": "enrichment_request", "stop": selected_stop, "topic": what_to_find})
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    st.success("Request queued - will search on next update.")

if st.button("Submit feedback"):
    with open("feedback.json") as f:
        existing = json.load(f)
    existing.append(feedback)
    with open("feedback.json", "w") as f:
        json.dump(existing, f, indent=2)
    st.success("Feedback saved. It'll be picked up next update.")