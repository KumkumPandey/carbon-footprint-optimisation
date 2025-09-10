import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from flask_login import current_user

class JWTAuth:
    @staticmethod
    def generate_token(user_id, role='employee'):
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            payload = JWTAuth.verify_token(token)
            if not payload:
                return jsonify({'error': 'Invalid token'}), 401
            
            request.current_user_id = payload['user_id']
            request.current_user_role = payload['role']
        except:
            return jsonify({'error': 'Invalid token format'}), 401
        
        return f(*args, **kwargs)
    return decorated

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'current_user_role') or request.current_user_role != required_role:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator