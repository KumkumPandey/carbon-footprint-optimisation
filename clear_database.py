import os
import sqlite3

def clear_database():
    """Clear all data from the SQLite database"""
    db_path = 'users.db'
    
    if os.path.exists(db_path):
        try:
            # Connect to database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Clear all tables
            for table in tables:
                table_name = table[0]
                if table_name != 'sqlite_sequence':  # Skip system table
                    cursor.execute(f"DELETE FROM {table_name}")
                    print(f"Cleared table: {table_name}")
            
            # Reset auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence")
            
            # Commit changes
            conn.commit()
            conn.close()
            
            print("Database cleared successfully!")
            print("All user, customer, truck, and location data has been deleted.")
            
        except Exception as e:
            print(f"Error clearing database: {e}")
    else:
        print("Database file not found. Nothing to clear.")

if __name__ == "__main__":
    print("Clearing all database data...")
    clear_database()