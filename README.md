# Gold & Silver Loan Management System

A complete, production-ready Windows desktop application for collateral-based gold and silver lending businesses in India.

## Features
- Live gold/silver rate integration (goldapi.io)
- Complete loan origination → disbursement → repayment lifecycle
- Customer onboarding with encrypted KYC
- Role-based access (Admin / Lender / Viewer)
- PDF receipts and Excel reports
- Automatic session timeout & audit logs
- MySQL database via SSH tunnel

---

## Installation (Development)

### Prerequisites
- Python 3.11+
- MySQL server accessible via SSH tunnel

### Setup
```bash
cd "windows application/gold_silver_loan"
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux (dev)
source venv/bin/activate

pip install -r requirements.txt
```

### Run
```bash
python main.py
```

### Database Setup (run once on server before first launch)
```bash
# SSH into your server, then run:
mysql -u root -p < setup_database.sql
```
This creates the `gold_loan_db` database and all 13 tables.

### First Launch
1. On the **Database Connection** screen, enter your SSH and MySQL credentials
2. Click **Connect to Database**
3. Log in with: **admin / Admin@1234** (you will be forced to change this)

---

## Build Windows EXE

### On a Windows machine with Python 3.11+ installed:
Double-click `build.bat` — it handles everything automatically.

Or manually:
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build_exe.spec --noconfirm
```

Output: `dist\GoldSilverLoan\GoldSilverLoan.exe`

### Create installer (optional):
Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then compile:
```
installer/installer.iss
```

---

## Configuration

All configuration is stored in:
- **Windows**: `%APPDATA%\GoldSilverLoan\config.json`
- **macOS/Linux (dev)**: `~/.goldsilverl​oan/config.json`

### Rate API
Get a free API key at [goldapi.io](https://www.goldapi.io) and enter it in **Settings → Rate API Provider**.

### SSH / Database
Configured via the login screen on first launch. Settings are saved to `config.json` in AppData — passwords are never bundled inside the EXE.

---

## Security Notes

1. **KYC documents**: Aadhaar/PAN references are stored encrypted using Fernet (per-installation key in `%APPDATA%\GoldSilverLoan\.enc_key`)
2. **Passwords**: Hashed with Argon2id — never stored in plain text
3. **Financial records**: Never deleted — only reversed with audit trail
4. **Session timeout**: Configurable, defaults to 30 minutes of inactivity

---

## Database Schema

Key tables:
| Table | Purpose |
|-------|---------|
| `users` | Logins, roles, session tracking |
| `customers` | Customer profiles |
| `kyc_documents` | Encrypted KYC references |
| `loans` | Loan lifecycle |
| `collateral_items` | Gold/silver items with valuations |
| `repayments` | Payment history (never deleted) |
| `metal_rate_history` | Live rate cache |
| `audit_logs` | Full activity audit trail |
| `app_settings` | Configurable business settings |

---

## Running Tests

```bash
pytest tests/ -v --tb=short
```

---

## Project Structure

```
gold_silver_loan/
├── app/
│   ├── config.py           # Configuration management
│   ├── database/           # SQLAlchemy connection + base
│   ├── models/             # ORM models (all tables)
│   ├── services/           # Business logic layer
│   ├── api/                # Metal rate API providers
│   ├── ui/                 # PySide6 UI
│   │   ├── login_window.py
│   │   ├── main_window.py
│   │   ├── pages/          # One file per page
│   │   ├── dialogs/        # Modal dialogs
│   │   └── widgets/        # Reusable components
│   └── utils/              # Security, PDF, Excel, formatters
├── assets/styles/main.qss  # Application stylesheet
├── tests/                  # Pytest tests
├── installer/              # Inno Setup installer script
├── build_exe.spec          # PyInstaller spec
├── main.py                 # Entry point
└── requirements.txt
```

---

## Regulatory Notice

This software is a management tool. It does not constitute authorization to conduct lending operations. Lenders must comply with applicable RBI regulations, PMLA/KYC requirements, state money-lending acts, and data protection laws independently.

---

## Changelog

### v1.0.0
- Initial release covering all 7 development phases
- Live rate integration via goldapi.io
- Full loan lifecycle management
- Encrypted KYC storage
- PDF receipts and Excel reports
- Windows EXE packaging via PyInstaller
