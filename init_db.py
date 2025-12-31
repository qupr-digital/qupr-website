"""
Database initialization script for Qupr Digital

This script creates the initial owner account.
Run this once after setting up the database.
"""

from app import create_app
from app.models.user import User
import sys

def init_database():
    """Initialize database with owner account"""
    app = create_app()
    
    with app.app_context():
        # Check if owner already exists
        owner = User.get_by_email('admin@quprdigital.tk')
        
        if owner:
            print("Owner account already exists!")
            return
        
        # Create owner account
        try:
            owner_id = User.create(
                name='Admin',
                email='admin@quprdigital.tk',
                password='admin123',  # Change this password immediately!
                role=User.ROLE_OWNER
            )
            
            print("✓ Database initialized successfully!")
            print("✓ Owner account created")
            print("\nLogin Credentials:")
            print("  Email: admin@quprdigital.tk")
            print("  Password: admin123")
            print("\n⚠️  IMPORTANT: Change the password immediately after first login!")
            
        except Exception as e:
            print(f"✗ Error creating owner account: {str(e)}")
            sys.exit(1)


if __name__ == '__main__':
    init_database()
