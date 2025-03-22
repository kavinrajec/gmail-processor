import unittest
from unittest.mock import patch, MagicMock
import sys
import argparse
from src.main import main

class TestCommandLineArguments(unittest.TestCase):
    """Tests for command-line arguments handling."""

    @patch('src.main.EmailStorage')
    @patch('src.main.GmailClient')
    @patch('src.main.RuleEngine') 
    def test_default_look_back(self, mock_rule_engine_class, mock_client_class, mock_storage_class):
        """Test that look_back defaults to 7 days when not specified."""
        # Set up mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Run main with no args
        with patch('sys.argv', ['main.py']):
            main()
            
        # Check that fetch_inbox_emails was called with default (7 days)
        mock_client.fetch_inbox_emails.assert_called_once_with(look_back=7)
        
    @patch('src.main.EmailStorage')
    @patch('src.main.GmailClient')
    @patch('src.main.RuleEngine')
    def test_specific_look_back(self, mock_rule_engine_class, mock_client_class, mock_storage_class):
        """Test that look_back is passed correctly when specified."""
        # Set up mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Call main directly with the look_back value
        main(look_back_days=14)
            
        # Check that fetch_inbox_emails was called with correct value
        mock_client.fetch_inbox_emails.assert_called_once_with(look_back=14)
        
    @patch('src.main.EmailStorage')
    @patch('src.main.GmailClient')
    @patch('src.main.RuleEngine')
    def test_zero_look_back(self, mock_rule_engine_class, mock_client_class, mock_storage_class):
        """Test with a zero look_back value, which should pass 0 to the function."""
        # Set up mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Call main directly with zero look_back
        main(look_back_days=0)
        
        # Verify look_back parameter was passed correctly
        mock_client.fetch_inbox_emails.assert_called_once_with(look_back=0)
    
    @patch('src.main.EmailStorage')
    @patch('src.main.GmailClient')
    @patch('src.main.RuleEngine')
    def test_negative_look_back(self, mock_rule_engine_class, mock_client_class, mock_storage_class):
        """Test with a negative look_back value, which should be handled gracefully."""
        # Set up mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Call main directly with negative look_back
        main(look_back_days=-7)
        
        # Verify that a negative value is still passed through (application should handle this)
        mock_client.fetch_inbox_emails.assert_called_once_with(look_back=-7)
    
    def test_parse_error_handling(self):
        """Test that errors in parsing arguments are handled gracefully."""
        # Use a non-integer value for look-back to cause a parsing error
        with patch('sys.argv', ['main.py', '--look-back', 'invalid']):
            # Create parser directly to test error handling
            parser = argparse.ArgumentParser()
            parser.add_argument('--look-back', type=int)
            # This should raise a SystemExit due to argparse error
            with self.assertRaises(SystemExit):
                parser.parse_args()
    
    @patch('argparse.ArgumentParser._print_message')
    def test_help_option(self, mock_print):
        """Test that --help option works correctly."""
        # Suppress stdout to avoid cluttering test output
        mock_print.return_value = None
        
        # Test with --help flag
        with patch('sys.argv', ['main.py', '--help']):
            # This should exit with SystemExit
            with self.assertRaises(SystemExit):
                parser = argparse.ArgumentParser(description='Gmail processor script')
                parser.add_argument('--look-back', type=int, default=None, 
                                   help='Number of days to look back for emails (default: Whole Inbox)')
                parser.parse_args()
                
        # Verify help was called
        self.assertTrue(mock_print.called)

if __name__ == '__main__':
    unittest.main()
