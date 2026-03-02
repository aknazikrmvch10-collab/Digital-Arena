import hashlib
import hmac
import json
import urllib.parse
from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)

def validate_telegram_data(init_data: str) -> dict | None:
    """
    Validates the initData string from Telegram Web App.
    Returns the parsed user data dictionary if valid, else None.
    """
    if not init_data:
        logger.warning("Auth failed: Empty init_data")
        return None
        
    try:
        # Parse the query string into a dictionary
        parsed_data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        
        # Extract the hash
        hash_value = parsed_data.pop('hash', None)
        if not hash_value:
            logger.warning("Auth failed: No hash in init_data")
            return None
            
        # Sort keys and create data check string
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        # Create secret key
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        # Compare hashes (constant time comparison recommended but == is fine for this)
        if calculated_hash != hash_value:
            logger.warning("Auth failed: Hash mismatch", calculated=calculated_hash, received=hash_value)
            return None
            
        # Parse user data
        if 'user' in parsed_data:
            return json.loads(parsed_data['user'])
            
        return None
    except Exception as e:
        logger.error("Auth Validation Error", error=str(e))
        return None

def validate_web_login_data(data: dict) -> dict | None:
    """
    Validates data received from the Telegram Login Widget.
    The data should be a dictionary containing id, first_name, username, photo_url, auth_date, and hash.
    Returns the user data dictionary if valid, else None.
    """
    if not data:
        logger.warning("Web Login Auth failed: Empty data")
        return None
        
    try:
        # Clone the dictionary to avoid modifying the original
        auth_data = data.copy()
        
        # Extract the hash
        hash_value = auth_data.pop('hash', None)
        if not hash_value:
            logger.warning("Web Login Auth failed: No hash in data")
            return None
            
        # Data check string is constructed by sorting all keys
        # Format: key=value
        data_check_list = []
        for k, v in sorted(auth_data.items()):
            if v is not None and v != "":
                data_check_list.append(f"{k}={v}")
                
        data_check_string = "\n".join(data_check_list)
        
        # In Telegram Login Widget, the secret key is SHA256 of the bot token
        secret_key = hashlib.sha256(settings.BOT_TOKEN.encode()).digest()
        
        # Calculate HMAC-SHA256
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != hash_value:
            logger.warning("Web Login Auth failed: Hash mismatch", calculated=calculated_hash, received=hash_value)
            return None
            
        return auth_data
    except Exception as e:
        logger.error("Web Login Auth Validation Error", error=str(e))
        return None

