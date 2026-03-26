import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime

MATATU_FARES = {
    'within_cbd': 10,
    'short': 15,
    'medium': 20,
    'long': 30
}

FUEL_PRICE_KES_PER_LITER = 183.72
VEHICLE_CONSUMPTION_KM_PER_LITER = 12
COST_PER_KM_KES = FUEL_PRICE_KES_PER_LITER / VEHICLE_CONSUMPTION_KM_PER_LITER

WALKING_SPEED_KM_H = 5
DRIVING_SPEED_KM_H = 30
MATATU_SPEED_KM_H = 20

WEATHER_IMPACT = {
    'clear': {'traffic_multiplier': 1.0, 'price_multiplier': 1.0, 'delay_percent': 0},
    'cloudy': {'traffic_multiplier': 1.1, 'price_multiplier': 1.05, 'delay_percent': 10},
    'rain': {'traffic_multiplier': 1.3, 'price_multiplier': 1.2, 'delay_percent': 30},
    'heavy_rain': {'traffic_multiplier': 1.5, 'price_multiplier': 1.3, 'delay_percent': 50}
}

class CostCalculator:
    def __init__(self, travel_times_df: Optional[pd.DataFrame] = None):
        self.travel_times_df = travel_times_df
        
    def calculate_matatu_fare(self, distance_km: float) -> int:
        if distance_km <= 2:
            return MATATU_FARES['within_cbd']
        elif distance_km <= 5:
            return MATATU_FARES['short']
        elif distance_km <= 15:
            return MATATU_FARES['medium']
        else:
            return MATATU_FARES['long']
    
    def calculate_driving_cost(self, distance_km: float) -> int:
        return int(distance_km * COST_PER_KM_KES)
    
    def calculate_walking_cost(self, distance_km: float) -> int:
        return 0
    
    def sec_to_time_str(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds} sec"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            if secs == 0:
                return f"{mins} min"
            return f"{mins} min {secs} sec"
        else:
            hrs = seconds // 3600
            mins = (seconds % 3600) // 60
            if mins == 0:
                return f"{hrs} hr"
            return f"{hrs} hr {mins} min"
    
    def calculate_all_costs(self, row: pd.Series) -> Dict:
        distance = row.get('distance_km', 10)
        
        walking_cost = self.calculate_walking_cost(distance)
        matatu_cost = self.calculate_matatu_fare(distance)
        driving_cost = self.calculate_driving_cost(distance)
        
        return {
            'walking_cost': walking_cost,
            'matatu_cost': matatu_cost,
            'driving_cost': driving_cost
        }
    
    def calculate_all_times(self, row: pd.Series) -> Dict:
        walking_sec = row.get('walking_time_sec', 0)
        driving_sec = row.get('driving_time_sec', 0)
        matatu_sec = row.get('matatus_time_sec', 0)
        
        return {
            'walking_time': self.sec_to_time_str(int(walking_sec)),
            'driving_time': self.sec_to_time_str(int(driving_sec)),
            'matatu_time': self.sec_to_time_str(int(matatu_sec)),
            'walking_sec': walking_sec,
            'driving_sec': driving_sec,
            'matatu_sec': matatu_sec
        }
    
    def get_route_suggestions(self, row: pd.Series) -> Dict:
        times = {
            'walking': row.get('walking_time_sec', 0),
            'driving': row.get('driving_time_sec', 0),
            'matatu': row.get('matatus_time_sec', 0)
        }
        
        costs = self.calculate_all_costs(row)
        
        fastest_mode = min(times, key=times.get)
        cheapest_key = min(costs, key=costs.get)
        cheapest_mode = cheapest_key.replace('_cost', '')
        
        time_values = list(times.values())
        cost_values = [costs['walking_cost'], costs['matatu_cost'], costs['driving_cost']]
        
        if fastest_mode == cheapest_mode:
            best_value = fastest_mode
        else:
            time_score = times[fastest_mode] / max(time_values) if max(time_values) > 0 else 1
            cost_score = costs['driving_cost'] / max(cost_values) if max(cost_values) > 0 else 0
            matatu_score = (times['matatu'] / max(time_values) if max(time_values) > 0 else 1) + (costs['matatu_cost'] / max(cost_values) if max(cost_values) > 0 else 0)
            
            if matatu_score <= time_score + cost_score / 10:
                best_value = 'matatu'
            else:
                best_value = fastest_mode
        
        cheapest_cost_val = costs.get(cheapest_key, 0)
        best_value_cost_val = costs.get(f'{best_value}_cost', 0)
        
        return {
            'fastest_mode': fastest_mode,
            'fastest_time': self.sec_to_time_str(int(times[fastest_mode])),
            'cheapest_mode': cheapest_mode,
            'cheapest_cost': cheapest_cost_val,
            'best_value_mode': best_value,
            'best_value_time': self.sec_to_time_str(int(times[best_value])),
            'best_value_cost': best_value_cost_val
        }
    
    def add_costs_to_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        cost_data = []
        
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            row_dict.update(self.calculate_all_costs(row))
            row_dict.update(self.calculate_all_times(row))
            row_dict.update(self.get_route_suggestions(row))
            cost_data.append(row_dict)
        
        return pd.DataFrame(cost_data)


