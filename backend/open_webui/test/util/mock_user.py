"""
Mock user context manager for testing.
Provides a way to mock authenticated users in API tests.
"""
import os
from contextlib import contextmanager
from typing import Optional
from unittest.mock import patch, MagicMock


@contextmanager
def mock_webui_user(
    id: str = 'test-user-id',
    email: str = 'test@example.com',
    name: str = 'Test User',
    role: str = 'user',
    api_key: Optional[str] = None,
):
    """
    Context manager to mock an authenticated user for testing.
    
    Args:
        id: User ID
        email: User email
        name: User name
        role: User role (admin, user, pending)
        api_key: Optional API key
    """
    from open_webui.models.users import UserModel
    
    # Create a mock user
    mock_user_data = {
        'id': id,
        'email': email,
        'name': name,
        'role': role,
        'api_key': api_key,
        'profile_image_url': '/user.png',
    }
    
    # Patch the token verification to return our mock user
    with patch('open_webui.utils.auth.get_current_user') as mock_get_user:
        mock_user = MagicMock()
        for key, value in mock_user_data.items():
            setattr(mock_user, key, value)
        
        # Make it iterable like a dict
        mock_user.__getitem__ = lambda self, key: mock_user_data.get(key)
        mock_user.__iter__ = lambda self: iter(mock_user_data.keys())
        
        mock_get_user.return_value = mock_user
        
        yield mock_user
