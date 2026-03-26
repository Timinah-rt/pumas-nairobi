import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timedelta
import os
import joblib

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class TrafficLSTMModel:
    def __init__(self, sequence_length=24, n_features=4):
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.model = None
        self.scaler = MinMaxScaler()
        self.target_scaler = MinMaxScaler()
        self.is_trained = False
        
    def _create_sequences(self, data, labels=None):
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            if labels is not None:
                y.append(labels[i + self.sequence_length])
        return np.array(X), np.array(y)
    
    def prepare_data(self, traffic_df, zone=None):
        if zone:
            df = traffic_df[traffic_df['zone'] == zone].copy()
        else:
            df = traffic_df.copy()
        
        df = df.sort_values('timestamp')
        
        features = df[['vehicle_count', 'avg_speed_kmh', 'traffic_index', 'hour']].values
        target = df['vehicle_count'].values
        
        scaled_features = self.scaler.fit_transform(features)
        scaled_target = self.target_scaler.fit_transform(target.reshape(-1, 1)).flatten()
        
        return scaled_features, scaled_target
    
    def build_model(self):
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
            
            model = Sequential([
                LSTM(64, return_sequences=True, input_shape=(self.sequence_length, self.n_features)),
                Dropout(0.2),
                BatchNormalization(),
                
                LSTM(32, return_sequences=False),
                Dropout(0.2),
                BatchNormalization(),
                
                Dense(16, activation='relu'),
                Dropout(0.1),
                
                Dense(1, activation='linear')
            ])
            
            model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            self.model = model
            return model
        except ImportError:
            print("TensorFlow not available. Using statistical model.")
            return None
    
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=50, batch_size=32):
        self.build_model()
        
        if self.model is None:
            self.is_trained = True
            return None
        
        if X_val is None or y_val is None:
            split = int(len(X_train) * 0.8)
            X_val, y_val = X_train[split:], y_train[split:]
            X_train, y_train = X_train[:split], y_train[:split]
        
        try:
            from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
            
            callbacks = [
                EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
                ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
            ]
            
            history = self.model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                verbose=0
            )
            
            self.is_trained = True
            return history
        except Exception as e:
            print(f"Training error: {e}")
            self.is_trained = True
            return None
    
    def predict(self, X):
        if self.model is None or not self.is_trained:
            return self._statistical_predict(X)
        
        try:
            predictions = self.model.predict(X, verbose=0)
            return self.target_scaler.inverse_transform(predictions).flatten()
        except:
            return self._statistical_predict(X)
    
    def _statistical_predict(self, X):
        base_values = X[:, -1, 0]
        hour_of_day = datetime.now().hour
        
        traffic_factor = 1.5 + np.sin((hour_of_day - 6) * np.pi / 12)
        traffic_factor = max(0.5, min(2.5, traffic_factor))
        
        predictions = base_values * traffic_factor
        return predictions
    
    def predict_future(self, last_sequence, n_steps=6):
        predictions = []
        current_sequence = last_sequence.copy()
        
        for _ in range(n_steps):
            if len(current_sequence.shape) == 2:
                current_sequence = current_sequence.reshape(1, *current_sequence.shape)
            
            pred = self.predict(current_sequence)
            predictions.append(pred[0] if isinstance(pred, np.ndarray) else pred)
            
            new_row = current_sequence[0, -1].copy()
            new_row[0] = pred[0] if isinstance(pred, np.ndarray) else pred
            current_sequence = np.roll(current_sequence, -1, axis=1)
            current_sequence[0, -1] = new_row
        
        return np.array(predictions)
    
    def save_model(self, path='models/lstm_model.h5'):
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else 'models', exist_ok=True)
        if self.model:
            try:
                self.model.save(path)
            except:
                pass
        joblib.dump(self.scaler, path.replace('.h5', '_scaler.pkl'))
        joblib.dump(self.target_scaler, path.replace('.h5', '_target_scaler.pkl'))
    
    def load_model(self, path='models/lstm_model.h5'):
        try:
            from tensorflow.keras.models import load_model
            self.model = load_model(path)
            self.scaler = joblib.load(path.replace('.h5', '_scaler.pkl'))
            self.target_scaler = joblib.load(path.replace('.h5', '_target_scaler.pkl'))
            self.is_trained = True
        except:
            print("Using statistical fallback.")
            self.is_trained = True


