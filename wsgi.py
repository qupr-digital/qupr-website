import os
from app import create_app

application = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    application.run()
