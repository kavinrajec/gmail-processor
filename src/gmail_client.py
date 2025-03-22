import os
from tqdm import tqdm
import logging
import time
from typing import List, Dict, Optional
from google.auth.transport.requests import Request

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GmailAPIError(Exception):
    """Custom exception for Gmail API errors."""
    pass

class GmailClient:
    """Handles authentication and operations with the Gmail API."""

    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
    SERVICE_NAME = 'gmail'
    SERVICE_VERSION = 'v1'

    def __init__(self, credentials_path: str, token_path: str):
        """Initialize the GmailClient.
        
        Args:
            credentials_path: Path to the OAuth credentials file
            token_path: Path to store/retrieve the OAuth token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API using OAuth 2.0."""
        logging.info("Starting Gmail API authentication process")
        creds = None
        if os.path.exists(self.token_path):
            logging.info("Found existing token file at %s", self.token_path)
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
                logging.info("Successfully loaded credentials from token file")
            except Exception as e:
                logging.error("Error loading credentials from token file: %s", e)
                creds = None

        if not creds:
            logging.info("No valid credentials found")
        elif creds.valid:
            logging.info("Credentials are valid")
        else:
            logging.info("Credentials need refresh or new authorization")

        if not creds or not creds.valid:
             if creds and creds.expired and creds.refresh_token:
                logging.info("Attempting to refresh expired credentials")
                try:
                    creds.refresh(Request())
                    logging.info("Successfully refreshed credentials")
                except Exception as e:
                    logging.error("Error refreshing credentials: %s", e)
                    logging.info("Removing invalid token file at %s", self.token_path)
                    os.remove(self.token_path)
                    creds = None
             if not creds:
                logging.info("Initiating OAuth2 authorization")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    logging.info("Successfully completed OAuth2 authorization")
                except Exception as e:
                    raise GmailAPIError(f"Failed to authenticate: {e}") from e

             logging.info("Saving credentials to token file at %s", self.token_path)
             try:
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                logging.info("Successfully saved credentials to token file")
             except Exception as e:
                logging.error("Error saving credentials to token file: %s", e)
        
        try:
            service = build(self.SERVICE_NAME, self.SERVICE_VERSION, credentials=creds)
            logging.info("Successfully built Gmail API service")
            return service
        except Exception as e:
            raise GmailAPIError(f"Failed to build Gmail API service: {e}") from e

    def fetch_inbox_emails(self, look_back: int = None) -> List[Dict]:
        """
        Fetch emails from the Inbox in batches since the last fetch.
        
        Args:
            look_back: Number of days to look back for emails
        
        Returns:
            List of email details
        """
        logging.info("Starting to fetch emails from Inbox")
        
        # Build query if timestamp is provided
        query = None
        if look_back:
            look_back_timestamp = int(time.time() - look_back * 24 * 60 * 60)
            query = f'after:{look_back_timestamp}'
            logging.info("Fetching emails after timestamp: %s", look_back_timestamp)
        else:
            logging.info("Fetching all emails as no look back provided")
        
        try:
            # Fetch all messages in batches
            all_messages = []
            page_token = None
            
            while True:
                response = self.service.users().messages().list(
                    userId='me', 
                    # labelIds=['INBOX'], 
                    q=query, 
                    pageToken=page_token
                ).execute()
                
                messages = response.get('messages', [])
                logging.info("Fetched %s emails in this batch", len(messages))
                if not messages:
                    break

                all_messages.extend(messages)
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            logging.info("Successfully received metadata for %s emails from Gmail API", len(all_messages))
            
            # Fetch and save email details with a progress bar, one at a time
            emails = []
            logging.info("Fetching and saving details for %s emails from mailbox...", len(all_messages))
            
            with tqdm(total=len(all_messages), desc="Processing emails") as pbar:
                for msg in all_messages:
                    # Fetch email details
                    email = self._get_email_details(msg['id'])
                    emails.append(email)
                        
                    pbar.update(1)
            
            processed_count = len(emails)
            logging.info("Successfully processed %s emails from Inbox", processed_count)
            return emails

        except HttpError as e:
            raise GmailAPIError(f"Failed to fetch emails: {e}") from e
        except Exception as e:
            raise GmailAPIError(f"Unexpected error while fetching emails: {e}") from e

    def _get_email_details(self, msg_id: str) -> Dict:
        """Retrieve detailed metadata and content for a single email."""
        try:
            # Get the full message including body content
            msg = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            if 'payload' not in msg or 'headers' not in msg['payload']:
                logging.warning("Message %s has unexpected format, missing payload or headers", msg_id)
                headers = {}
                message_content = ""
            else:
                headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
                message_content = self._get_message_content(msg)
            
            email_details = {
                'message_id': msg_id,
                'thread_id': msg.get('threadId', ''),
                'from': headers.get('from', ''),
                'subject': headers.get('subject', ''),
                'date_received': headers.get('date', ''),
                'labels': msg.get('labelIds', []),
                'message': message_content
            }

            logging.debug("Successfully extracted details for message %s", msg_id)
                
            return email_details
        except HttpError as e:
            raise GmailAPIError(f"Failed to get email details for message {msg_id}: {e}") from e
        except Exception as e:
            raise GmailAPIError(f"Unexpected error while getting email details for message {msg_id}: {e}") from e
            
    def _get_message_content(self, message: Dict) -> str:
        """Extract plain text content from a Gmail message."""
        if 'payload' not in message:
            return ""
            
        payload = message['payload']
        parts = [payload]  # Start with the main payload
        body_data = ""
        
        # Process parts recursively
        while parts:
            part = parts.pop(0)
            
            # Check if this part has a body
            if 'body' in part and 'data' in part['body'] and part['body']['data']:
                try:
                    from base64 import urlsafe_b64decode
                    import codecs
                    
                    # Decode body data
                    body_bytes = urlsafe_b64decode(part['body']['data'])
                    body_text = codecs.decode(body_bytes, 'utf-8', errors='replace')
                    body_data += body_text
                except Exception as e:
                    logging.warning(f"Failed to decode message body: {e}")
            
            # Add nested parts to the queue
            if 'parts' in part:
                parts.extend(part['parts'])
                
        return body_data

    def modify_email(self, msg_id: str, add_labels: Optional[List[str]] = None,
                     remove_labels: Optional[List[str]] = None):
        """Modify email labels (e.g., move or mark read/unread)."""
        add_labels = add_labels or []
        remove_labels = remove_labels or []
        
        body = {
            'addLabelIds': add_labels,
            'removeLabelIds': remove_labels
        }
        
        try:
            self.service.users().messages().modify(userId='me', id=msg_id, body=body).execute()
            logging.info("Successfully modified email %s with labels %s", msg_id, body)
        except HttpError as e:
            raise GmailAPIError(f"Failed to modify email {msg_id}: {e}") from e
        except Exception as e:
            raise GmailAPIError(f"Unexpected error while modifying email {msg_id}: {e}") from e