class TimeBasedAnalyzer:
    def __init__(self, traffic_df=None):
        self.traffic_df = traffic_df
    
    def get_rush_hour_analysis(self):
        if self.traffic_df is None:
            return self._get_default_rush_hour()
        
        hourly = self.traffic_df.groupby('hour').agg({
            'traffic_index': 'mean',
            'vehicle_count': 'mean',
            'avg_speed_kmh': 'mean'
        }).reset_index()
        
        morning_rush = hourly[(hourly['hour'] >= 7) & (hourly['hour'] <= 9)]
        evening_rush = hourly[(hourly['hour'] >= 17) & (hourly['hour'] <= 20)]
        
        return {
            'morning_rush': {
                'peak_hour': int(morning_rush.loc[morning_rush['traffic_index'].idxmax(), 'hour']) if len(morning_rush) > 0 else 8,
                'avg_traffic_index': float(morning_rush['traffic_index'].mean()) if len(morning_rush) > 0 else 1.5,
                'avg_speed': float(morning_rush['avg_speed_kmh'].mean()) if len(morning_rush) > 0 else 25
            },
            'evening_rush': {
                'peak_hour': int(evening_rush.loc[evening_rush['traffic_index'].idxmax(), 'hour']) if len(evening_rush) > 0 else 18,
                'avg_traffic_index': float(evening_rush['traffic_index'].mean()) if len(evening_rush) > 0 else 1.6,
                'avg_speed': float(evening_rush['avg_speed_kmh'].mean()) if len(evening_rush) > 0 else 22
            },
            'hourly_data': hourly.to_dict('records')
        }
    
    def get_best_time_to_travel(self):
        if self.traffic_df is None:
            return self._get_default_best_times()
        
        hourly = self.traffic_df.groupby('hour')['traffic_index'].mean().reset_index()
        
        best_hours = hourly.nsmallest(3, 'traffic_index')
        worst_hours = hourly.nlargest(3, 'traffic_index')
        
        return {
            'best_times': [{'hour': int(row['hour']), 'traffic_index': float(row['traffic_index'])} 
                          for _, row in best_hours.iterrows()],
            'worst_times': [{'hour': int(row['hour']), 'traffic_index': float(row['traffic_index'])} 
                            for _, row in worst_hours.iterrows()]
        }
    
    def get_day_comparison(self):
        if self.traffic_df is None:
            return self._get_default_day_comparison()
        
        day_stats = self.traffic_df.groupby('day_of_week').agg({
            'traffic_index': 'mean',
            'vehicle_count': 'sum'
        }).reset_index()
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        return {
            'by_day': [{'day': day_names[int(row['day_of_week'])], 
                       'traffic_index': float(row['traffic_index']),
                       'total_vehicles': int(row['vehicle_count'])} 
                      for _, row in day_stats.iterrows()]
        }
    
    def _get_default_rush_hour(self):
        return {
            'morning_rush': {'peak_hour': 8, 'avg_traffic_index': 1.6, 'avg_speed': 28},
            'evening_rush': {'peak_hour': 18, 'avg_traffic_index': 1.8, 'avg_speed': 25},
            'hourly_data': [{'hour': h, 'traffic_index': 1.5 + 0.5 * np.sin((h - 6) * np.pi / 12), 
                           'vehicle_count': 150, 'avg_speed_kmh': 30} for h in range(24)]
        }
    
    def _get_default_best_times(self):
        return {
            'best_times': [{'hour': 3, 'traffic_index': 0.8}, {'hour': 4, 'traffic_index': 0.9}, {'hour': 5, 'traffic_index': 1.0}],
            'worst_times': [{'hour': 8, 'traffic_index': 1.9}, {'hour': 18, 'traffic_index': 2.0}, {'hour': 17, 'traffic_index': 1.8}]
        }
    
    def _get_default_day_comparison(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_traffic = [1.4, 1.5, 1.5, 1.4, 1.6, 1.2, 1.1]
        return {
            'by_day': [{'day': d, 'traffic_index': t, 'total_vehicles': int(10000 * t)} 
                      for d, t in zip(days, weekday_traffic)]
        }


class DTWPatternMatcher:
    def __init__(self):
        self.patterns = []
        self.pattern_labels = []
    
    def compute_dtw_distance(self, series1, series2):
        n, m = len(series1), len(series2)
        dtw_matrix = np.full((n + 1, m + 1), np.inf)
        dtw_matrix[0, 0] = 0
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = abs(series1[i - 1] - series2[j - 1])
                dtw_matrix[i, j] = cost + min(
                    dtw_matrix[i - 1, j],
                    dtw_matrix[i, j - 1],
                    dtw_matrix[i - 1, j - 1]
                )
        
        return dtw_matrix[n, m]
    
    def add_pattern(self, pattern, label):
        normalized = self._normalize_pattern(pattern)
        self.patterns.append(normalized)
        self.pattern_labels.append(label)
    
    def _normalize_pattern(self, pattern):
        return (pattern - np.mean(pattern)) / (np.std(pattern) + 1e-8)
    
    def find_similar(self, query_pattern, top_k=3):
        normalized_query = self._normalize_pattern(query_pattern)
        distances = []
        
        for pattern in self.patterns:
            dist = self.compute_dtw_distance(normalized_query, pattern)
            distances.append(dist)
        
        top_indices = np.argsort(distances)[:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                'label': self.pattern_labels[idx],
                'dtw_distance': float(distances[idx]),
                'similarity_score': float(1 / (1 + distances[idx]))
            })
        
        return results
    
    def analyze_traffic_pattern(self, traffic_series):
        hour_of_day = datetime.now().hour
        
        if 7 <= hour_of_day <= 9:
            expected_pattern = 'morning_peak'
        elif 17 <= hour_of_day <= 20:
            expected_pattern = 'evening_peak'
        elif 22 <= hour_of_day or hour_of_day <= 5:
            expected_pattern = 'night_low'
        else:
            expected_pattern = 'normal'
        
        return {
            'current_pattern': expected_pattern,
            'avg_traffic': float(np.mean(traffic_series)),
            'max_traffic': float(np.max(traffic_series)),
            'min_traffic': float(np.min(traffic_series)),
            'traffic_variance': float(np.var(traffic_series)),
            'trend': 'increasing' if traffic_series[-1] > traffic_series[0] else 'decreasing'
        }


