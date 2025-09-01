# 📄 Mediclaim Processing API

## 📝 Overview

The Mediclaim Processing API is a robust, AI-powered backend designed to automate the adjudication of medical insurance claims. It ingests PDF hospital bills, extracts structured data using a multimodal LLM, applies a dynamic rules engine based on policy details, and determines the final payable amount. The API features a secure, role-based access control system, separating the core claims processing workflow from administrative functions.

## ✨ Features

- **AI-Powered Data Extraction**: Utilizes a multimodal LLM (GPT-4o) to extract structured data and confidence scores from PDF medical bills.
- **Dynamic Rules Engine**: Applies a flexible, policy-driven rules engine to adjudicate claims, handling non-payable items, complex sub-limits, and co-payments.
- **Secure Authentication**: Implements JWT Bearer Token authentication to secure all sensitive endpoints.
- **Role-Based Access Control**: Differentiates between "Claims Processor" and "Admin" roles with distinct permissions.
- **Full Admin Panel**: Provides a suite of admin APIs to manage users, roles, and insurance policy rulebooks directly in the database.
- **Robust & Scalable**: Built with FastAPI and SQLAlchemy for high performance.
- **Rate Limiting**: Protects the API from abuse with configurable rate limits on intensive endpoints.

## 🛠️ Tech Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **AI & LLMs**: OpenAI (GPT-4o), LangChain
- **Authentication**: JWT, Passlib
- **API Schemas**: Pydantic
- **Rate Limiting**: slowapi
- **PDF Processing**: pdf2image

## 📂 Project Structure

```
mediclaim_backend/
├── app/
│   ├── endpoints/
│   │   ├── admin.py
│   │   └── claims.py
│   ├── auth.py
│   ├── config.py
│   ├── crud.py
│   ├── database.py
│   ├── llm_tool_engine.py
│   ├── models.py
│   ├── normalization_service.py
│   ├── rules_engine.py
│   ├── schemas.py
│   ├── value_extractor.py
│   └── main.py
├── scripts/
│   ├── initialize_db.py
│   ├── create_roles.py
│   └── seed_policies.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## 🚀 Setup and Installation

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd mediclaim_backend
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** `pdf2image` requires the poppler system library. Install it with `sudo apt install poppler-utils` on Ubuntu/Debian.

### 4. Configure Environment Variables
Create a `.env` file from the example.
```bash
cp .env.example .env
```

Edit the `.env` file and add your actual secrets:
```env
DATABASE_URL="postgresql://mediclaim_user:your_secure_password@localhost/mediclaim_db"
OPENAI_API_KEY="sk-..."
JWT_SECRET_KEY="your_long_random_secret_key"
```

### 5. Set Up the PostgreSQL Database
Connect to PostgreSQL and create the database and user.
```sql
CREATE DATABASE mediclaim_db;
CREATE USER mediclaim_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE mediclaim_db TO mediclaim_user;
```

### 6. Initialize the Database
You can initialize the database in two ways:

#### Option A (Recommended): Restore from Dump
A `dump.sql` file is provided with this repository. It contains the complete database schema and all necessary initial data (roles, policies, users). Restore it using this command:
```bash
psql -U mediclaim_user -d mediclaim_db < dump.sql
```

#### Option B (Manual Initialization)
If you are not using the dump file, run the following scripts in order:
```bash
# 1. Create tables
python scripts/initialize_db.py

# 2. Create user roles
python scripts/create_roles.py

# 3. Add policy rulebooks to DB
python scripts/seed_policies.py

# 4. Create first admin user
python scripts/create_initial_data.py
```

## ▶️ Running the Application

To start the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at http://127.0.0.1:8000.

Interactive documentation is at http://127.0.0.1:8000/docs.

## 🧪 Testing

The project contains several standalone test scripts in the `tests/` directory that can be run directly with Python.

To run a specific test, execute its file from the project root. For example:
```bash
python tests/test_e2e_workflow.py
```

## 📝 API Endpoints Summary

### Authentication
- **POST** `/api/v1/token`: Login to get a JWT.

### Client API (Claims Processors)
- **POST** `/api/v1/claims/extract`: Upload PDF for AI data extraction.
- **POST** `/api/v1/claims/adjudicate`: Submit verified data for final adjudication.
- **GET** `/api/v1/claims/`: Get a list of all claims.
- **GET** `/api/v1/claims/{claim_id}`: Get details of a specific claim.

### Admin API (System Administrators)
- **POST** `/api/v1/admin/users`: Create a new user.
- **GET** `/api/v1/admin/users`: List all users.
- **PUT** `/api/v1/admin/users/{user_id}`: Update a user's details.
- **GET** `/api/v1/admin/policies`: List all policy rulebooks.
- **GET** `/api/v1/admin/policies/{policy_id}`: Get rules for a specific policy.
- **PUT** `/api/v1/admin/policies/{policy_id}`: Update rules for a specific policy.
