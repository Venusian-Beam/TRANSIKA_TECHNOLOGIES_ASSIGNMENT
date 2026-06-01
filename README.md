# Transika Payment Collections & FX Conversion API

A production-quality FastAPI service for initiating payment collections across African currencies and executing FX conversions with real-time quoting, fee calculation, and lifecycle management.

## Features

- **Payment Collections** — Initiate and track payment collections with time-based status transitions (`pending` → `processing` → `completed`).
- **FX Quoting** — Generate time-limited FX quotes across 12 currency corridors with transparent fee calculation.
- **Conversion Execution** — Execute quoted conversions with strict validation of quote expiry and collection completion.
- **Consistent Error Handling** — Uniform JSON error envelope across all endpoints with machine-readable error codes.
- **OpenAPI Documentation** — Auto-generated interactive API docs at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Supported Currencies

| Code | Currency                  |
|------|---------------------------|
| GHS  | Ghanaian Cedi             |
| NGN  | Nigerian Naira            |
| KES  | Kenyan Shilling           |
| ZAR  | South African Rand        |
| USD  | United States Dollar      |

## Tech Stack

- **Python** 3.12+
- **FastAPI** 0.115+
- **Pydantic** v2
- **Uvicorn** (ASGI server)
- **Pytest** (testing)

## Quick Start

### 1. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the docs

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

## API Overview

### Collections

| Method | Endpoint                        | Description                    |
|--------|---------------------------------|--------------------------------|
| POST   | `/collections/initiate`         | Initiate a payment collection  |
| GET    | `/collections/{collection_id}`  | Retrieve collection status     |

### Conversions

| Method | Endpoint                | Description                      |
|--------|-------------------------|----------------------------------|
| POST   | `/conversions/quote`    | Request an FX conversion quote   |
| POST   | `/conversions/execute`  | Execute a quoted FX conversion   |

### Error Response Format

All errors follow a consistent structure:

```json
{
  "code": "UNSUPPORTED_CURRENCY",
  "message": "Currency 'XYZ' is not supported.",
  "details": {
    "currency": "XYZ"
  }
}
```

## Fee Schedule

- **Rate:** 1.2% of the USD-equivalent source amount
- **Minimum:** USD 0.50

## Project Structure

```
app/
├── main.py                  # FastAPI app + global exception handlers
├── constants/
│   └── currencies.py        # Currency enum, FX rates, fee constants
├── exceptions/
│   └── handlers.py          # Custom exception hierarchy
├── models/
│   ├── collections.py       # Pydantic models for collections
│   ├── conversions.py       # Pydantic models for conversions
│   └── responses.py         # Uniform error response envelope
├── routers/
│   ├── collections.py       # Collection endpoints
│   └── conversions.py       # Conversion endpoints
├── services/
│   ├── collections.py       # Collection business logic
│   └── conversions.py       # Conversion business logic
└── storage/
    └── memory.py            # Thread-safe in-memory storage

tests/
├── conftest.py              # Shared fixtures (isolated TestClient)
├── test_collections.py      # Collection endpoint tests
└── test_conversions.py      # Conversion endpoint tests
```

## Running Tests

```bash
pytest -v
```

## Security Considerations

- **Input Validation:** All inputs are validated through Pydantic v2 models with enum constraints, positive-amount guards, and string length limits.
- **UUID Identifiers:** All resource IDs use UUID4, preventing sequential enumeration.
- **Error Isolation:** Exception handlers never leak stack traces or internal details.
- **Defence in Depth:** Currency validation occurs at both the Pydantic schema layer and the service layer.
- **Thread Safety:** In-memory stores use `threading.Lock` for safe concurrent access.
- **Fee Floor:** The USD 0.50 minimum fee prevents micro-transaction abuse.
- **Server-Side Expiry:** Quote TTL is enforced server-side; clients cannot extend it.

## AI Assistance

This project was built with the assistance of an AI coding agent (Antigravity by Google DeepMind) for architectural planning, code generation, and test creation.

## License

Proprietary — Transika Technologies.
