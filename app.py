import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
from streamlit_js_eval import get_geolocation

# Page Configuration
st.set_page_config(page_title="Bucharest Public Toilets Network", layout="wide")

st.title("🗺️ Smart Public Facilities Management System - Bucharest")
st.write("An advanced GIS platform to visualize all urban facilities and compute the optimal path based on real-time location.")

# Function to read the dataset safely
@st.cache_data
def process_data():
    try:
        df = pd.read_csv("Data.csv", encoding="utf-8", sep=None, engine='python')
    except:
        df = pd.read_csv("Data.csv", encoding="latin1", sep=None, engine='python')
    
    # تنظيف أسماء الأعمدة من أي مسافات زائدة مخفية في الإكسل
    df.columns = df.columns.str.strip()
    
    st.sidebar.write("📋 Detected columns in your file:", list(df.columns))
    
    # البحث التلقائي عن أعمدة الإحداثيات
    lat_col = [col for col in df.columns if 'Latitude' in col or 'lat' in col.lower()][0]
    lon_col = [col for col in df.columns if 'Longitude' in col or 'lon' in col.lower()][0]
    
    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
    df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
    
    # إعادة تسمية أعمدة الإحداثيات داخلياً لتسهيل الحسابات
    df = df.rename(columns={lat_col: 'Latitude Nordică', lon_col: 'Longitude Estică'})
    
    return df.dropna(subset=['Latitude Nordică', 'Longitude Estică']).copy()

# Load Database
df_clean = process_data()

# --- 1. Big Action Button for the Professor ---
st.subheader("🚀 Smart Routing Assistant")
find_closest = st.button("🔍 FIND THE NEAREST TOILET TO MY LIVE POSITION", type="primary", use_container_width=True)

# --- 2. GPS Location Detection ---
user_geo = get_geolocation()
my_coords = None

if user_geo and 'coords' in user_geo:
    my_lat = user_geo['coords']['latitude']
    my_lon = user_geo['coords']['longitude']
    my_coords = (my_lat, my_lon)
    st.sidebar.success(f"🎯 Live GPS Active: ({my_lat:.4f}, {my_lon:.4f})")
else:
    st.sidebar.warning("⚠️ GPS Loading / Permission required to unlock the Nearest Routing feature.")

# --- 3. Building the Map ---
m = folium.Map(location=[44.4355, 26.1025], zoom_start=13)  # Centered on Bucharest Center

# Add User Marker if GPS is active
if my_coords:
    folium.Marker(my_coords, popup="Your Location", icon=folium.Icon(color='blue', icon='user')).add_to(m)

# Logic when the Professor clicks the BIG BUTTON
if find_closest:
    if my_coords is None:
        st.error("❌ Cannot calculate route: Please enable your device location permission first.")
    else:
        closest_distance = float('inf')
        nearest_row = None

        for index, row in df_clean.iterrows():
            dist = geodesic(my_coords, (row['Latitude Nordică'], row['Longitude Estică'])).meters
            if dist < closest_distance:
                closest_distance = dist
                nearest_row = row

        if nearest_row is not None:
            nearest_coords = (nearest_row['Latitude Nordică'], nearest_row['Longitude Estică'])
            
            # جلب الاسم بأمان حتى لو اختلف الحرف كابيتال أو سمول
            title_val = nearest_row.get('titlu', nearest_row.get('title', 'Public Toilet'))
            type_val = nearest_row.get('tip', nearest_row.get('type', 'N/A'))
            taxa_val = nearest_row.get('taxa', 'N/A')
            
            # Highlight Results in UI
            st.markdown(f"### 🎯 Optimal Facility Found!")
            col1, col2, col3 = st.columns(3)
            col1.metric("Facility Name", str(title_val))
            col2.metric("Precise Distance", f"{closest_distance:.0f} meters")
            col3.metric("Type / Cost", f"{type_val} ({taxa_val})")
            
            # Draw Route on Map
            folium.PolyLine(
                locations=[my_coords, nearest_coords], 
                color='blue', weight=5, opacity=0.85,
                tooltip="Shortest Spatial Connection"
            ).add_to(m)
            
            m.location = my_coords
            m.zoom_start = 14

# Plot ALL Toilets from the Database safely
for index, row in df_clean.iterrows():
    # جلب القيم بأمان شديد (إذا لم يجد العمود المكتوب بالضبط، يضع علامة '-')
    t_titlu = row.get('titlu', row.get('title', 'Toilet'))
    t_program = row.get('program', '-')
    t_taxa = row.get('taxa', '-')
    t_access = row.get('Accesibil pentru persoane cu dizabilități', row.get('accessibility', '-'))
    t_clean = row.get('Curățenie', row.get('cleanliness', '-'))
    t_tip = row.get('tip', row.get('type', '-'))
    
    popup_text = f"""
    <div style='font-family: Arial, sans-serif; width: 240px;'>
        <h4 style='margin:0 0 5px 0; color:#d9534f;'>📍 {t_titlu}</h4>
        <p style='margin:3px 0;'><b>⏰ Program:</b> {t_program}</p>
        <p style='margin:3px 0;'><b>💰 Taxă:</b> {t_taxa}</p>
        <p style='margin:3px 0;'><b>♿ Accesibilitate:</b> {t_access}</p>
        <p style='margin:3px 0;'><b>✨ Curățenie:</b> {t_clean}</p>
        <p style='margin:3px 0;'><b>🏷️ Tip:</b> {t_tip}</p>
    </div>
    """
    
    folium.Marker(
        location=[row['Latitude Nordică'], row['Longitude Estică']],
        popup=folium.Popup(popup_text, max_width=260),
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)

# Render Map
st.subheader("🗺️ Interactive Infrastructure Map")
folium_static(m)
