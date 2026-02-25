import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from models import AuditLog
from utils.timezone import now_tashkent

def calculate_hash(previous_hash: str, timestamp, details: dict) -> str:
    """
    Calculates SHA256 hash for the log entry.
    Structure: confirm_hash(prev_hash + timestamp_iso + sorted_json_details)
    """
    # Ensure consistent JSON stringification
    details_str = json.dumps(details, sort_keys=True, separators=(',', ':'))
    # Use isoformat() but be careful about precision. 
    # Ideally, store timestamp as string if high precision is risky across DBs.
    timestamp_str = timestamp.isoformat() if timestamp else ""
    
    # payload to hash
    payload = f"{previous_hash}{timestamp_str}{details_str}"
    
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

async def log_event(db: AsyncSession, event_type: str, details: dict):
    """
    Logs an event to the audit chain.
    """
    # Get the last log to establish the chain link
    result = await db.execute(select(AuditLog).order_by(desc(AuditLog.id)).limit(1))
    last_log = result.scalars().first()
    
    previous_hash = last_log.hash if last_log else "GENESIS_HASH"
    
    # Create timestamp
    timestamp = now_tashkent()
    
    # Calculate new hash
    current_hash = calculate_hash(previous_hash, timestamp, details)
    
    # create record
    new_log = AuditLog(
        timestamp=timestamp,
        event_type=event_type,
        details=details,
        previous_hash=previous_hash,
        hash=current_hash
    )
    
    db.add(new_log)
    await db.commit()
    await db.refresh(new_log)
    
    return new_log

async def verify_chain(db: AsyncSession) -> bool:
    """
    Verifies the integrity of the entire audit chain.
    Returns True if valid, False if tampered.
    """
    result = await db.execute(select(AuditLog).order_by(AuditLog.id))
    logs = result.scalars().all()
    
    if not logs:
        return True
        
    previous_hash = "GENESIS_HASH"
    
    for log in logs:
        # Re-calculate hash
        calculated_hash = calculate_hash(previous_hash, log.timestamp, log.details)
        
        if calculated_hash != log.hash:
            print(f"INTEGRITY FAILURE at Log ID {log.id}")
            print(f"Expected: {calculated_hash}")
            print(f"Found:    {log.hash}")
            return False
            
        previous_hash = log.hash
        
    return True
