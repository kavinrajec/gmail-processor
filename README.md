# Gmail Processor

A standalone Python script that integrates with Gmail API, fetches emails from your inbox, stores them in a database, and performs rule-based operations on them.

## Features

- Authenticate with Gmail API using OAuth
- Fetch emails from your Gmail inbox
- Store emails in a SQLite database
- Process emails based on configurable rules
- Perform actions like marking as read/unread or moving emails
- Command line interface with parameters

## Requirements

- Python 3.9.6
- Pip package manager
- SQLite
- Gmail account
- Google Cloud Platform project with Gmail API enabled

## Installation

1. Clone this repository

```bash
git clone https://github.com/kavinrajec/gmail-processor.git
cd gmail-processor
```

2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in development mode (this will also install all dependencies)

```bash
pip install -e .
```

4. Set up Google Cloud Platform credentials
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth credentials (OAuth client ID)
   - Download the credentials JSON file and save it as `config/credentials.json`

## Configuration

### Rules

The application uses rules defined in `config/rules.json` to process emails. Each rule has:

- `description`: A human-readable description of the rule
- `mode`: How conditions should be evaluated (`all` or `any`)
  - `all`: All conditions must match for the rule to apply
  - `any`: At least one condition must match for the rule to apply
- `conditions`: A list of conditions to check
  - `field`: Email field to check (from, subject, message, date_received)
  - `predicate`: Type of comparison (contains, does_not_contain, equals, does_not_equal, less_than_days, greater_than_days)
  - `value`: Value to compare against
- `actions`: Actions to perform when conditions are met
  - `type`: Action type (mark_read, mark_unread, move_message)
  - `mailbox`: (For move_message action) The mailbox to move to

Example rule:

```json
{
  "description": "Mark promotional emails as read",
  "mode": "any",
  "conditions": [
    { "field": "subject", "predicate": "contains", "value": "Promotion" },
    { "field": "from", "predicate": "contains", "value": "newsletter" }
  ],
  "actions": [{ "type": "mark_read" }]
}
```

## Usage

### Basic Usage

Run the main script to process emails from your inbox:

```bash
python3 src/main.py
```

Alternatively, you can run it from any directory after installing the package in development mode:

```bash
python3 -m src.main
```

### Command Line Arguments

The script accepts the following command-line arguments:

- `--look-back DAYS`: Specifies how many days back to fetch emails (defaults to 7 days if not specified). Must be a positive integer. If a negative or zero value is provided, an error will be displayed.

Examples:

```bash
# Process emails from the last 7 days (default)
python3 src/main.py

# Process emails from the last 15 days
python3 src/main.py --look-back 15

# Process emails from the last 30 days
python3 src/main.py --look-back 30

# Invalid example - will show an error
python3 src/main.py --look-back -5
```

The look-back parameter helps you control the volume of emails processed in each run. The validation ensures you don't accidentally provide an invalid timeframe.

## Database

Emails are stored in a SQLite database (`email.db`) with the following structure:

- `message_id`: Unique identifier for the email (PRIMARY KEY)
- `thread_id`: Gmail thread identifier for grouping related emails
- `from_email`: Sender's email address
- `subject`: Email subject
- `date_received`: When the email was received (Unix timestamp)
- `labels`: Gmail labels (JSON-encoded list)
- `message`: Email body content

### Database Update Behavior

When the script runs multiple times:

- For new emails, all information is stored in the database
- For emails that are already in the database (based on `message_id`), only the `labels` field is updated
- This optimizes performance and ensures that label changes made by rules are preserved even when emails are reprocessed

## Running Tests

To run the test suite:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

Or with verbose output:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
