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
    
    # ============================================
    # DESCRIPTIVE ANALYTICS
    # ============================================
    
    def get_7day_trends(self):
        if self.traffic_df is None:
            return self._get_default_trends()
        
        last_7_days = datetime.now() - timedelta(days=7)
        df = self.traffic_df[self.traffic_df['timestamp'] >= last_7_days].copy()
        
        if len(df) == 0:
            return self._get_default_trends()
        
        df['date'] = df['timestamp'].dt.date
        daily = df.groupby('date').agg({
            'vehicle_count': 'mean',
            'traffic_index': 'mean',
            'avg_speed_kmh': 'mean'
        }).reset_index()
        
        return {
            'dates': daily['date'].dt.strftime('%Y-%m-%d').tolist(),
            'vehicle_count': daily['vehicle_count'].tolist(),
            'traffic_index': daily['traffic_index'].tolist(),
            'avg_speed': daily['avg_speed_kmh'].tolist()
        }
    
    def get_statistics_summary(self):
        stats = {}
        
        if self.traffic_df is not None:
            traffic_stats = self.traffic_df.agg({
                'vehicle_count': ['mean', 'min', 'max', 'std'],
                'avg_speed_kmh': ['mean', 'min', 'max', 'std'],
                'traffic_index': ['mean', 'min', 'max', 'std']
            })
            stats['traffic'] = {
                'vehicle_count': {
                    'avg': float(traffic_stats.loc['mean', 'vehicle_count']),
                    'min': float(traffic_stats.loc['min', 'vehicle_count']),
                    'max': float(traffic_stats.loc['max', 'vehicle_count']),
                    'std': float(traffic_stats.loc['std', 'vehicle_count'])
                },
                'speed': {
                    'avg': float(traffic_stats.loc['mean', 'avg_speed_kmh']),
                    'min': float(traffic_stats.loc['min', 'avg_speed_kmh']),
                    'max': float(traffic_stats.loc['max', 'avg_speed_kmh']),
                    'std': float(traffic_stats.loc['std', 'avg_speed_kmh'])
                },
                'traffic_index': {
                    'avg': float(traffic_stats.loc['mean', 'traffic_index']),
                    'min': float(traffic_stats.loc['min', 'traffic_index']),
                    'max': float(traffic_stats.loc['max', 'traffic_index']),
                    'std': float(traffic_stats.loc['std', 'traffic_index'])
                }
            }
        else:
            stats['traffic'] = self._get_default_stats()
        
        if self.gps_df is not None:
            gps_stats = self.gps_df.agg({
                'distance_km': ['mean', 'min', 'max'],
                'duration_min': ['mean', 'min', 'max']
            })
            stats['trips'] = {
                'avg_distance': float(gps_stats.loc['mean', 'distance_km']),
                'avg_duration': float(gps_stats.loc['mean', 'duration_min']),
                'total_trips': len(self.gps_df)
            }
        else:
            stats['trips'] = {'avg_distance': 0, 'avg_duration': 0, 'total_trips': 0}
        
        return stats
    
    def get_top_congested_zones(self, top_n=5):
        if self.traffic_df is None:
            return self._get_default_top_zones(top_n)
        
        congestion = self.traffic_df.groupby('zone').agg({
            'traffic_index': 'mean',
            'vehicle_count': 'mean'
        }).sort_values('traffic_index', ascending=False).head(top_n)
        
        return [{
            'zone': zone,
            'traffic_index': float(row['traffic_index']),
            'vehicle_count': float(row['vehicle_count'])
        } for zone, row in congestion.iterrows()]
    
    def get_top_routes(self, top_n=5):
        if self.gps_df is None:
            return self._get_default_top_routes(top_n)
        
        routes = self.gps_df.groupby(['origin_zone', 'destination_zone']).agg({
            'trip_id': 'count',
            'distance_km': 'mean',
            'duration_min': 'mean'
        }).sort_values('trip_id', ascending=False).head(top_n)
        
        return [{
            'origin': origin,
            'destination': dest,
            'trip_count': int(row['trip_id']),
            'avg_distance': float(row['distance_km']),
            'avg_duration': float(row['duration_min'])
        } for (origin, dest), row in routes.iterrows()]
    
    def get_time_distribution(self):
        if self.gps_df is None:
            return self._get_default_time_distribution()
        
        hour_dist = self.gps_df.groupby('hour').size()
        day_dist = self.gps_df.groupby('day_of_week').size()
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        return {
            'by_hour': {int(h): int(c) for h, c in hour_dist.items()},
            'by_day': {days[int(d)]: int(c) for d, c in day_dist.items()}
        }
    
    def get_route_summary(self):
        if self.gps_df is None:
            return self._get_default_route_summary()
        
        popular = self.gps_df.groupby(['origin_zone', 'destination_zone']).size().sort_values(ascending=False).head(10)
        
        mode_counts = self.gps_df['vehicle_type'].value_counts()
        
        return {
            'popular_routes': [{'origin': k[0], 'destination': k[1], 'count': int(v)} for k, v in popular.items()],
            'mode_distribution': {str(k): int(v) for k, v in mode_counts.items()}
        }
    
    # ============================================
    # DIAGNOSTIC ANALYTICS
    # ============================================
    
    def get_traffic_cause_breakdown(self):
        current_hour = datetime.now().hour
        weather = self.weather_api.get_current_weather("Nairobi")
        weather_condition = weather.get('weather_condition', 'clear')
        
        time_factor = 1.5 if (7 <= current_hour <= 9 or 17 <= current_hour <= 20) else 1.0
        
        weather_impact = {
            'clear': 0,
            'cloudy': 0.1,
            'rain': 0.3,
            'heavy_rain': 0.5
        }
        weather_factor = weather_impact.get(weather_condition, 0.2)
        
        location_factor = 0.3
        
        total = time_factor + weather_factor + location_factor
        if total > 1:
            time_factor = time_factor / total
            weather_factor = weather_factor / total
            location_factor = location_factor / total
        
        return {
            'time_factor': round(time_factor * 100, 1),
            'weather_factor': round(weather_factor * 100, 1),
            'location_factor': round(location_factor * 100, 1),
            'explanation': self._generate_cause_explanation(time_factor, weather_factor, location_factor, current_hour, weather_condition)
        }
    
    def _generate_cause_explanation(self, time_f, weather_f, loc_f, hour, weather):
        reasons = []
        
        if time_f >= 0.4:
            if 7 <= hour <= 9:
                reasons.append(f"Morning rush hour ({int(time_f*100)}%)")
            elif 17 <= hour <= 20:
                reasons.append(f"Evening rush hour ({int(time_f*100)}%)")
            else:
                reasons.append(f"Time of day ({int(time_f*100)}%)")
        
        if weather_f >= 0.15:
            reasons.append(f"{weather} weather ({int(weather_f*100)}%)")
        
        if loc_f >= 0.2:
            reasons.append(f"Location/traffic zone ({int(loc_f*100)}%)")
        
        return " + ".join(reasons) if reasons else "Normal traffic conditions"
    
    def get_anomalies(self, threshold=0.8):
        if self.traffic_df is None:
            return []
        
        hourly_avg = self.traffic_df.groupby('hour')['traffic_index'].mean()
        current_hour = datetime.now().hour
        
        if current_hour not in hourly_avg.index:
            return []
        
        baseline = hourly_avg.mean()
        current_value = hourly_avg.get(current_hour, 1.0)
        
        deviation = (current_value - baseline) / baseline if baseline > 0 else 0
        
        if deviation >= threshold:
            return [{
                'zone': 'All Zones',
                'hour': current_hour,
                'traffic_index': float(current_value),
                'baseline': float(baseline),
                'deviation_percent': round(deviation * 100, 1),
                'reason': self._get_anomaly_reason(current_hour, deviation)
            }]
        
        return []
    
    def _get_anomaly_reason(self, hour, deviation):
        if 7 <= hour <= 9:
            return "Morning rush hour causing unusually high traffic"
        elif 17 <= hour <= 20:
            return "Evening rush hour causing unusually high traffic"
        elif hour == 0:
            return "Late night traffic anomaly"
        else:
            return "Unusual traffic pattern detected"
    
    def get_factor_contributions(self):
        current_hour = datetime.now().hour
        weather = self.weather_api.get_current_weather("Nairobi")
        
        time_impact = 40 if (7 <= current_hour <= 9 or 17 <= current_hour <= 20) else 20
        
        weather_conditions = {
            'clear': 5,
            'cloudy': 15,
            'rain': 30,
            'heavy_rain': 50
        }
        weather_impact = weather_conditions.get(weather.get('weather_condition', 'clear'), 10)
        
        zone_risk_impact = 25
        
        total = time_impact + weather_impact + zone_risk_impact
        
        return {
            'time_factor': {'value': time_impact, 'label': 'Rush Hour' if 7 <= current_hour <= 9 or 17 <= current_hour <= 20 else 'Normal Hours'},
            'weather_factor': {'value': weather_impact, 'label': weather.get('weather_description', 'Unknown').title()},
            'zone_factor': {'value': zone_risk_impact, 'label': 'Location Risk'}
        }
    
    def compare_days(self):
        if self.traffic_df is None or 'day_of_week' not in self.traffic_df.columns:
            return self._get_default_day_comparison()
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        day_stats = self.traffic_df.groupby('day_of_week').agg({
            'traffic_index': 'mean',
            'vehicle_count': 'mean'
        }).reset_index()
        
        avg_traffic = day_stats['traffic_index'].mean()
        
        comparison = []
        for _, row in day_stats.iterrows():
            day_idx = int(row['day_of_week'])
            day_name = days[day_idx]
            traffic = float(row['traffic_index'])
            diff_from_avg = ((traffic - avg_traffic) / avg_traffic * 100) if avg_traffic > 0 else 0
            
            comparison.append({
                'day': day_name,
                'traffic_index': round(traffic, 2),
                'difference_percent': round(diff_from_avg, 1),
                'status': 'High' if diff_from_avg > 10 else 'Low' if diff_from_avg < -10 else 'Normal'
            })
        
        return {'days': comparison, 'average_traffic': round(avg_traffic, 2)}
    
    def diagnose_zones(self, zone1, zone2):
        z1_info = NAIROBI_ZONES.get(zone1, {})
        z2_info = NAIROBI_ZONES.get(zone2, {})
        
        z1_risk = z1_info.get('risk_level', 'medium')
        z2_risk = z2_info.get('risk_level', 'medium')
        
        risk_values = {'low': 1, 'medium': 2, 'high': 3}
        
        diagnosis = []
        
        if risk_values.get(z1_risk, 2) > risk_values.get(z2_risk, 2):
            diagnosis.append(f"{zone1} has higher risk ({z1_risk}) than {zone2} ({z2_risk})")
        elif risk_values.get(z1_risk, 2) < risk_values.get(z2_risk, 2):
            diagnosis.append(f"{zone2} has higher risk ({z2_risk}) than {zone1} ({z1_risk})")
        else:
            diagnosis.append(f"Both zones have similar risk level ({z1_risk})")
        
        z1_lat, z2_lat = z1_info.get('lat', 0), z2_info.get('lat', 0)
        if abs(z1_lat - z2_lat) > 0.1:
            diagnosis.append(f"Zones are {abs(z1_lat - z2_lat)*111:.1f} km apart")
        
        return {
            'zone1': {'name': zone1, 'risk': z1_risk, 'lat': z1_info.get('lat', 0), 'lon': z1_info.get('lon', 0)},
            'zone2': {'name': zone2, 'risk': z2_risk, 'lat': z2_info.get('lat', 0), 'lon': z2_info.get('lon', 0)},
            'diagnosis': diagnosis
        }
    
    # ============================================
    # PREDICTIVE ANALYTICS
    # ============================================
    
    def predict_24h_traffic(self):
        current_hour = datetime.now().hour
        
        hours = list(range(24))
        predictions = []
        
        for h in hours:
            base = 1.0
            if 7 <= h <= 9:
                base = 1.6
            elif 17 <= h <= 20:
                base = 1.7
            elif 0 <= h <= 5:
                base = 0.5
            
            predictions.append({
                'hour': h,
                'predicted_index': round(base * (1 + (np.random.random() - 0.5) * 0.1), 2),
                'confidence': 'high' if h == current_hour else 'medium'
            })
        
        return {'predictions': predictions, 'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')}
    
    def predict_weekly_outlook(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        outlook = []
        for i, day in enumerate(days):
            if i < 5:
                traffic = 1.4 if i in [0, 4] else 1.5
                label = 'High' if i in [0, 4] else 'Very High'
            else:
                traffic = 0.9
                label = 'Low'
            
            outlook.append({
                'day': day,
                'predicted_traffic': round(traffic, 2),
                'recommendation': 'Avoid travel' if traffic > 1.3 else 'Good time to travel' if traffic < 1.0 else 'Expect delays'
            })
        
        return {'outlook': outlook}
    
    def predict_demand(self):
        if self.gps_df is None:
            return {'routes': []}
        
        route_demand = self.gps_df.groupby(['origin_zone', 'destination_zone']).size().sort_values(ascending=False).head(5)
        
        demand = []
        for (origin, dest), count in route_demand.items():
            demand.append({
                'route': f"{origin} → {dest}",
                'predicted_demand': 'High' if count > 400 else 'Medium' if count > 200 else 'Low',
                'estimated_trips': int(count * 1.2)
            })
        
        return {'routes': demand}
    
    def predict_prices(self):
        current_hour = datetime.now().hour
        weather = self.weather_api.get_current_weather("Nairobi")
        
        base_matatu = 20
        base_driving = 150
        
        multiplier = 1.0
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 20:
            multiplier = 1.3
        
        weather_mult = {'clear': 1.0, 'cloudy': 1.05, 'rain': 1.2, 'heavy_rain': 1.4}
        multiplier *= weather_mult.get(weather.get('weather_condition', 'clear'), 1.0)
        
        return {
            'matatu': {'current': int(base_matatu * multiplier), 'typical': base_matatu},
            'driving': {'current': int(base_driving * multiplier), 'typical': base_driving},
            'wheelchair': {'current': 50, 'typical': 50}
        }
    
    def get_congestion_warnings(self):
        current_hour = datetime.now().hour
        warnings = []
        
        if 7 <= current_hour <= 9:
            warnings.append({
                'zone': 'CBD',
                'type': 'rush_hour',
                'message': 'Heavy congestion expected due to morning rush hour',
                'severity': 'high',
                'expected_delay': '15-25 minutes'
            })
        
        if 17 <= current_hour <= 19:
            warnings.append({
                'zone': 'Westlands',
                'type': 'rush_hour',
                'message': 'Evening rush hour congestion expected',
                'severity': 'high',
                'expected_delay': '10-20 minutes'
            })
        
        weather = self.weather_api.get_current_weather("Nairobi")
        if weather.get('weather_condition') in ['rain', 'heavy_rain']:
            warnings.append({
                'zone': 'All Zones',
                'type': 'weather',
                'message': f"Weather alert: {weather.get('weather_description', 'Rain')}. Expect slower traffic.",
                'severity': 'medium',
                'expected_delay': '5-15 minutes'
            })
        
        return {'warnings': warnings}
    
    # ============================================
    # DEFAULT/FALLBACK DATA
    # ============================================
    
    def _get_default_trends(self):
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
        return {
            'dates': dates,
            'vehicle_count': [50 + np.random.randint(-10, 20) for _ in range(7)],
            'traffic_index': [1.0 + np.random.uniform(-0.2, 0.3) for _ in range(7)],
            'avg_speed': [30 + np.random.randint(-5, 10) for _ in range(7)]
        }
    
    def _get_default_stats(self):
        return {
            'avg': 0, 'min': 0, 'max': 0, 'std': 0
        }
    
    def _get_default_top_zones(self, n):
        return [{'zone': z, 'traffic_index': 1.2, 'vehicle_count': 50} for z in list(NAIROBI_ZONES.keys())[:n]]
    
    def _get_default_top_routes(self, n):
        return [{'origin': 'CBD', 'destination': 'Westlands', 'trip_count': 100, 'avg_distance': 5.0, 'avg_duration': 15} for _ in range(n)]
    
    def _get_default_time_distribution(self):
        return {'by_hour': {i: np.random.randint(50, 200) for i in range(24)}, 'by_day': {'Monday': 500, 'Tuesday': 450, 'Wednesday': 480, 'Thursday': 520, 'Friday': 600, 'Saturday': 300, 'Sunday': 200}}
    
    def _get_default_route_summary(self):
        return {'popular_routes': [], 'mode_distribution': {}}
    
    def _get_default_day_comparison(self):
        return {'days': [], 'average_traffic': 1.0}
    
    def _get_mode_icon(self, mode: str) -> str:
        icons = {
            'walking': '🚶',
            'matatu': '🚌',
            'driving': '🚗'
        }
        return icons.get(mode.lower(), '➡️')


def get_nairobi_zones():
    return NAIROBI_ZONES
