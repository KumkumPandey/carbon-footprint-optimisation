from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from database_manager import DatabaseManager
import sqlite3
import os

class CompanySelector:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def register_new_company(self, company_data):
        """Register a new company with separate database"""
        try:
            print(f"Starting company registration for: {company_data['company_name']}")
            
            # Create company database
            result = self.db_manager.create_company_database(
                company_data['company_name'],
                company_data['owner_name']
            )
            
            print(f"Database creation result: {result}")
            
            if result:
                # Add company_id to company_data for owner creation
                company_data['company_id'] = result['company_id']
                print(f"Company ID set: {result['company_id']}")
                return result
            
            print("Failed to create company database")
            return None
            
        except Exception as e:
            print(f"Error registering company: {e}")
            return None
    
    def create_owner_user(self, db_path, company_data):
        """Create owner user in company database"""
        try:
            print(f"Creating owner user with data: {company_data}")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            from werkzeug.security import generate_password_hash
            
            # Generate owner ID using company name prefix
            company_name = company_data.get('company_name', '')
            if len(company_name) >= 3:
                company_code = company_name[:3].upper()
            else:
                company_code = company_name.upper().ljust(3, 'X')
            
            owner_id = f"OWN-{company_code}-001"
            
            print(f"Creating owner user: {owner_id} for company: {company_name}")
            
            # Check if table exists and has correct structure
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"Users table columns: {columns}")
            
            # Insert owner user
            cursor.execute('''
                INSERT INTO users (user_id, username, phone_no, email, password_hash, is_owner, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                owner_id,
                company_data.get('owner_name', ''),
                company_data.get('phone', ''),
                company_data.get('email', ''),
                generate_password_hash(company_data.get('password', '')),
                1,  # Use 1 instead of True for SQLite compatibility
                'active'
            ))
            
            conn.commit()
            
            # Verify insertion
            cursor.execute('SELECT user_id, username FROM users WHERE user_id = ?', (owner_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                print(f"Owner user created successfully: {owner_id} - {result[1]}")
                return owner_id
            else:
                print("Failed to verify owner user creation")
                return None
            
        except Exception as e:
            print(f"Error creating owner user: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def authenticate_user(self, user_id, password):
        """Authenticate user and return company database info"""
        try:
            print(f"Authenticating user: {user_id}")
            
            # Extract company ID from user ID (format: OWN-XXXX-001 or EMP-XXXX-001)
            if '-' in user_id:
                parts = user_id.split('-')
                if len(parts) >= 2:
                    company_prefix = parts[1]
                    print(f"Company prefix: {company_prefix}")
                    
                    # Find company database
                    companies = self.db_manager.list_all_companies()
                    print(f"Available companies: {[c['company_id'] for c in companies]}")
                    
                    for company in companies:
                        # Check both with and without 'C' prefix
                        if (company['company_id'].startswith('C' + company_prefix) or 
                            company['company_id'].startswith(company_prefix) or
                            company_prefix in company['company_id']):
                            
                            print(f"Found matching company: {company['company_id']}")
                            db_path = self.db_manager.get_company_database_path(company['company_id'])
                            
                            # Authenticate user in company database
                            user_info = self.verify_user_credentials(db_path, user_id, password)
                            if user_info:
                                user_info['company_info'] = company
                                user_info['database_path'] = db_path
                                print(f"Authentication successful for {user_id}")
                                return user_info
            
            print(f"Authentication failed for {user_id}")
            return None
            
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    def verify_user_credentials(self, db_path, user_id, password):
        """Verify user credentials in company database"""
        try:
            print(f"Verifying credentials for {user_id} in {db_path}")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # First check if user exists
            cursor.execute('SELECT user_id, username, password_hash, is_owner, email, phone_no FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"User {user_id} not found in database")
                # List all users for debugging
                cursor.execute('SELECT user_id FROM users')
                all_users = cursor.fetchall()
                print(f"Available users: {[u[0] for u in all_users]}")
                conn.close()
                return None
            
            print(f"User found: {result[0]}, checking password...")
            
            from werkzeug.security import check_password_hash
            
            if check_password_hash(result[2], password):
                print(f"Password verified for {user_id}")
                conn.close()
                return {
                    'user_id': result[0],
                    'username': result[1],
                    'is_owner': bool(result[3]),
                    'email': result[4],
                    'phone': result[5]
                }
            else:
                print(f"Password verification failed for {user_id}")
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"Error verifying credentials: {e}")
            return None
    
    def get_company_by_id(self, company_id):
        """Get company information by ID"""
        companies = self.db_manager.list_all_companies()
        for company in companies:
            if company['company_id'] == company_id:
                return company
        return None
    
    def add_employee_to_company(self, company_id, employee_data):
        """Add employee to specific company database"""
        try:
            db_path = self.db_manager.get_company_database_path(company_id)
            if not db_path:
                return None
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Generate employee ID
            cursor.execute('SELECT COUNT(*) FROM employees')
            emp_count = cursor.fetchone()[0] + 1
            employee_id = f"EMP-{company_id[1:5]}-{emp_count:03d}"
            
            # Insert employee
            cursor.execute('''
                INSERT INTO employees (name, employee_id, phone, license_number, aadhar_number, address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                employee_data['name'],
                employee_id,
                employee_data.get('phone', ''),
                employee_data.get('license', ''),
                employee_data.get('aadhar', ''),
                employee_data.get('address', '')
            ))
            
            # Create user account for employee
            from werkzeug.security import generate_password_hash
            
            cursor.execute('''
                INSERT INTO users (user_id, username, phone_no, password_hash, is_owner)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                employee_id,
                employee_data['name'],
                employee_data.get('phone', ''),
                generate_password_hash(employee_data.get('password', 'employee123')),
                False
            ))
            
            conn.commit()
            conn.close()
            
            return employee_id
            
        except Exception as e:
            print(f"Error adding employee: {e}")
            return None