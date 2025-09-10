import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Step 1: Load the preprocessed data
try:
    df = pd.read_csv('processed_logistics_data.csv')
except FileNotFoundError:
    print("Error: 'processed_logistics_data.csv' not found. Please run data_preprocessing.py first.")
    exit()

# Step 2: Define features (X) and target (y)
X = df[['distance_km', 'load_weight_kg']]
y = df['base_carbon_kg']

# Step 3: Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Step 4: Initialize and train the model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Step 5: Save the model
joblib.dump(model, 'base_carbon_model.pkl')
print("\nBase Carbon Model training complete and saved as 'base_carbon_model.pkl'!")

# Step 6: Evaluate the model
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"\nModel Performance Metrics:")
print(f"Mean Absolute Error (MAE): {mae:.2f} kg")
print(f"R-squared Score (R2): {r2:.2f}")