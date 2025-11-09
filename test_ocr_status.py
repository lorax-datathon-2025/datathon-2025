#!/usr/bin/env python3
"""Test to check if OCR is needed for the uploaded documents"""

import sys
sys.path.insert(0, '/mnt/c/Users/ryanm/OneDrive/Desktop/datathon-2025')

from app.storage import get_document_pages, get_meta, DOCS_TEXT
import json

# List all documents
print("=== Checking all uploaded documents ===\n")

for doc_id, pages in DOCS_TEXT.items():
    meta = get_meta(doc_id)
    filename = meta.get('filename', 'Unknown')
    page_count = len(pages)
    
    print(f"Document: {filename}")
    print(f"Doc ID: {doc_id}")
    print(f"Page count: {page_count}")
    
    # Check text length per page
    empty_pages = 0
    total_chars = 0
    for page_num, text in pages.items():
        text_len = len(text.strip())
        total_chars += text_len
        if text_len < 50:  # Very little text
            empty_pages += 1
            print(f"  Page {page_num}: {text_len} chars (possibly needs OCR)")
    
    avg_chars = total_chars / page_count if page_count > 0 else 0
    print(f"  Total characters: {total_chars}")
    print(f"  Average chars/page: {avg_chars:.1f}")
    print(f"  Pages with <50 chars: {empty_pages}/{page_count}")
    
    if empty_pages > page_count * 0.3:  # More than 30% pages are empty
        print(f"  ⚠️  WARNING: This document likely needs OCR!")
    elif avg_chars < 100:
        print(f"  ⚠️  WARNING: Very little text extracted, consider OCR")
    else:
        print(f"  ✓ Text extraction looks good")
    
    print()

print("\n=== Recommendation ===")
print("If documents show warnings above, consider adding OCR using:")
print("  - pytesseract + Tesseract OCR")
print("  - Google Cloud Vision API")
print("  - Azure Computer Vision")
