"""
Statute-Aware Section Chunker for Indian Legal Acts
=====================================================

Replaces naive chunk-based ingestion with structure-aware parsing that:
1. Detects real section boundaries in statute text
2. Creates one chunk per legal section with proper metadata
3. Preserves section numbers, titles, act names, chapter context
4. Handles multiple data formats found in our statute JSONs
5. Splits oversized sections while preserving context headers

Supported formats (auto-detected):
- chunk-based: BNS 2023 style (--- Section X --- markers)
- number-based: Indian Contract Act style (pre-chunked with real section nums)
- marker-based: Consumer Protection Act style (full text + subsection entries)
- monolithic: Companies Act 2013 style (single massive entry)

Author: LAW-GPT Team
"""

import hashlib
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Maximum chunk size in characters. Sections exceeding this will be sub-chunked.
MAX_CHUNK_CHARS = 3000
# Minimum chunk size - sections smaller than this may be merged with adjacent
MIN_CHUNK_CHARS = 100
# Overlap characters when sub-chunking long sections
OVERLAP_CHARS = 200


class StatuteSectionChunker:
    """
    Structure-aware chunker for Indian legal statutes.
    
    Parses raw statute text and creates properly bounded chunks with rich metadata:
    - act_name: Name of the statute/act
    - chapter: Current chapter heading
    - section_number: Real section number (e.g., "302", "2(47)")
    - section_title: Section title/heading
    - part: Part or Schedule heading if applicable
    """
    
    # Regex patterns for detecting section boundaries in raw text
    # Pattern for "--- Section X ---" markers (BNS style)
    MARKER_PATTERN = re.compile(
        r'^---\s*(?:Section\s+)?(\d+[A-Z]?)\s*---',
        re.MULTILINE
    )
    
    # Pattern for inline section numbering: "123. Title text"
    # Handles sections like "1.", "2.", "302.", "44A.", "10B."
    SECTION_NUM_PATTERN = re.compile(
        r'^\s*(\d+[A-Z]?)\.\s*\n',
        re.MULTILINE
    )
    
    # Section with title on same line: "302. Punishment for murder"
    SECTION_WITH_TITLE_PATTERN = re.compile(
        r'^\s*(\d+[A-Z]?)\.\s+([A-Z][^.\n]{5,80}(?:\.|-|—))',
        re.MULTILINE
    )
    
    # Chapter heading pattern
    CHAPTER_PATTERN = re.compile(
        r'^(?:Chapter|CHAPTER)\s+([IVXLCDM]+(?:\s*[A-Z])?)\b[^\n]*',
        re.MULTILINE
    )
    
    # Part heading pattern
    PART_PATTERN = re.compile(
        r'^(?:Part|PART)\s+([IVXLCDMA-Z]+)\b[^\n]*',
        re.MULTILINE
    )
    
    # Schedule heading pattern
    SCHEDULE_PATTERN = re.compile(
        r'^(?:Schedule|SCHEDULE|FIRST SCHEDULE|SECOND SCHEDULE|THIRD SCHEDULE)',
        re.MULTILINE
    )
    
    # Subsection entries from Kanoon-style data: "[Section 1] [Entire Act]"
    KANOON_HEADER_PATTERN = re.compile(
        r'^\[\s*\n*(?:Section\s+\d+|Entire\s+Act)\s*\n*\]',
        re.MULTILINE
    )

    def __init__(self, max_chunk_chars: int = MAX_CHUNK_CHARS, 
                 min_chunk_chars: int = MIN_CHUNK_CHARS):
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars

    def process_statute_file(self, file_path: Path) -> List[Dict]:
        """
        Process a single statute JSON file and return properly chunked records.
        
        Args:
            file_path: Path to the statute JSON file
            
        Returns:
            List of dicts with 'id', 'text', 'metadata' keys
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []
        
        act_name = data.get('act_name', file_path.stem.replace("_", " "))
        sections = data.get('sections', [])
        fmt = data.get('format_detected', '')
        
        if not sections:
            logger.warning(f"No sections found in {file_path.name}")
            return []
        
        # Auto-detect format and route to appropriate handler
        fmt_type = self._detect_format(sections, fmt)
        logger.info(f"Processing {file_path.name}: {len(sections)} raw entries, format={fmt_type}")
        
        if fmt_type == 'number-based':
            records = self._process_number_based(sections, act_name, file_path)
        elif fmt_type == 'number-with-title':
            records = self._process_number_with_title(sections, act_name, file_path)
        elif fmt_type == 'chunk-based':
            records = self._process_chunk_based(sections, act_name, file_path)
        elif fmt_type == 'marker-based':
            records = self._process_marker_based(sections, act_name, file_path)
        elif fmt_type == 'monolithic':
            records = self._process_monolithic(sections, act_name, file_path)
        else:
            # Fallback: treat as generic
            records = self._process_generic(sections, act_name, file_path)
        
        logger.info(f"  -> Produced {len(records)} chunks for {act_name}")
        return records

    def _detect_format(self, sections: List[Dict], format_hint: str) -> str:
        """Auto-detect the format of statute data."""
        
        # Check for monolithic (single massive entry)
        if len(sections) == 1 and len(sections[0].get('content', '')) > 50000:
            return 'monolithic'
        
        # Check if sections have real section numbers (not "Chunk N")
        sample = sections[:10]
        chunk_titled = sum(1 for s in sample 
                         if re.match(r'^Chunk\s+\d+$', str(s.get('section_title', ''))))
        if chunk_titled > len(sample) * 0.5:
            return 'chunk-based'
        
        # Check for massive first entry (marker-based with full text + subsections)
        if (len(sections) > 10 and 
            len(sections[0].get('content', '')) > 50000 and
            len(sections[1].get('content', '')) < 5000):
            return 'marker-based'
        
        # Check if section_numbers look like real numbers (plain "123" or "123.")
        real_nums = sum(1 for s in sample 
                       if re.match(r'^\d+[A-Z]?\.?$', str(s.get('section_number', '')).strip()))
        if real_nums > len(sample) * 0.5:
            return 'number-based'
        
        # Check for "number-with-title" format where section_number contains "N. Title"
        # e.g., "1. Short title, extent and commencement."
        num_with_title = sum(1 for s in sample
                            if re.match(r'^\d+[A-Z]?\.\s+\S', str(s.get('section_number', '')).strip()))
        if num_with_title > len(sample) * 0.5:
            return 'number-with-title'
        
        # Use format hint if provided (but NOT marker-based for small section counts)
        if format_hint in ('chunk-based', 'number-based'):
            return format_hint
        
        return 'generic'

    def _process_number_based(self, sections: List[Dict], act_name: str, 
                               file_path: Path) -> List[Dict]:
        """
        Process well-structured statutes (Indian Contract Act style).
        Each section already has correct section_number and section_title.
        Just need to add context headers and handle oversized sections.
        """
        records = []
        current_chapter = ""
        
        for i, section in enumerate(sections):
            sec_num = str(section.get('section_number', str(i + 1))).strip()
            sec_title = str(section.get('section_title', '')).strip()
            content = section.get('content', '').strip()
            
            if not content:
                continue
            
            # Detect chapter changes from content
            chapter_match = self.CHAPTER_PATTERN.search(content)
            if chapter_match:
                current_chapter = chapter_match.group(0).strip()
            
            # Build structured text
            chunks = self._build_section_chunks(
                act_name=act_name,
                section_number=sec_num,
                section_title=sec_title,
                content=content,
                chapter=current_chapter
            )
            
            for j, chunk_text in enumerate(chunks):
                chunk_id = f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_{sec_num}_{j}" if len(chunks) > 1 else f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_{sec_num}"
                records.append({
                    'id': self._sanitize_id(chunk_id),
                    'text': chunk_text,
                    'metadata': {
                        'domain': 'statutes',
                        'act': act_name,
                        'section_number': sec_num,
                        'section_title': sec_title,
                        'chapter': current_chapter,
                        'source_file': file_path.name,
                        'chunk_index': j if len(chunks) > 1 else 0,
                        'total_chunks': len(chunks)
                    }
                })
        
        return records

    def _process_number_with_title(self, sections: List[Dict], act_name: str,
                                    file_path: Path) -> List[Dict]:
        """
        Process statutes where section_number contains "N. Title text"
        (Competition Act, Partnership Act, Sale of Goods Act style).
        Parse the real section number and title from the compound field.
        """
        records = []
        
        for i, section in enumerate(sections):
            raw_num = str(section.get('section_number', '')).strip()
            content = section.get('content', '').strip()
            
            if not content:
                continue
            
            # Parse "N. Title text" from section_number
            num_title_match = re.match(r'^(\d+[A-Z]?)\.\s*(.*)', raw_num)
            if num_title_match:
                sec_num = num_title_match.group(1)
                sec_title = num_title_match.group(2).rstrip('.')
            else:
                sec_num = raw_num
                sec_title = str(section.get('section_title', '')).strip()
            
            chunks = self._build_section_chunks(
                act_name=act_name,
                section_number=sec_num,
                section_title=sec_title,
                content=content,
                chapter=''
            )
            
            for j, chunk_text in enumerate(chunks):
                chunk_id = f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_s{sec_num}_{j}" if len(chunks) > 1 else f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_s{sec_num}"
                records.append({
                    'id': self._sanitize_id(chunk_id),
                    'text': chunk_text,
                    'metadata': {
                        'domain': 'statutes',
                        'act': act_name,
                        'section_number': sec_num,
                        'section_title': sec_title,
                        'chapter': '',
                        'source_file': file_path.name,
                        'chunk_index': j if len(chunks) > 1 else 0,
                        'total_chunks': len(chunks)
                    }
                })
        
        return records

    def _process_chunk_based(self, sections: List[Dict], act_name: str,
                              file_path: Path) -> List[Dict]:
        """
        Process BNS-style data where each entry has "--- Section X ---" markers
        and section_title is just "Chunk N" (useless).
        Parse the real section info from the content.
        """
        records = []
        current_chapter = ""
        
        for i, section in enumerate(sections):
            content = section.get('content', '').strip()
            if not content:
                continue
            
            # Parse the structured content: --- Section X ---\nACT\nChapter Y\nS.\nN\nTitle\nDescription\nContent
            parsed = self._parse_chunk_marker_content(content)
            
            if parsed:
                sec_num = parsed['section_number']
                sec_title = parsed['section_title']
                body = parsed['body']
                if parsed.get('chapter'):
                    current_chapter = parsed['chapter']
            else:
                # Fallback: use what we have
                sec_num = str(section.get('section_number', str(i + 1))).strip()
                sec_title = str(section.get('section_title', '')).strip()
                body = content
            
            if not body.strip():
                continue
            
            chunks = self._build_section_chunks(
                act_name=act_name,
                section_number=sec_num,
                section_title=sec_title,
                content=body,
                chapter=current_chapter
            )
            
            for j, chunk_text in enumerate(chunks):
                chunk_id = f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_s{sec_num}_{j}" if len(chunks) > 1 else f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_s{sec_num}"
                records.append({
                    'id': self._sanitize_id(chunk_id),
                    'text': chunk_text,
                    'metadata': {
                        'domain': 'statutes',
                        'act': act_name,
                        'section_number': sec_num,
                        'section_title': sec_title,
                        'chapter': current_chapter,
                        'source_file': file_path.name,
                        'chunk_index': j if len(chunks) > 1 else 0,
                        'total_chunks': len(chunks)
                    }
                })
        
        return records

    def _process_marker_based(self, sections: List[Dict], act_name: str,
                               file_path: Path) -> List[Dict]:
        """
        Process Consumer Protection Act style:
        - First entry = ENTIRE act text (massive, 100K-800K chars)
        - Following entries = individual sections/subsections from Kanoon
        
        Strategy: Parse the full text from the first entry to extract sections.
        Skip the duplicate subsection entries to avoid redundancy.
        """
        records = []
        
        # Process the massive first entry by splitting into sections
        full_text = sections[0].get('content', '')
        if len(full_text) > 10000:
            records.extend(self._split_full_act_text(full_text, act_name, file_path))
        
        # Also process individual section entries (skip subsection entries and the full text)
        # These have patterns like "[Entire Act]" in content (from Kanoon)
        for i, section in enumerate(sections[1:], 1):
            content = section.get('content', '').strip()
            sec_num = str(section.get('section_number', '')).strip()
            sec_title = str(section.get('section_title', '')).strip()
            
            # Skip subsection entries (e.g., "(1)", "(2)", "(a)") - they're already in the full text
            if re.match(r'^\(\d+\)$', sec_num) or re.match(r'^\([a-z]\)$', sec_num):
                continue
            
            # Skip entries that are whole other acts (referenced acts embedded)
            if content.startswith('Union of India - Act\n') and sec_num != act_name:
                continue
            
            # Skip very short Kanoon subsection fragments
            if len(content) < 150 and self.KANOON_HEADER_PATTERN.search(content):
                continue
            
            # Clean Kanoon navigation artifacts
            content = self._clean_kanoon_artifacts(content)
            
            if not content.strip() or len(content) < self.min_chunk_chars:
                continue
            
            # Check if this is a real section entry (e.g., "1.", "42.")
            if re.match(r'^\d+[A-Z]?\.$', sec_num):
                sec_num_clean = sec_num.rstrip('.')
                
                # Build section chunk (may already exist from full text parse)
                # We keep these as they often have cleaner formatting
                chunks = self._build_section_chunks(
                    act_name=act_name,
                    section_number=sec_num_clean,
                    section_title=sec_title if sec_title != sec_num else '',
                    content=content,
                    chapter=''
                )
                
                for j, chunk_text in enumerate(chunks):
                    chunk_id = f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_k{sec_num_clean}_{j}"
                    records.append({
                        'id': self._sanitize_id(chunk_id),
                        'text': chunk_text,
                        'metadata': {
                            'domain': 'statutes',
                            'act': act_name,
                            'section_number': sec_num_clean,
                            'section_title': sec_title if sec_title != sec_num else '',
                            'chapter': '',
                            'source_file': file_path.name,
                            'source_type': 'kanoon_section',
                            'chunk_index': j,
                            'total_chunks': len(chunks)
                        }
                    })
        
        return records

    def _process_monolithic(self, sections: List[Dict], act_name: str,
                             file_path: Path) -> List[Dict]:
        """
        Process single-entry statutes (Companies Act 2013 style).
        The entire act is in one massive content field.
        """
        full_text = sections[0].get('content', '')
        return self._split_full_act_text(full_text, act_name, file_path)

    def _process_generic(self, sections: List[Dict], act_name: str,
                          file_path: Path) -> List[Dict]:
        """Fallback processor for unrecognized formats."""
        records = []
        for i, section in enumerate(sections):
            content = section.get('content', '').strip()
            if not content:
                continue
            
            sec_num = str(section.get('section_number', str(i + 1)))
            sec_title = str(section.get('section_title', ''))
            
            chunks = self._build_section_chunks(
                act_name=act_name,
                section_number=sec_num,
                section_title=sec_title,
                content=content,
                chapter=''
            )
            
            for j, chunk_text in enumerate(chunks):
                chunk_id = f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_g{i}_{j}"
                records.append({
                    'id': self._sanitize_id(chunk_id),
                    'text': chunk_text,
                    'metadata': {
                        'domain': 'statutes',
                        'act': act_name,
                        'section_number': sec_num,
                        'section_title': sec_title,
                        'source_file': file_path.name,
                        'chunk_index': j,
                        'total_chunks': len(chunks)
                    }
                })
        
        return records

    # ==================== CORE PARSING METHODS ====================

    def _parse_chunk_marker_content(self, content: str) -> Optional[Dict]:
        """
        Parse BNS-style chunk content:
        --- Section 302 ---
        BNS
        Chapter XVI
        S.
        302
        Punishment for murder.
        Description
        <actual content>
        """
        # Check for marker
        marker_match = self.MARKER_PATTERN.match(content)
        if not marker_match:
            return None
        
        sec_num = marker_match.group(1)
        rest = content[marker_match.end():].strip()
        
        lines = rest.split('\n')
        chapter = ''
        section_title = ''
        body_start = 0
        
        # Parse header fields
        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip act name abbreviation (e.g., "BNS")
            if idx == 0 and len(line_stripped) < 10 and not line_stripped.startswith('Chapter'):
                continue
            
            # Chapter line
            if line_stripped.startswith('Chapter') or line_stripped.startswith('CHAPTER'):
                chapter = line_stripped
                continue
            
            # "S." marker (section prefix)
            if line_stripped == 'S.':
                continue
            
            # Section number line (matches our section number)
            if line_stripped == sec_num:
                continue
            
            # "Description" marker
            if line_stripped == 'Description':
                body_start = idx + 1
                break
            
            # This is likely the section title
            if not section_title and len(line_stripped) > 3:
                section_title = line_stripped.rstrip('.')
                continue
            
            # If we haven't found "Description" but we're past the header
            if idx > 6:
                body_start = idx
                break
        
        body = '\n'.join(lines[body_start:]).strip() if body_start < len(lines) else rest
        
        return {
            'section_number': sec_num,
            'section_title': section_title,
            'chapter': chapter,
            'body': body
        }

    def _split_full_act_text(self, full_text: str, act_name: str, 
                              file_path: Path) -> List[Dict]:
        """
        Split a full act text into individual section chunks.
        Handles the main act parsing by finding section boundaries.
        """
        records = []
        
        # Clean the text first
        text = self._clean_kanoon_artifacts(full_text)
        
        # Find all section starts: "N. Title text" or standalone "N.\n"
        # We look for section markers at the start of a line
        section_pattern = re.compile(
            r'^(\d+[A-Z]?)\.\s*\n(.+?)(?=\n\d+[A-Z]?\.\s*\n|\Z)',
            re.MULTILINE | re.DOTALL
        )
        
        # Also try the pattern with title on same line
        section_pattern_titled = re.compile(
            r'^(\d+[A-Z]?)\.\s+([A-Z][^\n]+?)(?:\.—|—|-)\s*\n(.+?)(?=\n\d+[A-Z]?\.\s|\Z)',
            re.MULTILINE | re.DOTALL
        )
        
        # Try to find chapter-aware sections
        # First, detect all chapter boundaries
        chapters = list(self.CHAPTER_PATTERN.finditer(text))
        
        # Find sections using the simpler pattern first
        matches = list(section_pattern.finditer(text))
        
        if not matches:
            # Try the titled pattern
            matches_titled = list(section_pattern_titled.finditer(text))
            if matches_titled:
                for m in matches_titled:
                    sec_num = m.group(1)
                    sec_title = m.group(2).strip()
                    body = m.group(3).strip()
                    chapter = self._find_chapter_for_position(chapters, m.start(), text)
                    
                    chunks = self._build_section_chunks(
                        act_name=act_name,
                        section_number=sec_num,
                        section_title=sec_title,
                        content=body,
                        chapter=chapter
                    )
                    
                    for j, chunk_text in enumerate(chunks):
                        chunk_id = f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_f{sec_num}_{j}"
                        records.append({
                            'id': self._sanitize_id(chunk_id),
                            'text': chunk_text,
                            'metadata': {
                                'domain': 'statutes',
                                'act': act_name,
                                'section_number': sec_num,
                                'section_title': sec_title,
                                'chapter': chapter,
                                'source_file': file_path.name,
                                'source_type': 'full_text_parse',
                                'chunk_index': j,
                                'total_chunks': len(chunks)
                            }
                        })
            else:
                # Last resort: split by paragraphs with size limits
                records.extend(self._fallback_paragraph_split(text, act_name, file_path))
        else:
            current_chapter = ''
            for m_idx, m in enumerate(matches):
                sec_num = m.group(1)
                body = m.group(2).strip()
                
                # Extract title from first line of body
                first_line = body.split('\n')[0].strip() if body else ''
                sec_title = ''
                
                # Check if first line looks like a title
                if first_line and len(first_line) < 120 and not first_line.startswith('('):
                    sec_title = first_line.rstrip('.').rstrip('—').rstrip('-').strip()
                    body = '\n'.join(body.split('\n')[1:]).strip()
                
                # Find chapter context
                chapter = self._find_chapter_for_position(chapters, m.start(), text)
                if chapter:
                    current_chapter = chapter
                
                chunks = self._build_section_chunks(
                    act_name=act_name,
                    section_number=sec_num,
                    section_title=sec_title,
                    content=body,
                    chapter=current_chapter
                )
                
                for j, chunk_text in enumerate(chunks):
                    chunk_id = f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_f{sec_num}_{j}"
                    records.append({
                        'id': self._sanitize_id(chunk_id),
                        'text': chunk_text,
                        'metadata': {
                            'domain': 'statutes',
                            'act': act_name,
                            'section_number': sec_num,
                            'section_title': sec_title,
                            'chapter': current_chapter,
                            'source_file': file_path.name,
                            'source_type': 'full_text_parse',
                            'chunk_index': j,
                            'total_chunks': len(chunks)
                        }
                    })
        
        if not records:
            # Absolute fallback
            records.extend(self._fallback_paragraph_split(text, act_name, file_path))
        
        return records

    def _fallback_paragraph_split(self, text: str, act_name: str, 
                                   file_path: Path) -> List[Dict]:
        """
        Last resort: split by paragraphs with context-preserving headers.
        Used when no section boundaries can be detected.
        """
        records = []
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk = ""
        chunk_idx = 0
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < self.max_chunk_chars:
                current_chunk += '\n\n' + para if current_chunk else para
            else:
                if current_chunk:
                    chunk_text = f"Act: {act_name}\n\n{current_chunk}"
                    records.append({
                        'id': self._sanitize_id(f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_p{chunk_idx}"),
                        'text': chunk_text,
                        'metadata': {
                            'domain': 'statutes',
                            'act': act_name,
                            'section_number': f'para_{chunk_idx}',
                            'section_title': '',
                            'source_file': file_path.name,
                            'source_type': 'paragraph_split',
                            'chunk_index': chunk_idx,
                            'total_chunks': -1  # unknown until end
                        }
                    })
                    chunk_idx += 1
                current_chunk = para
        
        # Flush remaining
        if current_chunk:
            chunk_text = f"Act: {act_name}\n\n{current_chunk}"
            records.append({
                'id': self._sanitize_id(f"D8_{hashlib.md5(file_path.stem.encode()).hexdigest()[:8]}_p{chunk_idx}"),
                'text': chunk_text,
                'metadata': {
                    'domain': 'statutes',
                    'act': act_name,
                    'section_number': f'para_{chunk_idx}',
                    'section_title': '',
                    'source_file': file_path.name,
                    'source_type': 'paragraph_split',
                    'chunk_index': chunk_idx,
                    'total_chunks': chunk_idx + 1
                }
            })
        
        return records

    # ==================== TEXT BUILDING METHODS ====================

    def _build_section_chunks(self, act_name: str, section_number: str,
                               section_title: str, content: str,
                               chapter: str = '') -> List[str]:
        """
        Build one or more text chunks for a section.
        Adds structural header and splits if content exceeds max size.
        
        Returns list of chunk strings (usually just one).
        """
        # Build the context header that appears at the top of every chunk
        header_parts = [f"Act: {act_name}"]
        if chapter:
            header_parts.append(f"Chapter: {chapter}")
        
        sec_label = f"Section {section_number}"
        if section_title and section_title != section_number:
            sec_label += f" - {section_title}"
        header_parts.append(sec_label)
        
        header = '\n'.join(header_parts)
        
        # Clean the content
        content = content.strip()
        if not content:
            return [header]
        
        full_text = f"{header}\n\n{content}"
        
        # If within size limit, return as single chunk
        if len(full_text) <= self.max_chunk_chars:
            return [full_text]
        
        # Need to sub-chunk: split at paragraph/subsection boundaries
        return self._sub_chunk_section(header, content)

    def _sub_chunk_section(self, header: str, content: str) -> List[str]:
        """
        Split an oversized section into sub-chunks while preserving:
        - The header context on each chunk
        - Paragraph/subsection boundaries
        - Proviso/Explanation/Illustration groupings
        """
        chunks = []
        
        # Split into logical segments (subsections, explanations, provisos)
        segments = self._split_into_segments(content)
        
        current_chunk_parts = []
        current_size = len(header) + 2  # +2 for \n\n
        
        for segment in segments:
            segment_size = len(segment)
            
            if current_size + segment_size + 1 <= self.max_chunk_chars:
                current_chunk_parts.append(segment)
                current_size += segment_size + 1
            else:
                # Flush current chunk
                if current_chunk_parts:
                    chunk_text = header + '\n\n' + '\n'.join(current_chunk_parts)
                    chunks.append(chunk_text)
                
                # Start new chunk with this segment
                if segment_size + len(header) + 2 <= self.max_chunk_chars:
                    current_chunk_parts = [segment]
                    current_size = len(header) + 2 + segment_size
                else:
                    # Segment itself is too big, force-split it
                    for sub in self._force_split(segment, self.max_chunk_chars - len(header) - 2):
                        chunks.append(header + '\n\n' + sub)
                    current_chunk_parts = []
                    current_size = len(header) + 2
        
        # Flush remaining
        if current_chunk_parts:
            chunk_text = header + '\n\n' + '\n'.join(current_chunk_parts)
            chunks.append(chunk_text)
        
        return chunks if chunks else [header + '\n\n' + content[:self.max_chunk_chars]]

    def _split_into_segments(self, content: str) -> List[str]:
        """
        Split content into logical segments at subsection/paragraph boundaries.
        Preserves Provisos, Explanations, and Illustrations with their parent.
        """
        # Split at subsection markers: (1), (2), (a), (b), etc.
        # Also split at Explanation, Proviso, Illustration markers
        segment_pattern = re.compile(
            r'\n(?=\(\d+\)\s|\([a-z]\)\s|Explanation\b|Proviso\b|Illustration\b|PROVIDED\b|Schedule\b)',
            re.MULTILINE
        )
        
        parts = segment_pattern.split(content)
        
        # If we get good segments, return them
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]
        
        # Fallback: split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if len(paragraphs) > 1:
            return paragraphs
        
        # Last resort: return as-is (will be force-split later if needed)
        return [content]

    def _force_split(self, text: str, max_size: int) -> List[str]:
        """Force-split text at sentence boundaries when it exceeds max_size."""
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        current = ""
        
        # Split at sentence boundaries (period followed by space/newline)
        sentences = re.split(r'(?<=[.;])\s+', text)
        
        for sent in sentences:
            if len(current) + len(sent) + 1 <= max_size:
                current += ' ' + sent if current else sent
            else:
                if current:
                    chunks.append(current.strip())
                if len(sent) > max_size:
                    # Even a single sentence is too big, hard split
                    for start in range(0, len(sent), max_size - OVERLAP_CHARS):
                        chunks.append(sent[start:start + max_size])
                else:
                    current = sent
                    continue
                current = ""
        
        if current:
            chunks.append(current.strip())
        
        return chunks

    # ==================== UTILITY METHODS ====================

    def _find_chapter_for_position(self, chapters: list, pos: int, text: str) -> str:
        """Find the chapter heading that applies to a given text position."""
        current_chapter = ''
        for ch_match in chapters:
            if ch_match.start() <= pos:
                current_chapter = ch_match.group(0).strip()
            else:
                break
        return current_chapter

    def _clean_kanoon_artifacts(self, text: str) -> str:
        """Remove Kanoon.org navigation artifacts from text."""
        # Remove "[Section X] [Entire Act]" navigation markers
        text = re.sub(r'\[\s*\n*(?:Section\s+\d+|Entire\s+Act)\s*\n*\]', '', text)
        # Remove "Union of India - Section/Subsection" headers
        text = re.sub(r'Union of India - (?:Section|Subsection|Act)\n', '', text)
        # Remove multiple consecutive newlines (more than 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def _sanitize_id(chunk_id: str) -> str:
        """Sanitize chunk ID to be safe for vector store keys."""
        # Replace spaces, dots, special chars with underscores
        return re.sub(r'[^a-zA-Z0-9_-]', '_', chunk_id)


# ==================== CONVENIENCE FUNCTIONS ====================

def process_all_statutes(statutes_dir: str | Path, 
                          max_chunk_chars: int = MAX_CHUNK_CHARS) -> List[Dict]:
    """
    Process all statute JSON files in a directory.
    
    Args:
        statutes_dir: Path to directory containing statute JSON files
        max_chunk_chars: Maximum characters per chunk
        
    Returns:
        List of properly chunked records ready for vector store ingestion
    """
    statutes_dir = Path(statutes_dir)
    if not statutes_dir.exists():
        logger.error(f"Statutes directory not found: {statutes_dir}")
        return []
    
    chunker = StatuteSectionChunker(max_chunk_chars=max_chunk_chars)
    all_records = []
    
    for file_path in sorted(statutes_dir.glob("*.json")):
        if file_path.name == "summary.json":
            continue
        records = chunker.process_statute_file(file_path)
        all_records.extend(records)
    
    logger.info(f"Total statute chunks produced: {len(all_records)}")

    # Deduplicate IDs: if the same ID appears more than once, suffix with _b2, _b3, ...
    seen_ids: dict = {}
    for record in all_records:
        rid = record['id']
        if rid in seen_ids:
            seen_ids[rid] += 1
            record['id'] = f"{rid}_b{seen_ids[rid]}"
        else:
            seen_ids[rid] = 1

    duplicates_fixed = sum(1 for v in seen_ids.values() if v > 1)
    if duplicates_fixed:
        logger.warning(f"Fixed {duplicates_fixed} duplicate chunk IDs by appending _b<n> suffix")

    return all_records


# ==================== CLI TEST ====================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Default to BACKUP_DATA path
    default_dir = Path(__file__).parent.parent.parent / "DATA" / "Statutes" / "json"
    backup_dir = Path(str(Path(__file__).resolve().parent.parent / 'BACKUP_DATA'\DATA\Statutes\json")
    
    statutes_dir = default_dir if default_dir.exists() else backup_dir
    
    if len(sys.argv) > 1:
        statutes_dir = Path(sys.argv[1])
    
    print(f"Processing statutes from: {statutes_dir}")
    
    records = process_all_statutes(statutes_dir)
    
    print(f"\n{'='*60}")
    print(f"TOTAL RECORDS: {len(records)}")
    
    # Print summary by act
    from collections import Counter
    act_counts = Counter(r['metadata']['act'] for r in records)
    print(f"\nBy Act:")
    for act, count in act_counts.most_common():
        print(f"  {act}: {count} chunks")
    
    # Print sample chunks
    print(f"\n{'='*60}")
    print("SAMPLE CHUNKS:")
    for r in records[:5]:
        print(f"\n--- ID: {r['id']} ---")
        print(f"Section: {r['metadata'].get('section_number')} | Title: {r['metadata'].get('section_title', '')[:60]}")
        print(f"Chapter: {r['metadata'].get('chapter', '')[:60]}")
        print(f"Text ({len(r['text'])} chars):")
        print(r['text'][:300])
        print("...")
