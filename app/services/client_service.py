import secrets
import string
from app.models.user import User
from app.models.client import Client


class ClientService:
    """Service for client management"""
    
    @staticmethod
    def generate_password(length=12):
        """Generate random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password
    
    @staticmethod
    def create_client_with_user(company_name, gstin, billing_address,
                                contact_person, contact_email, contact_phone):
        """Create client and associated user account"""
        # Check if email already exists
        existing_user = User.get_by_email(contact_email)
        if existing_user:
            raise ValueError(f"A user with email {contact_email} already exists")
        
        # Create client
        client_id = Client.create(
            company_name=company_name,
            gstin=gstin,
            billing_address=billing_address,
            contact_person=contact_person,
            contact_email=contact_email,
            contact_phone=contact_phone
        )
        
        # Generate credentials
        password = ClientService.generate_password()
        
        # Create user account
        try:
            user_id = User.create(
                name=contact_person or company_name,
                email=contact_email,
                password=password,
                role=User.ROLE_CLIENT,
                client_id=client_id
            )
        except Exception as e:
            # If user creation fails, we should clean up the client
            # But for now, just raise the error
            raise Exception(f"Failed to create user account: {str(e)}")
        
        return {
            'client_id': client_id,
            'user_id': user_id,
            'email': contact_email,
            'password': password
        }
    
    @staticmethod
    def get_client_user(client_id):
        """Get user associated with client"""
        from app import get_db
        from bson import ObjectId
        db = get_db()
        return db.users.find_one({'client_id': ObjectId(client_id)})
    
    @staticmethod
    def reset_client_password(client_id):
        """Reset client user password"""
        user = ClientService.get_client_user(client_id)
        if not user:
            return None
        
        new_password = ClientService.generate_password()
        User.update_password(str(user['_id']), new_password)
        
        return {
            'email': user['email'],
            'password': new_password
        }
