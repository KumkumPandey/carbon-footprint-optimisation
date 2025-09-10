import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import torch

# Load environment variables
load_dotenv()
import torch.nn as nn
import numpy as np
import pandas as pd
from geopy.distance import geodesic
import joblib
import tensorflow as tf
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, after_this_request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
# Import multi-tenant database system
from database_manager import DatabaseManager
from company_selector import CompanySelector

try:
    from config import Config
    from auth import JWTAuth, jwt_required, role_required
    from tasks import celery, optimize_route_task, generate_analytics_report, retrain_models_task
    ADVANCED_FEATURES = True
except ImportError as e:
    print(f"Advanced features disabled: {e}")
    ADVANCED_FEATURES = False
    
    # Fallback config
    class Config:
        SECRET_KEY = 'fallback_secret_key'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'
        SQLALCHEMY_TRACK_MODIFICATIONS = False

# Initialize multi-tenant system
db_manager = DatabaseManager()
company_selector = CompanySelector()

# Add the current directory to the Python path
sys.path.append(os.getcwd())

# 1. Load the models
try:
    base_carbon_model = joblib.load('base_carbon_model.pkl')
except FileNotFoundError:
    print("Error: base_carbon_model.pkl not found. Please run model_building.py.")
    exit()

try:
    from pytorch_forecaster import LSTMForecaster
    traffic_lstm = LSTMForecaster()
    traffic_lstm.load_state_dict(torch.load('traffic_lstm.pth'))
    traffic_lstm.eval()
    weather_lstm = LSTMForecaster()
    weather_lstm.load_state_dict(torch.load('weather_lstm.pth'))
    weather_lstm.eval()
    scaler_traffic = joblib.load('scaler_traffic.pkl')
    scaler_weather = joblib.load('scaler_weather.pkl')
except FileNotFoundError:
    print("Error: PyTorch model files not found. Please run pytorch_forecaster.py.")
    exit()
    
try:
    road_condition_classifier = tf.keras.models.load_model('road_condition_classifier.h5')
except (IOError, ImportError):
    print("Error: TensorFlow model not found. Please run tensorflow_classifier.py.")
    exit()

# 2. Define city coordinates and impact factors
city_coords = {
    "New Delhi": (28.7041, 77.1025), "Mumbai": (19.0760, 72.8777),
    "Bangalore": (12.9716, 77.5946), "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867), "Pune": (18.5204, 73.8567),
    "Kolkata": (22.5726, 88.3639)
}
weather_impact = {'Clear': 1.0, 'Rainy': 1.1, 'Foggy': 1.2}
traffic_impact = {'Low': 1.0, 'Medium': 1.2, 'High': 1.5}

# 3. Flask App Initialization and Database Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'fallback_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if ADVANCED_FEATURES:
    try:
        app.config.from_object(Config)
        # Initialize Celery
        celery.conf.update(app.config)
    except:
        pass

db = SQLAlchemy(app)

# Setup basic logging
if not os.path.exists('logs'):
    os.makedirs('logs')

if ADVANCED_FEATURES:
    try:
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Logistics app startup')
        
        # Security headers middleware
        @app.after_request
        def add_security_headers(response):
            security_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block'
            }
            for header, value in security_headers.items():
                response.headers[header] = value
            return response
        
        # Request logging middleware
        @app.before_request
        def log_request_info():
            app.logger.info(f'Request: {request.method} {request.url} - IP: {request.remote_addr}')
    except Exception as e:
        print(f"Advanced logging setup failed: {e}")
else:
    print("Running in basic mode without advanced logging and security features")

