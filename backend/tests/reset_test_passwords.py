#!/usr/bin/env python3
"""
Reset test user passwords before running API tests.
Run this script before each test session to ensure consistent credentials.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import warnings

warnings.filterwarnings('ignore')

load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

TEST_USERS = [
    ('admin@company.com', 'admin123', 'admin'),
    ('manager@company.com', 'manager123', 'manager'),
    ('executive@company.com', 'executive123', 'executive'),
]

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


async def reset_test_passwords():
    """Reset all test user passwords to known values."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("Resetting test user passwords...")
    
    for email, password, role in TEST_USERS:
        # Check if user exists
        user = await db.users.find_one({'email': email})
        
        if user:
            # Update password
            new_hash = pwd_context.hash(password)
            result = await db.users.update_one(
                {'email': email},
                {'$set': {'hashed_password': new_hash}}
            )
            print(f"  Updated {email}: {result.modified_count} modified")
        else:
            # Create user
            import uuid
            from datetime import datetime, timezone
            
            doc = {
                'id': str(uuid.uuid4()),
                'email': email,
                'full_name': f'Test {role.title()}',
                'role': role,
                'is_active': True,
                'hashed_password': pwd_context.hash(password),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(doc)
            print(f"  Created {email}")
    
    client.close()
    print("Done!")


if __name__ == '__main__':
    asyncio.run(reset_test_passwords())
