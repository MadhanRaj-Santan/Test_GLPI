# GLPI_Login

Two FastAPI login prototypes for a GLPI integration:

- `Login/login.py` uses a signed session cookie.
- `Login/main.py` validates an organization-specific username and password before redirecting.

## Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Set credentials in the same PowerShell window before starting an app. Use real,
unique values locally; do not commit them.

For `Login/login.py`:

```powershell
$env:JWT_SECRET_KEY = "<long-random-secret>"
$env:LOGIN_USERNAME = "<username>"
$env:LOGIN_PASSWORD = "<password>"
python -m uvicorn Login.login:app --reload
```

For `Login/main.py`:

```powershell
$env:GLPI_ORG1_USERNAME = "<username>"
$env:GLPI_ORG1_PASSWORD = "<password>"
$env:GLPI_ORG1_URL = "https://your-glpi-instance.example"
python -m uvicorn Login.main:app --reload
```