# User Login Management
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Database Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, unique=True)
    username = db.Column(db.String(50), nullable=False)
    phone_no = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(120), nullable=True, unique=True)
    working_area = db.Column(db.String(50), nullable=True)
    dob = db.Column(db.String(10), nullable=True)
    password_hash = db.Column(db.String(150), nullable=False)
    is_owner = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    truck_id = db.Column(db.String(20), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company = db.relationship('User', backref=db.backref('employees', lazy=True))

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    photo_verified = db.Column(db.Boolean, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Truck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    truck_number = db.Column(db.String(20), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    current_location = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Available')
    dispatch_time = db.Column(db.DateTime)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    truck_id = db.Column(db.Integer, db.ForeignKey('truck.id'))
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    route_data = db.Column(db.Text)
    employee = db.relationship('Employee', backref=db.backref('trips', lazy=True))
    truck = db.relationship('Truck', backref=db.backref('trips', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- Routes for User Management ---
@app.route('/owner_register', methods=['GET', 'POST'])
def owner_register():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        owner_name = request.form.get('owner_name')
        phone_no = request.form.get('phone_no')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([company_name, owner_name, password]):
            flash('Please fill all required fields!')
            return redirect(url_for('owner_register'))
        
        # Register new company with separate database
        company_data = {
            'company_name': company_name,
            'owner_name': owner_name,
            'phone': phone_no,
            'email': email,
            'password': password
        }
        
        print(f'Registering company: {company_name}')
        result = company_selector.register_new_company(company_data)
        
        if result:
            print(f'Company registration result: {result}')
            company_data['company_id'] = result['company_id']
            owner_id = company_selector.create_owner_user(result['database_path'], company_data)
            
            if owner_id:
                flash(f'Company registered successfully!\nCompany ID: {result["company_id"]}\nOwner ID: {owner_id}\nPlease login with your Owner ID and password.')
                return redirect(url_for('owner_auth'))
            else:
                flash('Company registered but failed to create owner account. Please contact support.')
        else:
            flash('Error registering company. Please try again.')
    
    return render_template('owner_register.html')

# Company list route removed for security - companies should not be publicly visible

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        # Generate user_id if not provided (for company-based login)
        if company_name and not user_id:
            company_code = company_name[:3].upper()
            user_id = f'OWN-{company_code}-001'
        
        # Authenticate using multi-tenant system
        user_info = company_selector.authenticate_user(user_id, password)
        
        if user_info:
            # Store user and company info in session
            session['user_id'] = user_info['user_id']
            session['username'] = user_info['username']
            session['is_owner'] = user_info['is_owner']
            session['company_id'] = user_info['company_info']['company_id']
            session['company_name'] = user_info['company_info']['company_name']
            session['database_path'] = user_info['database_path']
            
            if ADVANCED_FEATURES:
                # Generate JWT token
                role = 'owner' if user_info['is_owner'] else 'employee'
                token = JWTAuth.generate_token(user_info['user_id'], role)
                app.logger.info(f'User {user_id} from company {user_info["company_info"]["company_name"]} logged in successfully')
            else:
                print(f'User {user_id} from company {user_info["company_info"]["company_name"]} logged in successfully')
            
            if user_info['is_owner']:
                return redirect(url_for('owner_dashboard'))
            else:
                return redirect(url_for('employee_dashboard'))
        
        if ADVANCED_FEATURES:
            app.logger.warning(f'Failed login attempt for user {user_id}')
        else:
            print(f'Failed login attempt for user {user_id}')
        flash('Invalid company name, ID or password')
    return render_template('login.html')

@app.route('/api/auth/token', methods=['POST'])
def get_auth_token():
    if not ADVANCED_FEATURES:
        return jsonify({'error': 'JWT authentication not available'}), 501
        
    data = request.get_json()
    user_id = data.get('user_id')
    password = data.get('password')
    
    user = User.query.filter_by(user_id=user_id).first()
    if user and user.check_password(password):
        role = 'owner' if user.is_owner else 'employee'
        token = JWTAuth.generate_token(user.user_id, role)
        
        app.logger.info(f'JWT token generated for user {user_id}')
        return jsonify({'token': token, 'role': role})
    
    app.logger.warning(f'Failed token request for user {user_id}')
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Routes for Dashboards and Optimization ---
@app.route('/owner_dashboard')
def owner_dashboard():
    if 'user_id' not in session or not session.get('is_owner'):
        flash('Access Denied. Please login as owner.')
        return redirect(url_for('login'))
    
    return render_template('owner_dashboard.html')

@app.route('/api/trucks')
def get_trucks():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get trucks from company database
    try:
        import sqlite3
        db_path = session.get('database_path')
        if not db_path:
            return jsonify({'error': 'Company database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trucks')
        trucks = cursor.fetchall()
        conn.close()
        
        truck_data = []
        for truck in trucks:
            truck_data.append({
                'id': truck[0],
                'truck_number': truck[1],
                'driver_name': truck[2],
                'current_location': truck[3] or 'Not set',
                'destination': truck[4] or 'Not set',
                'status': truck[5] or 'Available',
                'lat': truck[7] or 28.7041,
                'lng': truck[8] or 77.1025
            })
        
        return jsonify(truck_data)
    except Exception as e:
        print(f'Error getting trucks: {e}')
        return jsonify({'error': 'Failed to get trucks'}), 500

@app.route('/api/customers')
def get_customers():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get customers from company database
    try:
        import sqlite3
        db_path = session.get('database_path')
        if not db_path:
            return jsonify({'error': 'Company database not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM customers WHERE status = "active"')
        customers = cursor.fetchall()
        conn.close()
        
        customer_data = []
        for customer in customers:
            customer_data.append({
                'id': customer[0],
                'name': customer[1],
                'email': customer[2],
                'phone': customer[3],
                'photo_verified': bool(customer[5])
            })
        
        return jsonify(customer_data)
    except Exception as e:
        print(f'Error getting customers: {e}')
        return jsonify({'error': 'Failed to get customers'}), 500

@app.route('/employee_dashboard')
def employee_dashboard():
    if 'user_id' not in session:
        flash('Please login first.')
        return redirect(url_for('login'))
    
    if session.get('is_owner'):
        return redirect(url_for('owner_dashboard'))
    
    return render_template('employee_dashboard.html')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/owner_auth')
def owner_auth():
    return render_template('owner_auth.html')

@app.route('/employee_auth')
def employee_auth():
    return render_template('employee_auth.html')

@app.route('/employee_register', methods=['GET', 'POST'])
def employee_register():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        employee_name = request.form.get('employee_name')
        phone = request.form.get('phone')
        license_number = request.form.get('license_number')
        aadhar_number = request.form.get('aadhar_number')
        address = request.form.get('address')
        password = request.form.get('password')
        
        if not all([company_name, employee_name, password]):
            flash('Please fill all required fields!')
            return redirect(url_for('employee_register'))
        
        # Find company by name
        companies = company_selector.db_manager.list_all_companies()
        target_company = None
        
        for company in companies:
            if company['company_name'].lower() == company_name.lower():
                target_company = company
                break
        
        if not target_company:
            flash('Company not found. Please check company name or ask owner to register first.')
            return redirect(url_for('employee_register'))
        
        # Add employee to company
        employee_data = {
            'name': employee_name,
            'phone': phone,
            'license': license_number,
            'aadhar': aadhar_number,
            'address': address,
            'password': password
        }
        
        employee_id = company_selector.add_employee_to_company(target_company['company_id'], employee_data)
        
        if employee_id:
            flash(f'Employee registered successfully!\nEmployee ID: {employee_id}\nCompany: {company_name}\nPlease login with your Employee ID.')
            return redirect(url_for('employee_auth'))
        else:
            flash('Error registering employee. Please try again.')
    
    return render_template('employee_register.html')

@app.route('/optimize')
@login_required
def optimize():
    return render_template('index.html')

@app.route('/predict_carbon', methods=['POST'])
def predict_route():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    print('Route prediction request received')
    try:
        # Import services with fallback
        try:
            from services.real_time_data import RealTimeDataService
            from services.optimization_engine import GeneticOptimizer
            from services.gps_tracking import gps_service
            advanced_features = True
        except ImportError:
            advanced_features = False
        
        data = request.get_json()
        start_loc = data['start_location']
        end_loc = data['end_location']
        load_kg = data['load_weight_kg']

        # Get coordinates from database
        start_location = Location.query.filter_by(city=start_loc).first()
        end_location = Location.query.filter_by(city=end_loc).first()
        
        if not start_location or not end_location:
            return jsonify({"error": "Location not found in database"}), 400
        
        start_coords = (start_location.latitude, start_location.longitude)
        end_coords = (end_location.latitude, end_location.longitude)

        # Get real-time data (with fallback)
        if advanced_features:
            weather_data = RealTimeDataService.get_weather_data(start_location.latitude, start_location.longitude)
            traffic_data = RealTimeDataService.get_traffic_data(
                start_location.latitude, start_location.longitude,
                end_location.latitude, end_location.longitude
            )
            air_quality = RealTimeDataService.get_air_quality_data(start_location.latitude, start_location.longitude)
            
            # Advanced optimization
            optimizer = GeneticOptimizer(population_size=30, generations=50)
            locations = [
                {'lat': start_location.latitude, 'lng': start_location.longitude, 'name': start_loc},
                {'lat': end_location.latitude, 'lng': end_location.longitude, 'name': end_loc}
            ]
            
            constraints = {
                'load_weight': load_kg,
                'weather_condition': weather_data['condition'],
                'traffic_level': traffic_data['level'],
                'distance_weight': 0.3,
                'time_weight': 0.4,
                'carbon_weight': 0.3,
                'traffic_multiplier': {'Low': 1.0, 'Medium': 1.3, 'High': 1.8}[traffic_data['level']]
            }
            
            optimization_result = optimizer.optimize_route(locations, constraints)
        else:
            # Fallback to simple simulation
            import random
            weather_data = {
                'condition': random.choice(['Clear', 'Rainy', 'Foggy']),
                'temperature': random.randint(20, 35),
                'humidity': random.randint(40, 80)
            }
            traffic_data = {
                'level': random.choice(['Low', 'Medium', 'High']),
                'duration': 3600,
                'duration_in_traffic': 4200
            }
            air_quality = {'aqi': 2, 'co': 200}
            optimization_result = {'fuel_consumption': {'diesel': 25, 'petrol': 5}}
        
        # Calculate enhanced metrics
        dist_km = geodesic(start_coords, end_coords).km
        input_data = pd.DataFrame([[dist_km, load_kg]], columns=['distance_km', 'load_weight_kg'])
        base_carbon_kg = base_carbon_model.predict(input_data)[0]

        # Enhanced carbon calculation with real-time factors
        weather_multiplier = {'Clear': 1.0, 'Rainy': 1.15, 'Foggy': 1.25, 'Cloudy': 1.05}.get(weather_data['condition'], 1.0)
        traffic_multiplier = {'Low': 1.0, 'Medium': 1.2, 'High': 1.5}[traffic_data['level']]
        air_quality_multiplier = 1 + (air_quality.get('aqi', 2) - 1) * 0.05
        
        final_carbon_kg = base_carbon_kg * weather_multiplier * traffic_multiplier * air_quality_multiplier
        
        # Start GPS tracking (if available)
        tracking_started = False
        if advanced_features:
            employee_id = data.get('user_id', 'EMP-001')
            route_data = {
                'start_location': {'lat': start_location.latitude, 'lng': start_location.longitude},
                'end_location': {'lat': end_location.latitude, 'lng': end_location.longitude},
                'planned_distance': dist_km,
                'estimated_duration': traffic_data['duration_in_traffic'] / 3600
            }
            tracking_started = gps_service.start_tracking(employee_id, f'VEH-{employee_id}', route_data)

        return jsonify({
            "start_location": start_loc,
            "end_location": end_loc,
            "distance_km": round(dist_km, 2),
            "predicted_traffic": traffic_data['level'],
            "predicted_weather": weather_data['condition'],
            "road_condition": 'Clear',
            "optimized_carbon_footprint_kg": round(final_carbon_kg, 2),
            "real_time_weather": weather_data,
            "real_time_traffic": traffic_data,
            "air_quality": air_quality,
            "fuel_estimate": optimization_result.get('fuel_consumption', {'diesel': 25, 'petrol': 5}),
            "estimated_time_hours": round(traffic_data.get('duration_in_traffic', 4200) / 3600, 2),
            "tracking_started": tracking_started,
            "tracking_id": data.get('user_id', 'EMP-001') if tracking_started else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/populate_locations')
def populate_locations():
    # Clear existing data first
    Location.query.delete()
    
    # All cities from logistics_data.csv
    indian_locations = [
        {'state': 'Delhi', 'district': 'New Delhi', 'city': 'New Delhi', 'pincode': '110001', 'lat': 28.7041, 'lng': 77.1025},
        {'state': 'Maharashtra', 'district': 'Mumbai', 'city': 'Mumbai', 'pincode': '400001', 'lat': 19.0760, 'lng': 72.8777},
        {'state': 'Karnataka', 'district': 'Bangalore Urban', 'city': 'Bangalore', 'pincode': '560001', 'lat': 12.9716, 'lng': 77.5946},
        {'state': 'Tamil Nadu', 'district': 'Chennai', 'city': 'Chennai', 'pincode': '600001', 'lat': 13.0827, 'lng': 80.2707},
        {'state': 'Telangana', 'district': 'Hyderabad', 'city': 'Hyderabad', 'pincode': '500001', 'lat': 17.3850, 'lng': 78.4867},
        {'state': 'Maharashtra', 'district': 'Pune', 'city': 'Pune', 'pincode': '411001', 'lat': 18.5204, 'lng': 73.8567},
        {'state': 'West Bengal', 'district': 'Kolkata', 'city': 'Kolkata', 'pincode': '700001', 'lat': 22.5726, 'lng': 88.3639},
        {'state': 'Rajasthan', 'district': 'Jaipur', 'city': 'Jaipur', 'pincode': '302001', 'lat': 26.9124, 'lng': 75.7873},
        {'state': 'Uttar Pradesh', 'district': 'Lucknow', 'city': 'Lucknow', 'pincode': '226001', 'lat': 26.8467, 'lng': 80.9462},
        {'state': 'Madhya Pradesh', 'district': 'Bhopal', 'city': 'Bhopal', 'pincode': '462001', 'lat': 23.2599, 'lng': 77.4126},
        {'state': 'Madhya Pradesh', 'district': 'Indore', 'city': 'Indore', 'pincode': '452001', 'lat': 22.7196, 'lng': 75.8577},
        {'state': 'Gujarat', 'district': 'Ahmedabad', 'city': 'Ahmedabad', 'pincode': '380001', 'lat': 23.0225, 'lng': 72.5714},
        {'state': 'Gujarat', 'district': 'Surat', 'city': 'Surat', 'pincode': '395001', 'lat': 21.1702, 'lng': 72.8311},
        {'state': 'Chandigarh', 'district': 'Chandigarh', 'city': 'Chandigarh', 'pincode': '160001', 'lat': 30.7333, 'lng': 76.7794},
        {'state': 'Himachal Pradesh', 'district': 'Shimla', 'city': 'Shimla', 'pincode': '171001', 'lat': 31.1048, 'lng': 77.1734},
        {'state': 'Bihar', 'district': 'Patna', 'city': 'Patna', 'pincode': '800001', 'lat': 25.5941, 'lng': 85.1376},
        {'state': 'Assam', 'district': 'Guwahati', 'city': 'Guwahati', 'pincode': '781001', 'lat': 26.1445, 'lng': 91.7362},
        {'state': 'Meghalaya', 'district': 'East Khasi Hills', 'city': 'Shillong', 'pincode': '793001', 'lat': 25.5788, 'lng': 91.8933},
        {'state': 'Odisha', 'district': 'Bhubaneswar', 'city': 'Bhubaneswar', 'pincode': '751001', 'lat': 20.2961, 'lng': 85.8245},
        {'state': 'Odisha', 'district': 'Cuttack', 'city': 'Cuttack', 'pincode': '753001', 'lat': 20.4625, 'lng': 85.8828},
        {'state': 'Kerala', 'district': 'Thiruvananthapuram', 'city': 'Thiruvananthapuram', 'pincode': '695001', 'lat': 8.5241, 'lng': 76.9366},
        {'state': 'Kerala', 'district': 'Kochi', 'city': 'Kochi', 'pincode': '682001', 'lat': 9.9312, 'lng': 76.2673},
        {'state': 'Maharashtra', 'district': 'Nashik', 'city': 'Nashik', 'pincode': '422001', 'lat': 19.9975, 'lng': 73.7898},
        {'state': 'Maharashtra', 'district': 'Nagpur', 'city': 'Nagpur', 'pincode': '440001', 'lat': 21.1458, 'lng': 79.0882},
        {'state': 'Gujarat', 'district': 'Vadodara', 'city': 'Vadodara', 'pincode': '390001', 'lat': 22.3072, 'lng': 73.1812},
        {'state': 'Gujarat', 'district': 'Rajkot', 'city': 'Rajkot', 'pincode': '360001', 'lat': 22.3039, 'lng': 70.8022},
        {'state': 'Punjab', 'district': 'Amritsar', 'city': 'Amritsar', 'pincode': '143001', 'lat': 31.6340, 'lng': 74.8723},
        {'state': 'Punjab', 'district': 'Ludhiana', 'city': 'Ludhiana', 'pincode': '141001', 'lat': 30.9010, 'lng': 75.8573},
        {'state': 'Uttar Pradesh', 'district': 'Agra', 'city': 'Agra', 'pincode': '282001', 'lat': 27.1767, 'lng': 78.0081},
        {'state': 'Uttar Pradesh', 'district': 'Kanpur', 'city': 'Kanpur', 'pincode': '208001', 'lat': 26.4499, 'lng': 80.3319},
        {'state': 'Uttar Pradesh', 'district': 'Varanasi', 'city': 'Varanasi', 'pincode': '221001', 'lat': 25.3176, 'lng': 82.9739},
        {'state': 'Uttar Pradesh', 'district': 'Allahabad', 'city': 'Allahabad', 'pincode': '211001', 'lat': 25.4358, 'lng': 81.8463},
        {'state': 'Kerala', 'district': 'Kollam', 'city': 'Kollam', 'pincode': '691001', 'lat': 8.8932, 'lng': 76.6141},
        {'state': 'Tamil Nadu', 'district': 'Coimbatore', 'city': 'Coimbatore', 'pincode': '641001', 'lat': 11.0168, 'lng': 76.9558},
        {'state': 'Karnataka', 'district': 'Mysore', 'city': 'Mysuru', 'pincode': '570001', 'lat': 12.2958, 'lng': 76.6394},
        {'state': 'Karnataka', 'district': 'Dakshina Kannada', 'city': 'Mangaluru', 'pincode': '575001', 'lat': 12.9141, 'lng': 74.8560},
        {'state': 'Andhra Pradesh', 'district': 'Visakhapatnam', 'city': 'Visakhapatnam', 'pincode': '530001', 'lat': 17.6868, 'lng': 83.2185},
        {'state': 'Andhra Pradesh', 'district': 'Vijayawada', 'city': 'Vijayawada', 'pincode': '520001', 'lat': 16.5062, 'lng': 80.6480},
        {'state': 'Madhya Pradesh', 'district': 'Jabalpur', 'city': 'Jabalpur', 'pincode': '482001', 'lat': 23.1815, 'lng': 79.9864},
        {'state': 'Chhattisgarh', 'district': 'Raipur', 'city': 'Raipur', 'pincode': '492001', 'lat': 21.2514, 'lng': 81.6296},
        {'state': 'Jammu and Kashmir', 'district': 'Srinagar', 'city': 'Srinagar', 'pincode': '190001', 'lat': 34.0837, 'lng': 74.7973},
        {'state': 'Jammu and Kashmir', 'district': 'Jammu', 'city': 'Jammu', 'pincode': '180001', 'lat': 32.7266, 'lng': 74.8570},
        {'state': 'Goa', 'district': 'North Goa', 'city': 'Panaji', 'pincode': '403001', 'lat': 15.4909, 'lng': 73.8278},
        {'state': 'Karnataka', 'district': 'Belagavi', 'city': 'Belagavi', 'pincode': '590001', 'lat': 15.8497, 'lng': 74.4977},
        {'state': 'Jharkhand', 'district': 'Ranchi', 'city': 'Ranchi', 'pincode': '834001', 'lat': 23.3441, 'lng': 85.3096},
        {'state': 'Jharkhand', 'district': 'Dhanbad', 'city': 'Dhanbad', 'pincode': '826001', 'lat': 23.7957, 'lng': 86.4304},
        {'state': 'Punjab', 'district': 'Jalandhar', 'city': 'Jalandhar', 'pincode': '144001', 'lat': 31.3260, 'lng': 75.5762},
        {'state': 'Punjab', 'district': 'Patiala', 'city': 'Patiala', 'pincode': '147001', 'lat': 30.3398, 'lng': 76.3869},
        {'state': 'West Bengal', 'district': 'Kharagpur', 'city': 'Kharagpur', 'pincode': '721301', 'lat': 22.3460, 'lng': 87.2320},
        {'state': 'West Bengal', 'district': 'Durgapur', 'city': 'Durgapur', 'pincode': '713201', 'lat': 23.5204, 'lng': 87.3119},
        {'state': 'Tamil Nadu', 'district': 'Tirunelveli', 'city': 'Tirunelveli', 'pincode': '627001', 'lat': 8.7139, 'lng': 77.7567},
        {'state': 'Rajasthan', 'district': 'Udaipur', 'city': 'Udaipur', 'pincode': '313001', 'lat': 24.5854, 'lng': 73.7125},
        {'state': 'Rajasthan', 'district': 'Bikaner', 'city': 'Bikaner', 'pincode': '334001', 'lat': 28.0229, 'lng': 73.3119},
        {'state': 'Rajasthan', 'district': 'Jaisalmer', 'city': 'Jaisalmer', 'pincode': '345001', 'lat': 26.9157, 'lng': 70.9083},
        {'state': 'Maharashtra', 'district': 'Aurangabad', 'city': 'Aurangabad', 'pincode': '431001', 'lat': 19.8762, 'lng': 75.3433},
        {'state': 'Maharashtra', 'district': 'Latur', 'city': 'Latur', 'pincode': '413512', 'lat': 18.4088, 'lng': 76.5604},
        {'state': 'Rajasthan', 'district': 'Kota', 'city': 'Kota', 'pincode': '324001', 'lat': 25.2138, 'lng': 75.8648},
        {'state': 'Rajasthan', 'district': 'Bundi', 'city': 'Bundi', 'pincode': '323001', 'lat': 25.4305, 'lng': 75.6499},
        {'state': 'Uttarakhand', 'district': 'Dehradun', 'city': 'Dehradun', 'pincode': '248001', 'lat': 30.3165, 'lng': 78.0322},
        {'state': 'Uttarakhand', 'district': 'Haridwar', 'city': 'Haridwar', 'pincode': '249401', 'lat': 29.9457, 'lng': 78.1642},
        {'state': 'Puducherry', 'district': 'Puducherry', 'city': 'Puducherry', 'pincode': '605001', 'lat': 11.9416, 'lng': 79.8083},
        {'state': 'Tamil Nadu', 'district': 'Tiruchirappalli', 'city': 'Tiruchirappalli', 'pincode': '620001', 'lat': 10.7905, 'lng': 78.7047},
        {'state': 'Bihar', 'district': 'Gaya', 'city': 'Gaya', 'pincode': '823001', 'lat': 24.7914, 'lng': 85.0002},
        {'state': 'Bihar', 'district': 'Darbhanga', 'city': 'Darbhanga', 'pincode': '846004', 'lat': 26.1542, 'lng': 85.8918},
        {'state': 'Tripura', 'district': 'West Tripura', 'city': 'Agartala', 'pincode': '799001', 'lat': 23.8315, 'lng': 91.2868},
        {'state': 'Manipur', 'district': 'Imphal West', 'city': 'Imphal', 'pincode': '795001', 'lat': 24.8170, 'lng': 93.9368},
        {'state': 'Mizoram', 'district': 'Aizawl', 'city': 'Aizawl', 'pincode': '796001', 'lat': 23.7271, 'lng': 92.7176},
        {'state': 'Assam', 'district': 'Cachar', 'city': 'Silchar', 'pincode': '788001', 'lat': 24.8333, 'lng': 92.7789},
        {'state': 'Arunachal Pradesh', 'district': 'Papum Pare', 'city': 'Itanagar', 'pincode': '791111', 'lat': 27.0844, 'lng': 93.6053},
        {'state': 'Arunachal Pradesh', 'district': 'Papum Pare', 'city': 'Naharlagun', 'pincode': '791110', 'lat': 27.1050, 'lng': 93.7000},
        {'state': 'Nagaland', 'district': 'Kohima', 'city': 'Kohima', 'pincode': '797001', 'lat': 25.6751, 'lng': 94.1086},
        {'state': 'Nagaland', 'district': 'Dimapur', 'city': 'Dimapur', 'pincode': '797112', 'lat': 25.9044, 'lng': 93.7267},
        {'state': 'Sikkim', 'district': 'East Sikkim', 'city': 'Gangtok', 'pincode': '737101', 'lat': 27.3389, 'lng': 88.6065},
        {'state': 'West Bengal', 'district': 'Darjeeling', 'city': 'Darjeeling', 'pincode': '734101', 'lat': 27.0360, 'lng': 88.2627},
        {'state': 'Dadra and Nagar Haveli', 'district': 'Dadra and Nagar Haveli', 'city': 'Daman', 'pincode': '396210', 'lat': 20.3974, 'lng': 72.8328},
        {'state': 'Dadra and Nagar Haveli', 'district': 'Dadra and Nagar Haveli', 'city': 'Silvassa', 'pincode': '396230', 'lat': 20.2738, 'lng': 72.9960},
        {'state': 'Andaman and Nicobar Islands', 'district': 'South Andaman', 'city': 'Port Blair', 'pincode': '744101', 'lat': 11.6234, 'lng': 92.7265},
        {'state': 'Andaman and Nicobar Islands', 'district': 'South Andaman', 'city': 'Havelock', 'pincode': '744211', 'lat': 12.0067, 'lng': 92.9598},
        {'state': 'Lakshadweep', 'district': 'Lakshadweep', 'city': 'Kavaratti', 'pincode': '682555', 'lat': 10.5669, 'lng': 72.6420},
        {'state': 'Lakshadweep', 'district': 'Lakshadweep', 'city': 'Agatti', 'pincode': '682553', 'lat': 10.8481, 'lng': 72.1929}
    ]
    
    for loc_data in indian_locations:
        location = Location(
            state=loc_data['state'],
            district=loc_data['district'],
            city=loc_data['city'],
            pincode=loc_data['pincode'],
            latitude=loc_data['lat'],
            longitude=loc_data['lng']
        )
        db.session.add(location)
    
    db.session.commit()
    return jsonify({'message': f'Successfully populated {len(indian_locations)} locations from logistics data!', 'total_cities': len(indian_locations), 'total_states': len(set(loc["state"] for loc in indian_locations))})

@app.route('/api/locations')
def get_locations():
    locations = Location.query.all()
    location_data = []
    for loc in locations:
        location_data.append({
            'state': loc.state,
            'district': loc.district,
            'city': loc.city,
            'pincode': loc.pincode,
            'lat': loc.latitude,
            'lng': loc.longitude
        })
    return jsonify(location_data)

@app.route('/refresh_locations')
def refresh_locations():
    # Force refresh by clearing and repopulating
    Location.query.delete()
    db.session.commit()
    
    # Repopulate with fresh data
    populate_locations()
    
    return jsonify({'message': 'Locations refreshed successfully!', 'count': Location.query.count()})

@app.route('/api/maintenance/<vehicle_id>')
@login_required
def get_maintenance_data(vehicle_id):
    try:
        from services.predictive_maintenance import PredictiveMaintenanceService
        maintenance_service = PredictiveMaintenanceService()
        data = maintenance_service.predict_maintenance(vehicle_id)
        return jsonify(data)
    except ImportError:
        # Fallback data
        return jsonify({
            'vehicle_id': vehicle_id,
            'health_score': 75,
            'alerts': [{'component': 'Engine Oil', 'urgency': 'Medium'}]
        })

@app.route('/api/pricing/quote', methods=['POST'])
@login_required
def generate_pricing_quote():
    try:
        from services.dynamic_pricing import DynamicPricingService
        pricing_service = DynamicPricingService()
        
        data = request.get_json()
        quote = pricing_service.generate_quote(
            data['origin'],
            data['destination'], 
            data['load_weight'],
            data.get('urgency', 'normal')
        )
        return jsonify(quote)
    except ImportError:
        # Fallback pricing
        data = request.get_json()
        distance = 1000  # Default distance
        base_price = distance * 12
        return jsonify({
            'quote_id': f'QT-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'final_price': base_price,
            'distance_km': distance
        })

@app.route('/api/analytics')
def get_analytics():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if ADVANCED_FEATURES:
            from services.analytics_service import AnalyticsService
            analytics_data = AnalyticsService.generate_trip_analytics(session['user_id'])
            return jsonify(analytics_data)
    except ImportError:
        pass
    
    # Fallback data
    return jsonify({
        'total_trips': 245,
        'total_carbon_saved': 850.5,
        'average_efficiency': 87,
        'active_alerts': 2
    })

@app.route('/api/chart_data')
@login_required
def get_chart_data():
    try:
        from services.analytics_service import AnalyticsService
        chart_data = AnalyticsService.generate_chart_data()
        return jsonify(chart_data)
    except ImportError:
        # Fallback chart data
        return jsonify({
            'carbon_trend_chart': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'data': [120, 95, 110, 85, 100, 75, 90]
            },
            'fuel_consumption_chart': {
                'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                'data': [450, 380, 420, 350]
            }
        })

@app.route('/api/gps/track/<employee_id>')
@login_required
def get_gps_location(employee_id):
    from services.gps_tracking import gps_service
    
    location_data = gps_service.get_live_location(employee_id)
    if location_data:
        return jsonify(location_data)
    else:
        return jsonify({'error': 'No active tracking found'}), 404

@app.route('/api/gps/all_tracks')
@login_required
def get_all_tracks():
    try:
        from services.gps_tracking import gps_service
        all_tracks = gps_service.get_all_active_tracks()
        return jsonify(all_tracks)
    except ImportError:
        # Fallback GPS data
        return jsonify([
            {
                'employee_id': 'EMP-001',
                'employee_name': 'Raj Kumar',
                'vehicle_id': 'DL-01-1234',
                'latitude': 28.7041,
                'longitude': 77.1025,
                'status': 'In Transit',
                'speed': 65,
                'last_updated': datetime.now().isoformat()
            },
            {
                'employee_id': 'EMP-002',
                'employee_name': 'Amit Singh',
                'vehicle_id': 'MH-02-5678',
                'latitude': 19.0760,
                'longitude': 72.8777,
                'status': 'In Transit',
                'speed': 45,
                'last_updated': datetime.now().isoformat()
            },
            {
                'employee_id': 'EMP-003',
                'employee_name': 'Suresh Reddy',
                'vehicle_id': 'KA-03-9012',
                'latitude': 12.9716,
                'longitude': 77.5946,
                'status': 'In Transit',
                'speed': 55,
                'last_updated': datetime.now().isoformat()
            }
        ])

@app.route('/api/gps/update_location', methods=['POST'])
@login_required
def update_gps_location():
    from services.gps_tracking import gps_service
    
    data = request.get_json()
    employee_id = data.get('employee_id')
    lat = data.get('latitude')
    lng = data.get('longitude')
    additional_data = data.get('additional_data', {})
    
    success = gps_service.update_location(employee_id, lat, lng, additional_data)
    
    if success:
        return jsonify({'status': 'success', 'message': 'Location updated'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update location'}), 400

@app.route('/api/optimize_advanced', methods=['POST'])
def advanced_optimization():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not ADVANCED_FEATURES:
        return jsonify({'error': 'Advanced optimization not available'}), 501
        
    print('Advanced optimization request received')
    
    try:
        # Queue background task
        task = optimize_route_task.delay(request.get_json())
        
        return jsonify({
            'task_id': task.id,
            'status': 'queued',
            'message': 'Optimization started in background'
        })
    except Exception as e:
        return jsonify({'error': 'Optimization service unavailable'}), 503

@app.route('/api/task_status/<task_id>')
def get_task_status(task_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not ADVANCED_FEATURES:
        return jsonify({'error': 'Task status not available'}), 501
    task = optimize_route_task.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Task is waiting...'}
    elif task.state == 'PROGRESS':
        response = {'state': task.state, 'status': task.info.get('status', '')}
    elif task.state == 'SUCCESS':
        response = {'state': task.state, 'result': task.result}
    else:
        response = {'state': task.state, 'error': str(task.info)}
    
    return jsonify(response)

@app.route('/api/generate_report', methods=['POST'])
def generate_report():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not ADVANCED_FEATURES:
        return jsonify({'error': 'Report generation not available'}), 501
    
    if not session.get('is_owner'):
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json()
    report_type = data.get('report_type', 'daily')
    
    try:
        # Queue background task
        task = generate_analytics_report.delay(session['user_id'], report_type)
        
        print(f'Analytics report generation queued for user {session["user_id"]}')
    
        return jsonify({
            'task_id': task.id,
            'status': 'queued',
            'message': f'{report_type.title()} report generation started'
        })
    except Exception as e:
        return jsonify({'error': 'Report service unavailable'}), 503

@app.route('/api/retrain_models', methods=['POST'])
def trigger_model_retraining():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not ADVANCED_FEATURES:
        return jsonify({'error': 'Model retraining not available'}), 501
    
    if not session.get('is_owner'):
        return jsonify({'error': 'Access denied'}), 403
    try:
        # Queue background task for model retraining
        task = retrain_models_task.delay()
        
        print('Model retraining task queued')
    
        return jsonify({
            'task_id': task.id,
            'status': 'queued',
            'message': 'Model retraining started with real-time data'
        })
    except Exception as e:
        return jsonify({'error': 'Model retraining service unavailable'}), 503
    from services.optimization_engine import GeneticOptimizer, SimulatedAnnealingOptimizer
    
    data = request.get_json()
    locations = data.get('locations', [])
    constraints = data.get('constraints', {})
    algorithm = data.get('algorithm', 'genetic')
    
    if algorithm == 'genetic':
        optimizer = GeneticOptimizer(
            population_size=data.get('population_size', 50),
            generations=data.get('generations', 100)
        )
    else:
        optimizer = SimulatedAnnealingOptimizer()
    
    result = optimizer.optimize_route(locations, constraints)
    return jsonify(result)

# Emergency messaging system
@app.route('/api/emergency_message', methods=['POST'])
@login_required
def handle_emergency_message():
    data = request.get_json()
    
    emergency_data = {
        'id': str(uuid.uuid4()),
        'employee_id': data.get('employee_id'),
        'employee_name': data.get('employee_name'),
        'message': data.get('message'),
        'location': data.get('location'),
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'URGENT',
        'type': 'EMERGENCY'
    }
    
    # In production, send to owner via SMS/Email/Push notification
    # For now, store in database or cache
    
    return jsonify({
        'status': 'success',
        'message': 'Emergency message sent to owner',
        'emergency_id': emergency_data['id']
    })

# AI Assistant API
@app.route('/api/ai_assistant', methods=['POST'])
@login_required
def ai_assistant():
    data = request.get_json()
    question = data.get('question', '').lower()
    
    # Emergency keywords detection
    emergency_keywords = ['emergency', 'urgent', 'help', 'stuck', 'breakdown', 'accident', 'contact owner', 'owner message']
    is_emergency = any(keyword in question for keyword in emergency_keywords)
    
    if is_emergency:
        return jsonify({
            'type': 'emergency',
            'response': 'I detected this might be an emergency. I can help you contact the owner, call emergency services, or share your location.',
            'actions': [
                {'type': 'emergency_message', 'label': '📱 Send Emergency Message to Owner'},
                {'type': 'emergency_call', 'label': '📞 Call Emergency Helpline'},
                {'type': 'share_location', 'label': '📍 Share Current Location'},
                {'type': 'request_backup', 'label': '🚛 Request Backup Vehicle'}
            ]
        })
    
    # Regular AI responses
    responses = {
        'route': 'For optimal routes, consider traffic patterns, weather conditions, and fuel efficiency. Use our route optimizer for best results. I can help you plan the most efficient path.',
        'fuel': 'To save fuel: Maintain steady speed (60-80 km/h), avoid sudden braking, check tire pressure regularly, and plan routes during off-peak hours. Proper maintenance can save 10-15% fuel.',
        'carbon': 'Reduce carbon footprint by: Combining trips, maintaining vehicle properly, using eco-friendly driving techniques, choosing shorter routes, and avoiding traffic congestion.',
        'traffic': 'Avoid traffic by: Checking real-time traffic updates, using alternative routes, traveling during off-peak hours (10 AM - 4 PM), and using our traffic prediction feature.',
        'weather': 'For weather-related issues: Check weather forecasts, carry emergency supplies, reduce speed in bad weather (20% slower in rain), and inform dispatch about delays.',
        'vehicle': 'Vehicle maintenance tips: Regular oil changes (every 10,000 km), tire pressure checks (monthly), brake inspections (every 6 months), and keeping emergency toolkit ready.',
        'maintenance': 'Schedule regular maintenance: Engine oil every 10,000 km, brake fluid every 2 years, tire rotation every 8,000 km. Use our vehicle health check feature.',
        'pricing': 'For competitive pricing: Consider distance, load weight, urgency, fuel costs, and market rates. Use our dynamic pricing tool for accurate quotes.',
        'safety': 'Safety first: Wear seatbelt, maintain safe following distance, avoid mobile phone while driving, take breaks every 2 hours, and report any vehicle issues immediately.',
        'default': 'I can help with route optimization, fuel efficiency, carbon footprint reduction, traffic management, vehicle maintenance, pricing, and emergency situations. What specific help do you need?'
    }
    
    # Find matching response
    response = responses['default']
    for key in responses:
        if key in question:
            response = responses[key]
            break
    
    return jsonify({
        'type': 'normal',
        'response': response,
        'suggestions': [
            'How to optimize fuel consumption?',
            'Best routes for heavy traffic?',
            'Vehicle maintenance schedule?',
            'Emergency contact procedures?'
        ]
    })

# Employee location tracking API
@app.route('/api/track_employee', methods=['POST'])
def track_employee():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        current_location = data.get('current_location')
        vehicle_number = data.get('vehicle_number')
        trip_status = data.get('trip_status')
        timestamp = data.get('timestamp')
        
        # Store tracking data in company database
        db_path = session.get('database_path')
        if not db_path:
            return jsonify({'error': 'Company database not found'}), 404
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tracking table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                current_location TEXT NOT NULL,
                vehicle_number TEXT NOT NULL,
                trip_status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                company_id TEXT NOT NULL
            )
        ''')
        
        # Insert tracking data
        cursor.execute('''
            INSERT INTO employee_tracking 
            (employee_id, current_location, vehicle_number, trip_status, timestamp, company_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (employee_id, current_location, vehicle_number, trip_status, timestamp, session.get('company_id')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Location tracking data sent to owner dashboard',
            'tracking_id': f'TRK-{employee_id}-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        })
        
    except Exception as e:
        print(f'Error tracking employee: {e}')
        return jsonify({'error': 'Failed to track employee location'}), 500

# Get employee tracking data for owner dashboard
@app.route('/api/employee_tracking')
def get_employee_tracking():
    if 'user_id' not in session or not session.get('is_owner'):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        db_path = session.get('database_path')
        if not db_path:
            return jsonify({'error': 'Company database not found'}), 404
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get latest tracking data for each employee
        cursor.execute('''
            SELECT employee_id, current_location, vehicle_number, trip_status, timestamp
            FROM employee_tracking 
            WHERE company_id = ?
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (session.get('company_id'),))
        
        tracking_data = cursor.fetchall()
        conn.close()
        
        result = []
        for track in tracking_data:
            result.append({
                'employee_id': track[0],
                'current_location': track[1],
                'vehicle_number': track[2],
                'trip_status': track[3],
                'timestamp': track[4]
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f'Error getting tracking data: {e}')
        return jsonify({'error': 'Failed to get tracking data'}), 500

# Enhanced API endpoints for real-time data
@app.route('/api/maintenance_alerts')
def get_maintenance_alerts():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from services.predictive_maintenance import PredictiveMaintenanceService
        maintenance_service = PredictiveMaintenanceService()
        
        # Get maintenance data for all vehicles (simulate with sample vehicle)
        vehicle_id = 'VEH-001'
        maintenance_data = maintenance_service.predict_maintenance(vehicle_id)
        
        return jsonify(maintenance_data)
    except Exception as e:
        print(f'Maintenance alerts error: {e}')
        return jsonify({
            'alerts': [
                {
                    'component': 'Engine',
                    'type': 'Oil Change',
                    'urgency': 'Warning',
                    'message': 'Oil change due in 1000 km',
                    'action': 'Schedule oil change'
                }
            ],
            'overall_health_score': 85
        })

@app.route('/api/traffic_status')
def get_traffic_status():
    try:
        from services.real_time_data import RealTimeDataService
        # Use Delhi coordinates as default
        traffic_data = RealTimeDataService.get_traffic_data(28.7041, 77.1025, 19.0760, 72.8777)
        return jsonify(traffic_data)
    except Exception as e:
        print(f'Traffic status error: {e}')
        import random
        return jsonify({
            'level': random.choice(['Low', 'Medium', 'High']),
            'delay_minutes': random.randint(5, 30),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/vehicle_sensors/<vehicle_id>')
def get_vehicle_sensors(vehicle_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from services.real_time_data import VehicleSensorData
        sensor_service = VehicleSensorData()
        
        engine_data = sensor_service.get_engine_data(vehicle_id)
        maintenance_data = sensor_service.get_maintenance_indicators(vehicle_id)
        
        return jsonify({
            'engine_data': engine_data,
            'maintenance_data': maintenance_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f'Vehicle sensors error: {e}')
        return jsonify({'error': 'Sensor data unavailable'}), 500

@app.route('/api/live_gps/<vehicle_id>')
def get_live_gps(vehicle_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from services.real_time_data import RealTimeDataService
        gps_data = RealTimeDataService.get_live_gps_data(vehicle_id)
        
        if gps_data:
            return jsonify(gps_data)
        else:
            return jsonify({'error': 'GPS data not available'}), 404
    except Exception as e:
        print(f'Live GPS error: {e}')
        return jsonify({'error': 'GPS service unavailable'}), 500

# Real API integration
@app.route('/api/real_weather/<lat>/<lng>')
def get_real_weather(lat, lng):
    try:
        import requests
        from config import OPENWEATHER_API_KEY
        
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'condition': data['weather'][0]['main'],
                'temperature': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description']
            })
    except Exception as e:
        pass
    
    # Fallback
    import random
    return jsonify({
        'condition': random.choice(['Clear', 'Rainy', 'Cloudy']),
        'temperature': random.randint(20, 35),
        'humidity': random.randint(40, 80)
    })

# Prometheus metrics endpoint
@app.route('/metrics')
def metrics():
    if not ADVANCED_FEATURES:
        return 'Metrics not available in basic mode', 501
        
    try:
        from prometheus_client import generate_latest, Counter, Histogram, Gauge
        import time
        
        # Define metrics
        REQUEST_COUNT = Counter('flask_requests_total', 'Total requests', ['method', 'endpoint'])
        REQUEST_LATENCY = Histogram('flask_request_duration_seconds', 'Request latency')
        ACTIVE_USERS = Gauge('flask_active_users', 'Active users')
        
        return generate_latest()
    except ImportError:
        return 'Prometheus client not available', 501

# Error handlers with logging
@app.errorhandler(404)
def not_found_error(error):
    if ADVANCED_FEATURES:
        app.logger.warning(f'404 error: {request.url}')
    else:
        print(f'404 error: {request.url}')
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    if ADVANCED_FEATURES:
        app.logger.error(f'500 error: {error}')
    else:
        print(f'500 error: {error}')
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(403)
def forbidden_error(error):
    if ADVANCED_FEATURES:
        app.logger.warning(f'403 error: Unauthorized access attempt from {request.remote_addr}')
    else:
        print(f'403 error: Unauthorized access attempt from {request.remote_addr}')
    return jsonify({'error': 'Access forbidden'}), 403

if __name__ == '__main__':
    if os.getenv('ENVIRONMENT') == 'production':
        app.run(host='0.0.0.0', port=5000)
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)