"""
Test script for batch processing and status tracking.

Usage:
    python -m test.test_batch_api
"""
import requests
import time
import sys
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_batch_upload():
    """Test batch upload endpoint."""
    print("=" * 60)
    print("Testing Batch Upload API")
    print("=" * 60)
    
    # Find test files
    test_dir = Path(__file__).parent.parent / "data"
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        print("   Please add some PDF/DOCX files to the 'data' directory")
        return None
    
    # Get test files
    test_files = list(test_dir.glob("*.pdf")) + list(test_dir.glob("*.docx"))
    if not test_files:
        print("❌ No test files found in 'data' directory")
        print("   Please add some PDF/DOCX files")
        return None
    
    print(f"\n📁 Found {len(test_files)} test files:")
    for f in test_files[:5]:  # Limit to 5 files for testing
        print(f"   - {f.name}")
    
    # Prepare files for upload
    files = [('files', open(f, 'rb')) for f in test_files[:5]]
    
    try:
        print("\n📤 Uploading batch...")
        response = requests.post(f"{API_BASE}/batch/upload", files=files)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Batch upload successful!")
        print(f"   Job ID: {result['job_id']}")
        print(f"   Total files: {result['total_files']}")
        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message']}")
        
        return result['job_id']
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the server running?")
        print("   Start with: uvicorn app.main:app --reload")
        return None
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None
    finally:
        # Close files
        for _, f in files:
            f.close()


def test_status_tracking(job_id: str):
    """Test status tracking with real-time updates."""
    print("\n" + "=" * 60)
    print("Testing Real-Time Status Tracking")
    print("=" * 60)
    
    print(f"\n🔍 Tracking job: {job_id}")
    print("   (polling every 2 seconds)\n")
    
    last_progress = -1
    
    while True:
        try:
            response = requests.get(f"{API_BASE}/status/{job_id}")
            response.raise_for_status()
            status = response.json()
            
            # Show progress bar
            progress = status['progress']
            completed = status['completed']
            failed = status['failed']
            total = status['total_files']
            
            # Only print if progress changed
            if progress != last_progress:
                bar_length = 40
                filled = int(bar_length * progress / 100)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                print(f"\r[{bar}] {progress:.1f}% | "
                      f"✅ {completed} | ❌ {failed} | ⏳ {total - completed - failed}", 
                      end="", flush=True)
                last_progress = progress
            
            # Check if done
            if status['status'] in ['completed', 'failed']:
                print("\n")
                print(f"{'=' * 60}")
                print(f"Job Status: {status['status'].upper()}")
                print(f"{'=' * 60}")
                print(f"Total: {total} | Completed: {completed} | Failed: {failed}")
                print(f"Duration: {status['updated_at']}")
                
                # Show document details
                print("\n📄 Document Details:")
                for doc in status['documents']:
                    status_icon = "✅" if doc['status'] == 'completed' else "❌"
                    print(f"   {status_icon} {doc['filename']}: {doc['status']}")
                    if doc['error']:
                        print(f"      Error: {doc['error']}")
                
                break
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Status check failed: {e}")
            break


def test_list_jobs():
    """Test listing all jobs."""
    print("\n" + "=" * 60)
    print("Testing Job List API")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE}/jobs")
        response.raise_for_status()
        data = response.json()
        
        print(f"\n📋 Total jobs: {data['total']}\n")
        
        for job in data['jobs'][:10]:  # Show last 10 jobs
            status_icon = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(job['status'], '❓')
            
            print(f"{status_icon} Job {job['job_id'][:8]}...")
            print(f"   Status: {job['status']}")
            print(f"   Files: {job['completed']}/{job['total_files']} completed, "
                  f"{job['failed']} failed")
            print(f"   Created: {job['created_at']}")
            print()
            
    except Exception as e:
        print(f"❌ Failed to list jobs: {e}")


def main():
    """Run all tests."""
    print("\n🚀 RegDoc Batch Processing API Test")
    print(f"   Server: {API_BASE}\n")
    
    # Test 1: Batch upload
    job_id = test_batch_upload()
    if not job_id:
        print("\n⚠️  Cannot continue without a job ID")
        sys.exit(1)
    
    # Test 2: Real-time status tracking
    test_status_tracking(job_id)
    
    # Test 3: List all jobs
    test_list_jobs()
    
    print("\n✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
