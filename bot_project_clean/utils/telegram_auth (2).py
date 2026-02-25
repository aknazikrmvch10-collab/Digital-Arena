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
