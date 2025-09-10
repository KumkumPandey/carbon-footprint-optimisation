import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from geopy.distance import geodesic
import joblib
from sklearn.preprocessing import MinMaxScaler

# Step 1: Create a database file from the CSV data
# Note: Ensure you have a 'logistics_data.csv' file in the same directory
try:
    df_raw = pd.read_csv('logistics_data.csv')
    engine = create_engine('sqlite:///logistics.db')
    df_raw.to_sql('routes', engine, if_exists='replace', index=False)
    print("Raw data loaded into logistics.db")
except FileNotFoundError:
    print("Error: 'logistics_data.csv' not found. Please create it.")
    exit()

# Step 2: Load the data from the database
df = pd.read_sql_table('routes', engine)

# Step 3: Define city coordinates and calculate distance
city_coords = {
    "New Delhi": (28.7041, 77.1025), "Mumbai": (19.0760, 72.8777),
    "Bangalore": (12.9716, 77.5946), "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867), "Pune": (18.5204, 73.8567),
    "Kolkata": (22.5726, 88.3639)
}

def calculate_distance(row):
    start_point = city_coords[row['start_location']]
    end_point = city_coords[row['end_location']]
    return geodesic(start_point, end_point).km

df['distance_km'] = df.apply(calculate_distance, axis=1)

# Step 4: Create a proxy for base carbon footprint
df['base_carbon_kg'] = df['distance_km'] * 0.2 + df['load_weight_kg'] * 0.01

# Step 5: Save the preprocessed data
df.to_csv('processed_logistics_data.csv', index=False)
print("Data preprocessing complete. Saved to 'processed_logistics_data.csv'")