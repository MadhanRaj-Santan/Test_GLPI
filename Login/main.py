import os

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="GLPI Login Application")


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Set {name} before starting the app.")
    return value


# Temporary organization-to-GLPI mapping for local testing.
# Replace these example URLs with your actual GLPI instance URLs.
ORGANIZATIONS = {
    "org1": {
        "username": required_env("GLPI_ORG1_USERNAME"),
        "password": required_env("GLPI_ORG1_PASSWORD"),
        "glpi_url": "http://localhost",
    }
}


@app.get("/", response_class=HTMLResponse)
def login_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GLPI Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f1f5f9;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .login-box {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 20px #0001;
                width: 320px;
            }
            h2 { text-align: center; color: #1e293b; }
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
                border: none;
                cursor: pointer;
            }
            button:hover { background: #1d4ed8; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>GLPI Login</h2>
            <form action="/login" method="post">
                <input name="organization_id"
                       placeholder="Organization ID"
                       required>
                <input name="username"
                       placeholder="Username"
                       required>
                <input name="password"
                       type="password"
                       placeholder="Password"
                       required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.post("/login")
def login(
    organization_id: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    organization = ORGANIZATIONS.get(organization_id)

    if (
        organization is None
        or username != organization["username"]
        or password != organization["password"]
    ):
        return HTMLResponse(
            "<h3>Invalid organization ID, username, or password.</h3>"
            '<a href="/">Try again</a>',
            status_code=401,
        )

    # Redirect after successful validation.
    return RedirectResponse(
        url=organization["glpi_url"],
        status_code=303,
    )