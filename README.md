# ROBOX Desktop Application

## 🚀 How to Run the Application

### Step 1: Install Dependencies

pip install -r requirements.txt

### Step 2: Start Backend Server

**Open a terminal and run:**

```bash
cd backend
uvicorn app.main:app --reload
```

The backend will start at `http://localhost:8000`

**Note:** Make sure you have created `backend/.env` file with your MongoDB and SMTP credentials before starting.


### Step 3: Start Desktop Application

**Open another terminal and run:**

```bash
create a venv

For normal testing with out robot : pip install -r requirements.txt 

With robot: pip install -e.

python master_main_app.py

For MacOS:

brew install python@3.11
pyenv install 3.11.14
pyenv global 3.11.14

pyenv install 3.11.14
pyenv versions

python -m venv venv
source venv/bin/activate

python --version

```