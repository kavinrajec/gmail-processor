import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import json
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
from src.gmail_client import GmailClient, GmailAPIError


class TestGmailClient(unittest.TestCase):
    """Tests for the Gmail Client component."""

    def setUp(self):
        """Set up test environment."""
        # Create test credentials and token paths
        self.test_credentials_path = 'test_credentials.json'
        self.test_token_path = 'test_token.json'
        
        # Mock storage
        self.mock_storage = MagicMock()
        
        # Create sample email data for testing
        self.sample_message = {
            'id': 'test-msg-001',
            'threadId': 'test-thread-001',
            'labelIds': ['INBOX', 'UNREAD'],
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Subject', 'value': 'Test Email Subject'},
                    {'name': 'Date', 'value': 'Mon, 22 Mar 2025 10:00:00 +0000'}
                ],
                'body': {
                    'data': 'VGhpcyBpcyBhIHRlc3QgbWVzc2FnZSBib2R5Lg=='  # "This is a test message body." in base64
                }
            }
        }
        
        # Sample response for list messages
        self.list_messages_response = {
            'messages': [
                {'id': 'msg-001', 'threadId': 'thread-001'},
                {'id': 'msg-002', 'threadId': 'thread-002'}
            ],
            'nextPageToken': 'next-page-token'
        }
        
        # Sample response for list messages (last page)
        self.list_messages_response_last_page = {
            'messages': [
                {'id': 'msg-003', 'threadId': 'thread-003'}
            ]
        }
        
    def tearDown(self):
        """Clean up after tests."""
        # Remove test files if they exist
        for file_path in [self.test_credentials_path, self.test_token_path]:
            if os.path.exists(file_path):
                os.remove(file_path)

    @patch('src.gmail_client.build')
    @patch('src.gmail_client.Credentials')
    @patch('src.gmail_client.InstalledAppFlow')
    def test_authentication_with_existing_token(self, mock_flow, mock_credentials, mock_build):
        """Test authentication process with existing valid token."""
        # Mock credentials
        mock_credentials.from_authorized_user_file.return_value = MagicMock(valid=True)
        
        # Create empty token file
        with open(self.test_token_path, 'w') as f:
            f.write('{}')
        
        # Create the client
        client = GmailClient(self.test_credentials_path, self.test_token_path, self.mock_storage)
        
        # Verify token was loaded
        mock_credentials.from_authorized_user_file.assert_called_once_with(self.test_token_path, GmailClient.SCOPES)
        
        # Verify service was built
        mock_build.assert_called_once()

    @patch('src.gmail_client.build')
    @patch('src.gmail_client.Credentials')
    @patch('src.gmail_client.InstalledAppFlow')
    def test_authentication_with_token_refresh(self, mock_flow, mock_credentials, mock_build):
        """Test authentication process with token that needs refresh."""
        # Mock credentials
        mock_creds = MagicMock(valid=False, expired=True, refresh_token=True)
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        # Create empty token file
        with open(self.test_token_path, 'w') as f:
            f.write('{}')
        
        # Create the client
        client = GmailClient(self.test_credentials_path, self.test_token_path, self.mock_storage)
        
        # Verify token was refreshed
        mock_creds.refresh.assert_called_once()
        
        # Verify credentials were saved
        self.assertTrue(os.path.exists(self.test_token_path))

    @patch('src.gmail_client.build')
    @patch('src.gmail_client.Credentials')
    @patch('src.gmail_client.InstalledAppFlow')
    def test_authentication_with_new_flow(self, mock_flow, mock_credentials, mock_build):
        """Test authentication process with no valid token."""
        # Mock flow
        mock_flow_instance = MagicMock()
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance
        
        # Mock credentials to indicate no valid token
        mock_credentials.from_authorized_user_file.side_effect = Exception("File not found")
        
        # Create the client
        client = GmailClient(self.test_credentials_path, self.test_token_path, self.mock_storage)
        
        # Verify flow was created and run
        mock_flow.from_client_secrets_file.assert_called_once_with(self.test_credentials_path, GmailClient.SCOPES)
        mock_flow_instance.run_local_server.assert_called_once()

    @patch('src.gmail_client.build')
    def test_fetch_inbox_emails(self, mock_build):
        """Test fetching emails from inbox."""
        # Create mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock messages.list API call
        mock_list = MagicMock()
        mock_list.execute.side_effect = [
            self.list_messages_response,
            self.list_messages_response_last_page
        ]
        mock_service.users().messages().list.return_value = mock_list
        
        # Mock messages.get API call
        mock_get = MagicMock()
        mock_get.execute.return_value = self.sample_message
        mock_service.users().messages().get.return_value = mock_get
        
        # Create client without going through authentication
        client = GmailClient.__new__(GmailClient)
        client.service = mock_service
        client.email_storage = self.mock_storage
        
        # Call the method
        emails = client.fetch_inbox_emails()
        
        # Verify API calls
        mock_service.users().messages().list.assert_called()
        self.assertEqual(mock_service.users().messages().get.call_count, 3)  # 3 messages total
        
        # Verify storage calls
        self.assertEqual(self.mock_storage.save_email.call_count, 3)
        
        # Verify emails data
        self.assertEqual(len(emails), 3)

    @patch('src.gmail_client.build')
    def test_fetch_inbox_emails_with_look_back(self, mock_build):
        """Test fetching emails with look-back period."""
        # Create mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock messages.list API call
        mock_list = MagicMock()
        mock_list.execute.return_value = self.list_messages_response_last_page
        mock_service.users().messages().list.return_value = mock_list
        
        # Mock messages.get API call
        mock_get = MagicMock()
        mock_get.execute.return_value = self.sample_message
        mock_service.users().messages().get.return_value = mock_get
        
        # Create client without going through authentication
        client = GmailClient.__new__(GmailClient)
        client.service = mock_service
        client.email_storage = self.mock_storage
        
        # Call the method with look_back
        look_back_days = 7
        emails = client.fetch_inbox_emails(look_back=look_back_days)
        
        # Verify API call with query parameter
        call_args = mock_service.users().messages().list.call_args[1]
        self.assertIn('q', call_args)
        self.assertTrue(call_args['q'].startswith('after:'))

    @patch('src.gmail_client.build')
    def test_get_email_details(self, mock_build):
        """Test retrieving email details."""
        # Create mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock messages.get API call
        mock_get = MagicMock()
        mock_get.execute.return_value = self.sample_message
        mock_service.users().messages().get.return_value = mock_get
        
        # Create client without going through authentication
        client = GmailClient.__new__(GmailClient)
        client.service = mock_service
        
        # Call the method
        msg_id = 'test-msg-001'
        email_details = client._get_email_details(msg_id)
        
        # Verify API call
        mock_service.users().messages().get.assert_called_with(
            userId='me', id=msg_id, format='full'
        )
        
        # Verify email details
        self.assertEqual(email_details['message_id'], msg_id)
        self.assertEqual(email_details['from'], 'sender@example.com')
        self.assertEqual(email_details['subject'], 'Test Email Subject')
        self.assertEqual(email_details['date_received'], 'Mon, 22 Mar 2025 10:00:00 +0000')
        self.assertIn('message', email_details)

    @patch('src.gmail_client.build')
    def test_get_message_content(self, mock_build):
        """Test extracting message content."""
        # Create client without going through authentication
        client = GmailClient.__new__(GmailClient)
        
        # Call the method
        content = client._get_message_content(self.sample_message)
        
        # Verify content extraction
        self.assertEqual(content, 'This is a test message body.')

    @patch('src.gmail_client.build')
    def test_modify_email(self, mock_build):
        """Test modifying email labels."""
        # Create mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock messages.modify API call
        mock_modify = MagicMock()
        mock_service.users().messages().modify.return_value = mock_modify
        
        # Create client without going through authentication
        client = GmailClient.__new__(GmailClient)
        client.service = mock_service
        
        # Call the method
        msg_id = 'test-msg-001'
        add_labels = ['IMPORTANT']
        remove_labels = ['UNREAD']
        client.modify_email(msg_id, add_labels, remove_labels)
        
        # Verify API call
        mock_service.users().messages().modify.assert_called_with(
            userId='me', 
            id=msg_id, 
            body={'addLabelIds': add_labels, 'removeLabelIds': remove_labels}
        )

    @patch('src.gmail_client.build')
    def test_api_error_handling(self, mock_build):
        """Test handling of API errors."""
        # Create mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock messages.list API call to raise HttpError
        mock_list = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.reason = 'Rate Limit Exceeded'
        http_error = HttpError(mock_resp, b'Rate limit exceeded.')
        mock_list.execute.side_effect = http_error
        mock_service.users().messages().list.return_value = mock_list
        
        # Create client without going through authentication
        client = GmailClient.__new__(GmailClient)
        client.service = mock_service
        
        # Call the method and expect exception
        with self.assertRaises(GmailAPIError):
            client.fetch_inbox_emails()

if __name__ == '__main__':
    unittest.main()
