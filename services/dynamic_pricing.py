import math
from datetime import datetime, timedelta
from geopy.distance import geodesic

class DynamicPricingService:
    
    def __init__(self):
        self.base_rates = {
            'fuel_cost_per_km': 8.5,  # INR per km
            'driver_cost_per_hour': 150,  # INR per hour
            'vehicle_overhead_per_km': 3.2,  # INR per km
            'profit_margin': 0.25,  # 25%
            'gst_rate': 0.18  # 18% GST
        }
        
        self.surge_multipliers = {
            'peak_hours': 1.3,
            'weekend': 1.2,
            'monsoon': 1.15,
            'festival_season': 1.4,
            'urgent_delivery': 1.5
        }
    
    def generate_quote(self, origin, destination, load_weight, urgency='normal', pickup_date=None):
        """Generate dynamic pricing quote"""
        
        # Calculate base costs
        distance_km = self._calculate_distance(origin, destination)
        estimated_time_hours = distance_km / 50  # Assuming 50 km/h average speed
        
        # Base costs
        fuel_cost = distance_km * self.base_rates['fuel_cost_per_km']
        driver_cost = estimated_time_hours * self.base_rates['driver_cost_per_hour']
        overhead_cost = distance_km * self.base_rates['vehicle_overhead_per_km']
        
        # Load weight factor
        load_factor = 1 + (load_weight / 10000)  # Additional cost for heavy loads
        
        # Calculate surge multipliers
        surge_multiplier = self._calculate_surge_multiplier(urgency, pickup_date)
        
        # Total base cost
        base_total = (fuel_cost + driver_cost + overhead_cost) * load_factor
        
        # Apply surge and profit margin
        cost_with_surge = base_total * surge_multiplier
        cost_with_profit = cost_with_surge * (1 + self.base_rates['profit_margin'])
        
        # Add GST
        final_cost = cost_with_profit * (1 + self.base_rates['gst_rate'])
        
        return {
            'quote_id': f'QT-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'origin': origin,
            'destination': destination,
            'distance_km': round(distance_km, 2),
            'estimated_time_hours': round(estimated_time_hours, 2),
            'load_weight_kg': load_weight,
            'urgency': urgency,
            'cost_breakdown': {
                'fuel_cost': round(fuel_cost, 2),
                'driver_cost': round(driver_cost, 2),
                'overhead_cost': round(overhead_cost, 2),
                'load_factor': round(load_factor, 2),
                'surge_multiplier': round(surge_multiplier, 2),
                'base_total': round(base_total, 2),
                'profit_margin': round(cost_with_profit - cost_with_surge, 2),
                'gst_amount': round(final_cost - cost_with_profit, 2)
            },
            'pricing': {
                'base_price': round(base_total, 2),
                'surge_price': round(cost_with_surge, 2),
                'price_before_tax': round(cost_with_profit, 2),
                'gst_amount': round(final_cost - cost_with_profit, 2),
                'final_price': round(final_cost, 2)
            },
            'validity': {
                'valid_until': (datetime.now() + timedelta(hours=24)).isoformat(),
                'terms': 'Price valid for 24 hours. Subject to fuel price changes.'
            },
            'estimated_delivery': self._calculate_delivery_time(estimated_time_hours, urgency)
        }
    
    def get_price_comparison(self, origin, destination, load_weight):
        """Get price comparison for different urgency levels"""
        
        urgency_levels = ['normal', 'express', 'urgent']
        comparisons = []
        
        for urgency in urgency_levels:
            quote = self.generate_quote(origin, destination, load_weight, urgency)
            comparisons.append({
                'urgency': urgency,
                'price': quote['pricing']['final_price'],
                'delivery_time': quote['estimated_delivery'],
                'savings': 0 if urgency == 'urgent' else quote['pricing']['final_price'] - self.generate_quote(origin, destination, load_weight, 'urgent')['pricing']['final_price']
            })
        
        return {
            'comparison': comparisons,
            'recommended': min(comparisons, key=lambda x: x['price'] if x['urgency'] != 'urgent' else float('inf'))
        }
    
    def _calculate_distance(self, origin, destination):
        """Calculate distance between two locations"""
        
        # Simplified coordinate mapping
        coordinates = {
            'Delhi': (28.7041, 77.1025),
            'Mumbai': (19.0760, 72.8777),
            'Bangalore': (12.9716, 77.5946),
            'Chennai': (13.0827, 80.2707),
            'Hyderabad': (17.3850, 78.4867),
            'Pune': (18.5204, 73.8567),
            'Kolkata': (22.5726, 88.3639)
        }
        
        origin_coords = coordinates.get(origin, (28.7041, 77.1025))
        dest_coords = coordinates.get(destination, (19.0760, 72.8777))
        
        return geodesic(origin_coords, dest_coords).kilometers
    
    def _calculate_surge_multiplier(self, urgency, pickup_date):
        """Calculate surge pricing multiplier"""
        
        multiplier = 1.0
        
        # Urgency multiplier
        if urgency == 'express':
            multiplier *= 1.2
        elif urgency == 'urgent':
            multiplier *= self.surge_multipliers['urgent_delivery']
        
        # Time-based multipliers
        if pickup_date:
            pickup_dt = datetime.fromisoformat(pickup_date) if isinstance(pickup_date, str) else pickup_date
            
            # Peak hours (8-10 AM, 6-8 PM)
            if pickup_dt.hour in [8, 9, 18, 19]:
                multiplier *= self.surge_multipliers['peak_hours']
            
            # Weekend
            if pickup_dt.weekday() >= 5:
                multiplier *= self.surge_multipliers['weekend']
            
            # Monsoon season (June-September)
            if pickup_dt.month in [6, 7, 8, 9]:
                multiplier *= self.surge_multipliers['monsoon']
        
        return multiplier
    
    def _calculate_delivery_time(self, base_hours, urgency):
        """Calculate estimated delivery time"""
        
        multipliers = {
            'normal': 1.0,
            'express': 0.8,
            'urgent': 0.6
        }
        
        adjusted_hours = base_hours * multipliers.get(urgency, 1.0)
        delivery_time = datetime.now() + timedelta(hours=adjusted_hours)
        
        return delivery_time.strftime('%Y-%m-%d %H:%M')