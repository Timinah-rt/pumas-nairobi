import requests
from typing import Dict, List, Optional, Tuple
import os

class OpenRouteServiceAPI:
    BASE_URL = "https://api.openrouteservice.org"
    
    DEFAULT_API_KEY = "5b3ce3597851110001cf624835c82ec8b0aa4a2f8e6c8f2e2b3a9f4a"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ORS_API_KEY', self.DEFAULT_API_KEY)
    
    def get_route(self, start: Tuple[float, float], end: Tuple[float, float], 
                  mode: str = 'driving-car') -> Optional[Dict]:
        url = f"{self.BASE_URL}/v2/directions/{mode}"
        params = {
            'api_key': self.api_key,
            'start': f"{start[1]},{start[0]}",
            'end': f"{end[1]},{end[0]}"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._parse_route_response(data)
        except requests.exceptions.RequestException as e:
            print(f"ORS API Error: {e}")
            return self._get_fallback_route(start, end, mode)
    
    def get_route_with_waypoints(self, coordinates: List[Tuple[float, float]], 
                                  mode: str = 'driving-car') -> Optional[Dict]:
        url = f"{self.BASE_URL}/v2/directions/{mode}"
        
        coord_str = ';'.join([f"{lon},{lat}" for lat, lon in coordinates])
        
        params = {
            'api_key': self.api_key,
            'coordinates': coord_str
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return self._parse_route_response(data)
        except requests.exceptions.RequestException as e:
            print(f"ORS API Error: {e}")
            return None
    
    def _parse_route_response(self, data: Dict) -> Dict:
        if 'routes' not in data or len(data['routes']) == 0:
            return None
        
        route = data['routes'][0]
        summary = route.get('summary', {})
        geometry = route.get('geometry', '')
        segments = route.get('segments', [])
        
        return {
            'distance_km': summary.get('distance', 0) / 1000,
            'duration_min': summary.get('duration', 0) / 60,
            'geometry': geometry,
            'segments': [{
                'distance_km': seg.get('distance', 0) / 1000,
                'duration_min': seg.get('duration', 0) / 60,
                'steps': seg.get('steps', [])
            } for seg in segments],
            'bbox': data.get('bbox', [])
        }
    
    def _get_fallback_route(self, start: Tuple[float, float], end: Tuple[float, float], 
                           mode: str) -> Dict:
        import math
        
        lat_diff = abs(end[0] - start[0])
        lon_diff = abs(end[1] - start[1])
        distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111
        
        speeds = {
            'foot-walking': 5,
            'cycling-regular': 15,
            'driving-car': 30
        }
        speed = speeds.get(mode, 30)
        duration = distance / speed * 60
        
        return {
            'distance_km': round(distance, 2),
            'duration_min': round(duration, 1),
            'geometry': None,
            'segments': [],
            'bbox': [min(start[1], end[1]), min(start[0], end[0]),
                     max(start[1], end[1]), max(start[0], end[0])]
        }
    
    def get_isochrone(self, location: Tuple[float, float], 
                      range_type: str = 'time',
                      range_values: List[int] = [300, 600, 900]) -> Optional[Dict]:
        url = f"{self.BASE_URL}/v2/isochrones/driving-car"
        
        params = {
            'api_key': self.api_key,
            'location': f"{location[1]},{location[0]}",
            'range': ','.join(map(str, range_values)),
            'range_type': range_type
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"ORS Isochrone Error: {e}")
            return None
    
    def get_matrix(self, locations: List[Tuple[float, float]], 
                   mode: str = 'driving-car') -> Optional[Dict]:
        url = f"{self.BASE_URL}/v2/matrix/{mode}"
        
        coord_str = ';'.join([f"{lon},{lat}" for lat, lon in locations])
        
        params = {
            'api_key': self.api_key,
            'locations': coord_str,
            'metrics': 'duration,distance'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"ORS Matrix Error: {e}")
            return None


def get_route_info(start: Tuple[float, float], end: Tuple[float, float], 
                  mode: str = 'driving-car') -> Dict:
    api = OpenRouteServiceAPI()
    return api.get_route(start, end, mode)


def get_multi_route_info(zones: Dict[str, Dict], 
                         origin: str, dest: str) -> Dict:
    api = OpenRouteServiceAPI()
    
    if origin not in zones or dest not in zones:
        return None
    
    start = (zones[origin]['lat'], zones[origin]['lon'])
    end = (zones[dest]['lat'], zones[dest]['lon'])
    
    routes = {}
    
    modes = {
        'driving': 'driving-car',
        'walking': 'foot-walking',
        'cycling': 'cycling-regular'
    }
    
    for name, mode in modes.items():
        route = api.get_route(start, end, mode)
        if route:
            routes[name] = {
                'distance_km': route['distance_km'],
                'duration_min': route['duration_min'],
                'geometry': route.get('geometry')
            }
    
    return routes
