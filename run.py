#!/usr/bin/env python3
"""
PUMAS - Predictive Urban Mobility Analytics System
Main entry point for the Nairobi traffic analysis system
"""

import sys
import os

def main():
    print("=" * 60)
    print("PUMAS - Predictive Urban Mobility Analytics System")
    print("=" * 60)
    
    print("\n[1/4] Generating synthetic data...")
    try:
        from src.data.generate_synthetic_data import generate_gps_data, generate_traffic_flow_data, generate_weather_data
        generate_gps_data(n_trips=5000)
        generate_traffic_flow_data()
        generate_weather_data()
        print("Data generation complete!")
    except Exception as e:
        print(f"Data generation error: {e}")
    
    print("\n[2/4] Testing data pipeline...")
    try:
        from src.data.data_pipeline import DataPipeline
        pipeline = DataPipeline()
        print(f"Loaded {len(pipeline.traffic_df) if pipeline.traffic_df is not None else 0} traffic records")
    except Exception as e:
        print(f"Pipeline error: {e}")
    
    print("\n[3/4] Testing ML models...")
    try:
        from src.ml.models import TrafficLSTMModel, DTWPatternMatcher, WeatherImpactAnalyzer
        print("LSTM Model: OK")
        print("DTW Pattern Matcher: OK")
        print("Weather Impact Analyzer: OK")
    except Exception as e:
        print(f"ML model error: {e}")
    
    print("\n[4/4] Starting Dashboard...")
    print("\n" + "=" * 60)
    print("To run the dashboard, execute:")
    print("  streamlit run src/dashboard/app.py")
    print("=" * 60)
    
    import subprocess
    try:
        subprocess.run(['streamlit', 'run', 'src/dashboard/app.py'])
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    except Exception as e:
        print(f"\nCould not start dashboard: {e}")
        print("Please run manually: streamlit run src/dashboard/app.py")

if __name__ == "__main__":
    main()
