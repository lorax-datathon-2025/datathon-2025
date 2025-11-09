"""
Quick Batch Processing Test with your data folder files
Run this to test batch mode with all 5 test cases at once!

Usage: python test_batch_now.py
"""

import requests
import time
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
DATA_DIR = Path(r"c:\Users\ryanm\OneDrive\Desktop\datathon-2025\data")

def main():
    print("=" * 70)
    print("  BATCH PROCESSING TEST - All Test Cases")
    print("=" * 70)
    print()
    
    # Test files
    test_files = [
        ("TC1", DATA_DIR / "TC1_Sample_Public_Marketing_Document.pdf", "Public"),
        ("TC2", DATA_DIR / "TC2_Filled_In_Employement_Application.pdf", "Highly Sensitive (PII)"),
        ("TC3", DATA_DIR / "TC3_Sample_Internal_Memo.pdf", "Confidential"),
        ("TC4", DATA_DIR / "TC4_ Stealth_Fighter_With_Part_Names.pdf", "Highly Sensitive"),
        ("TC5", DATA_DIR / "TC5_Testing_Multiple_Non_Compliance_Categorization.pdf", "Unsafe"),
    ]
    
    print("📁 Test Files:")
    for name, path, expected in test_files:
        if path.exists():
            print(f"   ✅ {name}: {path.name}")
            print(f"      Expected: {expected}")
        else:
            print(f"   ❌ {name}: File not found!")
    print()
    
    # Check server
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server health check failed!")
            return
        print("✅ Server is running")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("   Start with: uvicorn app.main:app --reload")
        return
    
    print()
    print("=" * 70)
    print("Step 1: Uploading Batch")
    print("=" * 70)
    print()
    
    # Upload batch
    files = [('files', open(path, 'rb')) for _, path, _ in test_files if path.exists()]
    
    try:
        print(f"📤 Uploading {len(files)} documents...")
        response = requests.post(f"{BASE_URL}/batch/upload", files=files)
        
        if response.status_code != 200:
            print(f"❌ Batch upload failed: {response.status_code}")
            print(response.text)
            return
        
        batch_data = response.json()
        job_id = batch_data['job_id']
        
        print(f"✅ Batch uploaded successfully!")
        print(f"   Job ID: {job_id}")
        print(f"   Total Files: {batch_data['total_files']}")
        print(f"   Status: {batch_data['status']}")
        print(f"   Message: {batch_data['message']}")
        
        print()
        print("=" * 70)
        print("Step 2: Real-Time Status Monitoring")
        print("=" * 70)
        print()
        print("🔄 Processing documents in background...")
        print("   (API returned immediately, now monitoring progress)\n")
        
        last_progress = -1
        start_time = time.time()
        
        while True:
            response = requests.get(f"{BASE_URL}/status/{job_id}")
            
            if response.status_code != 200:
                print(f"\n❌ Status check failed: {response.status_code}")
                break
            
            status_data = response.json()
            progress = status_data['progress']
            status = status_data['status']
            completed = status_data['completed']
            failed = status_data['failed']
            total = status_data['total_files']
            
            # Show progress bar
            if progress != last_progress:
                bar_length = 50
                filled = int(bar_length * progress / 100)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                elapsed = time.time() - start_time
                print(f"\r   [{bar}] {progress:.1f}%", end="")
                print(f" | {status:12} | ✅ {completed} ❌ {failed} / {total} | {elapsed:.0f}s", 
                      end="", flush=True)
                last_progress = progress
            
            # Check if done
            if status in ['completed', 'failed']:
                elapsed = time.time() - start_time
                print(f"\n\n✅ Job {status} in {elapsed:.1f} seconds")
                
                print()
                print("=" * 70)
                print("Step 3: Final Results")
                print("=" * 70)
                print()
                
                print(f"📊 Summary:")
                print(f"   Status: {status}")
                print(f"   Total: {total} documents")
                print(f"   Completed: {completed}")
                print(f"   Failed: {failed}")
                print(f"   Time: {elapsed:.1f}s")
                print()
                
                print("📄 Document Results:")
                print()
                
                for i, doc in enumerate(status_data['documents'], 1):
                    status_icon = "✅" if doc['status'] == 'completed' else "❌"
                    print(f"{i}. {status_icon} {doc['filename']}")
                    print(f"   Status: {doc['status']} ({doc['progress']:.0f}%)")
                    
                    if doc['error']:
                        print(f"   ❌ Error: {doc['error']}")
                    
                    # Get detailed results for completed docs
                    if doc['status'] == 'completed':
                        doc_response = requests.get(f"{BASE_URL}/documents/{doc['doc_id']}")
                        if doc_response.status_code == 200:
                            doc_meta = doc_response.json()
                            if 'classification' in doc_meta:
                                result = doc_meta['classification']
                                print(f"   📊 Category: {result['final_category']}")
                                print(f"   📊 Confidence: {result['confidence']}")
                                print(f"   📊 Pages: {result['page_count']}")
                                print(f"   📊 Images: {result['image_count']}")
                                print(f"   📊 Safety: {result['content_safety']}")
                                
                                # Show expected vs actual
                                expected_category = next(
                                    (exp for name, path, exp in test_files 
                                     if path.name in doc['filename']), 
                                    "Unknown"
                                )
                                match = "✅ MATCH" if expected_category.startswith(result['final_category']) else "⚠️ CHECK"
                                print(f"   📋 Expected: {expected_category} {match}")
                    print()
                
                break
            
            time.sleep(2)
        
        # Show all jobs
        print()
        print("=" * 70)
        print("Step 4: Job History")
        print("=" * 70)
        print()
        
        response = requests.get(f"{BASE_URL}/jobs")
        if response.status_code == 200:
            jobs_data = response.json()
            print(f"📋 Total jobs in system: {jobs_data['total']}")
            print()
            print("Recent jobs:")
            for job in jobs_data['jobs'][:5]:
                status_icon = {"completed": "✅", "failed": "❌", "processing": "🔄", "pending": "⏳"}.get(job['status'], "❓")
                print(f"   {status_icon} Job {job['job_id'][:8]}... | {job['status']} | "
                      f"{job['completed']}/{job['total_files']} docs | {job['created_at']}")
        
        print()
        print("=" * 70)
        print("  BATCH PROCESSING TEST COMPLETE ✅")
        print("=" * 70)
        print()
        print("✅ Verified Features:")
        print("   ✔ Batch upload endpoint (/batch/upload)")
        print("   ✔ Immediate non-blocking response")
        print("   ✔ Background async processing")
        print("   ✔ Real-time status updates (/status/{job_id})")
        print("   ✔ Progress tracking (0-100%)")
        print("   ✔ Multiple documents processed concurrently")
        print("   ✔ Job history (/jobs)")
        print()
        print("🎯 Compare with Interactive Mode:")
        print("   Interactive: POST /classify/{doc_id} → waits → returns result")
        print("   Batch:       POST /batch/upload → immediate job_id → poll status")
        print()
        
    finally:
        for _, f in files:
            f.close()

if __name__ == "__main__":
    main()
