import torch
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
import requests
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self):
        self.weather_scaler = StandardScaler()
        self.traffic_scaler = StandardScaler()
    
    def collect_real_time_data(self):
        """Collect real-time data from APIs"""
        try:
            weather_data = self._fetch_weather_data()
            traffic_data = self._fetch_traffic_data()
            
            logger.info(f"Collected {len(weather_data)} weather records, {len(traffic_data)} traffic records")
            return weather_data, traffic_data
            
        except Exception as e:
            logger.error(f"Error collecting real-time data: {e}")
            return [], []
    
    def _fetch_weather_data(self):
        """Fetch weather data from OpenWeatherMap API"""
        cities = [
            {'name': 'Delhi', 'lat': 28.7041, 'lon': 77.1025},
            {'name': 'Mumbai', 'lat': 19.0760, 'lon': 72.8777},
            {'name': 'Bangalore', 'lat': 12.9716, 'lon': 77.5946}
        ]
        
        weather_data = []
        for city in cities:
            try:
                # Simulate API call (replace with actual API)
                data = {
                    'city': city['name'],
                    'temperature': np.random.normal(25, 5),
                    'humidity': np.random.normal(60, 15),
                    'pressure': np.random.normal(1013, 10),
                    'wind_speed': np.random.normal(10, 3),
                    'timestamp': datetime.now()
                }
                weather_data.append(data)
            except Exception as e:
                logger.error(f"Error fetching weather for {city['name']}: {e}")
        
        return weather_data
    
    def _fetch_traffic_data(self):
        """Fetch traffic data from Google Maps API"""
        routes = [
            {'origin': 'Delhi', 'destination': 'Mumbai'},
            {'origin': 'Mumbai', 'destination': 'Pune'},
            {'origin': 'Bangalore', 'destination': 'Chennai'}
        ]
        
        traffic_data = []
        for route in routes:
            try:
                # Simulate API call (replace with actual API)
                data = {
                    'route': f"{route['origin']}-{route['destination']}",
                    'duration': np.random.normal(480, 60),  # minutes
                    'duration_in_traffic': np.random.normal(540, 90),
                    'congestion_level': np.random.choice(['low', 'medium', 'high']),
                    'timestamp': datetime.now()
                }
                traffic_data.append(data)
            except Exception as e:
                logger.error(f"Error fetching traffic for {route}: {e}")
        
        return traffic_data
    
    def retrain_pytorch_models(self, weather_data, traffic_data):
        """Retrain PyTorch LSTM models with new data"""
        try:
            logger.info("Starting PyTorch model retraining...")
            
            # Prepare weather data
            if weather_data:
                weather_df = pd.DataFrame(weather_data)
                weather_features = weather_df[['temperature', 'humidity', 'pressure', 'wind_speed']].values
                weather_scaled = self.weather_scaler.fit_transform(weather_features)
                
                # Retrain weather LSTM (simplified)
                self._retrain_weather_lstm(weather_scaled)
            
            # Prepare traffic data
            if traffic_data:
                traffic_df = pd.DataFrame(traffic_data)
                traffic_features = traffic_df[['duration', 'duration_in_traffic']].values
                traffic_scaled = self.traffic_scaler.fit_transform(traffic_features)
                
                # Retrain traffic LSTM (simplified)
                self._retrain_traffic_lstm(traffic_scaled)
            
            # Save updated scalers
            joblib.dump(self.weather_scaler, 'scaler_weather.pkl')
            joblib.dump(self.traffic_scaler, 'scaler_traffic.pkl')
            
            logger.info("PyTorch model retraining completed successfully")
            
        except Exception as e:
            logger.error(f"Error retraining PyTorch models: {e}")
            raise
    
    def _retrain_weather_lstm(self, data):
        """Retrain weather LSTM model"""
        try:
            from pytorch_forecaster import LSTMForecaster
            
            model = LSTMForecaster()
            
            # Convert to tensor
            X = torch.FloatTensor(data)
            
            # Simple training loop (in production, use proper training)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            criterion = torch.nn.MSELoss()
            
            for epoch in range(10):  # Minimal training
                optimizer.zero_grad()
                output = model(X.unsqueeze(0))
                loss = criterion(output, X.unsqueeze(0))
                loss.backward()
                optimizer.step()
            
            # Save model
            torch.save(model.state_dict(), 'weather_lstm.pth')
            logger.info("Weather LSTM model retrained and saved")
            
        except Exception as e:
            logger.error(f"Error retraining weather LSTM: {e}")
    
    def _retrain_traffic_lstm(self, data):
        """Retrain traffic LSTM model"""
        try:
            from pytorch_forecaster import LSTMForecaster
            
            model = LSTMForecaster()
            
            # Convert to tensor
            X = torch.FloatTensor(data)
            
            # Simple training loop
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            criterion = torch.nn.MSELoss()
            
            for epoch in range(10):
                optimizer.zero_grad()
                output = model(X.unsqueeze(0))
                loss = criterion(output, X.unsqueeze(0))
                loss.backward()
                optimizer.step()
            
            # Save model
            torch.save(model.state_dict(), 'traffic_lstm.pth')
            logger.info("Traffic LSTM model retrained and saved")
            
        except Exception as e:
            logger.error(f"Error retraining traffic LSTM: {e}")
    
    def retrain_tensorflow_models(self, weather_data, traffic_data):
        """Retrain TensorFlow models with new data"""
        try:
            import tensorflow as tf
            
            logger.info("Starting TensorFlow model retraining...")
            
            if weather_data and traffic_data:
                # Prepare combined data for road condition classifier
                combined_data = self._prepare_road_condition_data(weather_data, traffic_data)
                
                # Retrain road condition classifier
                self._retrain_road_classifier(combined_data)
            
            logger.info("TensorFlow model retraining completed successfully")
            
        except Exception as e:
            logger.error(f"Error retraining TensorFlow models: {e}")
            raise
    
    def _prepare_road_condition_data(self, weather_data, traffic_data):
        """Prepare data for road condition classification"""
        combined_data = []
        
        for weather, traffic in zip(weather_data, traffic_data):
            features = [
                weather['temperature'],
                weather['humidity'],
                weather['wind_speed'],
                traffic['duration_in_traffic'] / traffic['duration']  # congestion ratio
            ]
            
            # Simple rule-based labeling (in production, use real labels)
            if weather['humidity'] > 80 or weather['wind_speed'] > 15:
                label = 2  # Poor conditions
            elif traffic['duration_in_traffic'] / traffic['duration'] > 1.3:
                label = 1  # Moderate conditions
            else:
                label = 0  # Good conditions
            
            combined_data.append({'features': features, 'label': label})
        
        return combined_data
    
    def _retrain_road_classifier(self, data):
        """Retrain road condition classifier"""
        try:
            import tensorflow as tf
            
            if not data:
                return
            
            # Prepare data
            X = np.array([item['features'] for item in data])
            y = np.array([item['label'] for item in data])
            
            # Convert to categorical
            y_categorical = tf.keras.utils.to_categorical(y, num_classes=3)
            
            # Load existing model or create new one
            try:
                model = tf.keras.models.load_model('road_condition_classifier.h5')
            except:
                model = tf.keras.Sequential([
                    tf.keras.layers.Dense(64, activation='relu', input_shape=(4,)),
                    tf.keras.layers.Dense(32, activation='relu'),
                    tf.keras.layers.Dense(3, activation='softmax')
                ])
                model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
            
            # Retrain model
            model.fit(X, y_categorical, epochs=10, verbose=0)
            
            # Save model
            model.save('road_condition_classifier.h5')
            logger.info("Road condition classifier retrained and saved")
            
        except Exception as e:
            logger.error(f"Error retraining road classifier: {e}")