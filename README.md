# Gold & Silver Loan Management System

A complete, production-ready Windows desktop application for collateral-based gold and silver lending businesses in India.

## Features
- Works 100% offline — local database created automatically on first launch
- Manual daily gold/silver rate entry (optional live rates via goldapi.io when online)
- Complete loan lifecycle: origination → approval → disbursement → repayment → closure → collateral release
- Loan renewal (collateral carried over) and auction review for overdue loans
- Printable PDF payment receipts; admin-only payment reversal with reason
- Customer onboarding with encrypted KYC
- Role-based access (Admin / Lender / Viewer)
- PDF receipts and Excel reports
- Automatic session timeout & audit logs
- Local SQLite database with daily automatic backups

---

## Installation (Development)

### Prerequisites
- Python 3.11+ (no database server needed)

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

### First Launch
1. Run the app — the database is created automatically in `%APPDATA%\GoldSilverLoan\database\gold_loan.db`
2. Log in with **admin / Admin@1234** — you will be asked to set your own password
3. Go to **Gold & Silver Rates** and enter today's rate (₹ per gram)

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

### Rates
Enter daily rates on the **Gold & Silver Rates** page. Optionally, when online, add a goldapi.io key in **Settings → Live Rates API** to fetch live rates.

### Data & Backups
- Database: `%APPDATA%\GoldSilverLoan\database\gold_loan.db`
- Automatic daily backups (last 10 kept): `%APPDATA%\GoldSilverLoan\backups\`
- Manual export/restore: **Backup & Restore** page

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
│   ├── database/           # Local SQLite connection, backups
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
