import unittest
import json
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from src.rule_engine import RuleEngine

class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        # This is just a placeholder setup, we'll create specific rule engines for each test
        self.tmp_files = []
        
    def tearDown(self):
        import os
        # Clean up any temporary files created during tests
        for file_path in self.tmp_files:
            if os.path.exists(file_path):
                os.unlink(file_path)
        
    def test_all_conditions_mode(self):
        # Create a rule engine with only the "all" rule
        rule = [
            {
                "description": "Test rule with all mode",
                "mode": "all",
                "conditions": [
                    {"field": "from", "predicate": "contains", "value": "test@example.com"},
                    {"field": "subject", "predicate": "contains", "value": "Important"}
                ],
                "actions": [{"type": "mark_read"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test when all conditions match
        email = ('msg1', 'thread1', 'test@example.com', 'Important Meeting', int(datetime.now().timestamp()), '[]', 'Important details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'mark_read')
        
        # Test when one condition doesn't match - make email completely different to ensure no match
        email = ('msg2', 'thread2', 'different@example.com', 'Not Important', int(datetime.now().timestamp()), '[]', 'Not important details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered
        
    def test_any_conditions_mode(self):
        # Create a rule engine with only the "any" rule
        rule = [
            {
                "description": "Test rule with any mode",
                "mode": "any",
                "conditions": [
                    {"field": "from", "predicate": "contains", "value": "newsletter"},
                    {"field": "subject", "predicate": "contains", "value": "Discount"}
                ],
                "actions": [{"type": "mark_unread"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test when one condition matches
        email = ('msg3', 'thread3', 'newsletter@example.com', 'Weekly Update', int(datetime.now().timestamp()), '[]', 'Weekly newsletter')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'mark_unread')
        
        # Test when a different condition matches
        email = ('msg4', 'thread4', 'info@example.com', 'Discount Offer', int(datetime.now().timestamp()), '[]', 'Discount details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'mark_unread')
        
        # Test when no conditions match
        email = ('msg5', 'thread5', 'info@example.com', 'Regular Update', int(datetime.now().timestamp()), '[]', 'Regular details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered
    
    def test_equals_predicate(self):
        # Create a rule engine with only the equals predicate rule
        rule = [
            {
                "description": "Test equals predicate",
                "mode": "all",
                "conditions": [
                    {"field": "subject", "predicate": "equals", "value": "Exact Match"}
                ],
                "actions": [{"type": "move_message", "mailbox": "INBOX"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test when subject exactly matches
        email = ('msg6', 'thread6', 'user@example.com', 'Exact Match', int(datetime.now().timestamp()), '[]', 'Exact match details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'move_message')
        
        # Test when subject doesn't exactly match
        email = ('msg7', 'thread7', 'user@example.com', 'Not an Exact Match', int(datetime.now().timestamp()), '[]', 'Not an exact match details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered
        
    def test_does_not_contain_predicate(self):
        # Create a rule engine with only the does_not_contain predicate rule
        rule = [
            {
                "description": "Test does_not_contain predicate",
                "mode": "all",
                "conditions": [
                    {"field": "from", "predicate": "does_not_contain", "value": "spam"}
                ],
                "actions": [{"type": "mark_read"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test when from doesn't contain 'spam'
        email = ('msg8', 'thread8', 'regular@example.com', 'Regular Email', int(datetime.now().timestamp()), '[]', 'Regular email details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'mark_read')
        
        # Test when from contains 'spam'
        email = ('msg9', 'thread9', 'spam-alert@example.com', 'Alert', int(datetime.now().timestamp()), '[]', 'Spam alert details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered
    
    def test_message_content(self):
        # Create a rule engine with only the message content rule
        rule = [
            {
                "description": "Test message content",
                "mode": "all",
                "conditions": [
                    {"field": "message", "predicate": "contains", "value": "confidential"}
                ],
                "actions": [{"type": "move_message", "mailbox": "IMPORTANT"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test with dictionary email format that includes message content
        email = ('msg10', 'thread10', 'sender@example.com', 'Project Update', int(datetime.now().timestamp()), '[]', 'This is a confidential document.')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'move_message')
        self.assertEqual(actions[0]['mailbox'], 'IMPORTANT')
        
        # Test when message doesn't contain the target word
        email = ('msg10', 'thread10', 'sender@example.com', 'Project Update', int(datetime.now().timestamp()), '[]', 'This is a regular document.')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered
    
    def test_date_predicates(self):
        # Create a rule engine with only the date comparison rule
        rule = [
            {
                "description": "Test date comparison",
                "mode": "all",
                "conditions": [
                    {"field": "date_received", "predicate": "greater_than_days", "value": 30}
                ],
                "actions": [{"type": "move_message", "mailbox": "TRASH"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test greater_than_days predicate
        old_date = datetime.now() - timedelta(days=60)
        email = ('msg11', 'thread11', 'old@example.com', 'Old Email', int(old_date.timestamp()), '[]', 'Old email details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'move_message')
        self.assertEqual(actions[0]['mailbox'], 'TRASH')
        
        # Test with recent date that shouldn't match
        recent_date = datetime.now() - timedelta(days=10)
        email = ('msg12', 'thread12', 'recent@example.com', 'Recent Email', int(recent_date.timestamp()), '[]', 'Recent email details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered
    
    def test_with_config_rules(self):
        # Test with the actual rules.json configuration
        engine = RuleEngine('config/rules.json')
        
        # Test with an email that should match the first rule
        email = ('id', 'thread-id', 'test@tenmiles.com', 'Interview Prep', int(datetime.now().timestamp()), '[]', 'Interview prep details')
        actions = engine.evaluate(email)
        self.assertTrue(len(actions) > 0, "Expected at least one action to be triggered")
        
    def test_does_not_equal_predicate(self):
        """Test the does_not_equal predicate."""
        # Create a rule engine with only the does_not_equal predicate rule
        rule = [
            {
                "description": "Test does_not_equal predicate",
                "mode": "all",
                "conditions": [
                    {"field": "subject", "predicate": "does_not_equal", "value": "Spam Email"}
                ],
                "actions": [{"type": "mark_read"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test when subject does not equal the value
        email = ('msg13', 'thread13', 'user@example.com', 'Regular Email', int(datetime.now().timestamp()), '[]', 'Regular email details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'mark_read')
        
        # Test when subject equals the value (should not match)
        email = ('msg14', 'thread14', 'user@example.com', 'Spam Email', int(datetime.now().timestamp()), '[]', 'Spam email details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered
    
    def test_less_than_days_predicate(self):
        """Test the less_than_days predicate."""
        # Create a rule engine with only the less_than_days rule
        rule = [
            {
                "description": "Test less_than_days predicate",
                "mode": "all",
                "conditions": [
                    {"field": "date_received", "predicate": "less_than_days", "value": 3}
                ],
                "actions": [{"type": "mark_unread"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test with recent email (less than 3 days)
        recent_date = datetime.now() - timedelta(days=1)
        email = ('msg15', 'thread15', 'recent@example.com', 'Recent Email', int(recent_date.timestamp()), '[]', 'Recent email details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'mark_unread')
        
        # Test with older email (more than 3 days)
        old_date = datetime.now() - timedelta(days=5)
        email = ('msg16', 'thread16', 'old@example.com', 'Old Email', int(old_date.timestamp()), '[]', 'Old email details')
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered
    
    def test_multiple_actions(self):
        """Test rules with multiple actions."""
        # Create a rule engine with a rule that has multiple actions
        rule = [
            {
                "description": "Test multiple actions",
                "mode": "all",
                "conditions": [
                    {"field": "subject", "predicate": "contains", "value": "Important"}
                ],
                "actions": [
                    {"type": "mark_unread"},
                    {"type": "move_message", "mailbox": "IMPORTANT"}
                ]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test with matching email
        email = ('msg17', 'thread17', 'user@example.com', 'Important Meeting', int(datetime.now().timestamp()), '[]', 'Important meeting details')
        actions = engine.evaluate(email)
        
        # Verify multiple actions are returned
        self.assertEqual(len(actions), 2)
        
        # Verify the specific actions
        action_types = [action['type'] for action in actions]
        self.assertIn('mark_unread', action_types)
        self.assertIn('move_message', action_types)
        
        # Verify the mailbox parameter is preserved
        move_action = next(action for action in actions if action['type'] == 'move_message')
        self.assertEqual(move_action['mailbox'], 'IMPORTANT')
    
    def test_combined_predicates(self):
        """Test rules with a combination of predicates on different fields."""
        # Create a rule engine with combined predicates
        rule = [
            {
                "description": "Test combined predicates",
                "mode": "all",
                "conditions": [
                    {"field": "from", "predicate": "contains", "value": "important"},
                    {"field": "subject", "predicate": "does_not_contain", "value": "spam"},
                    {"field": "message", "predicate": "contains", "value": "urgent"},
                    {"field": "date_received", "predicate": "less_than_days", "value": 2}
                ],
                "actions": [{"type": "mark_unread"}]
            }
        ]
        
        # Create temporary file for the rule
        tmp_file = NamedTemporaryFile(mode='w+', delete=False)
        json.dump(rule, tmp_file)
        tmp_file.close()
        self.tmp_files.append(tmp_file.name)
        
        # Initialize engine with only this rule
        engine = RuleEngine(tmp_file.name)
        
        # Test with email dictionary that matches all conditions
        email = ('msg18', 'thread18', 'important@example.com', 'Critical Update', int(datetime.now().timestamp()), '[]', 'This is an urgent matter that requires immediate attention.')
        
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['type'], 'mark_unread')
        
        # Test when one condition doesn't match
        email = ('msg18', 'thread18', 'important@example.com', 'Critical Update', int(datetime.now().timestamp()), '[]', 'This is a regular update.')  # No "urgent" in message
        actions = engine.evaluate(email)
        self.assertEqual(len(actions), 0)  # No actions should be triggered