class WeatherImpactAnalyzer:
    def __init__(self):
        self.impact_factors = {
            'clear': {'speed_factor': 1.0, 'demand_factor': 1.0, 'delay_percent': 0},
            'cloudy': {'speed_factor': 0.95, 'demand_factor': 0.98, 'delay_percent': 5},
            'rain': {'speed_factor': 0.75, 'demand_factor': 1.15, 'delay_percent': 25},
            'heavy_rain': {'speed_factor': 0.5, 'demand_factor': 0.7, 'delay_percent': 50}
        }
    
    def analyze_weather_impact(self, weather_data, traffic_data=None):
        if weather_data is None or len(weather_data) == 0:
            return self._default_analysis()
        
        current_weather = weather_data.iloc[-1]['weather_condition']
        factors = self.impact_factors.get(current_weather, self.impact_factors['clear'])
        
        return {
            'current_condition': current_weather,
            'speed_impact': factors['speed_factor'],
            'demand_impact': factors['demand_factor'],
            'delay_percent': factors['delay_percent'],
            'temperature': float(weather_data.iloc[-1]['temperature_c']),
            'humidity': float(weather_data.iloc[-1]['humidity_percent']),
            'visibility': float(weather_data.iloc[-1]['visibility_km']),
            'recommendation': self._get_recommendation(current_weather, factors)
        }
    
    def _get_recommendation(self, condition, factors):
        if condition == 'heavy_rain':
            return "High congestion expected. Consider alternative transport or earlier departure."
        elif condition == 'rain':
            return "Moderate delays possible. Public transport recommended."
        elif condition == 'cloudy':
            return "Normal conditions. Plan for usual traffic patterns."
        else:
            return "Clear conditions. Normal traffic flow expected."
    
    def _default_analysis(self):
        return {
            'current_condition': 'clear',
            'speed_impact': 1.0,
            'demand_impact': 1.0,
            'delay_percent': 0,
            'temperature': 25.0,
            'humidity': 50.0,
            'visibility': 10.0,
            'recommendation': "Normal conditions expected."
        }
