import sqlite3
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PersistenceManager:
    """
    Manages persistence for the router, currently using SQLite.
    Can be extended to support Redis for shared state.
    """
    
    def __init__(self, db_path: str = "router_state.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize the SQLite database"""
        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables for quota, health, and cache if not using dedicated managers
            # (Though currently quota and health have their own persistence)
            
            # For demonstration, we'll create a table for recent route decisions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS route_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    task_type TEXT,
                    prompt TEXT,
                    selected_provider_id TEXT,
                    selected_model TEXT,
                    score REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Initialized persistence database at {self.db_path}")

    def log_route_decision(self, task_type: str, prompt: str, 
                           provider_id: str, model: str, score: float):
        """Log a routing decision"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO route_history 
                (timestamp, task_type, prompt, selected_provider_id, selected_model, score)
                VALUES (strftime('%s', 'now'), ?, ?, ?, ?, ?)
            ''', (task_type, prompt, provider_id, model, score))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging route decision: {e}")

# Global persistence instance
persistence_manager = PersistenceManager()
