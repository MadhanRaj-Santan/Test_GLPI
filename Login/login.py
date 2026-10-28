import os
import secrets
from datetime import datetime, timedelta, timezone
from html import escape

import jwt
from pwdlib import PasswordHash
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# ==================================================
# 1. APPLICATION CONFIGURATION
# ==================================================

app = FastAPI(title="D-TOP | GLPI Integration Prototype")

def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Set {name} before starting the app.")
    return value


JWT_SECRET = required_env("JWT_SECRET_KEY")
LOGIN_USERNAME = required_env("LOGIN_USERNAME")
LOGIN_PASSWORD = required_env("LOGIN_PASSWORD")

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "dtop-local"
JWT_AUDIENCE = "dtop-local"
JWT_LIFETIME_MINUTES = 15

SESSION_COOKIE = "dtop_session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

password_hasher = PasswordHash.recommended()

# ==================================================
# 2. DEMO ORGANIZATION AND USER CONFIGURATION
# ==================================================

USERS = {
    LOGIN_USERNAME: {
        "password_hash": password_hasher.hash(LOGIN_PASSWORD),
        "organization_id": "org1",
    }
}

ORGANIZATIONS = {
    "org1": {
        "name": "Demo Organization",
        "glpi_url": os.getenv("GLPI_ORG1_URL", "http://localhost"),
    }
}

# ==================================================
# 3. JWT SESSION HELPERS
# ==================================================

def create_session_token(username: str, organization_id: str) -> str:
    """Create a short-lived signed JWT for the local prototype."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": username,
        "org_id": organization_id,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_LIFETIME_MINUTES),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": secrets.token_urlsafe(16),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_session_claims(request: Request):
    """Return validated session claims, or None if invalid."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    try:
        claims = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["sub", "org_id", "iat", "exp", "jti"]},
        )
    except jwt.InvalidTokenError:
        return None

    # Confirm the user still exists and belongs to this organization.
    user = USERS.get(claims["sub"])
    if not user or user["organization_id"] != claims["org_id"]:
        return None

    if claims["org_id"] not in ORGANIZATIONS:
        return None

    return claims


def set_session_cookie(response, token: str):
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=JWT_LIFETIME_MINUTES * 60,
        httponly=True,
        secure=COOKIE_SECURE,  # True when using HTTPS
        samesite="lax",
        path="/",
    )


def redirect_to_login():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return response


# ==================================================
# 4. LOGIN PAGE
# ==================================================

@app.get("/", response_class=HTMLResponse)
def login_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>D-TOP Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f1f5f9;
                display: grid;
                place-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .card {
                background: white;
                padding: 30px;
                border-radius: 12px;
                width: min(320px, 80vw);
                box-shadow: 0 4px 20px #0001;
            }
            input, button {
                box-sizing: border-box;
                width: 100%;
                padding: 12px;
                margin-top: 12px;
                border-radius: 6px;
            }
            input { border: 1px solid #cbd5e1; }
            button {
                background: #2563eb;
                color: white;
                border: 0;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>D-TOP Login</h2>
            <form action="/login" method="post">
                <input name="username" placeholder="Username"
                       autocomplete="username" required>
                <input name="password" type="password"
                       placeholder="Password"
                       autocomplete="current-password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """

# ==================================================
# 5. LOGIN AND SESSION CREATION
# ==================================================

@app.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
):
    user = USERS.get(username)

    if not user or not password_hasher.verify(password, user["password_hash"]):
        return HTMLResponse(
            "<h3>Invalid username or password.</h3><a href='/'>Try again</a>",
            status_code=401,
        )

    token = create_session_token(
        username=username,
        organization_id=user["organization_id"],
    )

    response = RedirectResponse("/dashboard", status_code=303)
    set_session_cookie(response, token)
    return response

# ==================================================
# 6. PROTECTED DASHBOARD
# ==================================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    claims = get_session_claims(request)
    if not claims:
        return redirect_to_login()

    username = escape(claims["sub"])
    organization_id = escape(claims["org_id"])
    organization = ORGANIZATIONS[claims["org_id"]]
    organization_name = escape(organization["name"])

    return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>D-TOP Dashboard</title></head>
        <body>
            <h2>Login successful</h2>
            <p>User: {username}</p>
            <p>Organization: {organization_name} ({organization_id})</p>
            <p>Local JWT session validated successfully.</p>
            <p><a href="/open-glpi">Open my organization's GLPI</a></p>
            <form action="/logout" method="post">
                <button type="submit">Logout</button>
            </form>
        </body>
        </html>
    """

# ==================================================
# 7. ORGANIZATION-SPECIFIC GLPI REDIRECT
# ==================================================

@app.get("/open-glpi")
def open_glpi(request: Request):
    claims = get_session_claims(request)
    if not claims:
        return redirect_to_login()

    organization = ORGANIZATIONS.get(claims["org_id"])
    if not organization:
        raise HTTPException(status_code=403, detail="Organization not found")

    return RedirectResponse(organization["glpi_url"], status_code=303)

# ==================================================
# 8. LOGOUT
# ==================================================

@app.post("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return response

# ==================================================
# 9. CURRENT USER API
# ==================================================

@app.get("/api/me")
def current_user(request: Request):
    claims = get_session_claims(request)
    if not claims:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    return {
        "username": claims["sub"],
        "organization_id": claims["org_id"],
    }