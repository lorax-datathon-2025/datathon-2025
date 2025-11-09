# Batch Processing & Real-Time Status Updates

## Overview

The system now supports both **interactive** and **batch processing** modes with real-time status tracking for all document classification jobs.

## Features

### ✅ Interactive Mode (Existing)
- Single document upload via `/upload` endpoint
- Immediate classification via `/classify/{doc_id}` endpoint
- Synchronous processing with instant results

### ✅ Batch Mode (NEW)
- **Bulk Upload**: `/batch/upload` endpoint for multiple documents
- **Background Processing**: Asynchronous job queue with concurrent processing
- **Job Tracking**: Unique `job_id` for each batch operation
- **Real-Time Status**: `/status/{job_id}` endpoint with detailed progress

## API Endpoints

### Batch Upload
```http
POST /batch/upload
Content-Type: multipart/form-data

files: [file1.pdf, file2.docx, file3.pdf, ...]
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_files": 10,
  "status": "pending",
  "message": "Batch upload initiated. Successfully queued 10 documents."
}
```

### Job Status (Real-Time Progress)
```http
GET /status/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "total_files": 10,
  "completed": 7,
  "failed": 1,
  "progress": 75.5,
  "created_at": "2025-11-09T10:30:00",
  "updated_at": "2025-11-09T10:35:23",
  "documents": [
    {
      "doc_id": "abc-123",
      "filename": "document1.pdf",
      "status": "completed",
      "progress": 100.0,
      "error": null
    },
    {
      "doc_id": "def-456",
      "filename": "document2.pdf",
      "status": "processing",
      "progress": 60.0,
      "error": null
    },
    {
      "doc_id": "ghi-789",
      "filename": "document3.pdf",
      "status": "failed",
      "progress": 0.0,
      "error": "ValueError: Unable to extract content"
    }
  ],
  "error": null
}
```

### List All Jobs
```http
GET /jobs
```

**Response:**
```json
{
  "total": 5,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "total_files": 10,
      "completed": 9,
      "failed": 1,
      "created_at": "2025-11-09T10:30:00",
      "updated_at": "2025-11-09T10:40:00"
    }
  ]
}
```

## Job Status Values

- **`pending`**: Job created, waiting to start
- **`processing`**: Documents being processed
- **`completed`**: All documents processed (may include some failures)
- **`failed`**: Job failed catastrophically
- **`cancelled`**: Job cancelled by user (future feature)

## Document Status Values

- **`pending`**: Queued for processing
- **`processing`**: Currently being classified (with progress 0-100%)
- **`completed`**: Successfully classified
- **`failed`**: Classification failed (with error message)

## Progress Tracking

### Document-Level Progress
Each document reports progress through stages:
- **10%**: Started processing
- **30%**: Document data loaded
- **60%**: Detectors completed
- **90%**: Classification completed
- **100%**: Results saved

### Job-Level Progress
Overall job progress is calculated as the average of all document progress values.

## Architecture

### Background Processing
- Uses FastAPI `BackgroundTasks` for async job execution
- `ThreadPoolExecutor` for CPU-bound operations (detectors, LLM calls)
- Concurrent processing of multiple documents within a job
- Non-blocking: API returns immediately with `job_id`

### Job Processor (`job_processor.py`)
- `process_batch_job()`: Orchestrates entire batch job
- `process_document_async()`: Handles individual document processing
- Real-time progress updates via `update_document_in_job()`
- Error handling with detailed error messages

### Storage Layer (`storage.py`)
- `JOBS`: In-memory job tracking dictionary
- `create_job()`: Initialize new batch job
- `get_job()`: Retrieve job status and details
- `update_job_status()`: Update overall job state
- `update_document_in_job()`: Track individual document progress

## Usage Examples

### Python Client
```python
import requests
import time

# 1. Batch upload
files = [
    ('files', open('doc1.pdf', 'rb')),
    ('files', open('doc2.pdf', 'rb')),
    ('files', open('doc3.pdf', 'rb')),
]
response = requests.post('http://localhost:8000/batch/upload', files=files)
job_id = response.json()['job_id']

# 2. Poll for status
while True:
    status = requests.get(f'http://localhost:8000/status/{job_id}').json()
    print(f"Progress: {status['progress']:.1f}% ({status['completed']}/{status['total_files']})")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(2)

# 3. Get individual results
for doc in status['documents']:
    if doc['status'] == 'completed':
        result = requests.get(f'http://localhost:8000/documents/{doc["doc_id"]}').json()
        print(f"{doc['filename']}: {result['classification']['final_category']}")
```

### cURL
```bash
# Batch upload
curl -X POST "http://localhost:8000/batch/upload" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf" \
  -F "files=@document3.pdf"

# Check status
curl "http://localhost:8000/status/{job_id}"

# List all jobs
curl "http://localhost:8000/jobs"
```

## Performance Considerations

### Concurrency
- Default: 4 concurrent workers (`ThreadPoolExecutor(max_workers=4)`)
- Adjustable in `job_processor.py`
- Balance between speed and resource usage

### Scalability
- Current: In-memory storage (`JOBS` dictionary)
- Production: Consider Redis, PostgreSQL, or MongoDB for persistence
- Large batches: Consider chunking into smaller sub-jobs

### Timeouts
- No timeout implemented yet
- Consider adding per-document timeout for LLM calls
- Job-level timeout to prevent hung jobs

## Future Enhancements

1. **WebSocket Support**: Real-time push updates instead of polling
2. **Job Cancellation**: `/cancel/{job_id}` endpoint
3. **Job Priorities**: Priority queue for important batches
4. **Persistence**: Database storage for jobs (survive restarts)
5. **Retry Logic**: Automatic retry for failed documents
6. **Rate Limiting**: Prevent overwhelming the LLM API
7. **Batch Results Export**: Download all results as CSV/JSON
8. **Scheduled Jobs**: Cron-like scheduling for recurring batches

## Testing

```bash
# Start the server
uvicorn app.main:app --reload

# Run batch upload test
python -c "
import requests
files = [('files', open('test/sample1.pdf', 'rb')),
         ('files', open('test/sample2.pdf', 'rb'))]
r = requests.post('http://localhost:8000/batch/upload', files=files)
print(r.json())
"
```

## Troubleshooting

### Job Stuck in "Processing"
- Check logs for errors in `job_processor.py`
- Verify LLM API credentials and rate limits
- Check for hung threads in `ThreadPoolExecutor`

### Memory Issues with Large Batches
- Reduce `max_workers` in `job_processor.py`
- Process in smaller batches
- Consider file streaming for large documents

### Progress Not Updating
- Ensure `update_document_in_job()` is called at each stage
- Check for exceptions that skip progress updates
- Verify job_id is correct

---

**Implementation Status**: ✅ Complete

- ✅ Batch upload endpoint (`/batch/upload`)
- ✅ Real-time status endpoint (`/status/{job_id}`)
- ✅ Background async processing
- ✅ Progress tracking (0-100% per document)
- ✅ Job management (create, update, query)
- ✅ Error handling with detailed messages
- ✅ List all jobs endpoint (`/jobs`)
