import requests
import json
from typing import Dict, Optional
from datetime import datetime
import os

class OpenWeatherMapAPI:
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    DEFAULT_API_KEY = "4d8fb5b93d4af21d66a2948710284366"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('OPENWEATHERMAP_API_KEY', self.DEFAULT_API_KEY)
    
    def get_current_weather(self, city: str = "Nairobi", country_code: str = "KE") -> Dict:
        url = f"{self.BASE_URL}/weather"
        params = {
            'q': f"{city},{country_code}",
            'appid': self.api_key,
            'units': 'metric'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._parse_weather_data(data)
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return self._get_default_weather()
    
    def get_weather_by_coords(self, lat: float, lon: float) -> Dict:
        url = f"{self.BASE_URL}/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._parse_weather_data(data)
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return self._get_default_weather()
    
    def get_forecast(self, city: str = "Nairobi", country_code: str = "KE", hours: int = 24) -> Dict:
        url = f"{self.BASE_URL}/forecast"
        params = {
            'q': f"{city},{country_code}",
            'appid': self.api_key,
            'units': 'metric',
            'cnt': min(hours // 3 + 1, 40)
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._parse_forecast_data(data)
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return {'error': str(e), 'forecast': []}
    
    def _parse_weather_data(self, data: Dict) -> Dict:
        weather = data.get('weather', [{}])[0]
        main = data.get('main', {})
        wind = data.get('wind', {})
        rain = data.get('rain', {})
        
        condition = weather.get('main', '').lower()
        condition_map = {
            'clear': 'clear',
            'clouds': 'cloudy',
            'rain': 'rain',
            'drizzle': 'rain',
            'thunderstorm': 'heavy_rain',
            'snow': 'heavy_rain',
            'mist': 'cloudy',
            'fog': 'cloudy',
            'haze': 'cloudy'
        }
        mapped_condition = condition_map.get(condition, 'clear')
        
        rain_amount = rain.get('1h', rain.get('3h', 0))
        if rain_amount > 5:
            mapped_condition = 'heavy_rain'
        elif mapped_condition == 'rain' and rain_amount < 2:
            mapped_condition = 'cloudy'
        
        return {
            'city': data.get('name', 'Nairobi'),
            'country': data.get('sys', {}).get('country', 'KE'),
            'temperature_c': round(main.get('temp', 25), 1),
            'feels_like_c': round(main.get('feels_like', 25), 1),
            'humidity_percent': main.get('humidity', 50),
            'pressure_hpa': main.get('pressure', 1013),
            'wind_speed_mps': wind.get('speed', 0),
            'wind_deg': wind.get('deg', 0),
            'cloudiness_percent': data.get('clouds', {}).get('all', 0),
            'visibility_km': data.get('visibility', 10000) / 1000,
            'rain_mm_last_hour': rain_amount,
            'weather_condition': mapped_condition,
            'weather_main': weather.get('main', 'Clear'),
            'weather_description': weather.get('description', 'clear sky'),
            'weather_icon': weather.get('icon', '01d'),
            'sunrise': datetime.fromtimestamp(data.get('sys', {}).get('sunrise', 0)).strftime('%H:%M'),
            'sunset': datetime.fromtimestamp(data.get('sys', {}).get('sunset', 0)).strftime('%H:%M'),
            'timestamp': datetime.now().isoformat(),
            'source': 'OpenWeatherMap'
        }
    
    def _parse_forecast_data(self, data: Dict) -> Dict:
        forecast_list = data.get('list', [])
        forecasts = []
        
        for item in forecast_list:
            main = item.get('main', {})
            weather = item.get('weather', [{}])[0]
            
            condition = weather.get('main', '').lower()
            condition_map = {
                'clear': 'clear',
                'clouds': 'cloudy',
                'rain': 'rain',
                'drizzle': 'rain',
                'thunderstorm': 'heavy_rain'
            }
            
            forecasts.append({
                'datetime': item.get('dt_txt', ''),
                'temperature_c': round(main.get('temp', 20), 1),
                'humidity_percent': main.get('humidity', 50),
                'weather_condition': condition_map.get(condition, 'clear'),
                'weather_description': weather.get('description', ''),
                'wind_speed_mps': item.get('wind', {}).get('speed', 0)
            })
        
        return {
            'city': data.get('city', {}).get('name', 'Nairobi'),
            'forecasts': forecasts,
            'source': 'OpenWeatherMap'
        }
    
    def _get_default_weather(self) -> Dict:
        hour = datetime.now().hour
        
        if 6 <= hour < 12:
            condition = 'clear'
            desc = 'partly cloudy'
        elif 12 <= hour < 17:
            condition = 'cloudy'
            desc = 'overcast'
        elif 17 <= hour < 20:
            condition = 'rain'
            desc = 'light rain'
        else:
            condition = 'clear'
            desc = 'clear night'
        
        return {
            'city': 'Nairobi',
            'country': 'KE',
            'temperature_c': 22.0,
            'feels_like_c': 21.0,
            'humidity_percent': 65,
            'pressure_hpa': 1015,
            'wind_speed_mps': 3.5,
            'wind_deg': 90,
            'cloudiness_percent': 40,
            'visibility_km': 10.0,
            'rain_mm_last_hour': 0,
            'weather_condition': condition,
            'weather_main': condition.title(),
            'weather_description': desc,
            'weather_icon': '01d',
            'sunrise': '06:15',
            'sunset': '18:30',
            'timestamp': datetime.now().isoformat(),
            'source': 'Simulated (API unavailable)'
        }
    
    def get_weather_icon_url(self, icon_code: str) -> str:
        return f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
    
    def format_weather_display(self, weather_data: Dict) -> str:
        icons = {
            'clear': '☀️',
            'cloudy': '☁️',
            'rain': '🌧️',
            'heavy_rain': '⛈️'
        }
        
        icon = icons.get(weather_data.get('weather_condition', 'clear'), '🌤️')
        temp = weather_data.get('temperature_c', 25)
        humidity = weather_data.get('humidity_percent', 50)
        desc = weather_data.get('weather_description', 'clear').title()
        
        return f"{icon} {desc}, {temp}°C, Humidity: {humidity}%"


def get_weather_data(city: str = "Nairobi") -> Dict:
    api = OpenWeatherMapAPI()
    return api.get_current_weather(city)
