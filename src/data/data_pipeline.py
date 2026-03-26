import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
from pathlib import Path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.cost_calculator import CostCalculator, WeatherPredictor, get_default_travel_times
from src.data.weather_api import OpenWeatherMapAPI, get_weather_data

NAIROBI_ZONES = {
    'CBD': {'lat': -1.2860, 'lon': 36.8178, 'risk_level': 'high'},
    'Westlands': {'lat': -1.2644, 'lon': 36.8032, 'risk_level': 'medium'},
    'Kilimani': {'lat': -1.2956, 'lon': 36.8190, 'risk_level': 'medium'},
    'Kasarani': {'lat': -1.2172, 'lon': 36.8980, 'risk_level': 'medium'},
    'Karen': {'lat': -1.3186, 'lon': 36.6780, 'risk_level': 'low'},
    'Embakasi': {'lat': -1.3274, 'lon': 36.9273, 'risk_level': 'high'},
    'Ruiru': {'lat': -1.1467, 'lon': 36.9581, 'risk_level': 'low'},
    'Machakos': {'lat': -1.5177, 'lon': 37.2634, 'risk_level': 'medium'},
    'Nairobi West': {'lat': -1.3087, 'lon': 36.8370, 'risk_level': 'high'},
    'Parklands': {'lat': -1.2711, 'lon': 36.8402, 'risk_level': 'medium'},
}

