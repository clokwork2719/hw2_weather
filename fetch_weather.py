import os
import requests
import json
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv

# Suppress insecure request warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")

# Approximate coordinates for the regions
REGION_COORDS = {
    "北部地區": [25.0, 121.5],
    "中部地區": [24.0, 121.0],
    "南部地區": [23.0, 120.3],
    "東北部地區": [24.7, 121.7],
    "東部地區": [23.8, 121.4],
    "東南部地區": [22.8, 121.1]
}

def fetch_and_parse_data():
    if not API_KEY:
        st.error("API_KEY not found in .env file.")
        return pd.DataFrame()
        
    url = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001?Authorization={API_KEY}&downloadType=WEB&format=JSON"
    try:
        resp = requests.get(url, verify=False)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

    try:
        locations = data["cwaopendata"]["resources"]["resource"]["data"]["agrWeatherForecasts"]["weatherForecasts"]["location"]
        
        records = []
        for loc in locations:
            loc_name = loc["locationName"]
            if loc_name not in REGION_COORDS:
                continue
                
            weather_elements = loc["weatherElements"]
            max_t_list = weather_elements["MaxT"]["daily"]
            min_t_list = weather_elements["MinT"]["daily"]
            
            for max_t, min_t in zip(max_t_list, min_t_list):
                date = max_t["dataDate"]
                max_temp = float(max_t["temperature"])
                min_temp = float(min_t["temperature"])
                
                records.append({
                    "Region": loc_name,
                    "Date": date,
                    "Max_Temp": max_temp,
                    "Min_Temp": min_temp,
                    "Avg_Temp": (max_temp + min_temp) / 2
                })
        
        df = pd.DataFrame(records)
        df.to_csv("weather_data.csv", index=False)
        return df
    except KeyError as e:
        st.error(f"Error parsing data structure: {e}")
        return pd.DataFrame()

def get_color(avg_temp):
    if avg_temp < 20:
        return "blue"
    elif 20 <= avg_temp < 25:
        return "green"
    elif 25 <= avg_temp < 30:
        return "orange"  # using orange instead of yellow for better visibility on map, though instructed yellow, folium marker handles colors specifically. Wait, folium supports 'yellow' too for some markers, but let's use standard hex or available names.
    else:
        return "red"
        
def get_hex_color(avg_temp):
    if avg_temp < 20:
        return "#3186cc" # blue
    elif 20 <= avg_temp < 25:
        return "#2ca02c" # green
    elif 25 <= avg_temp <= 30:
        return "#ffcc00" # yellow
    else:
        return "#d62728" # red

st.set_page_config(page_title="Taiwan Agriculture Weather Forecast", layout="wide")

st.title("Taiwan 7-Day Agriculture Weather Forecast")

# Add a fetch button to refresh data manually, but load from CSV if it exists
df = pd.DataFrame()
if os.path.exists("weather_data.csv") and os.path.getsize("weather_data.csv") > 10:
    try:
        df = pd.read_csv("weather_data.csv")
    except pd.errors.EmptyDataError:
        pass

if st.button("Fetch / Refresh Data") or df.empty:
    with st.spinner("Fetching data from CWA API..."):
        df = fetch_and_parse_data()
        if not df.empty:
            st.success("Data fetched successfully!")

if not df.empty:
    dates = df["Date"].unique()
    selected_date = st.select_slider("Select Date", options=dates)
    
    filtered_df = df[df["Date"] == selected_date]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Map View - {selected_date}")
        m = folium.Map(location=[23.7, 121.0], zoom_start=7)
        
        for _, row in filtered_df.iterrows():
            region = row["Region"]
            if region in REGION_COORDS:
                avg_temp = row["Avg_Temp"]
                color = get_hex_color(avg_temp)
                
                popup_content = (
                    f"<b>{region}</b><br>"
                    f"Avg Temp: {avg_temp:.1f}°C<br>"
                    f"Max Temp: {row['Max_Temp']}°C<br>"
                    f"Min Temp: {row['Min_Temp']}°C"
                )
                
                folium.CircleMarker(
                    location=REGION_COORDS[region],
                    radius=15,
                    popup=folium.Popup(popup_content, max_width=200),
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    tooltip=region
                ).add_to(m)
                
        st_folium(m, width=800, height=600)
        
    with col2:
        st.subheader("Temperature Data")
        st.dataframe(
            filtered_df[["Region", "Min_Temp", "Max_Temp", "Avg_Temp"]].reset_index(drop=True),
            width='stretch'
        )
