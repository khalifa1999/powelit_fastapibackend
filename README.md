# PowerLit Backend

FastAPI backend for automated electrical blueprint analysis and load calculation.

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment file and configure:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application:
```bash
python main.py
# Or with uvicorn:
uvicorn main:app --reload
```

## API Documentation

Once running, access the API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Features

- Blueprint analysis using Gemini Vision
- Load calculation per Ghana GS1009 standards
- Compliance checking via RAG
- Power source recommendations

## Project Structure

```
powerlit_fastapi/
├── app/
│   ├── config.py          # Configuration settings
│   ├── models/            # Pydantic models
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── data/                  # Data storage
├── tests/                 # Test files
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── README.md
```
