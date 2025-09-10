import random
from datetime import datetime, timedelta
import json

class AnalyticsService:
    @staticmethod
    def generate_trip_analytics(user_id=None):
        """Generate comprehensive trip analytics"""
        return {
            'total_trips': random.randint(150, 300),
            'total_carbon_saved': round(random.uniform(500, 1200), 1),
            'average_efficiency': random.randint(75, 95),
            'active_alerts': random.randint(0, 5),
            'fuel_efficiency': round(random.uniform(12, 18), 1),
            'on_time_delivery': random.randint(85, 98),
            'cost_savings': round(random.uniform(15000, 45000), 0)
        }
    
    @staticmethod
    def generate_chart_data():
        """Generate chart data for dashboard"""
        # Carbon trend data (last 7 days)
        carbon_data = [round(random.uniform(80, 150), 1) for _ in range(7)]
        
        # Fuel consumption data (last 4 weeks)
        fuel_data = [round(random.uniform(300, 500), 0) for _ in range(4)]
        
        # Weather impact distribution
        weather_impact = {
            'Clear': random.randint(40, 60),
            'Rainy': random.randint(20, 35),
            'Foggy': random.randint(10, 20),
            'Cloudy': random.randint(10, 25)
        }
        
        # Traffic impact distribution
        traffic_impact = {
            'Low': random.randint(45, 65),
            'Medium': random.randint(25, 40),
            'High': random.randint(15, 30)
        }
        
        return {
            'carbon_trend_chart': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'data': carbon_data
            },
            'fuel_consumption_chart': {
                'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                'data': fuel_data
            },
            'weather_impact': weather_impact,
            'traffic_impact': traffic_impact,
            'efficiency_metrics': {
                'fuel_efficiency': random.randint(80, 95),
                'route_optimization': random.randint(75, 90),
                'time_management': random.randint(85, 98),
                'carbon_reduction': random.randint(80, 95),
                'cost_effectiveness': random.randint(70, 85)
            }
        }
    
    @staticmethod
    def get_maintenance_predictions():
        """Get predictive maintenance data"""
        vehicles = ['DL-01-1234', 'MH-02-5678', 'KA-03-9012', 'UP-04-3456']
        
        predictions = []
        for vehicle in vehicles:
            health_score = random.randint(25, 95)
            
            alerts = []
            if health_score < 50:
                alerts.extend(['Engine Oil - Critical', 'Brake Pads - High'])
            elif health_score < 80:
                alerts.append('Tire Pressure - Medium')
            
            predictions.append({
                'vehicle_id': vehicle,
                'health_score': health_score,
                'alerts': alerts,
                'next_service_km': random.randint(200, 2000),
                'estimated_cost': random.randint(2000, 15000)
            })
        
        return predictions
    
    @staticmethod
    def generate_performance_report():
        """Generate detailed performance report"""
        return {
            'fleet_utilization': random.randint(80, 95),
            'average_speed': round(random.uniform(45, 65), 1),
            'idle_time_percentage': random.randint(5, 15),
            'route_deviation': random.randint(2, 8),
            'customer_satisfaction': random.randint(85, 98),
            'driver_performance': {
                'excellent': random.randint(40, 60),
                'good': random.randint(25, 40),
                'average': random.randint(10, 25),
                'needs_improvement': random.randint(0, 10)
            }
        }