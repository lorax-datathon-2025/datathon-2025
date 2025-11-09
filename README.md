# datathon-2025

## RegDoc Guardrail API

AI-powered document classification system with interactive and batch processing capabilities.

## Features

### ✅ Document Classification
- Multi-category classification (Public, Confidential, Highly Sensitive, Unsafe)
- PII detection and content safety analysis
- Dual-LLM reasoning for enhanced accuracy
- Citation-based explanations

### ✅ Processing Modes

#### Interactive Mode
- Single document upload via `/upload`
- Real-time classification via `/classify/{doc_id}`
- Immediate results

#### Batch Mode ⚡ NEW
- Bulk document upload via `/batch/upload`
- Background async processing
- Real-time status tracking via `/status/{job_id}`
- Progress monitoring (0-100% per document)
- Job management and history

See [BATCH_PROCESSING.md](BATCH_PROCESSING.md) for detailed documentation.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Create .env file with your API keys
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=models/gemini-2.0-flash-exp
```

### 3. Run Server
```bash
uvicorn app.main:app --reload
```

### 4. Test Batch Processing
```bash
# Interactive mode
curl -X POST "http://localhost:8000/upload" -F "file=@document.pdf"

# Batch mode
curl -X POST "http://localhost:8000/batch/upload" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.pdf"

# Check status
curl "http://localhost:8000/status/{job_id}"

# Or run the test script
python -m test.test_batch_api
```

## API Endpoints

### Interactive Endpoints
- `POST /upload` - Upload single document
- `POST /classify/{doc_id}` - Classify document
- `GET /documents/{doc_id}` - Get document info
- `POST /hitl` - Human-in-the-loop override

### Batch Endpoints ⚡ NEW
- `POST /batch/upload` - Upload multiple documents
- `GET /status/{job_id}` - Get job status with real-time progress
- `GET /jobs` - List all batch jobs

### System
- `GET /health` - Health check

## Architecture

```
app/
├── main.py              # FastAPI application with batch endpoints
├── orchestrator.py      # Classification logic
├── job_processor.py     # Background batch processing ⚡ NEW
├── storage.py           # Data storage with job tracking ⚡ NEW
├── models.py            # Pydantic models with batch types ⚡ NEW
├── detectors.py         # PII and pattern detection
├── llm_client.py        # LLM integration
├── utils_text.py        # Text extraction
└── hitl.py              # Human-in-the-loop
```

## Documentation

- [Batch Processing Guide](BATCH_PROCESSING.md) - Comprehensive batch mode documentation
- API Docs: http://localhost:8000/docs (when server is running)

## Development

```bash
# Run tests
python -m test.test_batch_api

# Check logs
# Server logs will show batch processing progress

# View API docs
# Navigate to http://localhost:8000/docs
```

## Implementation Status

✅ **Completed Features:**
- Interactive document upload and classification
- Batch upload endpoint (`/batch/upload`)
- Real-time status tracking (`/status/{job_id}`)
- Background async processing with ThreadPoolExecutor
- Progress tracking (0-100% per document)
- Job history and listing (`/jobs`)
- Error handling with detailed messages
- Concurrent document processing

🔄 **Future Enhancements:**
- WebSocket support for push-based updates
- Job cancellation
- Persistent storage (Redis/PostgreSQL)
- Retry logic for failed documents
- Batch results export (CSV/JSON)

## License

MIT