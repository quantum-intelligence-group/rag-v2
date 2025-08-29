"""
Text normalization utilities for documents and user queries.

This module provides functions to normalize text during document ingestion
and query processing to improve search quality.
"""
import re
from typing import List, Dict, Any

from app.logging import get_logger

logger = get_logger(__name__)


def normalize_query(query: str) -> str:
    """
    Normalize user query for better search results.
    
    Args:
        query: Raw user query string
        
    Returns:
        Normalized query string
    """
    if not query or not query.strip():
        return ""
    
    # Convert to lowercase for case-insensitive search
    normalized = query.lower().strip()
    
    # Remove extra whitespace (multiple spaces, tabs, newlines)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Remove common punctuation that doesn't add search value
    # Keep hyphens, apostrophes, and quotes as they can be meaningful
    normalized = re.sub(r'[^\w\s\-\'\"]', ' ', normalized)
    
    # Clean up any extra spaces created by punctuation removal
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Remove very short words (1 character) that are likely not meaningful
    # but keep single letters that might be meaningful (like "C" for programming)
    words = normalized.split()
    meaningful_words = []
    for word in words:
        if len(word) > 1 or word.isalpha():
            meaningful_words.append(word)
    
    normalized = ' '.join(meaningful_words)
    
    logger.info("query_normalized", extra={
        "original_query": query,
        "normalized_query": normalized,
        "original_length": len(query),
        "normalized_length": len(normalized)
    })
    
    return normalized


def normalize_document_text(text: str) -> str:
    """
    Normalize document text during ingestion.
    
    This function handles:
    - Whitespace collapse
    - De-hyphenation of line wraps
    - Basic cleanup for better indexing
    
    Args:
        text: Raw document text
        
    Returns:
        Normalized document text
    """
    if not text or not text.strip():
        return ""
    
    normalized = text.strip()
    
    # Collapse multiple whitespace characters into single spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # De-hyphenate line wraps (word- followed by whitespace and word)
    # This handles cases like "hyphen-\nated" -> "hyphenated"
    normalized = re.sub(r'(\w)-\s+(\w)', r'\1\2', normalized)
    
    # Clean up common OCR artifacts and formatting issues
    # Remove extra spaces before punctuation
    normalized = re.sub(r'\s+([,.;:!?])', r'\1', normalized)
    
    # Ensure single space after punctuation
    normalized = re.sub(r'([,.;:!?])([^\s])', r'\1 \2', normalized)
    
    # Remove excessive repeated characters (likely OCR errors)
    # e.g., "helllllo" -> "hello" but keep intentional repetition like "ooooh"
    normalized = re.sub(r'(.)\1{3,}', r'\1\1', normalized)
    
    return normalized.strip()


def strip_repeating_headers_footers(text: str, threshold: int = 3) -> str:
    """
    Remove repeating headers and footers that appear multiple times.
    
    This is useful for removing page headers/footers that get extracted
    as part of the document text.
    
    Args:
        text: Document text
        threshold: Minimum number of occurrences to consider as repeating
        
    Returns:
        Text with repeating patterns removed
    """
    if not text or len(text) < 50:  # Skip very short texts
        return text
    
    lines = text.split('\n')
    if len(lines) < 10:  # Need sufficient lines to detect patterns
        return text
    
    # Count line occurrences
    line_counts: Dict[str, int] = {}
    for line in lines:
        cleaned_line = line.strip()
        if len(cleaned_line) > 5:  # Only consider substantial lines
            line_counts[cleaned_line] = line_counts.get(cleaned_line, 0) + 1
    
    # Identify repeating lines
    repeating_lines = {
        line for line, count in line_counts.items() 
        if count >= threshold and len(line) > 10  # Must be substantial content
    }
    
    if not repeating_lines:
        return text
    
    # Remove repeating lines
    filtered_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line not in repeating_lines:
            filtered_lines.append(line)
    
    result = '\n'.join(filtered_lines)
    
    logger.info("repeating_patterns_removed", extra={
        "original_lines": len(lines),
        "filtered_lines": len(filtered_lines),
        "patterns_removed": len(repeating_lines)
    })
    
    return result


def convert_lists_to_markdown(text: str) -> str:
    """
    Convert common list formats to markdown.
    
    Handles:
    - Numbered lists (1. item, 1) item)
    - Bullet points (• item, - item, * item)
    - Simple indented lists
    
    Args:
        text: Document text
        
    Returns:
        Text with lists converted to markdown format
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    converted_lines = []
    
    for line in lines:
        original_line = line
        stripped = line.strip()
        
        if not stripped:
            converted_lines.append(line)
            continue
        
        # Convert numbered lists: "1. item" or "1) item"
        if re.match(r'^\d+[.)]?\s+', stripped):
            # Extract the number and content
            match = re.match(r'^(\d+)[.)]?\s+(.*)', stripped)
            if match:
                number, content = match.groups()
                converted_lines.append(f"{number}. {content}")
                continue
        
        # Convert bullet points: "• item", "- item", "* item"
        if re.match(r'^[•\-\*]\s+', stripped):
            # Extract content after bullet
            content = re.sub(r'^[•\-\*]\s+', '', stripped)
            converted_lines.append(f"- {content}")
            continue
        
        # Convert simple indented items (assuming they're list items)
        if re.match(r'^\s{2,}[^\s]', line) and not re.match(r'^\s*\d+[.)]', line):
            # This is an indented item that's not already a numbered list
            content = line.strip()
            if content and not content.startswith('-') and not content.startswith('*'):
                converted_lines.append(f"  - {content}")
                continue
        
        # No conversion needed
        converted_lines.append(original_line)
    
    return '\n'.join(converted_lines)