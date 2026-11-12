
import requests
import pandas as pd
import clickhouse_connect

# ClickHouse connection
client = clickhouse_connect.get_client(
    host="localhost",
    port=8123,
    username="admin",
    password="Admin123"
)

# Open-Meteo historical API
url = "https://archive-api.open-meteo.com/v1/archive"

params = {
    "latitude": 39.9526,
    "longitude": -75.1652,
    "start_date": "2026-10-12",
    "end_date": "2026-11-10",
    "hourly": ["temperature_2m"],
    
    "timezone": "America/New_York",
    "temperature_unit": "fahrenheit"
}

response = requests.get(url, params=params, timeout=60)
print(response.raise_for_status())

data = response.json()

# Convert API response into DataFrame
hourly_df = pd.DataFrame(data["hourly"])

# Add date, timezone and city to HOURLY dataframe
hourly_df["time"] = pd.to_datetime(
    hourly_df["time"],
    errors="coerce"
)

# Remove invalid datetime records
hourly_df = hourly_df.dropna(subset=["time"])

# Extract date
hourly_df["date"] = hourly_df["time"].dt.date
hourly_df["city"] = "Philadelphia"

# Find minimum and maximum temperature indexes for each date
min_idx = hourly_df.groupby("date")["temperature_2m"].idxmin()
max_idx = hourly_df.groupby("date")["temperature_2m"].idxmax()

# Get daily minimum and maximum temperatures
daily_df = hourly_df.groupby("date").agg(
    min_temperature=("temperature_2m", "min"),
    max_temperature=("temperature_2m", "max")
)

# Get the corresponding times
daily_df["min_temperature_time"] = (
    hourly_df.loc[min_idx].set_index("date")["time"]
)

daily_df["max_temperature_time"] = (
    hourly_df.loc[max_idx].set_index("date")["time"]
)

# Add timezone and city
daily_df["timezone"] = data["timezone"]
daily_df["city"] = "Philadelphia"

# Reset index
df = daily_df.reset_index()

# Convert times to strings for ClickHouse
df["min_temperature_time"] = (
    df["min_temperature_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
)

df["max_temperature_time"] = (
    df["max_temperature_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
)

print(df.head(10))

print("\nDataFrame Information:")
print(df.info())

# Save data into ClickHouse
client.insert_df("weather_db.daily_weather", df)
client.insert_df("weather_db.hourly_daily_weather", hourly_df)

print("\nData saved successfully!")

client.close()
