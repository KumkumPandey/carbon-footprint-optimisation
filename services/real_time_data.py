"""
Real-time Data Service for live GPS, weather, and traffic data integration
"""
import requests
import json
from datetime import datetime
import os
from typing import Dict, Any, Optional

class RealTimeDataService:
    """Service for fetching real-time data from various APIs"""
    
    def __init__(self):
        # API Keys (should be in environment variables)
        self.weather_api_key = os.getenv('OPENWEATHER_API_KEY', 'demo_key')
        self.traffic_api_key = os.getenv('GOOGLE_MAPS_API_KEY', 'demo_key')
        self.air_quality_api_key = os.getenv('AIR_QUALITY_API_KEY', 'demo_key')
    
    @staticmethod
    def get_weather_data(lat: float, lng: float) -> Dict[str, Any]:
        """Fetch real-time weather data"""
        try:
            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key or api_key == 'demo_key':
                return RealTimeDataService._simulate_weather_data()
            
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': lat,
                'lon': lng,
                'appid': api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'condition': data['weather'][0]['main'],
                    'temperature': data['main']['temp'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind']['speed'],
                    'visibility': data.get('visibility', 10000) / 1000,  # Convert to km
                    'description': data['weather'][0]['description'],
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Weather API error: {e}")
        
        return RealTimeDataService._simulate_weather_data()
    
    @staticmethod
    def get_traffic_data(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> Dict[str, Any]:
        """Fetch real-time traffic data"""
        try:
            api_key = os.getenv('GOOGLE_MAPS_API_KEY')
            if not api_key or api_key == 'demo_key':
                return RealTimeDataService._simulate_traffic_data()
            
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                'origin': f"{start_lat},{start_lng}",
                'destination': f"{end_lat},{end_lng}",
                'departure_time': 'now',
                'traffic_model': 'best_guess',
                'key': api_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK' and data['routes']:
                    route = data['routes'][0]['legs'][0]
                    duration = route['duration']['value']
                    duration_in_traffic = route.get('duration_in_traffic', {}).get('value', duration)
                    
                    # Calculate traffic level based on delay
                    delay_ratio = duration_in_traffic / duration
                    if delay_ratio < 1.2:
                        level = 'Low'
                    elif delay_ratio < 1.5:
                        level = 'Medium'
                    else:
                        level = 'High'
                    
                    return {
                        'level': level,
                        'duration': duration,
                        'duration_in_traffic': duration_in_traffic,
                        'delay_minutes': (duration_in_traffic - duration) / 60,
                        'distance_meters': route['distance']['value'],
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            print(f"Traffic API error: {e}")
        
        return RealTimeDataService._simulate_traffic_data()
    
    @staticmethod
    def get_air_quality_data(lat: float, lng: float) -> Dict[str, Any]:
        """Fetch real-time air quality data"""
        try:
            api_key = os.getenv('AIR_QUALITY_API_KEY')
            if not api_key or api_key == 'demo_key':
                return RealTimeDataService._simulate_air_quality_data()
            
            # Using OpenWeatherMap Air Pollution API
            url = f"http://api.openweathermap.org/data/2.5/air_pollution"
            params = {
                'lat': lat,
                'lon': lng,
                'appid': os.getenv('OPENWEATHER_API_KEY', 'demo_key')
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                components = data['list'][0]['components']
                aqi = data['list'][0]['main']['aqi']
                
                return {
                    'aqi': aqi,
                    'co': components.get('co', 0),
                    'no2': components.get('no2', 0),
                    'pm2_5': components.get('pm2_5', 0),
                    'pm10': components.get('pm10', 0),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            print(f"Air Quality API error: {e}")
        
        return RealTimeDataService._simulate_air_quality_data()
    
    @staticmethod
    def get_live_gps_data(vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Fetch live GPS data from vehicle tracking system"""
        try:
            # This would integrate with actual GPS tracking hardware/service
            # For now, simulate GPS data
            import random
            
            # Simulate GPS coordinates around major Indian cities
            cities = [
                {'name': 'Delhi', 'lat': 28.7041, 'lng': 77.1025},
                {'name': 'Mumbai', 'lat': 19.0760, 'lng': 72.8777},
                {'name': 'Bangalore', 'lat': 12.9716, 'lng': 77.5946}
            ]
            
            city = random.choice(cities)
            
            return {
                'vehicle_id': vehicle_id,
                'latitude': city['lat'] + random.uniform(-0.1, 0.1),
                'longitude': city['lng'] + random.uniform(-0.1, 0.1),
                'speed': random.randint(40, 80),
                'heading': random.randint(0, 360),
                'altitude': random.randint(100, 500),
                'accuracy': random.randint(3, 10),
                'timestamp': datetime.now().isoformat(),
                'status': random.choice(['moving', 'stopped', 'idle'])
            }
        except Exception as e:
            print(f"GPS data error: {e}")
            return None
    
    @staticmethod
    def _simulate_weather_data() -> Dict[str, Any]:
        """Fallback simulated weather data"""
        import random
        conditions = ['Clear', 'Cloudy', 'Rainy', 'Foggy']
        return {
            'condition': random.choice(conditions),
            'temperature': random.randint(20, 35),
            'humidity': random.randint(40, 80),
            'wind_speed': random.randint(5, 20),
            'visibility': random.randint(5, 10),
            'description': 'Simulated weather data',
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def _simulate_traffic_data() -> Dict[str, Any]:
        """Fallback simulated traffic data"""
        import random
        levels = ['Low', 'Medium', 'High']
        level = random.choice(levels)
        base_duration = 3600  # 1 hour base
        multipliers = {'Low': 1.0, 'Medium': 1.3, 'High': 1.8}
        
        return {
            'level': level,
            'duration': base_duration,
            'duration_in_traffic': int(base_duration * multipliers[level]),
            'delay_minutes': (base_duration * multipliers[level] - base_duration) / 60,
            'distance_meters': 50000,
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def _simulate_air_quality_data() -> Dict[str, Any]:
        """Fallback simulated air quality data"""
        import random
        return {
            'aqi': random.randint(1, 5),
            'co': random.randint(100, 500),
            'no2': random.randint(20, 100),
            'pm2_5': random.randint(10, 50),
            'pm10': random.randint(20, 100),
            'timestamp': datetime.now().isoformat()
        }

class VehicleSensorData:
    """Service for collecting real-time vehicle sensor data"""
    
    @staticmethod
    def get_engine_data(vehicle_id: str) -> Dict[str, Any]:
        """Get real-time engine sensor data"""
        import random
        
        # Simulate OBD-II data
        return {
            'vehicle_id': vehicle_id,
            'engine_temp': random.randint(80, 110),  # Celsius
            'rpm': random.randint(800, 3000),
            'speed': random.randint(0, 100),  # km/h
            'fuel_level': random.randint(10, 100),  # percentage
            'oil_pressure': random.randint(20, 80),  # psi
            'battery_voltage': round(random.uniform(12.0, 14.5), 1),
            'coolant_temp': random.randint(70, 100),
            'intake_air_temp': random.randint(20, 60),
            'throttle_position': random.randint(0, 100),
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def get_maintenance_indicators(vehicle_id: str) -> Dict[str, Any]:
        """Get maintenance-related sensor data"""
        import random
        
        return {
            'vehicle_id': vehicle_id,
            'brake_pad_wear': random.randint(20, 100),  # percentage remaining
            'tire_pressure': {
                'front_left': round(random.uniform(28, 35), 1),
                'front_right': round(random.uniform(28, 35), 1),
                'rear_left': round(random.uniform(28, 35), 1),
                'rear_right': round(random.uniform(28, 35), 1)
            },
            'oil_life': random.randint(10, 100),  # percentage remaining
            'air_filter_condition': random.choice(['Good', 'Fair', 'Replace']),
            'belt_condition': random.choice(['Good', 'Worn', 'Replace']),
            'last_service_km': random.randint(5000, 15000),
            'next_service_km': random.randint(1000, 5000),
            'timestamp': datetime.now().isoformat()
        }