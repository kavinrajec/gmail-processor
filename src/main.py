import argparse

from src.gmail_client import GmailClient
from src.email_storage import EmailStorage
from src.rule_engine import RuleEngine

def main(look_back_days: int = 7):
    # Initialize components
    client = GmailClient('config/credentials.json', 'config/token.json')
    storage = EmailStorage('email.db')
    engine = RuleEngine('config/rules.json')

    # Fetch emails (they are saved to database automatically during fetching)
    emails = client.fetch_inbox_emails(look_back=look_back_days)

    # Save to database immediately if we have storage
    if storage:
        storage.save_emails(emails)

    # Process emails with rules
    for email in storage.get_all_emails():
        actions = engine.evaluate(email)
        if actions:
            engine.apply_actions(client, email[0],email[5], actions)

def positive_int(value):
    """Validator to ensure value is a positive integer"""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"--look-back must be a positive integer, got {value}")
    return ivalue

if __name__ == '__main__':
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Gmail processor script')
    parser.add_argument('--look-back', type=positive_int, default=7, 
                      help='Number of days to look back for emails (must be positive, default: 7 days)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run main function with provided or default look_back days
    main(args.look_back)
