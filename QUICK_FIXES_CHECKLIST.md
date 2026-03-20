# LAW-GPT Quick Fixes Checklist

## 🔴 CRITICAL (Do This Week)

### 1. Fix Multilingual Support
**Current Score:** 40/100 | **Target:** 85/100

**Problem:** Hindi queries getting English-only responses with missing keywords

**Quick Fix:**
```python
# In your RAG system, add this function:

def detect_and_respond_in_language(query, response):
    """Detect query language and translate response"""
    import langdetect
    from deep_translator import GoogleTranslator
    
    # Detect language
    lang = langdetect.detect(query)
    
    # If not English, translate response
    if lang != 'en':
        translator = GoogleTranslator(source='en', target=lang)
        response = translator.translate(response)
    
    return response

# Install: pip install langdetect deep-translator
```

**Files to Modify:**
- `kaanoon_test/enhanced_rag_with_caching.py` (line ~200)
- Add translation step after answer generation
- Test with Hindi, Tamil, Bengali queries

**Expected Time:** 2-3 hours  
**Impact:** +45 points in multilingual category

---

### 2. Optimize Response Time
**Current:** 11.85s | **Target:** <5s

**Quick Wins:**

#### A. Increase Cache Size
```python
# File: kaanoon_test/enhanced_rag_with_caching.py
# Line ~42

# CHANGE FROM:
cache = QueryCache(max_size=1000, ttl_seconds=3600)

# CHANGE TO:
cache = QueryCache(max_size=5000, ttl_seconds=7200)
```

#### B. Pre-cache Popular Queries
```python
# Add to system initialization
POPULAR_QUERIES = [
    "What is IPC Section 302?",
    "How to file an FIR?",
    "What is IPC 420?",
    # ... add 50-100 more
]

for query in POPULAR_QUERIES:
    system.query(query)  # Warm up cache
```

#### C. Reduce Retrieval Count
```python
# File: rag_system/core/enhanced_retriever.py
# Line ~150

# CHANGE FROM:
results = hybrid_store.hybrid_search(query, n_results=50)

# CHANGE TO:
results = hybrid_store.hybrid_search(query, n_results=30)
```

**Expected Time:** 1-2 hours  
**Impact:** 50% faster responses (11.85s → 6s)

---

## 🟡 IMPORTANT (Do This Month)

### 3. Improve Case Law Coverage
**Current Score:** 74.2/100 | **Target:** 90/100

**Problem:** "Rarest of Rare doctrine" missing "life imprisonment" alternative

**Quick Fix:**
```python
# Add to prompts/chatbot_rules_enhanced.py

CASE_LAW_ENHANCEMENT = """
When explaining landmark cases or doctrines:
1. Provide complete definition
2. Explain ALL alternatives (e.g., death penalty OR life imprisonment)
3. Cite the original case with year
4. Explain current application
5. Mention any modifications/amendments
"""

# Also add these to your database:
LANDMARK_CASES = {
    "Rarest of Rare": {
        "case": "Bachan Singh v. State of Punjab (1980)",
        "doctrine": "Death penalty only in rarest of rare cases",
        "alternatives": ["Life imprisonment", "Imprisonment for a term"],
        "criteria": "When alternative is unquestionably foreclosed"
    },
    # Add 50-100 more landmark cases
}
```

**Expected Time:** 4-5 hours  
**Impact:** +15 points in case law category

---

### 4. Fix Comparative Analysis
**Current:** Only explains concepts separately, doesn't compare

**Problem Example:** "Difference between IPC 302 and 304" → Only explains 302