class WeatherPredictor:
    def __init__(self):
        self.weather_impact = WEATHER_IMPACT
        
    def get_weather_impact(self, condition: str) -> Dict:
        return self.weather_impact.get(condition.lower(), self.weather_impact['clear'])
    
    def predict_adjusted_time(self, base_time_sec: float, weather_condition: str) -> Tuple[int, int]:
        impact = self.get_weather_impact(weather_condition)
        multiplier = impact['traffic_multiplier']
        adjusted_time = int(base_time_sec * multiplier)
        delay_percent = impact['delay_percent']
        return adjusted_time, delay_percent
    
    def predict_adjusted_price(self, base_price: int, weather_condition: str) -> Tuple[int, int]:
        impact = self.get_weather_impact(weather_condition)
        multiplier = impact['price_multiplier']
        adjusted_price = int(base_price * multiplier)
        increase_percent = int((multiplier - 1) * 100)
        return adjusted_price, increase_percent
    
    def predict_all_for_trip(self, row: pd.Series, weather_condition: str) -> Dict:
        weather_info = self.get_weather_impact(weather_condition)
        
        predictions = {
            'weather_condition': weather_condition,
            'weather_description': self._get_weather_description(weather_condition),
            'traffic_impact': weather_info['delay_percent'],
            'price_impact': int((weather_info['price_multiplier'] - 1) * 100)
        }
        
        modes = ['walking', 'driving', 'matatu']
        for mode in modes:
            time_col = f'{mode}_time_sec' if mode != 'matatu' else 'matatus_time_sec'
            cost_col = f'{mode}_cost'
            
            base_time = row.get(time_col, 0)
            base_cost = row.get(cost_col, 0)
            
            if base_time > 0:
                adjusted_time, delay_pct = self.predict_adjusted_time(base_time, weather_condition)
                predictions[f'{mode}_time_normal'] = self._sec_to_time_str(int(base_time))
                predictions[f'{mode}_time_adjusted'] = self._sec_to_time_str(adjusted_time)
                predictions[f'{mode}_time_delay'] = f"+{delay_pct}%"
            else:
                predictions[f'{mode}_time_normal'] = "N/A"
                predictions[f'{mode}_time_adjusted'] = "N/A"
                predictions[f'{mode}_time_delay'] = "0%"
            
            if base_cost > 0:
                adjusted_cost, price_increase = self.predict_adjusted_price(base_cost, weather_condition)
                predictions[f'{mode}_cost_normal'] = base_cost
                predictions[f'{mode}_cost_adjusted'] = adjusted_cost
                predictions[f'{mode}_cost_increase'] = f"+{price_increase}%"
            else:
                predictions[f'{mode}_cost_normal'] = base_cost
                predictions[f'{mode}_cost_adjusted'] = base_cost
                predictions[f'{mode}_cost_increase'] = "0%"
        
        return predictions
    
    def _sec_to_time_str(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds} sec"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            if secs == 0:
                return f"{mins} min"
            return f"{mins} min {secs} sec"
        else:
            hrs = seconds // 3600
            mins = (seconds % 3600) // 60
            if mins == 0:
                return f"{hrs} hr"
            return f"{hrs} hr {mins} min"
    
    def _get_weather_description(self, condition: str) -> str:
        descriptions = {
            'clear': '☀️ Clear skies - Normal traffic expected',
            'cloudy': '☁️ Cloudy - Slightly increased traffic',
            'rain': '🌧️ Rain - Expect delays and higher fares',
            'heavy_rain': '⛈️ Heavy Rain - Significant delays, surge pricing'
        }
        return descriptions.get(condition.lower(), descriptions['clear'])
    
    def generate_weather_summary(self, weather_data: Dict) -> str:
        condition = weather_data.get('weather_condition', 'clear')
        impact = self.get_weather_impact(condition)
        
        summary = f"""
**Current Weather:** {self._get_weather_description(condition)}

**Impact Analysis:**
- Traffic delay: +{impact['delay_percent']}%
- Price increase: +{int((impact['price_multiplier'] - 1) * 100)}%

**Recommendations:**
"""
        if condition == 'heavy_rain':
            summary += "- Consider working from home if possible\n"
            summary += "- Allow extra travel time (up to 50% more)\n"
            summary += "- Public transport recommended\n"
        elif condition == 'rain':
            summary += "- Leave earlier than usual\n"
            summary += "- Consider matatu over driving\n"
        elif condition == 'cloudy':
            summary += "- Normal conditions prevail\n"
        else:
            summary += "- Great day for travel!\n"
        
        return summary


