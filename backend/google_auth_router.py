"""
Google OAuth Authentication Router
===================================
Handles Emergent-managed Google OAuth login and registration.
"""

from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
import httpx

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter(prefix="/api/auth", tags=["Google OAuth"])

# Emergent Auth endpoint
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

# Session duration
SESSION_DURATION_DAYS = 7


class GoogleCallbackRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from Emergent OAuth callback")


class UsernameChangeRequest(BaseModel):
    user_id: str
    new_username: str = Field(..., min_length=3, max_length=30)
    password: Optional[str] = None  # Required for password-based accounts


class ProfileUpdateRequest(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    profile_logo: Optional[str] = None  # URL to logo image
    bio: Optional[str] = None
    status_message: Optional[str] = None


# ============ API Endpoints ============

@router.post("/google/callback")
async def google_oauth_callback(request: GoogleCallbackRequest, response: Response):
    """
    Process Google OAuth callback from Emergent Auth.
    Exchanges session_id for user data and creates/updates user in database.
    """
    try:
        # Call Emergent Auth to get user data
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": request.session_id},
                timeout=10.0
            )
        
        if auth_response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Failed to verify session with authentication server"
            )
        
        auth_data = auth_response.json()
        
        # Extract user info from Emergent Auth response
        email = auth_data.get("email")
        name = auth_data.get("name", "")
        picture = auth_data.get("picture", "")
        session_token = auth_data.get("session_token")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Check if user exists by email
        existing_user = await db.user_profiles.find_one(
            {"email": email},
            {"_id": 0}
        )
        
        now = datetime.now(timezone.utc)
        
        if existing_user:
            # Update existing user
            user_id = existing_user.get("id")
            
            await db.user_profiles.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "last_login": now.isoformat(),
                        "google_picture": picture,
                        "auth_method": "google"
                    },
                    "$inc": {"stats.total_logins": 1}
                }
            )
            
            user = existing_user
            user["last_login"] = now.isoformat()
            is_new_user = False
        else:
            # Create new user
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            
            # Generate username from email (before @)
            base_username = email.split("@")[0].lower()
            base_username = "".join(c for c in base_username if c.isalnum() or c == "_")[:20]
            
            # Check if username exists, add number if needed
            username = base_username
            counter = 1
            while await db.user_profiles.find_one({"username": username}):
                username = f"{base_username}{counter}"
                counter += 1
            
            new_user = {
                "id": user_id,
                "username": username,
                "display_name": name or username,
                "email": email,
                "google_picture": picture,
                "profile_picture": picture,  # Use Google picture as default
                "auth_method": "google",
                "password_hash": None,  # No password for Google auth
                "permission_level": "basic",
                "is_transcendent": False,
                "created_at": now.isoformat(),
                "last_login": now.isoformat(),
                "legacy_usernames": [],  # Track username history
                "stats": {
                    "total_logins": 1
                },
                "resources": {
                    "gold": 100,
                    "essence": 0
                },
                "ve_balance": 0.0,
                "chat_color": "default",
                "show_online": True,
                "allow_whispers": True,
                "bio": "",
                "status_message": ""
            }
            
            await db.user_profiles.insert_one(new_user)
            user = new_user
            is_new_user = True
        
        # Create session record
        session_record = {
            "session_id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": (now + timedelta(days=SESSION_DURATION_DAYS)).isoformat(),
            "created_at": now.isoformat(),
            "auth_method": "google"
        }
        
        await db.user_sessions.insert_one(session_record)
        
        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=SESSION_DURATION_DAYS * 24 * 60 * 60,
            path="/"
        )
        
        return {
            "success": True,
            "is_new_user": is_new_user,
            "user": {
                "user_id": user_id,
                "id": user_id,
                "username": user.get("username"),
                "display_name": user.get("display_name", name),
                "email": email,
                "picture": picture,
                "permission_level": user.get("permission_level", "basic"),
                "is_transcendent": user.get("is_transcendent", False),
                "auth_method": "google"
            }
        }
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unavailable: {str(e)}")
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/username/change")
async def change_username(request: UsernameChangeRequest):
    """
    Change a user's username. Stores old username in legacy_usernames list.
    """
    new_username = request.new_username.lower().strip()
    
    # Validate username format
    if not new_username.isalnum() and "_" not in new_username:
        raise HTTPException(
            status_code=400,
            detail="Username can only contain letters, numbers, and underscores"
        )
    
    # Check if username is taken
    existing = await db.user_profiles.find_one(
        {"username": new_username, "id": {"$ne": request.user_id}}
    )
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    
    # Get current user
    user = await db.user_profiles.find_one({"id": request.user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_username = user.get("username")
    
    # If password-based auth, verify password
    if user.get("auth_method") != "google" and user.get("password_hash"):
        if not request.password:
            raise HTTPException(
                status_code=400,
                detail="Password required to change username"
            )
        import bcrypt
        if not bcrypt.checkpw(request.password.encode(), user["password_hash"].encode()):
            raise HTTPException(status_code=401, detail="Invalid password")
    
    # Add current username to legacy list
    legacy_usernames = user.get("legacy_usernames", [])
    if current_username and current_username not in legacy_usernames:
        legacy_usernames.append({
            "username": current_username,
            "changed_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Update username
    await db.user_profiles.update_one(
        {"id": request.user_id},
        {
            "$set": {
                "username": new_username,
                "legacy_usernames": legacy_usernames,
                "username_changed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "new_username": new_username,
        "previous_username": current_username,
        "legacy_usernames": [l.get("username") for l in legacy_usernames]
    }


@router.get("/user/{user_id}/legacy-names")
async def get_legacy_usernames(user_id: str):
    """Get a user's username history (legacy names)."""
    user = await db.user_profiles.find_one(
        {"id": user_id},
        {"_id": 0, "username": 1, "legacy_usernames": 1, "display_name": 1}
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "current_username": user.get("username"),
        "display_name": user.get("display_name"),
        "legacy_usernames": user.get("legacy_usernames", [])
    }


@router.put("/profile/update")
async def update_profile_details(request: ProfileUpdateRequest):
    """Update profile details including logo URL."""
    user = await db.user_profiles.find_one({"id": request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = {}
    
    if request.display_name is not None:
        if len(request.display_name) < 2 or len(request.display_name) > 30:
            raise HTTPException(
                status_code=400,
                detail="Display name must be 2-30 characters"
            )
        updates["display_name"] = request.display_name
    
    if request.profile_logo is not None:
        # Validate URL format (basic check)
        if request.profile_logo and not request.profile_logo.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail="Profile logo must be a valid URL"
            )
        updates["profile_logo"] = request.profile_logo
        updates["profile_picture"] = request.profile_logo  # Also set as profile picture
    
    if request.bio is not None:
        if len(request.bio) > 500:
            raise HTTPException(status_code=400, detail="Bio must be under 500 characters")
        updates["bio"] = request.bio
    
    if request.status_message is not None:
        if len(request.status_message) > 100:
            raise HTTPException(status_code=400, detail="Status must be under 100 characters")
        updates["status_message"] = request.status_message
    
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.user_profiles.update_one(
            {"id": request.user_id},
            {"$set": updates}
        )
    
    return {
        "success": True,
        "updated_fields": list(updates.keys())
    }


@router.get("/me")
async def get_current_user(request: Request):
    """
    Get current authenticated user from session cookie.
    Used for session verification.
    """
    # Check cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user = await db.user_profiles.find_one(
        {"id": session["user_id"]},
        {"_id": 0, "password_hash": 0}
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout - clear session cookie and delete session from database."""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        # Delete session from database
        await db.user_sessions.delete_one({"session_token": session_token})
    
    # Clear cookie
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="none"
    )
    
    return {"success": True, "message": "Logged out successfully"}


class PasswordChangeRequest(BaseModel):
    user_id: str
    current_password: str
    new_password: str = Field(..., min_length=6)


@router.post("/password/change")
async def change_password(request: PasswordChangeRequest):
    """Change password for password-based accounts."""
    import bcrypt
    
    user = await db.user_profiles.find_one({"id": request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cannot change password for Google accounts
    if user.get("auth_method") == "google" and not user.get("password_hash"):
        raise HTTPException(
            status_code=400,
            detail="Google accounts cannot change password here"
        )
    
    # Verify current password
    if not user.get("password_hash"):
        raise HTTPException(status_code=400, detail="No password set for this account")
    
    if not bcrypt.checkpw(request.current_password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Hash new password
    new_hash = bcrypt.hashpw(request.new_password.encode(), bcrypt.gensalt()).decode()
    
    # Update password
    await db.user_profiles.update_one(
        {"id": request.user_id},
        {
            "$set": {
                "password_hash": new_hash,
                "password_changed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"success": True, "message": "Password changed successfully"}

