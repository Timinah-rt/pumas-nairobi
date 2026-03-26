import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

NAIROBI_CENTER = (-1.2921, 36.8219)
ZONES = {
    'CBD': (-1.2860, 36.8178),
    'Westlands': (-1.2644, 36.8032),
    'Kilimani': (-1.2956, 36.6890),
    'Kasarani': (-1.2172, 36.8980),
    'Karen': (-1.3186, 36.6780),
    'Embakasi': (-1.3274, 36.9273),
    'Ruiru': (-1.1467, 36.9581),
    'Machakos': (-1.5177, 37.2634),
    'Nairobi West': (-1.3087, 36.8370),
    'Parklands': (-1.2711, 36.8402),
}

def generate_gps_data(n_trips=1000, date_range=30):
    np.random.seed(42)
    data = []
    
    start_date = datetime.now() - timedelta(days=date_range)
    
    for i in range(n_trips):
        zone_names = list(ZONES.keys())
        origin = np.random.choice(zone_names)
        destination = np.random.choice([z for z in zone_names if z != origin])
        
        origin_coords = ZONES[origin]
        dest_coords = ZONES[destination]
        
        timestamp = start_date + timedelta(
            days=np.random.randint(0, date_range),
            hours=np.random.randint(5, 22),
            minutes=np.random.randint(0, 59)
        )
        
        distance = np.sqrt((dest_coords[0] - origin_coords[0])**2 + 
                          (dest_coords[1] - origin_coords[1])**2) * 111
        
        base_duration = distance / 30 * 60
        traffic_factor = 1.5 + np.sin(timestamp.hour * np.pi / 12) * 0.5
        weather_delay = np.random.choice([0, 0.2, 0.5], p=[0.7, 0.2, 0.1])
        
        duration = base_duration * traffic_factor * (1 + weather_delay)
        speed = distance / (duration / 60) if duration > 0 else 30
        
        data.append({
            'trip_id': f'TRIP_{i+1:06d}',
            'timestamp': timestamp.isoformat(),
            'origin_zone': origin,
            'destination_zone': destination,
            'origin_lat': origin_coords[0] + np.random.uniform(-0.01, 0.01),
            'origin_lon': origin_coords[1] + np.random.uniform(-0.01, 0.01),
            'dest_lat': dest_coords[0] + np.random.uniform(-0.01, 0.01),
            'dest_lon': dest_coords[1] + np.random.uniform(-0.01, 0.01),
            'distance_km': distance * (1 + np.random.uniform(-0.1, 0.1)),
            'duration_min': duration,
            'speed_kmh': speed,
            'vehicle_type': np.random.choice(['matatu', 'taxi', 'boda_boda', 'bus']),
            'weather_condition': np.random.choice(['clear', 'cloudy', 'rain', 'heavy_rain'], 
                                                   p=[0.6, 0.2, 0.15, 0.05]),
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),
            'is_weekend': timestamp.weekday() >= 5
        })
    
    return pd.DataFrame(data)

def generate_traffic_flow_data(hours=24, zones=list(ZONES.keys())):
    np.random.seed(42)
    data = []
    
    for hour in range(hours):
        traffic_multiplier = 1.5 + np.sin((hour - 6) * np.pi / 12)
        traffic_multiplier = max(0.5, min(2.5, traffic_multiplier))
        
        for zone in zones:
            base_count = np.random.randint(50, 200)
            vehicle_count = int(base_count * traffic_multiplier * np.random.uniform(0.8, 1.2))
            
            congestion_level = 'low' if traffic_multiplier < 1.2 else 'medium' if traffic_multiplier < 1.8 else 'high'
            
            data.append({
                'timestamp': datetime.now().replace(hour=hour, minute=0, second=0).isoformat(),
                'hour': hour,
                'zone': zone,
                'zone_lat': ZONES[zone][0],
                'zone_lon': ZONES[zone][1],
                'vehicle_count': vehicle_count,
                'avg_speed_kmh': 60 / traffic_multiplier,
                'congestion_level': congestion_level,
                'traffic_index': traffic_multiplier
            })
    
    return pd.DataFrame(data)

def generate_weather_data(days=30):
    np.random.seed(42)
    data = []
    
    conditions = {
        'clear': {'temp_range': (20, 28), 'humidity_range': (40, 60)},
        'cloudy': {'temp_range': (18, 25), 'humidity_range': (50, 70)},
        'rain': {'temp_range': (15, 22), 'humidity_range': (70, 90)},
        'heavy_rain': {'temp_range': (13, 20), 'humidity_range': (85, 100)}
    }
    
    for day in range(days):
        weather = np.random.choice(list(conditions.keys()), 
                                   p=[0.5, 0.25, 0.2, 0.05])
        temp_range = conditions[weather]['temp_range']
        humidity_range = conditions[weather]['humidity_range']
        
        for hour in range(24):
            data.append({
                'timestamp': (datetime.now() - timedelta(days=days-day-1)).replace(
                    hour=hour, minute=0, second=0).isoformat(),
                'temperature_c': np.random.uniform(temp_range[0], temp_range[1]),
                'humidity_percent': np.random.uniform(humidity_range[0], humidity_range[1]),
                'weather_condition': weather,
                'wind_speed_kmh': np.random.uniform(5, 25) if weather != 'heavy_rain' else np.random.uniform(15, 40),
                'visibility_km': 10 if weather == 'clear' else 5 if weather == 'cloudy' else 2 if weather == 'rain' else 0.5,
                'rain_mm': 0 if weather in ['clear', 'cloudy'] else np.random.uniform(1, 5) if weather == 'rain' else np.random.uniform(5, 15)
            })
    
    return pd.DataFrame(data)

if __name__ == '__main__':
    os.makedirs('data/processed', exist_ok=True)
    
    print('Generating GPS trip data...')
    gps_df = generate_gps_data(n_trips=5000)
    gps_df.to_csv('data/processed/gps_trips.csv', index=False)
    print(f'Generated {len(gps_df)} GPS trips')
    
    print('Generating traffic flow data...')
    traffic_df = generate_traffic_flow_data()
    traffic_df.to_csv('data/processed/traffic_flow.csv', index=False)
    print(f'Generated {len(traffic_df)} traffic flow records')
    
    print('Generating weather data...')
    weather_df = generate_weather_data()
    weather_df.to_csv('data/processed/weather_data.csv', index=False)
    print(f'Generated {len(weather_df)} weather records')
    
    print('Data generation complete!')
