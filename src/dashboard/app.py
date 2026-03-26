import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

try:
    from src.data.data_pipeline import DataPipeline, get_nairobi_zones
    from src.data.weather_api import OpenWeatherMapAPI
    from src.data.cost_calculator import get_default_travel_times, WeatherPredictor
    from src.data.routing_api import OpenRouteServiceAPI
    from src.ml.models import TimeBasedAnalyzer
except ModuleNotFoundError:
    from data_pipeline import DataPipeline, get_nairobi_zones
    from weather_api import OpenWeatherMapAPI
    from cost_calculator import get_default_travel_times, WeatherPredictor
    from routing_api import OpenRouteServiceAPI
    from ml.models import TimeBasedAnalyzer

st.set_page_config(
    page_title="PUMAS - Nairobi Traffic Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

NAIROBI_ZONES = get_nairobi_zones()

st.markdown("""
<style>
    .hero-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: white;
        margin: 0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        letter-spacing: 1px;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        color: rgba(255,255,255,0.95);
        margin: 0.3rem 0 0 0;
        font-weight: 400;
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    
    .weather-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .mode-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: transform 0.2s;
    }
    
    .mode-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.12);
    }
    
    .walking-card { border-left: 5px solid #4CAF50; }
    .matatu-card { border-left: 5px solid #FF9800; }
    .driving-card { border-left: 5px solid #2196F3; }
    .wheelchair-card { border-left: 5px solid #EC4899; }
    
    .suggestion-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    .fastest { background-color: #E3F2FD; border: 1px solid #2196F3; }
    .cheapest { background-color: #E8F5E9; border: 1px solid #4CAF50; }
    .best-value { background-color: #FFF3E0; border: 1px solid #FF9800; }
    .wheelchair { background-color: #FCE4EC; border: 1px solid #EC4899; }
    
    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: #E8F5E9;
        color: #4CAF50;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
    }
    
    .pulse-dot {
        width: 10px;
        height: 10px;
        background: #4CAF50;
        border-radius: 50%;
        animation: pulse-animation 2s infinite;
    }
    
    @keyframes pulse-animation {
        0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(76, 175, 80, 0); }
        100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background: #f5f5f5;
        padding: 0.5rem;
        border-radius: 10px;
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: #1E88E5 !important;
        color: white !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #1565C0 !important;
    }
    
    .heat-legend {
        display: flex;
        justify-content: center;
        gap: 2rem;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
        margin-top: 1rem;
    }
    
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1565C0;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }
    
    .route-line {
        stroke: #1E88E5;
        stroke-width: 3;
        stroke-dasharray: 8,4;
        fill: none;
    }
    
    .zone-marker {
        background: #1E88E5;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_pipeline():
    return DataPipeline()


def display_live_clock():
    now = datetime.now()
    return now


def display_weather_widget(weather_data):
    icons = {'clear': '☀️', 'cloudy': '☁️', 'rain': '🌧️', 'heavy_rain': '⛈️'}
    condition = weather_data.get('weather_condition', 'clear')
    icon = icons.get(condition, '🌤️')
    
    st.markdown(f"""
    <div class="weather-box">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="margin: 0;">{icon} {weather_data.get('weather_description', '').title()}</h2>
                <p style="font-size: 2.5rem; font-weight: 700; margin: 0.5rem 0;">{weather_data.get('temperature_c', 25)}°C</p>
            </div>
            <div style="text-align: right; font-size: 1.1rem;">
                <p style="margin: 0;">💧 Humidity: {weather_data.get('humidity_percent', 50)}%</p>
                <p style="margin: 0;">💨 Wind: {weather_data.get('wind_speed_mps', 0)} m/s</p>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; opacity: 0.9;">Source: {weather_data.get('source', 'OpenWeatherMap')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def create_animated_route_map(origin, dest, show_heatmap=True):
    nairobi_center = [-1.2921, 36.8219]
    m = folium.Map(location=nairobi_center, zoom_start=11, tiles='cartodbpositron')
    
    if show_heatmap:
        heat_data = []
        for zone_name, zone_info in NAIROBI_ZONES.items():
            traffic_factor = 1.5 + np.sin(datetime.now().hour * np.pi / 12)
            if zone_info.get('risk_level') == 'high':
                traffic_factor *= 1.3
            heat_data.append([zone_info['lat'], zone_info['lon'], traffic_factor])
        
        from folium.plugins import HeatMap
        HeatMap(heat_data, radius=35, blur=25, gradient={0.4: '#4CAF50', 0.65: '#FFEB3B', 1: '#F44336'}).add_to(m)
    
    for zone_name, zone_info in NAIROBI_ZONES.items():
        traffic_factor = 1.5 + np.sin(datetime.now().hour * np.pi / 12)
        color = '#4CAF50'
        
        if zone_info.get('risk_level') == 'high':
            color = '#F44336'
            radius = 22
        elif zone_info.get('risk_level') == 'medium':
            color = '#FF9800'
            radius = 16
        else:
            color = '#4CAF50'
            radius = 12
        
        if origin and zone_name == origin:
            color = '#1E88E5'
            radius = 25
        elif dest and zone_name == dest:
            color = '#EC4899'
            radius = 25
        
        folium.CircleMarker(
            location=[zone_info['lat'], zone_info['lon']],
            radius=radius,
            popup=f"<b style='font-size:14px'>{zone_name}</b><br>Risk: {zone_info['risk_level'].title()}",
            tooltip=f"{zone_name}",
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=3
        ).add_to(m)
        
        icon_html = f'''
        <div style="
            background: {color};
            color: white;
            padding: 4px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 700;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            font-family: Arial, sans-serif;
        ">{zone_name[:4]}</div>
        '''
        folium.Marker(
            location=[zone_info['lat'] + 0.018, zone_info['lon']],
            icon=folium.DivIcon(html=icon_html, icon_size=(60, 28), icon_anchor=(30, 14))
        ).add_to(m)
    
    if origin and dest:
        origin_coords = [NAIROBI_ZONES[origin]['lat'], NAIROBI_ZONES[origin]['lon']]
        dest_coords = [NAIROBI_ZONES[dest]['lat'], NAIROBI_ZONES[dest]['lon']]
        
        folium.PolyLine(
            locations=[origin_coords, dest_coords],
            color='#1E88E5',
            weight=4,
            opacity=0.8,
            dash_array='10,5'
        ).add_to(m)
        
        folium.Marker(
            origin_coords,
            popup=f"<b>Start:</b> {origin}",
            icon=folium.Icon(color='green', icon='play', prefix='fa')
        ).add_to(m)
        
        folium.Marker(
            dest_coords,
            popup=f"<b>End:</b> {dest}",
            icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa')
        ).add_to(m)
        
        try:
            from folium.plugins import AntPath
            AntPath(
                locations=[origin_coords, dest_coords],
                color='#1E88E5',
                pulse_color='#EC4899',
                weight=5,
                delay=1500
            ).add_to(m)
        except:
            pass
    
    return m


def display_mode_comparison(comparison, show_wheelchair=True):
    if not comparison:
        st.warning("No data available")
        return
    
    st.markdown("## 🚶 vs 🚌 vs 🚗 Mode Comparison")
    
    modes = comparison.get('modes', {})
    cols = st.columns(4 if show_wheelchair else 3)
    
    with cols[0]:
        walk = modes.get('walking', {})
        st.markdown(f"""
        <div class="mode-card walking-card">
            <h3 style="margin: 0 0 0.5rem 0; color: #4CAF50;">🚶 Walking</h3>
            <p style="font-size: 2rem; font-weight: 700; color: #4CAF50; margin: 0;">{walk.get('time', 'N/A')}</p>
            <p style="font-size: 1.2rem; color: #4CAF50; margin: 0.5rem 0 0 0;">{walk.get('cost', 0)} KES</p>
            <small style="color: #888;">Free & Healthy</small>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        matatu = modes.get('matatu', {})
        st.markdown(f"""
        <div class="mode-card matatu-card">
            <h3 style="margin: 0 0 0.5rem 0; color: #FF9800;">🚌 Matatu</h3>
            <p style="font-size: 2rem; font-weight: 700; color: #FF9800; margin: 0;">{matatu.get('time', 'N/A')}</p>
            <p style="font-size: 1.2rem; color: #FF9800; margin: 0.5rem 0 0 0;">{matatu.get('cost', 0)} KES</p>
            <small style="color: #888;">Most Popular</small>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        drive = modes.get('driving', {})
        st.markdown(f"""
        <div class="mode-card driving-card">
            <h3 style="margin: 0 0 0.5rem 0; color: #2196F3;">🚗 Driving</h3>
            <p style="font-size: 2rem; font-weight: 700; color: #2196F3; margin: 0;">{drive.get('time', 'N/A')}</p>
            <p style="font-size: 1.2rem; color: #2196F3; margin: 0.5rem 0 0 0;">{drive.get('cost', 0)} KES</p>
            <small style="color: #888;">Fastest Option</small>
        </div>
        """, unsafe_allow_html=True)
    
    if show_wheelchair and len(cols) > 3:
        with cols[3]:
            st.markdown(f"""
            <div class="mode-card wheelchair-card">
                <h3 style="margin: 0 0 0.5rem 0; color: #EC4899;">♿ Wheelchair</h3>
                <p style="font-size: 2rem; font-weight: 700; color: #EC4899; margin: 0;">{walk.get('time', 'N/A')}</p>
                <p style="font-size: 1.2rem; color: #EC4899; margin: 0.5rem 0 0 0;">50 KES</p>
                <small style="color: #888;">Accessible Route</small>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("## 💡 Route Suggestions")
    
    suggestions = comparison.get('suggestions', {})
    cols = st.columns(4 if show_wheelchair else 3)
    
    with cols[0]:
        fastest = suggestions.get('fastest', {})
        st.markdown(f"""<div class="suggestion-box fastest"><h4 style="margin: 0;">🏃 Fastest</h4><p style="margin: 0.5rem 0 0 0;">{fastest.get('icon', '➡️')} {fastest.get('mode', '').title()}</p><p style="font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0 0 0;">{fastest.get('time', 'N/A')}</p></div>""", unsafe_allow_html=True)
    
    with cols[1]:
        cheapest = suggestions.get('cheapest', {})
        st.markdown(f"""<div class="suggestion-box cheapest"><h4 style="margin: 0;">💰 Cheapest</h4><p style="margin: 0.5rem 0 0 0;">{cheapest.get('icon', '➡️')} {cheapest.get('mode', '').title()}</p><p style="font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0 0 0;">{cheapest.get('cost', 0)} KES</p></div>""", unsafe_allow_html=True)
    
    with cols[2]:
        best = suggestions.get('best_value', {})
        st.markdown(f"""<div class="suggestion-box best-value"><h4 style="margin: 0;">⭐ Best Value</h4><p style="margin: 0.5rem 0 0 0;">{best.get('icon', '➡️')} {best.get('mode', '').title()}</p><p style="font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0 0 0;">{best.get('time', 'N/A')} | {best.get('cost', 0)} KES</p></div>""", unsafe_allow_html=True)
    
    if show_wheelchair and len(cols) > 3:
        with cols[3]:
            st.markdown(f"""<div class="suggestion-box wheelchair"><h4 style="margin: 0;">♿ Accessible</h4><p style="margin: 0.5rem 0 0 0;">♿ Wheelchair Route</p><p style="font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0 0 0;">{walk.get('time', 'N/A')} | 50 KES</p></div>""", unsafe_allow_html=True)


def display_traffic_predictions(pipeline):
    st.markdown("## 🔮 Traffic Predictions")
    
    current_hour = datetime.now().hour
    hours = [(current_hour + i) % 24 for i in range(1, 7)]
    
    base_traffic = 150
    predictions = []
    for h in hours:
        factor = 1.5 + np.sin((h - 6) * np.pi / 12)
        pred = base_traffic * factor * np.random.uniform(0.95, 1.05)
        predictions.append(int(pred))
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=[f"{h:02d}:00" for h in hours],
            y=predictions,
            mode='lines+markers+text',
            fill='tonexty',
            fillcolor='rgba(30, 136, 229, 0.2)',
            line=dict(color='#1E88E5', width=4),
            marker=dict(size=14, color='#EC4899'),
            text=[f"{p}" for p in predictions],
            textposition='top center',
            textfont=dict(size=12, color='#333')
        ))
        
        fig.update_layout(
            title='6-Hour Traffic Forecast',
            template='plotly_white',
            height=300,
            xaxis=dict(gridcolor='#e0e0e0'),
            yaxis=dict(gridcolor='#e0e0e0'),
            margin=dict(l=20, r=20, t=50, b=30)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        time_analyzer = TimeBasedAnalyzer()
        rush_hour = time_analyzer.get_rush_hour_analysis()
        
        mr = rush_hour['morning_rush']
        er = rush_hour['evening_rush']
        
        fig = go.Figure(data=[
            go.Bar(name='Morning Rush', x=['Morning Rush'], y=[mr['avg_traffic_index']], marker_color='#FF9800', text=[f"{mr['avg_traffic_index']:.2f}"], textposition='outside'),
            go.Bar(name='Evening Rush', x=['Evening Rush'], y=[er['avg_traffic_index']], marker_color='#F44336', text=[f"{er['avg_traffic_index']:.2f}"], textposition='outside')
        ])
        
        fig.update_layout(
            title='Rush Hour Traffic Index',
            template='plotly_white',
            height=300,
            showlegend=True,
            margin=dict(l=20, r=20, t=50, b=30)
        )
        
        st.plotly_chart(fig, use_container_width=True)


def display_weather_predictions(trip_data, weather_data, predictor):
    condition = weather_data.get('weather_condition', 'clear')
    impact = predictor.get_weather_impact(condition)
    
    st.markdown(f"## 🌤️ Weather Impact - {condition.title()}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin: 0 0 1rem 0;">Current Conditions</h4>
            <p>🌡️ Temperature: <strong>{weather_data.get('temperature_c', 25)}°C</strong></p>
            <p>💧 Humidity: <strong>{weather_data.get('humidity_percent', 50)}%</strong></p>
            <p>🌧️ Rain (1hr): <strong>{weather_data.get('rain_mm_last_hour', 0)} mm</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin: 0 0 1rem 0;">Impact Analysis</h4>
            <p>⏱️ Traffic Delay: <strong style="color: #F44336;">+{impact['delay_percent']}%</strong></p>
            <p>💵 Price Increase: <strong style="color: #FF9800;">+{int((impact['price_multiplier'] - 1) * 100)}%</strong></p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        predictions = predictor.predict_all_for_trip(pd.Series(trip_data), condition)
        
        modes = ['walking', 'driving', 'matatu']
        icons = {'walking': '🚶', 'driving': '🚗', 'matatu': '🚌'}
        
        data = []
        for mode in modes:
            time_adjusted = predictions.get(f'{mode}_time_adjusted', 'N/A')
            delay = predictions.get(f'{mode}_time_delay', '0%')
            cost_adjusted = predictions.get(f'{mode}_cost_adjusted', 0)
            data.append({
                'Mode': f"{icons.get(mode, '➡️')} {mode.title()}",
                'Adjusted Time': str(time_adjusted),
                'Delay': delay,
                'Adjusted Cost': f"{cost_adjusted} KES"
            })
        
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


def display_cost_analysis(pipeline):
    st.markdown("## 💵 Cost Analysis")
    
    if pipeline.zone_travel_times is not None:
        df = pipeline.zone_travel_times
        
        col1, col2, col3 = st.columns(3)
        
        avg_matatu = df['matatu_cost'].mean()
        avg_driving = df['driving_cost'].mean()
        monthly_matatu = avg_matatu * 2 * 22
        
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <h3 style="color: #FF9800; margin: 0;">🚌 Matatu</h3>
                <p style="font-size: 2.5rem; font-weight: 700; color: #FF9800; margin: 1rem 0;">{avg_matatu:.0f} KES</p>
                <p style="color: #888; margin: 0;">Average Fare</p>
                <hr style="margin: 1rem 0; border-color: #eee;">
                <p style="font-size: 1.2rem;">Monthly: <strong>{monthly_matatu:.0f} KES</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <h3 style="color: #2196F3; margin: 0;">🚗 Driving</h3>
                <p style="font-size: 2.5rem; font-weight: 700; color: #2196F3; margin: 1rem 0;">{avg_driving:.0f} KES</p>
                <p style="color: #888; margin: 0;">Average Cost</p>
                <hr style="margin: 1rem 0; border-color: #eee;">
                <p style="font-size: 1.2rem;">Monthly: <strong>{avg_driving * 2 * 22:.0f} KES</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <h3 style="color: #4CAF50; margin: 0;">🚶 Walking</h3>
                <p style="font-size: 2.5rem; font-weight: 700; color: #4CAF50; margin: 1rem 0;">0 KES</p>
                <p style="color: #888; margin: 0;">Always Free</p>
                <hr style="margin: 1rem 0; border-color: #eee;">
                <p style="font-size: 1.2rem;">Bonus: <strong>💚 Health</strong></p>
            </div>
            """, unsafe_allow_html=True)


def display_time_analysis():
    st.markdown("## ⏰ Time-Based Analysis")
    
    time_analyzer = TimeBasedAnalyzer()
    best_times = time_analyzer.get_best_time_to_travel()
    day_comparison = time_analyzer.get_day_comparison()
    
    col1, col2 = st.columns(2)
    
    with col1:
        day_names = [d['day'] for d in day_comparison['by_day']]
        traffic_values = [d['traffic_index'] for d in day_comparison['by_day']]
        
        fig = go.Figure()
        
        colors = ['#F44336' if v > 1.4 else '#FF9800' if v > 1.2 else '#4CAF50' for v in traffic_values]
        
        fig.add_trace(go.Bar(
            x=day_names,
            y=traffic_values,
            marker_color=colors,
            text=[f'{v:.2f}' for v in traffic_values],
            textposition='outside'
        ))
        
        fig.update_layout(
            title='Traffic by Day of Week',
            template='plotly_white',
            height=300,
            margin=dict(l=20, r=20, t=50, b=30)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = go.Figure()
        
        best_hours = [f"{t['hour']:02d}:00" for t in best_times['best_times']]
        
        fig.add_trace(go.Bar(
            y=best_hours[::-1],
            x=[1, 1, 1],
            orientation='h',
            marker_color='#4CAF50',
            text=['Best Time to Travel'] * 3,
            textposition='inside',
            hovertemplate='%{y}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Best Times to Travel',
            template='plotly_white',
            height=300,
            showlegend=False,
            xaxis=dict(showticklabels=False, showgrid=False),
            margin=dict(l=80, r=20, t=50, b=30)
        )
        
        st.plotly_chart(fig, use_container_width=True)


def main():
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">PUMAS</h1>
        <p class="hero-subtitle">Predictive Urban Mobility Analytics System - Nairobi</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_time, col_weather = st.columns([1, 3])
    
    with col_time:
        now = datetime.now()
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <p style="color: #888; margin: 0; font-size: 0.9rem;">Current Time</p>
            <p style="font-size: 2.5rem; font-weight: 700; color: #1E88E5; margin: 0.5rem 0;">{now.strftime("%H:%M:%S")}</p>
            <p style="color: #888; margin: 0;">{now.strftime("%A, %d %B %Y")}</p>
            <div class="live-indicator" style="margin-top: 1rem; display: inline-flex;">
                <span class="pulse-dot"></span>
                <span>LIVE</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_weather:
        display_weather_widget(OpenWeatherMapAPI().get_current_weather("Nairobi"))
    
    st.markdown("---")
    
    pipeline = load_pipeline()
    predictor = WeatherPredictor()
    
    tabs = st.tabs(["🗺️ Trip Planner", "📍 Zone Details", "⏰ Time Analysis", "💵 Cost Analysis", "🗺️ All Zones"])
    
    with tabs[0]:
        st.markdown("## Plan Your Trip")
        
        col1, col2 = st.columns(2)
        
        with col1:
            origin = st.selectbox("From Zone", list(NAIROBI_ZONES.keys()), index=0, key="origin")
        
        with col2:
            dest = st.selectbox("To Zone", list(NAIROBI_ZONES.keys()), index=1, key="dest")
        
        col3 = st.columns([1, 1, 2])[0:3]
        show_heatmap = st.checkbox("🗺️ Show Congestion Heatmap", value=True)
        show_wheelchair = st.checkbox("♿ Include Wheelchair Accessible Routes", value=True)
        
        if origin and dest and origin != dest:
            comparison = pipeline.compare_modes(origin, dest)
            
            if comparison:
                st.markdown(f"### 📍 {origin} → {dest}")
                st.markdown(f"**Distance:** {comparison.get('distance_km', 0)} km")
                
                display_mode_comparison(comparison, show_wheelchair)
                
                with st.expander("🔮 View Traffic Predictions"):
                    display_traffic_predictions(pipeline)
                
                with st.expander("🌤️ View Weather Impact"):
                    trip_data = pipeline.get_zone_travel_info(origin, dest)
                    weather_data = OpenWeatherMapAPI().get_current_weather("Nairobi")
                    if trip_data:
                        display_weather_predictions(trip_data, weather_data, predictor)
        
        st.markdown("---")
        st.markdown("### 🗺️ Route Map")
        route_map = create_animated_route_map(origin if 'origin' in dir() else None, 
                                              dest if 'dest' in dir() else None, show_heatmap)
        st_folium(route_map, width=700, height=450)
        
        if show_heatmap:
            st.markdown("""
            <div class="heat-legend">
                <span>🟢 Low Traffic</span>
                <span>🟡 Medium</span>
                <span>🟠 High</span>
                <span>🔴 Very High</span>
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[1]:
        st.markdown("## Zone Details")
        
        selected_zone = st.selectbox("Select Zone", list(NAIROBI_ZONES.keys()))
        
        zone_info = NAIROBI_ZONES.get(selected_zone, {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Latitude", f"{zone_info.get('lat', 0):.4f}°")
        with col2:
            st.metric("Longitude", f"{zone_info.get('lon', 0):.4f}°")
        with col3:
            risk = zone_info.get('risk_level', 'unknown')
            st.metric("Risk Level", risk.upper())
        
        zone_travel = pipeline.get_zone_travel_times(selected_zone)
        
        if zone_travel and zone_travel['outgoing']:
            st.markdown(f"### Travel Times from {selected_zone}")
            
            outgoing_df = pd.DataFrame(zone_travel['outgoing'])
            display_cols = ['dest_zone', 'distance_km', 'walking_time', 'matatu_time', 'driving_time', 'fastest_mode']
            available_cols = [c for c in display_cols if c in outgoing_df.columns]
            st.dataframe(outgoing_df[available_cols], use_container_width=True, hide_index=True)
        
        zone_map = create_animated_route_map(selected_zone, None, False)
        st_folium(zone_map, width=700, height=400)
    
    with tabs[2]:
        display_time_analysis()
    
    with tabs[3]:
        display_cost_analysis(pipeline)
    
    with tabs[4]:
        st.markdown("## All Zones Map")
        
        full_map = create_animated_route_map(None, None, True)
        st_folium(full_map, width=900, height=550)
        
        st.markdown("""
        <div class="heat-legend">
            <span>🟢 Low Traffic</span>
            <span>🟡 Medium</span>
            <span>🟠 High</span>
            <span>🔴 Very High</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Zone Information")
        
        zones_data = []
        for zone_name, zone_info in NAIROBI_ZONES.items():
            zones_data.append({
                'Zone': zone_name,
                'Latitude': f"{zone_info.get('lat', 0):.4f}°",
                'Longitude': f"{zone_info.get('lon', 0):.4f}°",
                'Risk Level': zone_info.get('risk_level', 'unknown').upper(),
                'Wheelchair Access': '♿ Available' if zone_info.get('risk_level') != 'high' else '⚠️ Limited'
            })
        
        st.dataframe(pd.DataFrame(zones_data), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    with st.expander("ℹ️ System Information"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Project:** PUMAS - Predictive Urban Mobility Analytics System")
            st.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        with col2:
            st.write("**Student:** Rita Timinah (SCT-C002-0028/2022)")
            st.write("**Supervisor:** Mr. Samwel Adhola")
            st.write("**Institution:** JKUAT - Data Science and Analytics")


if __name__ == "__main__":
    main()
