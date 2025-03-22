import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
from datetime import datetime, timedelta
from src.gmail_client import GmailClient
from src.email_storage import EmailStorage
from src.rule_engine import RuleEngine
from src.main import main

class TestIntegration(unittest.TestCase):
    """Integration tests for the Gmail Processor application."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary paths for testing
        self.test_db_path = 'test_integration.db'
        self.test_credentials_path = 'config/credentials.json'
        self.test_token_path = 'config/token.json'
        self.test_rules_path = 'config/test_rules.json'
        
        # Sample emails for testing
        self.sample_emails = [
            {
                'message_id': 'test-msg-001',
                'thread_id': 'test-thread-001',
                'from': 'newsletter@example.com',
                'subject': 'Weekly Newsletter',
                'date_received': datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'),
                'labels': ['INBOX', 'UNREAD'],
                'message': 'This is the weekly newsletter with some updates. Click to unsubscribe.'
            },
            {
                'message_id': 'test-msg-002',
                'thread_id': 'test-thread-002',
                'from': 'test@tenmiles.com',
                'subject': 'Interview Preparation',
                'date_received': datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'),
                'labels': ['INBOX'],
                'message': 'Here are the details for your upcoming interview.'
            },
            {
                'message_id': 'test-msg-003',
                'thread_id': 'test-thread-003',
                'from': 'old@example.com',
                'subject': 'Your Order Confirmation',
                'date_received': (datetime.now() - timedelta(days=45)).strftime('%a, %d %b %Y %H:%M:%S +0000'),
                'labels': ['INBOX', 'UNREAD'],
                'message': 'The invoice attached contains your order details.'
            }
        ]
        
        # Sample rules for testing
        self.sample_rules = [
            {
                "description": "Mark newsletters as read",
                "mode": "any",
                "conditions": [
                    {"field": "from", "predicate": "contains", "value": "newsletter"},
                    {"field": "message", "predicate": "contains", "value": "unsubscribe"}
                ],
                "actions": [
                    {"type": "mark_read"}
                ]
            },
            {
                "description": "Move interview emails",
                "mode": "all",
                "conditions": [
                    {"field": "from", "predicate": "contains", "value": "tenmiles.com"},
                    {"field": "subject", "predicate": "contains", "value": "Interview"}
                ],
                "actions": [
                    {"type": "move_message", "mailbox": "IMPORTANT"}
                ]
            },
            {
                "description": "Handle old invoices",
                "mode": "all",
                "conditions": [
                    {"field": "message", "predicate": "contains", "value": "invoice"},
                    {"field": "date_received", "predicate": "greater_than_days", "value": 30}
                ],
                "actions": [
                    {"type": "mark_read"},
                    {"type": "move_message", "mailbox": "ARCHIVED"}
                ]
            }
        ]

    def tearDown(self):
        """Clean up after tests."""
        # Remove test database if it exists
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
            
        # Remove test rules file if it exists
        if os.path.exists(self.test_rules_path):
            os.remove(self.test_rules_path)

    @patch('src.main.EmailStorage')
    @patch('src.main.GmailClient')
    @patch('src.main.RuleEngine')
    def test_end_to_end_workflow(self, mock_rule_engine_class, mock_client_class, mock_storage_class):
        """Test the end-to-end workflow of fetching, storing, and processing emails."""
        # Set up mocks
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_inbox_emails.return_value = self.sample_emails
        
        mock_engine = MagicMock()
        mock_rule_engine_class.return_value = mock_engine
        
        # Configure get_all_emails to return our sample data
        mock_storage.get_all_emails.return_value = [
            # Convert dict to tuple format that storage would return
            (email['message_id'], email['from'], email['subject'], 
             int(datetime.now().timestamp()), json.dumps(email['labels']), email['message'])
            for email in self.sample_emails
        ]
        
        # Configure evaluate to return appropriate actions for each email
        def evaluate_side_effect(email):
            msg_id = email[0] if isinstance(email, tuple) else email.get('message_id')
            if msg_id == 'test-msg-001':
                return [{"type": "mark_read"}]
            elif msg_id == 'test-msg-002':
                return [{"type": "move_message", "mailbox": "IMPORTANT"}]
            elif msg_id == 'test-msg-003':
                return [{"type": "mark_read"}, {"type": "move_message", "mailbox": "ARCHIVED"}]
            return []
            
        mock_engine.evaluate.side_effect = evaluate_side_effect
        
        # Run the main function
        main(look_back_days=7)
        
        # Verify workflow:
        # 1. Client initialized and fetched emails
        mock_client_class.assert_called_once()
        mock_client.fetch_inbox_emails.assert_called_once_with(look_back=7)
        
        # 2. Rule engine initialized
        mock_rule_engine_class.assert_called_once()
        
        # 3. Each email was evaluated and had actions applied
        self.assertEqual(mock_engine.evaluate.call_count, 3)  # Once for each email
        self.assertEqual(mock_engine.apply_actions.call_count, 3)  # Once for each email

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_rule_engine_integration(self, mock_json_load, mock_file_open):
        """Test RuleEngine integration with the rules file."""
        # Mock the rules file
        mock_json_load.return_value = self.sample_rules
        
        # Create RuleEngine instance
        engine = RuleEngine(self.test_rules_path)
        
        # Verify file was opened and rules loaded
        mock_file_open.assert_called_with(self.test_rules_path, 'r')
        mock_json_load.assert_called_once()
        
        # Test each rule with appropriate emails
        
        # Test newsletter rule
        email = ('test-msg-001', 'test-thread-001', 'newsletter@example.com', 'Newsletter', 
                 int(datetime.now().timestamp()), '[]', 'Click here to unsubscribe')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'mark_read')
        
        # Test interview rule
        email = ('test-msg-002', 'test-thread-002', 'hr@tenmiles.com', 'Interview Schedule', 
                 int(datetime.now().timestamp()), '[]', 'Details for your interview')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'move_message')
        self.assertEqual(actions[0]['mailbox'], 'IMPORTANT')
        
        # Test old invoice rule
        old_date = datetime.now() - timedelta(days=60)
        email = ('test-msg-003', 'test-thread-003', 'billing@example.com', 'Your Invoice', 
                 int(old_date.timestamp()), '[]', 'Please find attached invoice')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 2)  # Should match both actions
        action_types = [action['type'] for action in actions]
        self.assertIn('mark_read', action_types)
        self.assertIn('move_message', action_types)

    @patch('src.gmail_client.build')
    @patch('src.gmail_client.Credentials')
    def test_client_storage_integration(self, mock_credentials, mock_build):
        """Test integration between GmailClient and EmailStorage."""
        # Create a real EmailStorage with test database
        storage = EmailStorage(self.test_db_path)
        
        # Mock the Gmail API service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Make credentials appear valid
        mock_credentials.from_authorized_user_file.return_value = MagicMock(valid=True)
        
        # Create a mock response for messages.list
        mock_list = MagicMock()
        mock_list.execute.return_value = {
            'messages': [{'id': email['message_id']} for email in self.sample_emails]
        }
        mock_service.users().messages().list.return_value = mock_list
        
        # Create mock responses for messages.get
        def messages_get_side_effect(**kwargs):
            msg_id = kwargs['id']
            email = next((e for e in self.sample_emails if e['message_id'] == msg_id), None)
            
            if not email:
                return MagicMock(execute=MagicMock(return_value={}))
                
            mock_response = MagicMock()
            mock_response.execute.return_value = {
                'id': email['message_id'],
                'labelIds': email['labels'],
                'payload': {
                    'headers': [
                        {'name': 'From', 'value': email['from']},
                        {'name': 'Subject', 'value': email['subject']},
                        {'name': 'Date', 'value': email['date_received']}
                    ],
                    'body': {
                        'data': 'VGVzdCBtZXNzYWdlIGJvZHk='  # "Test message body" in base64
                    }
                }
            }
            return mock_response
            
        mock_service.users().messages().get.side_effect = messages_get_side_effect
        
        # Create client with real storage
        client = GmailClient(self.test_credentials_path, self.test_token_path, storage)
        
        # Override service with our mock
        client.service = mock_service
        
        # Test fetch_inbox_emails
        emails = client.fetch_inbox_emails()
        
        # Verify correct number of emails were found and stored
        self.assertEqual(len(emails), len(self.sample_emails))
        
        # Query the database to verify emails were stored
        stored_emails = storage.get_all_emails()
        self.assertEqual(len(stored_emails), len(self.sample_emails))
        
        # Check message content was stored
        for email in stored_emails:
            self.assertIsNotNone(email[5])  # Index 5 is the message field

    @patch('argparse.ArgumentParser.parse_args')
    @patch('src.main.EmailStorage')
    @patch('src.main.GmailClient')
    @patch('src.main.RuleEngine')
    def test_command_line_arguments(self, mock_rule_engine, mock_client_class, mock_storage, mock_parse_args):
        """Test command line argument handling."""
        # Mock the argument parser
        mock_args = MagicMock()
        mock_args.look_back = 14
        mock_parse_args.return_value = mock_args
        
        # Set up other mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Import main module
        from src.main import main
        
        # Call directly with the command line args value
        main(look_back_days=14)
        
        # Verify look_back parameter was passed correctly
        mock_client.fetch_inbox_emails.assert_called_once_with(look_back=14)

if __name__ == '__main__':
    unittest.main()
