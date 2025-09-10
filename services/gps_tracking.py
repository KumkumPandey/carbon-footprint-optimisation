import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import threading

class GPSTrackingService:
    
    def __init__(self):
        self.active_tracks = {}
        self.tracking_history = {}
        self.update_interval = 30  # seconds
        self._tracking_thread = None
        self._is_tracking = False
    
    def start_tracking(self, employee_id: str, vehicle_id: str, route_data: Dict) -> bool:
        """Start GPS tracking for an employee"""
        try:
            track_data = {
                'employee_id': employee_id,
                'vehicle_id': vehicle_id,
                'route_data': route_data,
                'start_time': datetime.now().isoformat(),
                'current_location': route_data.get('start_location', {}),
                'status': 'active',
                'waypoints': [],
                'total_distance': 0,
                'estimated_arrival': None
            }
            
            self.active_tracks[employee_id] = track_data
            
            # Start tracking thread if not already running
            if not self._is_tracking:
                self._start_tracking_thread()
            
            return True
            
        except Exception as e:
            print(f"Error starting GPS tracking: {e}")
            return False
    
    def stop_tracking(self, employee_id: str) -> Dict:
        """Stop GPS tracking and return trip summary"""
        if employee_id not in self.active_tracks:
            return {'error': 'No active tracking found'}
        
        track_data = self.active_tracks[employee_id]
        track_data['end_time'] = datetime.now().isoformat()
        track_data['status'] = 'completed'
        
        # Move to history
        if employee_id not in self.tracking_history:
            self.tracking_history[employee_id] = []
        
        self.tracking_history[employee_id].append(track_data)
        
        # Remove from active tracks
        del self.active_tracks[employee_id]
        
        return {
            'trip_summary': {
                'employee_id': employee_id,
                'duration': self._calculate_duration(track_data),
                'total_distance': track_data['total_distance'],
                'waypoints_count': len(track_data['waypoints']),
                'average_speed': self._calculate_average_speed(track_data)
            }
        }
    
    def get_live_location(self, employee_id: str) -> Optional[Dict]:
        """Get current live location of employee"""
        if employee_id not in self.active_tracks:
            return None
        
        track_data = self.active_tracks[employee_id]
        return {
            'employee_id': employee_id,
            'current_location': track_data['current_location'],
            'last_update': datetime.now().isoformat(),
            'status': track_data['status'],
            'progress_percentage': self._calculate_progress(track_data)
        }
    
    def get_all_active_tracks(self) -> Dict:
        """Get all currently active GPS tracks"""
        active_locations = {}
        
        for employee_id, track_data in self.active_tracks.items():
            active_locations[employee_id] = {
                'employee_id': employee_id,
                'vehicle_id': track_data['vehicle_id'],
                'current_location': track_data['current_location'],
                'status': track_data['status'],
                'start_time': track_data['start_time'],
                'progress': self._calculate_progress(track_data)
            }
        
        return active_locations
    
    def update_location(self, employee_id: str, lat: float, lng: float, additional_data: Dict = None) -> bool:
        """Update employee's current location"""
        if employee_id not in self.active_tracks:
            return False
        
        track_data = self.active_tracks[employee_id]
        
        # Create new waypoint
        waypoint = {
            'lat': lat,
            'lng': lng,
            'timestamp': datetime.now().isoformat(),
            'speed': additional_data.get('speed', 0) if additional_data else 0,
            'heading': additional_data.get('heading', 0) if additional_data else 0
        }
        
        # Calculate distance from last point
        if track_data['waypoints']:
            last_point = track_data['waypoints'][-1]
            distance = self._calculate_distance(
                (last_point['lat'], last_point['lng']),
                (lat, lng)
            )
            track_data['total_distance'] += distance
        
        # Update current location and add waypoint
        track_data['current_location'] = {'lat': lat, 'lng': lng}
        track_data['waypoints'].append(waypoint)
        
        return True
    
    def get_route_history(self, employee_id: str, limit: int = 10) -> List[Dict]:
        """Get historical route data for employee"""
        if employee_id not in self.tracking_history:
            return []
        
        history = self.tracking_history[employee_id]
        return history[-limit:] if limit else history
    
    def generate_geofence_alerts(self, employee_id: str, geofences: List[Dict]) -> List[Dict]:
        """Check if employee is within defined geofences"""
        if employee_id not in self.active_tracks:
            return []
        
        current_location = self.active_tracks[employee_id]['current_location']
        alerts = []
        
        for geofence in geofences:
            if self._is_within_geofence(current_location, geofence):
                alerts.append({
                    'type': 'geofence_entry',
                    'geofence_name': geofence['name'],
                    'employee_id': employee_id,
                    'timestamp': datetime.now().isoformat(),
                    'location': current_location
                })
        
        return alerts
    
    def _start_tracking_thread(self):
        """Start background thread for GPS updates"""
        self._is_tracking = True
        self._tracking_thread = threading.Thread(target=self._tracking_loop)
        self._tracking_thread.daemon = True
        self._tracking_thread.start()
    
    def _tracking_loop(self):
        """Background loop for simulating GPS updates"""
        while self._is_tracking and self.active_tracks:
            try:
                for employee_id in list(self.active_tracks.keys()):
                    # Simulate GPS movement
                    self._simulate_movement(employee_id)
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"Error in tracking loop: {e}")
        
        self._is_tracking = False
    
    def _simulate_movement(self, employee_id: str):
        """Simulate GPS movement for demo purposes"""
        if employee_id not in self.active_tracks:
            return
        
        track_data = self.active_tracks[employee_id]
        current_loc = track_data['current_location']
        
        # Simulate small movement (0.001 degrees ≈ 100 meters)
        import random
        new_lat = current_loc['lat'] + random.uniform(-0.001, 0.001)
        new_lng = current_loc['lng'] + random.uniform(-0.001, 0.001)
        
        # Update location with simulated data
        self.update_location(employee_id, new_lat, new_lng, {
            'speed': random.randint(40, 80),
            'heading': random.randint(0, 360)
        })
    
    def _calculate_distance(self, point1: tuple, point2: tuple) -> float:
        """Calculate distance between two GPS points"""
        from geopy.distance import geodesic
        return geodesic(point1, point2).kilometers
    
    def _calculate_duration(self, track_data: Dict) -> str:
        """Calculate trip duration"""
        start_time = datetime.fromisoformat(track_data['start_time'])
        end_time = datetime.fromisoformat(track_data.get('end_time', datetime.now().isoformat()))
        
        duration = end_time - start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        
        return f"{int(hours)}h {int(minutes)}m"
    
    def _calculate_average_speed(self, track_data: Dict) -> float:
        """Calculate average speed during trip"""
        if not track_data['waypoints'] or track_data['total_distance'] == 0:
            return 0
        
        start_time = datetime.fromisoformat(track_data['start_time'])
        end_time = datetime.fromisoformat(track_data.get('end_time', datetime.now().isoformat()))
        
        duration_hours = (end_time - start_time).total_seconds() / 3600
        
        if duration_hours > 0:
            return round(track_data['total_distance'] / duration_hours, 2)
        
        return 0
    
    def _calculate_progress(self, track_data: Dict) -> float:
        """Calculate trip progress percentage"""
        # Simplified progress calculation
        # In real implementation, this would compare against planned route
        
        if not track_data['waypoints']:
            return 0
        
        # Simulate progress based on time elapsed
        start_time = datetime.fromisoformat(track_data['start_time'])
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        # Assume 4-hour trip for simulation
        estimated_total_time = 4 * 3600  # 4 hours in seconds
        progress = min((elapsed_time / estimated_total_time) * 100, 100)
        
        return round(progress, 1)
    
    def _is_within_geofence(self, location: Dict, geofence: Dict) -> bool:
        """Check if location is within geofence"""
        center_lat = geofence['center']['lat']
        center_lng = geofence['center']['lng']
        radius_km = geofence['radius_km']
        
        distance = self._calculate_distance(
            (location['lat'], location['lng']),
            (center_lat, center_lng)
        )
        
        return distance <= radius_km

# Global GPS tracking service instance
gps_service = GPSTrackingService()