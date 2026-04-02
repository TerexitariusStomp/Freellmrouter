import time
import json
import sqlite3
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from .registry import Provider
import logging

logger = logging.getLogger(__name__)


@dataclass
class QuotaInfo:
    """Information about a provider's quota/credits"""
    provider_id: str
    requests_used_today: int = 0
    tokens_used_today: int = 0
    last_request_time: float = 0.0
    last_429_time: float = 0.0
    consecutive_failures: int = 0
    estimated_credit_remaining: float = 1.0  # Ratio 0.0-1.0
    quota_reset_time: float = 0.0  # Unix timestamp for quota reset
    is_unlimited: bool = False


class QuotaManager:
    """Manages quota and credit tracking for providers"""
    
    def __init__(self, db_path: str = "quota.db"):
        self.db_path = db_path
        self._in_memory_cache: Dict[str, QuotaInfo] = {}
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database for quota tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create quota table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS provider_quota (
                provider_id TEXT PRIMARY KEY,
                requests_used_today INTEGER DEFAULT 0,
                tokens_used_today INTEGER DEFAULT 0,
                last_request_time REAL DEFAULT 0,
                last_429_time REAL DEFAULT 0,
                consecutive_failures INTEGER DEFAULT 0,
                estimated_credit_remaining REAL DEFAULT 1.0,
                quota_reset_time REAL DEFAULT 0,
                is_unlimited BOOLEAN DEFAULT 0,
                updated_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # Create request log table for detailed tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id TEXT,
                timestamp REAL,
                success BOOLEAN,
                status_code INTEGER,
                tokens_used INTEGER DEFAULT 0,
                response_time REAL,
                FOREIGN KEY (provider_id) REFERENCES provider_quota (provider_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Load existing quota info into cache
        self._load_all_quota_info()
    
    def _load_all_quota_info(self):
        """Load all quota information from database into cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM provider_quota')
        rows = cursor.fetchall()
        
        for row in rows:
            quota_info = QuotaInfo(
                provider_id=row[0],
                requests_used_today=row[1],
                tokens_used_today=row[2],
                last_request_time=row[3],
                last_429_time=row[4],
                consecutive_failures=row[5],
                estimated_credit_remaining=row[6],
                quota_reset_time=row[7],
                is_unlimited=bool(row[8])
            )
            self._in_memory_cache[quota_info.provider_id] = quota_info
        
        conn.close()
    
    def get_quota_info(self, provider_id: str) -> QuotaInfo:
        """Get quota information for a provider"""
        if provider_id in self._in_memory_cache:
            return self._in_memory_cache[provider_id]
        
        # If not in cache, load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM provider_quota WHERE provider_id = ?', (provider_id,))
        row = cursor.fetchone()
        
        if row:
            quota_info = QuotaInfo(
                provider_id=row[0],
                requests_used_today=row[1],
                tokens_used_today=row[2],
                last_request_time=row[3],
                last_429_time=row[4],
                consecutive_failures=row[5],
                estimated_credit_remaining=row[6],
                quota_reset_time=row[7],
                is_unlimited=bool(row[8])
            )
            self._in_memory_cache[provider_id] = quota_info
            conn.close()
            return quota_info
        
        conn.close()
        
        # If still not found, create default quota info
        quota_info = QuotaInfo(provider_id=provider_id)
        self._in_memory_cache[provider_id] = quota_info
        self._save_quota_info(quota_info)
        return quota_info
    
    def _save_quota_info(self, quota_info: QuotaInfo):
        """Save quota information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO provider_quota 
            (provider_id, requests_used_today, tokens_used_today, last_request_time, 
             last_429_time, consecutive_failures, estimated_credit_remaining, 
             quota_reset_time, is_unlimited, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            quota_info.provider_id,
            quota_info.requests_used_today,
            quota_info.tokens_used_today,
            quota_info.last_request_time,
            quota_info.last_429_time,
            quota_info.consecutive_failures,
            quota_info.estimated_credit_remaining,
            quota_info.quota_reset_time,
            quota_info.is_unlimited,
            time.time()
        ))
        
        conn.commit()
        conn.close()
    
    def record_request(self, provider_id: str, success: bool, 
                      status_code: int = 200, tokens_used: int = 0,
                      response_time: float = 0.0):
        """Record a request made to a provider"""
        quota_info = self.get_quota_info(provider_id)
        
        # Update quota info
        quota_info.requests_used_today += 1
        quota_info.tokens_used_today += tokens_used
        quota_info.last_request_time = time.time()
        
        if not success:
            quota_info.consecutive_failures += 1
            if status_code == 429:
                quota_info.last_429_time = time.time()
        else:
            quota_info.consecutive_failures = 0  # Reset on success
        
        # Estimate credit remaining based on usage patterns
        quota_info.estimated_credit_remaining = self._estimate_credit_remaining(quota_info)
        
        # Save to database and cache
        self._save_quota_info(quota_info)
        self._in_memory_cache[provider_id] = quota_info
        
        # Log detailed request
        self._log_request(provider_id, success, status_code, tokens_used, response_time)
        
        logger.info(f"Recorded request for {provider_id}: success={success}, "
                   f"status={status_code}, tokens={tokens_used}")
    
    def _estimate_credit_remaining(self, quota_info: QuotaInfo) -> float:
        """Estimate credit remaining based on usage patterns"""
        # For unlimited providers, return high value
        if quota_info.is_unlimited:
            return 0.9  # Slightly less than 1.0 to allow for some conservation
        
        # If we have quota reset time and daily limits from provider config,
        # we could calculate more precisely
        # For now, use a simple decay based on usage and failures
        
        # Base estimation on inverse of usage (with minimum)
        usage_factor = min(quota_info.requests_used_today / 1000.0, 0.8)  # Cap at 80% usage penalty
        failure_factor = min(quota_info.consecutive_failures * 0.2, 0.6)  # Cap at 60% failure penalty
        
        # Calculate remaining credit
        remaining = max(0.1, 1.0 - usage_factor - failure_factor)
        return min(1.0, remaining)  # Cap at 1.0
    
    def _log_request(self, provider_id: str, success: bool, 
                    status_code: int, tokens_used: int, response_time: float):
        """Log detailed request information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO request_log 
            (provider_id, timestamp, success, status_code, tokens_used, response_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            provider_id,
            time.time(),
            success,
            status_code,
            tokens_used,
            response_time
        ))
        
        conn.commit()
        conn.close()
    
    def get_quota_data_for_scoring(self) -> Dict[str, Dict]:
        """Get quota data formatted for the scoring system"""
        quota_data = {}
        for provider_id, quota_info in self._in_memory_cache.items():
            quota_data[provider_id] = {
                "requests_used": quota_info.requests_used_today,
                "tokens_used": quota_info.tokens_used_today,
                "last_429_time": quota_info.last_429_time,
                "consecutive_failures": quota_info.consecutive_failures,
                "estimated_credit_remaining": quota_info.estimated_credit_remaining,
                "is_unlimited": quota_info.is_unlimited
            }
        return quota_data
    
    def reset_daily_quota(self, provider_id: Optional[str] = None):
        """Reset daily quota for a provider or all providers"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if provider_id:
            cursor.execute('''
                UPDATE provider_quota 
                SET requests_used_today = 0, 
                    tokens_used_today = 0,
                    updated_at = ?
                WHERE provider_id = ?
            ''', (time.time(), provider_id))
            
            if provider_id in self._in_memory_cache:
                quota_info = self._in_memory_cache[provider_id]
                quota_info.requests_used_today = 0
                quota_info.tokens_used_today = 0
                self._save_quota_info(quota_info)
        else:
            cursor.execute('''
                UPDATE provider_quota 
                SET requests_used_today = 0, 
                    tokens_used_today = 0,
                    updated_at = ?
            ''', (time.time(),))
            
            # Update cache
            for quota_info in self._in_memory_cache.values():
                quota_info.requests_used_today = 0
                quota_info.tokens_used_today = 0
                self._save_quota_info(quota_info)
        
        conn.commit()
        conn.close()
        logger.info(f"Reset daily quota for {'provider ' + provider_id if provider_id else 'all providers'}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get overall usage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get total requests today
        cursor.execute('SELECT SUM(requests_used_today) FROM provider_quota')
        total_requests = cursor.fetchone()[0] or 0
        
        # Get total tokens today
        cursor.execute('SELECT SUM(tokens_used_today) FROM provider_quota')
        total_tokens = cursor.fetchone()[0] or 0
        
        # Get provider breakdown
        cursor.execute('''
            SELECT provider_id, requests_used_today, tokens_used_today, 
                   estimated_credit_remaining
            FROM provider_quota
            ORDER BY requests_used_today DESC
        ''')
        provider_stats = []
        for row in cursor.fetchall():
            provider_stats.append({
                "provider_id": row[0],
                "requests_used_today": row[1],
                "tokens_used_today": row[2],
                "estimated_credit_remaining": row[3]
            })
        
        conn.close()
        
        return {
            "total_requests_today": total_requests,
            "total_tokens_today": total_tokens,
            "provider_stats": provider_stats
        }


# Global quota manager instance
quota_manager = QuotaManager()