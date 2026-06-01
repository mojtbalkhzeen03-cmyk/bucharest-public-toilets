import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import time
# Import the GPS tracking tool
from streamlit_js_eval import get_geolocation

# Page Configuration
st.set_page_config(page_title="Bucharest Public Toilets", layout="wide")

st.title("🗺️ Public Toilets System - Bucharest")
st.write("Urban Economics Exercise: Automatically locating the nearest public Toilet based on your real-time location and drawing a direct path connection.")

# Initialize the geocoding engine
geolocator = Nominatim(user_agent="uauim_urban_app")

# Function to read the data and convert addresses to GPS coordinates
@st.cache_data
def process_data():
    # Using cp1252 to handle Romanian characters safely from Excel without errors
    df = pd.read_csv("Data.csv", encoding="latin1")
    lats, lons = [], []
    
    st.write("🔄 Reading facility addresses and converting to geographic coordinates...")
    for index, row in df.iterrows():
        full_address = f"{row['address']}, {row['city']}, Romania"
        try:
            location = geolocator.geocode(full_address)
            if location:
                lats.append(location.latitude)
                lons.append(location.longitude)
            else:
                lats.append(None)
                lons.append(None)
        except:
            lats.append(None)
            lons.append(None)
        time.sleep(1) # 1-second delay to keep the server connection stable
        
    df['lat'] = lats
    df['lon'] = lons
    return df.dropna(subset=['lat', 'lon']).copy()

# Run the data processor
df_clean = process_data()
st.success("✅ Facility map dataset prepared successfully!")

st.subheader("📍 Real-time GPS Location Detection")

# Get user's real-time GPS coordinates from the browser
with st.spinner("Connecting to satellite to pinpoint your live location..."):
    user_geo = get_geolocation()

# Verify that the browser successfully retrieved the location and permission was granted
if user_geo and 'coords' in user_geo:
    my_lat = user_geo['coords']['latitude']
    my_lon = user_geo['coords']['longitude']
    my_coords = (my_lat, my_lon)
    
    st.success(f"🎯 Live location detected! Coordinates: ({my_lat:.4f}, {my_lon:.4f})")
    
    # Calculate the geodesic distance between the user and all facilities in the CSV file
    df_clean['distance'] = df_clean.apply(lambda x: geodesic(my_coords, (x['lat'], x['lon'])).meters, axis=1)
    
    # Select the closest toilet (minimum distance)
    nearest = df_clean.sort_values(by='distance').iloc[0]
    nearest_coords = (nearest['lat'], nearest['lon'])
    
    # Display results to the user / professor
    st.info(f"🏃 The nearest toilet is located at: **{nearest['address']}** ({nearest['name']})")
    st.metric(label="📏 Precise Distance to the toilet", value=f"{nearest['distance']:.0f} meters")
    
    # Draw the interactive live map
    m = folium.Map(location=my_coords, zoom_start=15)
    
    # 1. Blue marker for the user's current live location
    folium.Marker(my_coords, popup="Your Current Location", icon=folium.Icon(color='blue', icon='user')).add_to(m)
    
    # 2. Red marker for the nearest toilet from the doctor's dataset
    folium.Marker(nearest_coords, popup=nearest['name'], icon=folium.Icon(color='red', icon='info-sign')).add_to(m)
    
    # 3. Draw the line connecting your location to the nearest toilet point
    folium.PolyLine(
        locations=[my_coords, nearest_coords], 
        color='blue', 
        weight=4, 
        opacity=0.7,
        tooltip="Shortest Spatial Connection Line"
    ).add_to(m)
    
    folium_static(m)
else:
    st.warning("⚠️ Action Required: Please allow / enable 'Location Permission' in your browser so the system can track your position automatically.")
