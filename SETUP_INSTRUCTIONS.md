# Setup Instructions for Telegram Football Manager

## Python 3.11 Installation Required

This project requires **Python 3.11** to be installed on your system. Python is not currently detected on your machine.

### Installing Python 3.11

#### Windows

1. **Download Python 3.11**:
   - Visit [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - Download Python 3.11.x (latest 3.11 version)

2. **Install Python**:
   - Run the installer
   - ✅ **IMPORTANT**: Check "Add Python 3.11 to PATH"
   - Click "Install Now"

3. **Verify Installation**:
   ```bash
   py -3.11 --version
   ```
   Should output: `Python 3.11.x`

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

#### macOS

```bash
# Using Homebrew
brew install python@3.11
```

---

## Quick Start (After Python 3.11 is Installed)

### Option 1: Automated Setup (Recommended)

#### Windows
```bash
setup_venv.bat
```

#### Linux/macOS
```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

### Option 2: Manual Setup

1. **Create Virtual Environment**:
   ```bash
   # Windows
   py -3.11 -m venv venv
   venv\Scripts\activate
   
   # Linux/macOS
   python3.11 -m venv venv
   source venv/bin/activate
   ```

2. **Upgrade pip**:
   ```bash
   python -m pip install --upgrade pip
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

---

## Project Structure Created

```
telegram-football-manager/
├── app/
│   ├── __init__.py           # Package initialization
│   └── main.py               # FastAPI application entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── pyproject.toml            # Project configuration
├── README.md                 # Project documentation
├── setup_venv.bat            # Windows setup script
├── setup_venv.sh             # Linux/macOS setup script
└── SETUP_INSTRUCTIONS.md     # This file
```

---

## Next Steps

After Python 3.11 is installed and the virtual environment is set up:

1. **Install PostgreSQL 15+** (for database)
2. **Install Redis 7+** (for caching and task queue)
3. **Create Telegram Bot** (via [@BotFather](https://t.me/botfather))
4. **Configure .env file** with your credentials
5. **Continue with Task 1.2** in the implementation plan

---

## Verification

To verify your setup is complete:

```bash
# Activate virtual environment
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Check Python version
python --version
# Should output: Python 3.11.x

# Check installed packages
pip list

# Run the application
python app/main.py
# Should start FastAPI server on http://localhost:8000
```

---

## Troubleshooting

### "Python not found" error
- Ensure Python 3.11 is installed
- Ensure Python is added to PATH
- Restart your terminal/command prompt

### "pip not found" error
- Run: `python -m ensurepip --upgrade`

### Virtual environment activation issues
- Windows: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Linux/macOS: Ensure script has execute permissions: `chmod +x setup_venv.sh`

---

## Support

For issues or questions, refer to:
- [Requirements Document](.kiro/specs/telegram-football-manager/requirements.md)
- [Design Document](.kiro/specs/telegram-football-manager/design.md)
- [Implementation Tasks](.kiro/specs/telegram-football-manager/tasks.md)
