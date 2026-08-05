Walters Opticians Backend API
A high-performance RESTful API built with FastAPI, SQLAlchemy, and Pydantic to power the Walters Opticians e-commerce platform. Features role-based JWT authentication, multi-attribute catalog filtering, and dual-identifier product management.

Features
JWT Authentication & Authorization: Secure user registration, login, and profile management with HTTP Bearer token security and role-based access control (admin vs customer).

Flexible Product Lookup: Retrieve, update, or delete catalog items dynamically using either a numeric ID or an exact product Name.

Advanced Catalog Search & Filtering: Filter products by brand, frame shape, color description, price range, and stock availability, with built-in multi-column text search (q) and pagination.

Environment Security: Isolation of secrets (SECRET_KEY, algorithm, token expiration) managed through Pydantic settings and .env.

Auto-Generated OpenAPI Documentation: Interactive Swagger UI configured for token authorization out of the box.

Tech Stack
Framework: FastAPI

Database / ORM: SQLite / SQLAlchemy

Data Validation: Pydantic V2 / pydantic-settings

Security & Auth: python-jose (JWT), passlib (Bcrypt hashing), FastAPI HTTPBearer

ASGI Server: Uvicorn

Walters-Opticians-Backend/
├── app/
│   ├── api/
│   │   ├── deps.py             # Security & DB dependency injections
│   │   └── v1/
│   │       ├── auth.py         # Login, Registration & User profile routes
│   │       ├── products.py     # Catalog CRUD & flexible search endpoints
│   │       ├── cart.py         # Cart management endpoints
│   │       ├── orders.py       # Order processing endpoints
│   │       ├── currency.py     # Currency conversion utilities
│   │       └── store_settings.py
│   ├── core/
│   │   ├── config.py           # Pydantic environment configuration
│   │   └── security.py         # Password hashing & JWT generation
│   ├── db/
│   │   ├── base.py             # SQLAlchemy Base declarative setup
│   │   └── session.py          # Database engine & session creation
│   ├── models/                 # SQLAlchemy database models
│   ├── schemas/                # Pydantic validation & response schemas
│   └── main.py                 # FastAPI application entry point
├── .env                        # Local environment secrets (Git-ignored)
├── .gitignore
├── requirements.txt
└── README.md


Getting Started
Prerequisites
Python 3.10+ installed on your system.

1. Clone the Repository
    git clone https://github.com/YT-TONY/Walters-Opticians-Backend.git
    cd Walters-Opticians-Backend
2. Set Up Virtual Environment
    python -m venv venv
    .\venv\Scripts\Activate.ps1

    python3 -m venv venv
    source venv/bin/activate
3. Install Dependencies
      pip install -r requirements.txt
4. Configure Environment Variables
      Create a .env file in the root directory:
   
SECRET_KEY=your_super_secret_hex_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
6. Run Development Server
    uvicorn app.main:app --reload
The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

API Documentation
Once the server is running, navigate to the interactive documentation:

Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)


## Core Endpoints Overview

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/signup` | Register a new user account | No |
| `POST` | `/api/v1/auth/login` | Authenticate & receive JWT access token | No |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile details | Yes (Bearer Token) |

### Products & Catalog (`/api/v1/products`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/products/` | Query catalog with search (`q`), filters (`brand`, `shape`, `color`), price limits, stock status, and pagination | No |
| `GET` | `/api/v1/products/{identifier}` | Get single product by numeric `id` or exact `name` | No |
| `POST` | `/api/v1/products/` | Create a new catalog item | Yes (Admin Only) |
| `PUT` | `/api/v1/products/{identifier}` | Update product details dynamically by `id` or `name` | Yes (Admin Only) |
| `DELETE` | `/api/v1/products/{identifier}` | Remove product from catalog by `id` or `name` | Yes (Admin Only) |