**Quick Fix:**
```python
# File: prompts/chatbot_rules_enhanced.py
# Add this detection and special handling

def is_comparison_query(query):
    """Detect if query asks for comparison"""
    comparison_words = ['difference', 'compare', 'vs', 'versus', 'between']
    return any(word in query.lower() for word in comparison_words)

# Add this prompt template:
COMPARISON_TEMPLATE = """
Question asks for COMPARISON between {concept_a} and {concept_b}.

Structure your answer as:

1. {concept_a}: [Brief definition]
2. {concept_b}: [Brief definition]
3. KEY DIFFERENCES:
   - Intent: {concept_a} requires X, WHEREAS {concept_b} requires Y
   - Punishment: {concept_a} has X, WHILE {concept_b} has Y
   - Application: {concept_a} is for X, BUT {concept_b} is for Y

Always use comparison words: whereas, while, but, unlike, in contrast
"""
```

**Expected Time:** 2-3 hours  
**Impact:** +10 points on comparison queries

---

## 🟢 NICE TO HAVE (Do Next Quarter)

### 5. Expand Corporate Law Coverage
**Current Score:** 70/100 | **Target:** 85/100

**Action:**
- Add Companies Act 2013 full database (JSON format)
- Add SEBI regulations
- Add 50+ corporate case laws

**Expected Time:** 1 week  
**Impact:** +15 points in corporate law

---

### 6. Better Edge Case Handling

**Current:** Identifies errors but could be more helpful

**Enhancement:**
```python
def handle_invalid_section(section_num):
    """When user asks for non-existent IPC section"""
    return f"""
    IPC Section {section_num} does not exist in the Indian Penal Code.
    
    Did you mean one of these?
    - IPC Section {find_nearest_section(section_num)}
    - IPC Section {find_alternative_section(section_num)}
    
    Or describe what you're looking for, and I'll help you find the right section.
    """
```

**Expected Time:** 1-2 hours  
**Impact:** Better user experience

---

## Implementation Priority

### Week 1: Critical Fixes
- [ ] Day 1-2: Multilingual support
- [ ] Day 3-4: Response time optimization
- [ ] Day 5: Test and validate

**Expected Score:** 86 → 90.5

### Week 2-3: Important Fixes
- [ ] Week 2: Case law coverage
- [ ] Week 2: Comparative analysis
- [ ] Week 3: Test and validate

**Expected Score:** 90.5 → 93.2

### Week 4+: Nice to Have
- [ ] Corporate law expansion
- [ ] Edge case handling
- [ ] Continuous testing

**Expected Score:** 93.2 → 95+

---

## Testing After Each Fix

Run this command after implementing each fix:
```bash
python comprehensive_quality_test.py
```

Compare results with baseline:
- Baseline: 86.01/100, 94.1% pass rate
- Target: 95/100, 99% pass rate

---

## Quick Command Reference

```bash
# Run backend
cd kaanoon_test
python comprehensive_accuracy_test_server.py

# Run frontend
cd frontend
npm run dev

# Run quality test
cd ..
python comprehensive_quality_test.py

# Check specific category
grep -A 5 "Multilingual" quality_assessment_report_*.txt
```

---

## Files You'll Need to Edit

1. **Multilingual:**
   - `kaanoon_test/enhanced_rag_with_caching.py`
   - Add translation step

2. **Response Time:**
   - `kaanoon_test/enhanced_rag_with_caching.py` (cache size)
   - `rag_system/core/enhanced_retriever.py` (retrieval count)

3. **Case Laws:**
   - `prompts/chatbot_rules_enhanced.py`
   - Add case law database/JSON

4. **Comparative Analysis:**
   - `prompts/chatbot_rules_enhanced.py`
   - Add comparison detection and template

---

## Success Metrics

| Fix | Before | After | Improvement |
|-----|--------|-------|-------------|
| Multilingual | 40/100 | 85/100 | +45 pts |
| Response Time | 11.85s | 6s | -48% |
| Case Laws | 74.2/100 | 90/100 | +16 pts |
| Comparisons | 33% | 90% | +57 pts |
| **OVERALL** | **86/100** | **95/100** | **+9 pts** |

---

**Next Action:** Start with Multilingual fix (biggest impact, quickest fix)

**Questions?** Review detailed analysis in `CHATBOT_GAP_ANALYSIS_REPORT.md`
