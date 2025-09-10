import os
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
import uuid

class DatabaseManager:
    def __init__(self):
        self.databases_dir = 'company_databases'
        if not os.path.exists(self.databases_dir):
            os.makedirs(self.databases_dir)
    
    def generate_company_id(self):
        """Generate unique company ID"""
        return f"C{str(uuid.uuid4())[:8].upper()}"
    
    def create_company_database(self, company_name, owner_name):
        """Create separate database for each company"""
        company_id = self.generate_company_id()
        db_name = f"{company_id}_{company_name.replace(' ', '_')}.db"
        db_path = os.path.join(self.databases_dir, db_name)
        
        try:
            # Create database connection
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create company info table
            cursor.execute('''
                CREATE TABLE company_info (
                    id INTEGER PRIMARY KEY,
                    company_id TEXT UNIQUE NOT NULL,
                    company_name TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Create users table (owners and employees)
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    phone_no TEXT,
                    email TEXT UNIQUE,
                    working_area TEXT,
                    dob TEXT,
                    password_hash TEXT NOT NULL,
                    is_owner BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Create employees table
            cursor.execute('''
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    employee_id TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    license_number TEXT,
                    aadhar_number TEXT,
                    address TEXT,
                    truck_id TEXT,
                    hired_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Create customers table
            cursor.execute('''
                CREATE TABLE customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT,
                    photo_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Create trucks table
            cursor.execute('''
                CREATE TABLE trucks (
                    id INTEGER PRIMARY KEY,
                    truck_number TEXT UNIQUE NOT NULL,
                    driver_name TEXT NOT NULL,
                    current_location TEXT,
                    destination TEXT,
                    status TEXT DEFAULT 'Available',
                    dispatch_time TIMESTAMP,
                    lat REAL,
                    lng REAL,
                    fuel_capacity REAL,
                    load_capacity REAL
                )
            ''')
            
            # Create trips table
            cursor.execute('''
                CREATE TABLE trips (
                    id INTEGER PRIMARY KEY,
                    employee_id INTEGER,
                    truck_id INTEGER,
                    start_location TEXT,
                    end_location TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    distance_km REAL,
                    carbon_footprint REAL,
                    fuel_consumed REAL,
                    route_data TEXT,
                    status TEXT DEFAULT 'planned',
                    FOREIGN KEY (employee_id) REFERENCES employees (id),
                    FOREIGN KEY (truck_id) REFERENCES trucks (id)
                )
            ''')
            
            # Create analytics table
            cursor.execute('''
                CREATE TABLE analytics (
                    id INTEGER PRIMARY KEY,
                    date DATE,
                    total_trips INTEGER DEFAULT 0,
                    total_distance REAL DEFAULT 0,
                    total_carbon REAL DEFAULT 0,
                    total_fuel REAL DEFAULT 0,
                    efficiency_score REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert company info
            cursor.execute('''
                INSERT INTO company_info (company_id, company_name, owner_name)
                VALUES (?, ?, ?)
            ''', (company_id, company_name, owner_name))
            
            conn.commit()
            conn.close()
            
            print(f"Company database created: {db_name}")
            return {
                'company_id': company_id,
                'database_path': db_path,
                'database_name': db_name
            }
            
        except Exception as e:
            print(f"Error creating company database: {e}")
            return None
    
    def get_company_database_path(self, company_id):
        """Get database path for a company"""
        for filename in os.listdir(self.databases_dir):
            if filename.startswith(company_id):
                return os.path.join(self.databases_dir, filename)
        return None
    
    def list_all_companies(self):
        """List all registered companies"""
        companies = []
        
        for filename in os.listdir(self.databases_dir):
            if filename.endswith('.db'):
                db_path = os.path.join(self.databases_dir, filename)
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute('SELECT company_id, company_name, owner_name, created_at FROM company_info LIMIT 1')
                    result = cursor.fetchone()
                    if result:
                        companies.append({
                            'company_id': result[0],
                            'company_name': result[1],
                            'owner_name': result[2],
                            'created_at': result[3],
                            'database_file': filename
                        })
                    conn.close()
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
        
        return companies
    
    def delete_company_database(self, company_id):
        """Delete company database"""
        db_path = self.get_company_database_path(company_id)
        if db_path and os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"Company database deleted: {company_id}")
                return True
            except Exception as e:
                print(f"Error deleting database: {e}")
                return False
        return False
    
    def get_company_stats(self, company_id):
        """Get statistics for a company"""
        db_path = self.get_company_database_path(company_id)
        if not db_path:
            return None
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get counts
            cursor.execute('SELECT COUNT(*) FROM employees WHERE status = "active"')
            employee_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM customers WHERE status = "active"')
            customer_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM trucks')
            truck_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM trips')
            trip_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'employees': employee_count,
                'customers': customer_count,
                'trucks': truck_count,
                'trips': trip_count
            }
            
        except Exception as e:
            print(f"Error getting company stats: {e}")
            return None