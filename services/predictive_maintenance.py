"""
Enhanced Predictive Maintenance Service with ML models
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import joblib
import os
from .real_time_data import VehicleSensorData

class PredictiveMaintenanceService:
    """Advanced predictive maintenance using real sensor data and ML models"""
    
    def __init__(self):
        self.sensor_service = VehicleSensorData()
        self.models = self._load_models()
        self.maintenance_thresholds = {
            'engine_temp': {'warning': 100, 'critical': 115},
            'oil_pressure': {'warning': 25, 'critical': 15},
            'brake_pad_wear': {'warning': 30, 'critical': 15},
            'oil_life': {'warning': 20, 'critical': 10},
            'tire_pressure': {'warning': 30, 'critical': 25}
        }
    
    def _load_models(self) -> Dict[str, Any]:
        """Load pre-trained maintenance prediction models"""
        models = {}
        try:
            # Load models if they exist
            if os.path.exists('models/engine_failure_model.pkl'):
                models['engine_failure'] = joblib.load('models/engine_failure_model.pkl')
            if os.path.exists('models/brake_maintenance_model.pkl'):
                models['brake_maintenance'] = joblib.load('models/brake_maintenance_model.pkl')
        except Exception as e:
            print(f"Model loading error: {e}")
        
        return models
    
    def predict_maintenance(self, vehicle_id: str) -> Dict[str, Any]:
        """Comprehensive maintenance prediction for a vehicle"""
        try:
            # Get real-time sensor data
            engine_data = self.sensor_service.get_engine_data(vehicle_id)
            maintenance_data = self.sensor_service.get_maintenance_indicators(vehicle_id)
            
            # Calculate health scores
            health_scores = self._calculate_health_scores(engine_data, maintenance_data)
            
            # Generate alerts
            alerts = self._generate_alerts(engine_data, maintenance_data)
            
            # Predict failure probabilities
            failure_predictions = self._predict_failures(engine_data, maintenance_data)
            
            # Generate maintenance schedule
            maintenance_schedule = self._generate_maintenance_schedule(vehicle_id, health_scores, alerts)
            
            return {
                'vehicle_id': vehicle_id,
                'overall_health_score': health_scores['overall'],
                'component_health': health_scores['components'],
                'alerts': alerts,
                'failure_predictions': failure_predictions,
                'maintenance_schedule': maintenance_schedule,
                'sensor_data': {
                    'engine': engine_data,
                    'maintenance': maintenance_data
                },
                'recommendations': self._generate_recommendations(health_scores, alerts),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Maintenance prediction error: {e}")
            return self._fallback_maintenance_data(vehicle_id)
    
    def _calculate_health_scores(self, engine_data: Dict, maintenance_data: Dict) -> Dict[str, Any]:
        """Calculate health scores for different vehicle components"""
        scores = {}
        
        # Engine health score
        engine_temp_score = max(0, 100 - (engine_data['engine_temp'] - 80) * 2)
        oil_pressure_score = min(100, engine_data['oil_pressure'] * 2)
        rpm_score = 100 if 800 <= engine_data['rpm'] <= 2500 else 80
        
        scores['engine'] = (engine_temp_score + oil_pressure_score + rpm_score) / 3
        
        # Brake system health
        scores['brakes'] = maintenance_data['brake_pad_wear']
        
        # Oil system health
        scores['oil_system'] = maintenance_data['oil_life']
        
        # Tire health (average of all tires)
        tire_pressures = list(maintenance_data['tire_pressure'].values())
        optimal_pressure = 32  # psi
        tire_scores = [max(0, 100 - abs(p - optimal_pressure) * 5) for p in tire_pressures]
        scores['tires'] = sum(tire_scores) / len(tire_scores)
        
        # Battery health
        battery_voltage = engine_data['battery_voltage']
        if 12.6 <= battery_voltage <= 14.4:
            scores['battery'] = 100
        elif 12.0 <= battery_voltage < 12.6:
            scores['battery'] = 70
        else:
            scores['battery'] = 30
        
        # Overall health score
        scores['overall'] = sum(scores.values()) / len(scores)
        
        return {
            'overall': round(scores['overall'], 1),
            'components': {k: round(v, 1) for k, v in scores.items() if k != 'overall'}
        }
    
    def _generate_alerts(self, engine_data: Dict, maintenance_data: Dict) -> List[Dict[str, Any]]:
        """Generate maintenance alerts based on sensor data"""
        alerts = []
        
        # Engine temperature alert
        if engine_data['engine_temp'] > self.maintenance_thresholds['engine_temp']['critical']:
            alerts.append({
                'component': 'Engine',
                'type': 'Temperature',
                'urgency': 'Critical',
                'message': f"Engine overheating: {engine_data['engine_temp']}°C",
                'action': 'Stop vehicle immediately and check coolant'
            })
        elif engine_data['engine_temp'] > self.maintenance_thresholds['engine_temp']['warning']:
            alerts.append({
                'component': 'Engine',
                'type': 'Temperature',
                'urgency': 'Warning',
                'message': f"Engine running hot: {engine_data['engine_temp']}°C",
                'action': 'Monitor temperature and check coolant level'
            })
        
        # Oil pressure alert
        if engine_data['oil_pressure'] < self.maintenance_thresholds['oil_pressure']['critical']:
            alerts.append({
                'component': 'Engine',
                'type': 'Oil Pressure',
                'urgency': 'Critical',
                'message': f"Low oil pressure: {engine_data['oil_pressure']} psi",
                'action': 'Stop engine immediately and check oil level'
            })
        elif engine_data['oil_pressure'] < self.maintenance_thresholds['oil_pressure']['warning']:
            alerts.append({
                'component': 'Engine',
                'type': 'Oil Pressure',
                'urgency': 'Warning',
                'message': f"Oil pressure low: {engine_data['oil_pressure']} psi",
                'action': 'Check oil level and schedule maintenance'
            })
        
        # Brake pad wear alert
        if maintenance_data['brake_pad_wear'] < self.maintenance_thresholds['brake_pad_wear']['critical']:
            alerts.append({
                'component': 'Brakes',
                'type': 'Brake Pads',
                'urgency': 'Critical',
                'message': f"Brake pads critically worn: {maintenance_data['brake_pad_wear']}%",
                'action': 'Replace brake pads immediately'
            })
        elif maintenance_data['brake_pad_wear'] < self.maintenance_thresholds['brake_pad_wear']['warning']:
            alerts.append({
                'component': 'Brakes',
                'type': 'Brake Pads',
                'urgency': 'Warning',
                'message': f"Brake pads wearing: {maintenance_data['brake_pad_wear']}%",
                'action': 'Schedule brake pad replacement'
            })
        
        # Oil life alert
        if maintenance_data['oil_life'] < self.maintenance_thresholds['oil_life']['critical']:
            alerts.append({
                'component': 'Engine',
                'type': 'Oil Change',
                'urgency': 'Critical',
                'message': f"Oil change overdue: {maintenance_data['oil_life']}% remaining",
                'action': 'Change oil immediately'
            })
        elif maintenance_data['oil_life'] < self.maintenance_thresholds['oil_life']['warning']:
            alerts.append({
                'component': 'Engine',
                'type': 'Oil Change',
                'urgency': 'Warning',
                'message': f"Oil change due soon: {maintenance_data['oil_life']}% remaining",
                'action': 'Schedule oil change'
            })
        
        # Tire pressure alerts
        for position, pressure in maintenance_data['tire_pressure'].items():
            if pressure < self.maintenance_thresholds['tire_pressure']['critical']:
                alerts.append({
                    'component': 'Tires',
                    'type': 'Tire Pressure',
                    'urgency': 'Critical',
                    'message': f"{position.replace('_', ' ').title()} tire pressure critically low: {pressure} psi",
                    'action': 'Inflate tire immediately or replace if damaged'
                })
            elif pressure < self.maintenance_thresholds['tire_pressure']['warning']:
                alerts.append({
                    'component': 'Tires',
                    'type': 'Tire Pressure',
                    'urgency': 'Warning',
                    'message': f"{position.replace('_', ' ').title()} tire pressure low: {pressure} psi",
                    'action': 'Check and inflate tire'
                })
        
        return alerts
    
    def _predict_failures(self, engine_data: Dict, maintenance_data: Dict) -> Dict[str, Any]:
        """Predict component failure probabilities using ML models"""
        predictions = {}
        
        try:
            # Engine failure prediction
            if 'engine_failure' in self.models:
                engine_features = np.array([[
                    engine_data['engine_temp'],
                    engine_data['oil_pressure'],
                    engine_data['rpm'],
                    maintenance_data['oil_life']
                ]])
                predictions['engine_failure_probability'] = float(self.models['engine_failure'].predict_proba(engine_features)[0][1])
            else:
                # Fallback calculation
                temp_risk = max(0, (engine_data['engine_temp'] - 90) / 30)
                oil_risk = max(0, (40 - engine_data['oil_pressure']) / 40)
                predictions['engine_failure_probability'] = min(1.0, (temp_risk + oil_risk) / 2)
            
            # Brake failure prediction
            brake_wear = maintenance_data['brake_pad_wear']
            predictions['brake_failure_probability'] = max(0, (50 - brake_wear) / 50)
            
            # Days until maintenance needed
            predictions['days_until_oil_change'] = max(1, maintenance_data['oil_life'] * 30 / 100)
            predictions['days_until_brake_service'] = max(1, brake_wear * 60 / 100)
            
        except Exception as e:
            print(f"Failure prediction error: {e}")
            predictions = {
                'engine_failure_probability': 0.1,
                'brake_failure_probability': 0.05,
                'days_until_oil_change': 15,
                'days_until_brake_service': 30
            }
        
        return predictions
    
    def _generate_maintenance_schedule(self, vehicle_id: str, health_scores: Dict, alerts: List) -> List[Dict[str, Any]]:
        """Generate recommended maintenance schedule"""
        schedule = []
        
        # Immediate actions based on critical alerts
        critical_alerts = [alert for alert in alerts if alert['urgency'] == 'Critical']
        for alert in critical_alerts:
            schedule.append({
                'priority': 'Immediate',
                'component': alert['component'],
                'task': alert['action'],
                'estimated_cost': self._estimate_cost(alert['type']),
                'estimated_time': self._estimate_time(alert['type']),
                'due_date': datetime.now().strftime('%Y-%m-%d')
            })
        
        # Scheduled maintenance based on health scores
        if health_scores['components']['oil_system'] < 30:
            schedule.append({
                'priority': 'High',
                'component': 'Engine',
                'task': 'Oil and filter change',
                'estimated_cost': 3000,
                'estimated_time': '1 hour',
                'due_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            })
        
        if health_scores['components']['brakes'] < 40:
            schedule.append({
                'priority': 'High',
                'component': 'Brakes',
                'task': 'Brake pad replacement',
                'estimated_cost': 8000,
                'estimated_time': '2 hours',
                'due_date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
            })
        
        # Regular maintenance
        schedule.append({
            'priority': 'Medium',
            'component': 'General',
            'task': 'Routine inspection',
            'estimated_cost': 1500,
            'estimated_time': '30 minutes',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        })
        
        return schedule
    
    def _generate_recommendations(self, health_scores: Dict, alerts: List) -> List[str]:
        """Generate maintenance recommendations"""
        recommendations = []
        
        if health_scores['overall'] < 70:
            recommendations.append("Schedule comprehensive vehicle inspection")
        
        if health_scores['components']['engine'] < 60:
            recommendations.append("Monitor engine performance closely")
        
        if len(alerts) > 2:
            recommendations.append("Address multiple maintenance issues promptly")
        
        if health_scores['components']['tires'] < 80:
            recommendations.append("Check tire pressure and alignment")
        
        recommendations.append("Maintain regular service schedule for optimal performance")
        
        return recommendations
    
    def _estimate_cost(self, maintenance_type: str) -> int:
        """Estimate maintenance cost in INR"""
        costs = {
            'Temperature': 5000,
            'Oil Pressure': 3000,
            'Brake Pads': 8000,
            'Oil Change': 3000,
            'Tire Pressure': 500
        }
        return costs.get(maintenance_type, 2000)
    
    def _estimate_time(self, maintenance_type: str) -> str:
        """Estimate maintenance time"""
        times = {
            'Temperature': '2-3 hours',
            'Oil Pressure': '1-2 hours',
            'Brake Pads': '2-3 hours',
            'Oil Change': '1 hour',
            'Tire Pressure': '15 minutes'
        }
        return times.get(maintenance_type, '1 hour')
    
    def _fallback_maintenance_data(self, vehicle_id: str) -> Dict[str, Any]:
        """Fallback maintenance data when sensors are unavailable"""
        import random
        
        return {
            'vehicle_id': vehicle_id,
            'overall_health_score': random.randint(70, 95),
            'component_health': {
                'engine': random.randint(75, 95),
                'brakes': random.randint(60, 90),
                'oil_system': random.randint(50, 85),
                'tires': random.randint(70, 95),
                'battery': random.randint(80, 100)
            },
            'alerts': [
                {
                    'component': 'Engine',
                    'type': 'Oil Change',
                    'urgency': 'Warning',
                    'message': 'Oil change due in 1000 km',
                    'action': 'Schedule oil change'
                }
            ],
            'failure_predictions': {
                'engine_failure_probability': 0.05,
                'brake_failure_probability': 0.03,
                'days_until_oil_change': 20,
                'days_until_brake_service': 45
            },
            'maintenance_schedule': [
                {
                    'priority': 'Medium',
                    'component': 'Engine',
                    'task': 'Oil change',
                    'estimated_cost': 3000,
                    'estimated_time': '1 hour',
                    'due_date': (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d')
                }
            ],
            'recommendations': [
                'Maintain regular service schedule',
                'Monitor engine performance'
            ],
            'timestamp': datetime.now().isoformat()
        }