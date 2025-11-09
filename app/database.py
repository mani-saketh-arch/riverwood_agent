import os
import mysql.connector
from mysql.connector import pooling
from typing import Optional, List, Dict, Tuple
from datetime import datetime, time
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        """Initialize MySQL connection pool with SSL"""
        # Parse DATABASE_URL if provided, else use individual vars
        database_url = os.getenv("DATABASE_URL")
        
        if database_url:
            # Parse: mysql+pymysql://user:pass@host:port/database
            import re
            pattern = r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
            match = re.match(pattern, database_url)
            if match:
                user, password, host, port, database = match.groups()
            else:
                raise ValueError("Invalid DATABASE_URL format")
        else:
            # Use individual environment variables
            host = os.getenv("MYSQL_HOST")
            port = int(os.getenv("MYSQL_PORT", 3306))
            user = os.getenv("MYSQL_USER")
            password = os.getenv("MYSQL_PASSWORD")
            database = os.getenv("MYSQL_DATABASE")
        
        # SSL configuration for Aiven
        ssl_config = {
            'ca': os.path.join(os.path.dirname(__file__), '..', 'ca.pem')
        }
        
        self.pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="riverwood_pool",
            pool_size=5,
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            ssl_ca=ssl_config['ca'],
            ssl_verify_cert=True
        )
    
    def get_connection(self):
        """Get connection from pool"""
        return self.pool.get_connection()
    
    # ========== CUSTOMER OPERATIONS ==========
    
    def create_customer(self, phone_number: str, name: str = None, 
                       preferred_language: str = "English",
                       preferred_call_time: str = "09:00:00") -> Optional[int]:
        """Create new customer"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                INSERT INTO customers 
                (phone_number, name, preferred_language, preferred_call_time, is_verified)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (phone_number, name, preferred_language, preferred_call_time, True))
            conn.commit()
            
            customer_id = cursor.lastrowid
            cursor.close()
            conn.close()
            return customer_id
            
        except mysql.connector.IntegrityError:
            # Customer already exists
            return None
        except Exception as e:
            print(f"Error creating customer: {e}")
            return None
    
    def get_customer_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get customer by phone number"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = "SELECT * FROM customers WHERE phone_number = %s"
            cursor.execute(query, (phone_number,))
            customer = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return customer
            
        except Exception as e:
            print(f"Error fetching customer: {e}")
            return None
    
    def verify_customer(self, phone_number: str, twilio_verified: bool = True) -> bool:
        """Mark customer as verified"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                UPDATE customers 
                SET is_verified = %s, twilio_verified = %s
                WHERE phone_number = %s
            """
            cursor.execute(query, (True, twilio_verified, phone_number))
            conn.commit()
            
            success = cursor.rowcount > 0
            cursor.close()
            conn.close()
            return success
            
        except Exception as e:
            print(f"Error verifying customer: {e}")
            return False
    
    def update_customer_preferences(self, phone_number: str, 
                                   preferred_language: str = None,
                                   preferred_call_time: str = None) -> bool:
        """Update customer preferences"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            updates = []
            values = []
            
            if preferred_language:
                updates.append("preferred_language = %s")
                values.append(preferred_language)
            
            if preferred_call_time:
                updates.append("preferred_call_time = %s")
                values.append(preferred_call_time)
            
            if not updates:
                return False
            
            values.append(phone_number)
            query = f"UPDATE customers SET {', '.join(updates)} WHERE phone_number = %s"
            
            cursor.execute(query, tuple(values))
            conn.commit()
            
            success = cursor.rowcount > 0
            cursor.close()
            conn.close()
            return success
            
        except Exception as e:
            print(f"Error updating preferences: {e}")
            return False
    
    def get_all_verified_customers(self) -> List[Dict]:
        """Get all verified and active customers"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT * FROM customers 
                WHERE is_verified = TRUE AND is_active = TRUE
            """
            cursor.execute(query)
            customers = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return customers
            
        except Exception as e:
            print(f"Error fetching customers: {e}")
            return []
    
    def get_customers_for_calling(self, target_time: str = None) -> List[Dict]:
        """Get customers ready for calling at specific time"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if target_time:
                query = """
                    SELECT * FROM customers 
                    WHERE is_verified = TRUE 
                    AND is_active = TRUE 
                    AND twilio_verified = TRUE
                    AND preferred_call_time = %s
                """
                cursor.execute(query, (target_time,))
            else:
                query = """
                    SELECT * FROM customers 
                    WHERE is_verified = TRUE 
                    AND is_active = TRUE 
                    AND twilio_verified = TRUE
                """
                cursor.execute(query)
            
            customers = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return customers
            
        except Exception as e:
            print(f"Error fetching customers for calling: {e}")
            return []
    
    # ========== CALL LOG OPERATIONS ==========
    
    def create_call_log(self, customer_id: int, call_sid: str, 
                       call_status: str, call_duration: int = 0,
                       conversation_summary: str = None,
                       language_used: str = None) -> bool:
        """Create call log entry"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                INSERT INTO call_logs 
                (customer_id, call_sid, call_status, call_duration, 
                 conversation_summary, language_used)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (customer_id, call_sid, call_status, 
                                 call_duration, conversation_summary, language_used))
            conn.commit()
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error creating call log: {e}")
            return False
    
    def get_call_history(self, phone_number: str, limit: int = 10) -> List[Dict]:
        """Get call history for a customer"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT cl.* FROM call_logs cl
                JOIN customers c ON cl.customer_id = c.id
                WHERE c.phone_number = %s
                ORDER BY cl.call_date DESC
                LIMIT %s
            """
            cursor.execute(query, (phone_number, limit))
            logs = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return logs
            
        except Exception as e:
            print(f"Error fetching call history: {e}")
            return []
    
    # ========== OTP OPERATIONS ==========
    
    def create_otp_verification(self, phone_number: str, verification_sid: str) -> bool:
        """Store OTP verification request"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                INSERT INTO otp_verifications 
                (phone_number, verification_sid)
                VALUES (%s, %s)
            """
            cursor.execute(query, (phone_number, verification_sid))
            conn.commit()
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error creating OTP verification: {e}")
            return False
    
    def mark_otp_verified(self, phone_number: str) -> bool:
        """Mark OTP as verified"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                UPDATE otp_verifications 
                SET is_verified = TRUE
                WHERE phone_number = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            cursor.execute(query, (phone_number,))
            conn.commit()
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error marking OTP verified: {e}")
            return False
    
    # ========== CONSTRUCTION UPDATES ==========
    
    def get_latest_construction_updates(self, limit: int = 5) -> List[Dict]:
        """Get latest construction updates"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT * FROM construction_updates 
                WHERE is_active = TRUE
                ORDER BY update_date DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            updates = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return updates
            
        except Exception as e:
            print(f"Error fetching construction updates: {e}")
            return []

# Global database instance
db = Database()