class DataPipeline:
    def __init__(self, data_dir='data/processed'):
        self.data_dir = Path(data_dir)
        self.gps_df = None
        self.traffic_df = None
        self.weather_df = None
        self.zone_travel_times = None
        self.weather_api = OpenWeatherMapAPI()
        self.cost_calculator = None
        self.weather_predictor = WeatherPredictor()
        self._load_data()
    
    def _load_data(self):
        if (self.data_dir / 'gps_trips.csv').exists():
            self.gps_df = pd.read_csv(self.data_dir / 'gps_trips.csv')
            self.gps_df['timestamp'] = pd.to_datetime(self.gps_df['timestamp'])
        
        if (self.data_dir / 'traffic_flow.csv').exists():
            self.traffic_df = pd.read_csv(self.data_dir / 'traffic_flow.csv')
            self.traffic_df['timestamp'] = pd.to_datetime(self.traffic_df['timestamp'])
        
        if (self.data_dir / 'weather_data.csv').exists():
            self.weather_df = pd.read_csv(self.data_dir / 'weather_data.csv')
            self.weather_df['timestamp'] = pd.to_datetime(self.weather_df['timestamp'])
        
        zone_travel_path = self.data_dir / 'zone_travel_times.csv'
        if zone_travel_path.exists():
            self.zone_travel_times = pd.read_csv(zone_travel_path)
            self.cost_calculator = CostCalculator(self.zone_travel_times)
        else:
            self.zone_travel_times = get_default_travel_times()
            self.cost_calculator = CostCalculator(self.zone_travel_times)
            os.makedirs(self.data_dir, exist_ok=True)
            self.zone_travel_times.to_csv(zone_travel_path, index=False)
    
    def get_zone_traffic(self, zone, hours=24):
        if self.traffic_df is None:
            return None
        
        recent = self.traffic_df[self.traffic_df['zone'] == zone]
        recent = recent.sort_values('timestamp', ascending=False)
        return recent.head(hours)
    
    def get_traffic_patterns(self):
        if self.traffic_df is None:
            return None
        
        patterns = self.traffic_df.groupby(['zone', 'hour']).agg({
            'vehicle_count': 'mean',
            'avg_speed_kmh': 'mean',
            'traffic_index': 'mean'
        }).reset_index()
        
        return patterns
    
    def get_congestion_hotspots(self, top_n=5):
        if self.traffic_df is None:
            return None
        
        hotspots = self.traffic_df.groupby('zone').agg({
            'traffic_index': 'mean',
            'vehicle_count': 'mean'
        }).sort_values('traffic_index', ascending=False).head(top_n)
        
        return hotspots
    
    def simulate_realtime_data(self):
        if self.traffic_df is None:
            return None
        
        last_row = self.traffic_df.iloc[-1].copy()
        current_hour = datetime.now().hour
        
        traffic_factor = 1.5 + np.sin((current_hour - 6) * np.pi / 12)
        traffic_factor = max(0.5, min(2.5, traffic_factor))
        
        new_data = []
        for zone in self.traffic_df['zone'].unique():
            zone_info = NAIROBI_ZONES.get(zone, {})
            new_data.append({
                'timestamp': datetime.now(),
                'hour': current_hour,
                'zone': zone,
                'zone_lat': zone_info.get('lat', -1.2921),
                'zone_lon': zone_info.get('lon', 36.8219),
                'vehicle_count': int(last_row['vehicle_count'] * traffic_factor * np.random.uniform(0.9, 1.1)),
                'avg_speed_kmh': last_row['avg_speed_kmh'] / traffic_factor,
                'congestion_level': 'high' if traffic_factor > 1.8 else 'medium' if traffic_factor > 1.2 else 'low',
                'traffic_index': traffic_factor
            })
        
        return pd.DataFrame(new_data)
    
    def get_hourly_summary(self):
        if self.traffic_df is None:
            return None
        
        summary = self.traffic_df.groupby('hour').agg({
            'vehicle_count': ['mean', 'sum'],
            'avg_speed_kmh': 'mean',
            'traffic_index': 'mean'
        }).reset_index()
        
        summary.columns = ['hour', 'avg_vehicle_count', 'total_vehicles', 'avg_speed', 'traffic_index']
        return summary
    
    def get_zone_statistics(self):
        if self.gps_df is None:
            return None
        
        stats = self.gps_df.groupby('origin_zone').agg({
            'trip_id': 'count',
            'distance_km': 'mean',
            'duration_min': 'mean',
            'speed_kmh': 'mean'
        }).reset_index()
        
        stats.columns = ['zone', 'trip_count', 'avg_distance_km', 'avg_duration_min', 'avg_speed_kmh']
        return stats
    
    def get_current_weather(self):
        return get_weather_data("Nairobi")
    
    def get_zone_travel_info(self, origin_zone: str, dest_zone: str):
        if self.zone_travel_times is None:
            return None
        
        trip = self.zone_travel_times[
            (self.zone_travel_times['origin_zone'] == origin_zone) &
            (self.zone_travel_times['dest_zone'] == dest_zone)
        ]
        
        if len(trip) == 0:
            return None
        
        trip = trip.iloc[0]
        result = trip.to_dict()
        
        if self.cost_calculator:
            times = self.cost_calculator.calculate_all_times(trip)
            costs = self.cost_calculator.calculate_all_costs(trip)
            suggestions = self.cost_calculator.get_route_suggestions(trip)
            result.update(times)
            result.update(costs)
            result.update(suggestions)
        
        return result
    
    def predict_trip_with_weather(self, origin_zone: str, dest_zone: str, weather_condition: str = None):
        trip = self.get_zone_travel_info(origin_zone, dest_zone)
        
        if trip is None:
            return None
        
        if weather_condition is None:
            weather_data = self.get_current_weather()
            weather_condition = weather_data.get('weather_condition', 'clear')
        
        predictions = self.weather_predictor.predict_all_for_trip(pd.Series(trip), weather_condition)
        trip.update(predictions)
        
        return trip
    
    def get_all_zones(self):
        return list(NAIROBI_ZONES.keys())
    
    def get_zone_coordinates(self, zone: str):
        return NAIROBI_ZONES.get(zone, {})
    
    def get_zone_travel_times(self, zone: str):
        if self.zone_travel_times is None:
            return None
        
        outgoing = self.zone_travel_times[self.zone_travel_times['origin_zone'] == zone]
        incoming = self.zone_travel_times[self.zone_travel_times['dest_zone'] == zone]
        
        return {
            'outgoing': outgoing.to_dict('records') if len(outgoing) > 0 else [],
            'incoming': incoming.to_dict('records') if len(incoming) > 0 else []
        }
    
    def compare_modes(self, origin_zone: str, dest_zone: str):
        trip = self.get_zone_travel_info(origin_zone, dest_zone)
        
        if trip is None:
            return None
        
        comparison = {
            'origin_zone': origin_zone,
            'dest_zone': dest_zone,
            'distance_km': trip.get('distance_km', 0),
            'modes': {
                'walking': {
                    'time': trip.get('walking_time', 'N/A'),
                    'time_sec': trip.get('walking_sec', 0),
                    'cost': trip.get('walking_cost', 0),
                    'icon': '🚶'
                },
                'matatu': {
                    'time': trip.get('matatu_time', 'N/A'),
                    'time_sec': trip.get('matatu_sec', 0),
                    'cost': trip.get('matatu_cost', 0),
                    'icon': '🚌'
                },
                'driving': {
                    'time': trip.get('driving_time', 'N/A'),
                    'time_sec': trip.get('driving_sec', 0),
                    'cost': trip.get('driving_cost', 0),
                    'icon': '🚗'
                }
            },
            'suggestions': {
                'fastest': {
                    'mode': trip.get('fastest_mode', ''),
                    'time': trip.get('fastest_time', ''),
                    'icon': self._get_mode_icon(trip.get('fastest_mode', ''))
                },
                'cheapest': {
                    'mode': trip.get('cheapest_mode', ''),
                    'cost': trip.get('cheapest_cost', 0),
                    'icon': self._get_mode_icon(trip.get('cheapest_mode', ''))
                },
                'best_value': {
                    'mode': trip.get('best_value_mode', ''),
                    'time': trip.get('best_value_time', ''),
                    'cost': trip.get('best_value_cost', 0),
                    'icon': self._get_mode_icon(trip.get('best_value_mode', ''))
                }
            }
        }
        
        return comparison
    
    def _get_mode_icon(self, mode: str) -> str:
        icons = {
            'walking': '🚶',
            'matatu': '🚌',
            'driving': '🚗'
        }
        return icons.get(mode.lower(), '➡️')


def get_nairobi_zones():
    return NAIROBI_ZONES
