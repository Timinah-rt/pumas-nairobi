# PUMAS Setup Guide

Quick guide to run PUMAS (Predictive Urban Mobility Analytics System) on any computer.

---

## Option 1: Quick Start (5 minutes)

### 1. Install Python
Download Python 3.9+ from https://python.org

### 2. Install Dependencies
Open terminal/command prompt and run:

```bash
cd "path\to\JKUAT_PROJECT"
pip install -r requirements.txt
```

Or install manually:

```bash
pip install streamlit pandas numpy folium plotly requests tensorflow keras
```

### 3. Run the Dashboard

```bash
python -m streamlit run src/dashboard/app.py --server.port 8510
```

Open browser to: **http://localhost:8510**

---

## Option 2: Anaconda Setup (Recommended)

### 1. Install Anaconda
Download from https://www.anaconda.com/download

### 2. Create Environment
```bash
conda create -n JRBAN_MOBILITY python=3.9
conda activate JRBAN_MOBILITY
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Dashboard
```bash
python -m streamlit run src/dashboard/app.py --server.port 8510
```

---

## Optional: API Keys (for real data)

### OpenWeatherMap (for weather data)
1. Go to https://openweathermap.org/api
2. Sign up (free)
3. Copy your API key
4. Edit `src/data/weather_api.py` and add your key

### OpenRouteService (for routing)
1. Go to https://openrouteservice.org/dev/#/signup
2. Sign up (free)
3. Copy your API token
4. Edit `src/data/routing_api.py` and add your token

**Without API keys**, the dashboard uses simulated data and works fine.

---

## Troubleshooting

### "Module not found" error
```bash
pip install <module_name>
```

### Port already in use
Try a different port:
```bash
python -m streamlit run src/dashboard/app.py --server.port 8502
```

### Permission error (Linux/Mac)
```bash
sudo pip install -r requirements.txt
```

---

## Files Overview

| File | Purpose |
|------|---------|
| `src/dashboard/app.py` | Main dashboard |
| `src/data/` | Data processing |
| `src/ml/models.py` | ML models |
| `data/processed/` | Sample data |

---

## Need Help?

Check `README.md` for full documentation.
