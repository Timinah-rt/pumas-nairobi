# PUMAS - Predictive Urban Mobility Analytics System

**Student:** Rita Timinah (SCT-C002-0028/2022)  
**Supervisor:** Mr. Samwel Adhola  
**Course:** Data Science and Analytics  
**Institution:** Jomo Kenyatta University of Agriculture and Technology (JKUAT)

---

## Overview

PUMAS is a real-time traffic prediction and visualization system for Nairobi, Kenya. It provides traffic analysis, route suggestions, weather-based predictions, and wheelchair-accessible route options for three transport modes: Walking, Matatu, and Driving.

## Features

- **Multi-Mode Transport Analysis** - Compare Walking, Matatu, Driving, and Wheelchair routes
- **Route Suggestions** - Fastest, Cheapest, and Best Value recommendations
- **Fixed Matatu Fares** - 10-30 KES based on distance
- **Weather-Based Predictions** - Real weather data from OpenWeatherMap API
- **Interactive Maps** - Folium-based visualization with congestion heatmaps
- **Animated Routes** - AntPath animation for route visualization
- **Wheelchair Accessible Routes** - Dedicated accessible transport option
- **Time Analysis** - Rush hour, best travel times, day-of-week patterns
- **Cost Analysis** - Monthly cost projections and fare comparisons

## Project Structure

```
JKUAT_PROJECT/
├── data/
│   ├── raw/
│   │   └── TransportData/         # Zenodo TUMI travel times data
│   └── processed/
│       ├── zone_travel_times.csv # Zone-to-zone travel times
│       ├── gps_trips.csv         # GPS trip records
│       ├── traffic_flow.csv      # Traffic flow data
│       └── weather_data.csv      # Weather conditions
├── src/
│   ├── data/
│   │   ├── data_pipeline.py      # Data loading and processing
│   │   ├── cost_calculator.py    # Fare calculations & route suggestions
│   │   ├── weather_api.py        # OpenWeatherMap integration
│   │   ├── routing_api.py        # OpenRouteService integration
│   │   ├── zenodo_processor.py   # Zenodo data parser
│   │   └── generate_synthetic_data.py  # Synthetic data generator
│   ├── ml/
│   │   └── models.py             # LSTM, DTW, TimeBasedAnalyzer models
│   └── dashboard/
│       └── app.py                # Streamlit dashboard
├── models/                        # Trained ML models (empty)
├── notebooks/                     # Jupyter notebooks
├── .streamlit/
│   └── config.toml               # Streamlit configuration
├── requirements.txt
├── run.py                        # Main entry point
└── README.md
```

## Installation

### Prerequisites
- Python 3.9+
- Anaconda (recommended)

### Setup

```bash
# Clone or download the project
cd "JKUAT_PROJECT"

# Create conda environment
conda create -n JRBAN_MOBILITY python=3.9
conda activate JRBAN_MOBILITY

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
python -m streamlit run src/dashboard/app.py --server.port 8510
```

Or use the main runner:

```bash
python run.py
```

## Usage

### Dashboard Tabs

1. **Trip Planner** - Plan trips with origin/destination selection
2. **Zone Details** - Detailed metrics for specific zones
3. **Time Analysis** - Rush hour, best travel times, day-of-week analysis
4. **Cost Analysis** - Monthly costs, fare comparisons
5. **All Zones Map** - Interactive map with all zones and congestion overlay

### Features

- Select origin and destination zones
- Toggle congestion heatmap visibility
- Include/exclude wheelchair accessible routes
- View traffic predictions
- See weather impact on travel

## Data Sources

- **Travel Times by Transport Mode** - Zenodo (TUMI Nairobi travel times)
- **Weather Data** - OpenWeatherMap API (real-time)
- **Synthetic Zone Data** - Generated travel times for 10 Nairobi zones

## Transport Modes & Fares

| Mode | Fare Range | Features |
|------|------------|----------|
| Walking | Free | Free & Healthy |
| Matatu | 10-30 KES | Most Popular, Fixed rates |
| Driving | Fuel cost | Fastest Option |
| Wheelchair | 50 KES | Accessible Route |

## Technologies

- **Python 3.9+** - Core language
- **Streamlit** - Dashboard framework
- **Folium** - Interactive maps
- **Plotly** - Charts and visualizations
- **TensorFlow/Keras** - LSTM neural networks
- **Pandas/NumPy** - Data processing
- **OpenWeatherMap API** - Real weather data
- **OpenRouteService API** - Routing services

## Deployment

### Local Deployment

```bash
conda activate JRBAN_MOBILITY
python -m streamlit run src/dashboard/app.py --server.port 8510
```

### Streamlit Cloud (Free)

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Deploy!

## Contributing

This is a JKUAT Data Science project.

- **Student:** Rita Timinah
- **Supervisor:** Mr. Samwel Adhola

## License

MIT License

## Acknowledgments

- TUMI (Transport Union Mobility Initiative) for travel time data
- Digital Transport for Africa for GTFS Nairobi data
- JKUAT Department of Data Science and Analytics
