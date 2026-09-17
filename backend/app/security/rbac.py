from typing import List
from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.security.auth import get_current_user

def require_roles(allowed_roles: List[str]):
    """Dependency factory checking that current user has one of the allowed roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles {allowed_roles}, but current role is {current_user.role}."
            )
        return current_user
    return role_checker

# Reusable role-check dependencies
require_platform_admin = require_roles(["PLATFORM_ADMIN"])
require_hospital_admin = require_roles(["HOSPITAL_ADMIN", "PLATFORM_ADMIN"])
require_doctor = require_roles(["DOCTOR", "PLATFORM_ADMIN"])
require_patient = require_roles(["PATIENT"])
require_staff_or_admin = require_roles(["DOCTOR", "HOSPITAL_ADMIN", "PLATFORM_ADMIN"])
