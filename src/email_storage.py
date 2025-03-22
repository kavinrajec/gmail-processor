import sqlite3
from datetime import datetime
import time
from typing import List, Dict
import json
import logging

class EmailStorage:
    """Manages email storage in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with the necessary tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Email storage table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    message_id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    from_email TEXT,
                    subject TEXT,
                    date_received INTEGER,  -- Unix timestamp
                    labels TEXT,            -- JSON-encoded list
                    message TEXT            -- Email body/content
                )
            ''')
            
            # Create an index on date_received for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_date_received ON emails(date_received)')
            
            # Create an index on thread_id for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_thread_id ON emails(thread_id)')

    def save_email(self, email: Dict) -> int:
        """Store a single email in the database and return its date.
        
        Args:
            email: Single email dictionary with message details
            
        Returns:
            Unix timestamp of the email's received date
        """
        date_str = email['date_received'].split(' (')[0]  # Remove anything like "(UTC)"
        
        # List of date formats to try
        date_formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # Standard RFC format: 'Mon, 15 Mar 2023 10:30:45 +0000'
            '%d %b %Y %H:%M:%S %z',      # Format without weekday: '29 Nov 2024 09:39:18 +0000'
        ]
        
        date = None
        for date_format in date_formats:
            try:
                date = int(datetime.strptime(date_str, date_format).timestamp())
                break  # Successfully parsed the date, exit the loop
            except ValueError:
                continue  # Try the next format
        
        if date is None:
            logging.warning("Failed to parse date '%s' with any known format. Using current time as fallback.", email['date_received'])
            date = int(time.time())  # Final fallback to current timestamp
            
        message_content = email.get('message', '')
            
        with sqlite3.connect(self.db_path) as conn:
            # Use UPSERT to insert new email or update only the labels if it already exists
            conn.execute('''
                INSERT INTO emails (message_id, thread_id, from_email, subject, date_received, labels, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET labels = excluded.labels
            ''', (email['message_id'], email.get('thread_id', ''), email['from'], email['subject'], date, json.dumps(email['labels']), message_content))
            conn.commit()
            
        logging.debug("Saved/updated email with ID %s to database", email['message_id'])
        return date
        
    def save_emails(self, emails: List[Dict]):
        """Store multiple emails in the database."""
        if not emails:
            logging.info("No emails to save")
            return
            
        with sqlite3.connect(self.db_path) as conn:
            for email in emails:
                date_str = email['date_received'].split(' (')[0]  # Remove anything like "(UTC)"
                
                # List of date formats to try
                date_formats = [
                    '%a, %d %b %Y %H:%M:%S %z',  # Standard RFC format: 'Mon, 15 Mar 2023 10:30:45 +0000'
                    '%d %b %Y %H:%M:%S %z',      # Format without weekday: '29 Nov 2024 09:39:18 +0000'
                ]
                
                date = None
                for date_format in date_formats:
                    try:
                        date = int(datetime.strptime(date_str, date_format).timestamp())
                        break  # Successfully parsed the date, exit the loop
                    except ValueError:
                        continue  # Try the next format
                
                if date is None:
                    logging.warning("Failed to parse date '%s' with any known format. Using current time as fallback.", email['date_received'])
                    date = int(time.time())  # Final fallback to current timestamp
                
                message_content = email.get('message', '')
                
                # Use UPSERT to insert new email or update only the labels if it already exists
                conn.execute('''
                    INSERT INTO emails (message_id, thread_id, from_email, subject, date_received, labels, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(message_id) DO UPDATE SET labels = excluded.labels
                ''', (email['message_id'], email.get('thread_id', ''), email['from'], email['subject'], date, json.dumps(email['labels']), message_content))
            conn.commit()
            logging.info("Successfully processed %d emails (new or updated) in database", len(emails))

    def get_all_emails(self) -> List[tuple]:
        """Retrieve all stored emails."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM emails')
            return cursor.fetchall()
