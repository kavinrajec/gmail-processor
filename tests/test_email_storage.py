import unittest
import os
import sqlite3
import json
from datetime import datetime
from src.email_storage import EmailStorage

class TestEmailStorage(unittest.TestCase):
    def setUp(self):
        # Use a test database file
        self.test_db_path = 'test_email.db'
        
        # Create a new storage instance for each test
        self.storage = EmailStorage(self.test_db_path)
        
        # Sample email data with message content
        self.sample_email = {
            'message_id': 'test-msg-001',
            "thread_id": "test-thread-001",
            'from': 'sender@example.com',
            'subject': 'Test Email Subject',
            'date_received': 'Mon, 22 Mar 2025 10:00:00 +0000',
            'labels': ['INBOX', 'UNREAD'],
            'message': 'This is the body content of the test email message.'
        }
        
    def tearDown(self):
        # Clean up the test database after each test
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def test_db_initialization(self):
        """Test that the database is properly initialized with the expected schema."""
        # Connect directly to the database to check schema
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(emails)")
            columns = {info[1] for info in cursor.fetchall()}
            
            # Check that all expected columns exist
            expected_columns = {'message_id', 'thread_id', 'from_email', 'subject', 'date_received', 'labels', 'message'}
            for col in expected_columns:
                self.assertIn(col, columns, f"Column {col} is missing from the schema")
    
    def test_save_and_retrieve_email_with_message(self):
        """Test saving and retrieving an email with message content."""
        # Save the sample email
        timestamp = self.storage.save_email(self.sample_email)
        
        # Verify the timestamp was calculated correctly
        expected_date = datetime.strptime('Mon, 22 Mar 2025 10:00:00 +0000', '%a, %d %b %Y %H:%M:%S %z')
        self.assertEqual(timestamp, int(expected_date.timestamp()))
        
        # Retrieve all emails and check contents
        emails = self.storage.get_all_emails()
        self.assertEqual(len(emails), 1, "Expected one email in storage")
        
        # Check that the retrieved email has all the expected fields
        email = emails[0]  # Get the first (and only) email
        
        # Unpack the email tuple
        msg_id, thread_id, from_email, subject, date_received, labels_json, message = email
        
        self.assertEqual(msg_id, self.sample_email['message_id'])
        self.assertEqual(from_email, self.sample_email['from'])
        self.assertEqual(subject, self.sample_email['subject'])
        self.assertEqual(date_received, timestamp)
        self.assertEqual(json.loads(labels_json), self.sample_email['labels'])
        self.assertEqual(message, self.sample_email['message'])
    
    def test_multiple_emails_storage(self):
        """Test storing and retrieving multiple emails with message content."""
        # Create additional sample emails
        emails = [
            self.sample_email,
            {
                'message_id': 'test-msg-002',
                'thread_id': 'test-thread-002',
                'from': 'another@example.com',
                'subject': 'Another Test Email',
                'date_received': 'Tue, 23 Mar 2025 11:00:00 +0000',
                'labels': ['INBOX'],
                'message': 'Another test message with different content.'
            },
            {
                'message_id': 'test-msg-003',
                'thread_id': 'test-thread-003',
                    'from': 'third@example.com',
                'subject': 'Third Test Email',
                'date_received': 'Wed, 24 Mar 2025 12:00:00 +0000',
                'labels': ['INBOX', 'IMPORTANT'],
                'message': 'This is the third test message with unique content.'
            }
        ]
        
        # Save multiple emails at once
        self.storage.save_emails(emails)
        
        # Retrieve all emails and check the count
        stored_emails = self.storage.get_all_emails()
        self.assertEqual(len(stored_emails), 3, "Expected three emails in storage")
        
        # Check that message content is preserved for all emails
        message_contents = [email[6] for email in stored_emails]  # Index 6 is the message field (after adding thread_id)
        for email in emails:
            self.assertIn(email['message'], message_contents, 
                         f"Message content '{email['message']}' not found in stored emails")
    
    def test_date_parsing_formats(self):
        """Test that various date formats are parsed correctly."""
        # Test different date formats
        date_formats = [
            ('Mon, 22 Mar 2025 10:00:00 +0000', '%a, %d %b %Y %H:%M:%S %z'),  # Standard format
            ('22 Mar 2025 10:00:00 +0000', '%d %b %Y %H:%M:%S %z')  # Format without weekday
        ]
        
        for date_str, format_str in date_formats:
            # Create a new email with this date format
            email = self.sample_email.copy()
            email['message_id'] = f"date-test-{date_str}"
            email['date_received'] = date_str
            
            # Save the email
            timestamp = self.storage.save_email(email)
            
            # Verify timestamp conversion
            expected_date = datetime.strptime(date_str, format_str)
            expected_timestamp = int(expected_date.timestamp())
            self.assertEqual(timestamp, expected_timestamp, 
                             f"Date '{date_str}' was not parsed correctly")

if __name__ == '__main__':
    unittest.main()