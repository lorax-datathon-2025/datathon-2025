# Quick API Reference - Batch Processing

## Batch Upload
**Upload multiple documents for background processing**

```bash
POST /batch/upload
Content-Type: multipart/form-data
```

**Request:**
```bash
curl -X POST "http://localhost:8000/batch/upload" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf" \
  -F "files=@document3.pdf"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_files": 3,
  "status": "pending",
  "message": "Batch upload initiated. Successfully queued 3 documents."
}
```

---

## Get Job Status
**Check real-time progress of a batch job**

```bash
GET /status/{job_id}
```

**Request:**
```bash
curl "http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "total_files": 3,
  "completed": 2,
  "failed": 0,
  "progress": 66.7,
  "created_at": "2025-11-09T10:30:00",
  "updated_at": "2025-11-09T10:31:45",
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
      "status": "completed",
      "progress": 100.0,
      "error": null
    },
    {
      "doc_id": "ghi-789",
      "filename": "document3.pdf",
      "status": "processing",
      "progress": 60.0,
      "error": null
    }
  ],
  "error": null
}
```

---

## List All Jobs
**View all batch processing jobs**

```bash
GET /jobs
```

**Request:**
```bash
curl "http://localhost:8000/jobs"
```

**Response:**
```json
{
  "total": 5,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "total_files": 3,
      "completed": 3,
      "failed": 0,
      "created_at": "2025-11-09T10:30:00",
      "updated_at": "2025-11-09T10:32:00"
    },
    {
      "job_id": "660e8400-e29b-41d4-a716-446655440001",
      "status": "processing",
      "total_files": 10,
      "completed": 5,
      "failed": 1,
      "created_at": "2025-11-09T09:15:00",
      "updated_at": "2025-11-09T09:20:00"
    }
  ]
}
```

---

## Status Values

### Job Status
- `pending` - Job created, waiting to start
- `processing` - Documents being processed
- `completed` - All documents processed
- `failed` - Job failed

### Document Status
- `pending` - Queued for processing
- `processing` - Currently being classified
- `completed` - Successfully classified
- `failed` - Classification failed

---

## Progress Tracking

### Document Progress Stages
| Progress | Stage                    |
|----------|--------------------------|
| 0%       | Pending                  |
| 10%      | Started processing       |
| 30%      | Document data loaded     |
| 60%      | Detectors completed      |
| 90%      | Classification completed |
| 100%     | Results saved            |

### Job Progress
Overall job progress = Average of all document progress values

---

## Python Example

```python
import requests
import time

# 1. Upload batch
files = [
    ('files', open('doc1.pdf', 'rb')),
    ('files', open('doc2.pdf', 'rb')),
    ('files', open('doc3.pdf', 'rb')),
]
response = requests.post('http://localhost:8000/batch/upload', files=files)
job_id = response.json()['job_id']

# 2. Poll for completion
while True:
    status = requests.get(f'http://localhost:8000/status/{job_id}').json()
    print(f"Progress: {status['progress']:.1f}%")
    
    if status['status'] == 'completed':
        break
    
    time.sleep(2)

# 3. Get results
for doc in status['documents']:
    if doc['status'] == 'completed':
        result = requests.get(f'http://localhost:8000/documents/{doc["doc_id"]}').json()
        print(f"{doc['filename']}: {result['classification']['final_category']}")
```

---

## JavaScript Example

```javascript
// 1. Upload batch
const formData = new FormData();
formData.append('files', file1);
formData.append('files', file2);
formData.append('files', file3);

const uploadResponse = await fetch('http://localhost:8000/batch/upload', {
  method: 'POST',
  body: formData
});
const { job_id } = await uploadResponse.json();

// 2. Poll for completion
async function pollStatus(jobId) {
  const response = await fetch(`http://localhost:8000/status/${jobId}`);
  const status = await response.json();
  
  console.log(`Progress: ${status.progress.toFixed(1)}%`);
  
  if (status.status === 'completed') {
    return status;
  }
  
  await new Promise(resolve => setTimeout(resolve, 2000));
  return pollStatus(jobId);
}

const finalStatus = await pollStatus(job_id);

// 3. Get results
for (const doc of finalStatus.documents) {
  if (doc.status === 'completed') {
    const result = await fetch(`http://localhost:8000/documents/${doc.doc_id}`);
    const data = await result.json();
    console.log(`${doc.filename}: ${data.classification.final_category}`);
  }
}
```

---

## Testing

```bash
# Start server
uvicorn app.main:app --reload

# Run test script
python -m test.test_batch_api

# Manual test with curl
curl -X POST "http://localhost:8000/batch/upload" \
  -F "files=@test/sample1.pdf" \
  -F "files=@test/sample2.pdf"

# Save job_id from response, then:
curl "http://localhost:8000/status/{job_id}"
```

---

## Error Handling

### Failed Upload
```json
{
  "detail": "All uploads failed. Files: document1.pdf, document2.pdf"
}
```

### Job Not Found
```json
{
  "detail": "Job not found"
}
```

### Document Failed
```json
{
  "doc_id": "abc-123",
  "filename": "document.pdf",
  "status": "failed",
  "progress": 0.0,
  "error": "ValueError: Unable to extract content"
}
```

---

## Tips

1. **Polling Interval**: Use 2-5 second intervals to avoid overwhelming the server
2. **Large Batches**: Split into smaller batches for better monitoring
3. **Timeout**: Current implementation has no timeout - monitor long-running jobs
4. **Concurrency**: Default 4 workers, adjustable in `job_processor.py`
5. **Memory**: Each job stores full document data - consider cleanup for large batches
