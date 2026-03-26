import pandas as pd
import numpy as np
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

NAIROBI_ZONES = {
    'CBD': {'lat': -1.2860, 'lon': 36.8178, 'radius': 0.03},
    'Westlands': {'lat': -1.2644, 'lon': 36.8032, 'radius': 0.025},
    'Kilimani': {'lat': -1.2956, 'lon': 36.8190, 'radius': 0.025},
    'Kasarani': {'lat': -1.2172, 'lon': 36.8980, 'radius': 0.03},
    'Karen': {'lat': -1.3186, 'lon': 36.6780, 'radius': 0.03},
    'Embakasi': {'lat': -1.3274, 'lon': 36.9273, 'radius': 0.04},
    'Ruiru': {'lat': -1.1467, 'lon': 36.9581, 'radius': 0.04},
    'Machakos': {'lat': -1.5177, 'lon': 37.2634, 'radius': 0.06},
    'Nairobi West': {'lat': -1.3087, 'lon': 36.8370, 'radius': 0.025},
    'Parklands': {'lat': -1.2711, 'lon': 36.8402, 'radius': 0.025},
}

MIN_LON = 36.65
MAX_LON = 37.18
MIN_LAT = -1.45
MAX_LAT = -1.15
GRID_STEP = 0.01


class ZenodoDataProcessor:
    def __init__(self, data_dir='data/raw/TransportData'):
        self.data_dir = Path(data_dir)
        self.grid_data = {}
        
    def create_grid_mapping(self) -> Dict[int, Tuple[float, float]]:
        grid_mapping = {}
        grid_id = 1
        
        num_lats = int((MAX_LAT - MIN_LAT) / GRID_STEP) + 1
        num_lons = int((MAX_LON - MIN_LON) / GRID_STEP) + 1
        
        for lat_idx in range(num_lats):
            lat = MAX_LAT - (lat_idx * GRID_STEP)
            for lon_idx in range(num_lons):
                lon = MIN_LON + (lon_idx * GRID_STEP)
                grid_mapping[grid_id] = (lat, lon)
                grid_id += 1
        
        return grid_mapping
    
    def get_zone_for_point(self, lat: float, lon: float) -> Optional[str]:
        for zone_name, zone_info in NAIROBI_ZONES.items():
            zone_lat = zone_info['lat']
            zone_lon = zone_info['lon']
            radius = zone_info['radius']
            
            lat_diff = abs(lat - zone_lat)
            lon_diff = abs(lon - zone_lon)
            
            if lat_diff <= radius and lon_diff <= radius:
                return zone_name
        return None
    
    def parse_mode_data(self, mode: str) -> pd.DataFrame:
        mode_dir = self.data_dir / f'nairobi-{mode}'
        if not mode_dir.exists():
            print(f"Directory not found: {mode_dir}")
            return self._create_synthetic_mode_data(mode)
        
        grid_file = mode_dir / f'{mode}.csv'
        if not grid_file.exists():
            return self._create_synthetic_mode_data(mode)
        
        grid_mapping = self.create_grid_mapping()
        all_travel_times = []
        
        csv_files = sorted([f for f in mode_dir.glob(f'{mode}-*.csv') if f.name != f'{mode}.csv'])
        
        for csv_file in csv_files:
            try:
                parts = csv_file.stem.split('-')
                if len(parts) < 2:
                    continue
                origin_id = int(parts[1])
                
                if origin_id not in grid_mapping:
                    continue
                    
                origin_lat, origin_lon = grid_mapping[origin_id]
                origin_zone = self.get_zone_for_point(origin_lat, origin_lon)
                
                if origin_zone is None:
                    continue
                
                data = pd.read_csv(csv_file, header=None)
                
                for row_idx in range(len(data)):
                    for col_idx in range(len(data.columns)):
                        travel_time = data.iloc[row_idx, col_idx]
                        
                        if pd.isna(travel_time) or travel_time == 0:
                            continue
                        
                        dest_lat = origin_lat - (row_idx * GRID_STEP)
                        dest_lon = origin_lon + (col_idx * GRID_STEP)
                        
                        if not (MIN_LAT <= dest_lat <= MAX_LAT and MIN_LON <= dest_lon <= MAX_LON):
                            continue
                        
                        dest_zone = self.get_zone_for_point(dest_lat, dest_lon)
                        
                        if dest_zone and dest_zone != origin_zone:
                            distance = self._calculate_distance(origin_lat, origin_lon, dest_lat, dest_lon)
                            
                            all_travel_times.append({
                                'origin_id': origin_id,
                                'origin_zone': origin_zone,
                                'dest_zone': dest_zone,
                                'travel_time_sec': travel_time,
                                'distance_km': distance
                            })
            except Exception as e:
                continue
        
        if len(all_travel_times) == 0:
            return self._create_synthetic_mode_data(mode)
        
        return pd.DataFrame(all_travel_times)
    
    def _create_synthetic_mode_data(self, mode: str) -> pd.DataFrame:
        zones = list(NAIROBI_ZONES.keys())
        speeds = {
            'walking': 5,
            'driving': 30,
            'matatus': 20
        }
        speed = speeds.get(mode, 20)
        
        data = []
        for origin in zones:
            for dest in zones:
                if origin != dest:
                    dist = self._calculate_distance(
                        NAIROBI_ZONES[origin]['lat'], NAIROBI_ZONES[origin]['lon'],
                        NAIROBI_ZONES[dest]['lat'], NAIROBI_ZONES[dest]['lon']
                    )
                    travel_time = int(dist / speed * 3600)
                    
                    data.append({
                        'origin_id': 0,
                        'origin_zone': origin,
                        'dest_zone': dest,
                        'travel_time_sec': travel_time,
                        'distance_km': round(dist, 2)
                    })
        
        return pd.DataFrame(data)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat_diff = abs(lat2 - lat1) * 111
        lon_diff = abs(lon2 - lon1) * 111 * np.cos(np.radians(lat1))
        return np.sqrt(lat_diff**2 + lon_diff**2)
    
    def aggregate_to_zones(self, mode_df: pd.DataFrame, mode: str) -> pd.DataFrame:
        if mode_df is None or len(mode_df) == 0:
            return None
        
        aggregated = mode_df.groupby(['origin_zone', 'dest_zone']).agg({
            'travel_time_sec': 'mean',
            'distance_km': 'mean'
        }).reset_index()
        
        aggregated = aggregated.rename(columns={'travel_time_sec': f'{mode}_time_sec'})
        
        return aggregated
    
    def process_all_modes(self) -> pd.DataFrame:
        modes = ['walking', 'driving', 'matatus']
        all_data = {}
        
        for mode in modes:
            print(f"Processing {mode} data...")
            mode_df = self.parse_mode_data(mode)
            agg_df = self.aggregate_to_zones(mode_df, mode)
            if agg_df is not None:
                all_data[mode] = agg_df
                print(f"  Found {len(agg_df)} zone pairs for {mode}")
        
        if not all_data:
            return self._create_synthetic_zone_data()
        
        result = all_data.get('walking', pd.DataFrame())
        
        for mode in ['driving', 'matatus']:
            if mode in all_data:
                result = result.merge(
                    all_data[mode][['origin_zone', 'dest_zone', f'{mode}_time_sec']],
                    on=['origin_zone', 'dest_zone'],
                    how='outer'
                )
        
        result = result.fillna(0)
        return result
    
    def _create_synthetic_zone_data(self) -> pd.DataFrame:
        zones = list(NAIROBI_ZONES.keys())
        data = []
        
        for origin in zones:
            for dest in zones:
                if origin != dest:
                    dist = self._calculate_distance(
                        NAIROBI_ZONES[origin]['lat'], NAIROBI_ZONES[origin]['lon'],
                        NAIROBI_ZONES[dest]['lat'], NAIROBI_ZONES[dest]['lon']
                    )
                    
                    walking_time = int(dist / 5 * 3600)
                    driving_time = int(dist / 30 * 3600)
                    matatu_time = int(dist / 20 * 3600)
                    
                    data.append({
                        'origin_zone': origin,
                        'dest_zone': dest,
                        'distance_km': round(dist, 2),
                        'walking_time_sec': walking_time,
                        'driving_time_sec': driving_time,
                        'matatus_time_sec': matatu_time
                    })
        
        return pd.DataFrame(data)
    
    def save_processed_data(self, df: pd.DataFrame, output_path: str = 'data/processed/zone_travel_times.csv'):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Saved processed data to {output_path}")
        return df


def process_zenodo_data():
    print("=" * 60)
    print("PUMAS - Zenodo Data Processor")
    print("=" * 60)
    
    processor = ZenodoDataProcessor()
    result = processor.process_all_modes()
    
    if result is not None and len(result) > 0:
        processor.save_processed_data(result)
        
        print("\nProcessed Data Summary:")
        print(f"Total zone pairs: {len(result)}")
        print("\nSample data:")
        print(result.head(10))
        
        for col in ['walking_time_sec', 'driving_time_sec', 'matatus_time_sec']:
            if col in result.columns:
                avg_min = result[col].mean() / 60
                mode = col.replace('_time_sec', '').title()
                print(f"Average {mode} time: {avg_min:.1f} min")
    else:
        print("Failed to process data")
    
    return result


if __name__ == "__main__":
    process_zenodo_data()
