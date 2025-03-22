import json
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Union
import logging

class RuleEngine:
    """Evaluates rules and applies actions to emails."""

    # Define predicates with their corresponding functions
    PREDICATES: Dict[str, Callable] = {
        # String predicates
        'contains': lambda value, target: target in value if value else False,
        'does_not_contain': lambda value, target: target not in value if value else True,
        'equals': lambda value, target: value == target,
        'does_not_equal': lambda value, target: value != target,
        
        # Date predicates
        'less_than_days': lambda age, days: age < timedelta(days=int(days)),
        'greater_than_days': lambda age, days: age > timedelta(days=int(days))
    }

    def __init__(self, rules_path: str):
        self.rules = self._load_rules(rules_path)

    def _load_rules(self, rules_path: str) -> List[Dict]:
        """Load rules from a JSON file."""
        try:
            with open(rules_path, 'r') as f:
                rules = json.load(f)
                if not rules:  # Handle empty list
                    logging.warning(f"Rules file {rules_path} is empty. No rules will be applied.")
                    return []
                return rules
        except FileNotFoundError:
            logging.error(f"Rules file {rules_path} not found. No rules will be applied.")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {rules_path}: {e}. No rules will be applied.")
            return []

    def evaluate(self, email: Union[tuple, Dict]) -> List[Dict]:
        """Return actions for an email if rule conditions are met.
        
        Args:
            email: Email data as a tuple from database or as a dictionary
            
        Returns:
            List of applicable actions for this email
        """
        # Handle email as tuple from database or as dictionary
        if isinstance(email, tuple):
            _, _, from_email, subject, date_received, _, message_content = email
            date_received = datetime.fromtimestamp(date_received)
        else:
            # If it's a dictionary with full email details
            from_email = email.get('from', '')
            subject = email.get('subject', '')
            date_received = email.get('date_received', datetime.now())
            if isinstance(date_received, str):
                # Convert string to datetime if needed
                try:
                    date_received = datetime.fromisoformat(date_received.replace('Z', '+00:00'))
                except ValueError:
                    date_received = datetime.now()
            message_content = email.get('message', '')
            
        applicable_actions = []

        for rule in self.rules:
            # Extract rule mode (default to 'all' if not specified)
            rule_mode = rule.get('mode', 'all').lower()
            
            # Check if conditions are met based on the rule mode
            if rule_mode == 'all' and self._all_conditions_met(from_email, subject, date_received, message_content, rule['conditions']):
                applicable_actions.extend(rule['actions'])
            elif rule_mode == 'any' and self._any_conditions_met(from_email, subject, date_received, message_content, rule['conditions']):
                applicable_actions.extend(rule['actions'])
                
        return applicable_actions

    def _all_conditions_met(self, from_email: str, subject: str, date_received: datetime, 
                           message_content: str, conditions: List[Dict]) -> bool:
        """Check if ALL conditions in a rule are satisfied."""
        now = datetime.now()
        for cond in conditions:
            # Get the appropriate value based on the field
            field_name = cond['field'].lower()
            if field_name == 'from':
                field_value = from_email
            elif field_name == 'subject':
                field_value = subject
            elif field_name == 'message':
                field_value = message_content
            elif field_name == 'date_received':
                field_value = now - date_received
            else:
                logging.warning(f"Unknown field name: {field_name}")
                return False
                
            # Get the predicate function
            predicate_name = cond['predicate']
            if predicate_name not in self.PREDICATES:
                logging.warning(f"Unknown predicate: {predicate_name}")
                return False
                
            predicate_fn = self.PREDICATES[predicate_name]
            
            # Check if the condition is met
            if not predicate_fn(field_value, cond['value']):
                return False
                
        return True
        
    def _any_conditions_met(self, from_email: str, subject: str, date_received: datetime, 
                           message_content: str, conditions: List[Dict]) -> bool:
        """Check if ANY condition in a rule is satisfied."""
        now = datetime.now()
        
        if not conditions:  # If there are no conditions, return False
            return False
            
        for cond in conditions:
            # Get the appropriate value based on the field
            field_name = cond['field'].lower()
            if field_name == 'from':
                field_value = from_email
            elif field_name == 'subject':
                field_value = subject
            elif field_name == 'message':
                field_value = message_content
            elif field_name == 'date_received':
                field_value = now - date_received
            else:
                logging.warning(f"Unknown field name: {field_name}")
                continue  # Skip this condition but continue checking others
                
            # Get the predicate function
            predicate_name = cond['predicate']
            if predicate_name not in self.PREDICATES:
                logging.warning(f"Unknown predicate: {predicate_name}")
                continue  # Skip this condition but continue checking others
                
            predicate_fn = self.PREDICATES[predicate_name]
            
            # If any condition is met, return True
            if predicate_fn(field_value, cond['value']):
                return True
                
        return False

    @staticmethod
    def apply_actions(client, msg_id: str, labels: List[str], actions: List[Dict]):
        """Apply actions to an email via the Gmail client."""
        add_labels, remove_labels = [], []
        for action in actions:
            if action['type'] == 'move_message' and action['mailbox'] not in labels:
                add_labels.append(action['mailbox'])
            elif action['type'] == 'move_message':
                logging.info(f"Skipping move to {action['mailbox']} as message already has this label")
            elif action['type'] == 'mark_read' and 'UNREAD' in labels:
                remove_labels.append('UNREAD')
            elif action['type'] == 'mark_read':
                logging.info("Skipping mark_read as message is already read")
            elif action['type'] == 'mark_unread' and 'UNREAD' not in labels:
                add_labels.append('UNREAD')
            elif action['type'] == 'mark_unread':
                logging.info("Skipping mark_unread as message is already unread")
        if add_labels or remove_labels:
            client.modify_email(msg_id, add_labels, remove_labels)