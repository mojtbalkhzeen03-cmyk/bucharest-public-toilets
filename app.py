import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
from streamlit_js_eval import get_geolocation

# 1. إعدادات الصفحة العامة للموقع
st.set_page_config(page_title="Bucharest Public Toilets Network", layout="wide")

st.title("🗺️ Smart Public Facilities Management System - Bucharest")
st.write("An advanced GIS platform to visualize all urban facilities and compute the optimal path based on real-time location.")

# 2. دالة قراءة وتنظيف البيانات المحدثة للإحداثيات العشرية
@st.cache_data
def process_data():
    try:
        df = pd.read_csv("Data.csv", encoding="utf-8", sep=None, engine='python')
    except:
        df = pd.read_csv("Data.csv", encoding="latin1", sep=None, engine='python')
    
    # تنظيف أسماء الأعمدة من أي مسافات مخفية قد يضعها الإكسل
    df.columns = df.columns.str.strip()
    
    # إظهار الأعمدة المكتشفة في القائمة الجانبية كدليل للمهندس للتأكد منها
    st.sidebar.write("📋 Detected columns in your file:", list(df.columns))
    
    # البحث التلقائي الصارم عن أعمدتك (Latitude Nordica و Longitude Estica) بدون الحركات الحرفية
    lat_col = [col for col in df.columns if 'nordica' in col.lower() or 'lat' in col.lower()][0]
    lon_col = [col for col in df.columns if 'estica' in col.lower() or 'lon' in col.lower()][0]
    
    # التأكد من استبدال الفواصل بناط عشرية إن وجدت بالخطأ لمنع المشاكل
    df[lat_col] = df[lat_col].astype(str).str.replace(',', '.').str.strip()
    df[lon_col] = df[lon_col].astype(str).str.replace(',', '.').str.strip()
    
    # تحويل الإحداثيات الجاهزة إلى أرقام عشرية صافية تفهمها الحسابات الجغرافية
    df['Latitude_Internal'] = pd.to_numeric(df[lat_col], errors='coerce')
    df['Longitude_Internal'] = pd.to_numeric(df[lon_col], errors='coerce')
    
    # حذف أي سطر فارغ لا يحتوي على إحداثيات صحيحة لضمان سلامة الخريطة
    final_df = df.dropna(subset=['Latitude_Internal', 'Longitude_Internal']).copy()
    st.sidebar.success(f"📊 Successfully loaded {len(final_df)} toilets from your file!")
    
    return final_df

# تشغيل دالة جلب قاعدة البيانات
df_clean = process_data()

# --- 3. الزر الكبير المخصص للأستاذ للبحث عن الأقرب بعرض الشاشة ---
st.subheader("🚀 Smart Routing Assistant")
find_closest = st.button("🔍 FIND THE NEAREST TOILET TO MY LIVE POSITION", type="primary", use_container_width=True)

# --- 4. التقاط موقع المستخدم الفعلي عبر الـ GPS ---
user_geo = get_geolocation()
my_coords = None

if user_geo and 'coords' in user_geo:
    my_lat = user_geo['coords']['latitude']
    my_lon = user_geo['coords']['longitude']
    my_coords = (my_lat, my_lon)
    st.sidebar.success(f"🎯 Live GPS Active: ({my_lat:.4f}, {my_lon:.4f})")
else:
    st.sidebar.warning("⚠️ GPS Loading / Permission required to unlock the Nearest Routing feature.")

# --- 5. بناء الخريطة التفاعلية وتوسيطها تلقائياً على بوخارست ---
m = folium.Map(location=[44.4355, 26.1025], zoom_start=13)

# إضافة ماركر أزرق لموقع المستخدم الحقيقي إذا كان الـ GPS يعمل ومسموح به
if my_coords:
    folium.Marker(my_coords, popup="Your Location", icon=folium.Icon(color='blue', icon='user')).add_to(m)

# العمليات الحسابية عند ضغط الدكتور على الزر الكبير في الأعلى
if find_closest:
    if my_coords is None:
        st.error("❌ Cannot calculate route: Please enable your device location permission first.")
    else:
        if df_clean.empty:
            st.error("❌ Database is empty. No valid decimal coordinates found to compute routing.")
        else:
            closest_distance = float('inf')
            nearest_row = None

            for index, row in df_clean.iterrows():
                dist = geodesic(my_coords, (row['Latitude_Internal'], row['Longitude_Internal'])).meters
                if dist < closest_distance:
                    closest_distance = dist
                    nearest_row = row

            if nearest_row is not None:
                nearest_coords = (nearest_row['Latitude_Internal'], nearest_row['Longitude_Internal'])
                
                # جلب أسماء المخرجات بأمان وعرضها للجنة والأستاذ
                title_val = nearest_row.get('titlu', nearest_row.get('title', 'Public Toilet'))
                type_val = nearest_row.get('tip', nearest_row.get('type', 'N/A'))
                taxa_val = nearest_row.get('taxa', 'N/A')
                
                st.markdown(f"### 🎯 Optimal Facility Found!")
                col1, col2, col3 = st.columns(3)
                col1.metric("Facility Name", str(title_val))
                col2.metric("Precise Distance", f"{closest_distance:.0f} meters")
                col3.metric("Type / Cost", f"{type_val} ({taxa_val})")
                
                # رسم الخط الأزرق المباشر الواصل بين موقعك والمرحاض الأقرب جغرافياً
                folium.PolyLine(
                    locations=[my_coords, nearest_coords], 
                    color='blue', weight=5, opacity=0.85,
                    tooltip="Shortest Spatial Connection"
                ).add_to(m)
                
                m.location = my_coords
                m.zoom_start = 14

# --- 6. إسقاط كافة دبابيس المراحيض من ملفك المحدث على الخريطة ---
for index, row in df_clean.iterrows():
    t_titlu = row.get('titlu', row.get('title', 'Toilet'))
    t_program = row.get('program', '-')
    t_taxa = row.get('taxa', '-')
    t_access = row.get('Accesibil pentru persoane cu dizabilități', row.get('accessibility', '-'))
    t_clean = row.get('Curățenie', row.get('cleanliness', '-'))
    t_tip = row.get('tip', row.get('type', '-'))
    
    # تنسيق نافذة الـ Popup بجميع التفاصيل التفصيلية التي قمت بإضافتها
    popup_text = f"""
    <div style='font-family: Arial, sans-serif; width: 240px;'>
        <h4 style='margin:0 0 5px 0; color:#d9534f;'>📍 {t_titlu}</h4>
        <p style='margin:3px 0;'><b>⏰ Program:</b> {t_program}</p>
        <p style='margin:3px 0;'><b>💰 Taxă:</b> {t_taxa}</p>
        <p style='margin:3px 0;'><b>♿ Accesibilitate (A11Y):</b> {t_access}</p>
        <p style='margin:3px 0;'><b>✨ Curățenie:</b> {t_clean}</p>
        <p style='margin:3px 0;'><b>🏷️ Tip:</b> {t_tip}</p>
    </div>
    """
    
    folium.Marker(
        location=[row['Latitude_Internal'], row['Longitude_Internal']],
        popup=folium.Popup(popup_text, max_width=260),
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)

# عرض الخريطة الحية النهائية على المتصفح
st.subheader("🗺️ Interactive Infrastructure Map")
folium_static(m)