def get_default_travel_times() -> pd.DataFrame:
    zones = ['CBD', 'Westlands', 'Kilimani', 'Kasarani', 'Karen', 'Embakasi', 'Ruiru', 'Machakos', 'Nairobi West', 'Parklands']
    
    zone_coords = {
        'CBD': (-1.2860, 36.8178),
        'Westlands': (-1.2644, 36.8032),
        'Kilimani': (-1.2956, 36.8190),
        'Kasarani': (-1.2172, 36.8980),
        'Karen': (-1.3186, 36.6780),
        'Embakasi': (-1.3274, 36.9273),
        'Ruiru': (-1.1467, 36.9581),
        'Machakos': (-1.5177, 37.2634),
        'Nairobi West': (-1.3087, 36.8370),
        'Parklands': (-1.2711, 36.8402)
    }
    
    data = []
    for origin in zones:
        for dest in zones:
            if origin != dest:
                lat1, lon1 = zone_coords[origin]
                lat2, lon2 = zone_coords[dest]
                
                lat_diff = abs(lat2 - lat1) * 111
                lon_diff = abs(lon2 - lon1) * 111 * np.cos(np.radians(lat1))
                distance = np.sqrt(lat_diff**2 + lon_diff**2)
                
                walking_time = int(distance / WALKING_SPEED_KM_H * 3600)
                driving_time = int(distance / DRIVING_SPEED_KM_H * 3600)
                matatu_time = int(distance / MATATU_SPEED_KM_H * 3600)
                
                data.append({
                    'origin_zone': origin,
                    'dest_zone': dest,
                    'distance_km': round(distance, 1),
                    'walking_time_sec': walking_time,
                    'driving_time_sec': driving_time,
                    'matatus_time_sec': matatu_time
                })
    
    df = pd.DataFrame(data)
    
    calculator = CostCalculator(df)
    return calculator.add_costs_to_dataframe(df)
