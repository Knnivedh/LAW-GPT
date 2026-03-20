"""Quick local test of the new _is_simple_query() logic against all 25 accuracy questions."""
import re

def _is_simple_query(query):
    query_lower = query.lower().strip()
    
    personal_indicators = [
        r'\bi\s+(am|was|have|had|bought|paid|filed|need|want|got|received|signed)',
        r'\bmy\s+(wife|husband|father|mother|brother|sister|boss|employer|landlord|tenant|neighbour|neighbor|daughter|son|family|property|salary|land|house|flat|car|money|account|loan|complaint|case|fir)',
        r'\bwe\s+(are|were|have|had|bought|paid|filed|signed)',
        r'\b(our|us)\b.*\b(property|house|flat|land|money|case|dispute|issue)',
        r'\b(help me|please help|guide me|advise me|what should i|what can i|how (can|do|should) i|can i file|should i file)',
        r'\b(was (arrested|terminated|cheated|harassed|threatened|assaulted))',
        r'\b(got (arrested|fired|terminated|cheated|notice|letter))',
        r'\b(received\s+(a |an )?(notice|letter|summon|order|fir))',
        r'\b(filed\s+(a |an )?(fir|complaint|case|petition|suit))',
    ]
    for p in personal_indicators:
        if re.search(p, query_lower):
            return False, 'PERSONAL'

    if re.match(r'^what\s+(is|are)\s+', query_lower): return True, 'what_is'
    if re.match(r'^what\s+(did|does|do|has|have|was|were)\s+', query_lower): return True, 'what_did'
    if re.match(r'^how\s+(many|much|does|do|is|are|can)\s+', query_lower): return True, 'how'
    if re.match(r'^when\s+(did|does|was|were|is|will)\s+', query_lower): return True, 'when'
    if re.match(r'^who\s+(can|is|are|has|have|was|were|should)\s+', query_lower): return True, 'who'
    if re.match(r'^which\s+', query_lower): return True, 'which'
    if re.match(r'^(define|explain|describe|list|enumerate|outline|summarize|summarise|discuss|compare|differentiate|distinguish|clarify|tell\s+me\s+about)\s+', query_lower): return True, 'imperative'
    if re.match(r'^(has|is|does|do|can|are|was|were|will|shall|should|may)\s+', query_lower): return True, 'yesno'
    if re.match(r'^(if\s+a\s+|suppose\s+|assuming\s+|a\s+(person|consumer|woman|man|buyer|seller|employee|employer|tenant|landlord|citizen|victim|accused|complainant)\s+)', query_lower): return True, 'hypothetical'
    if re.match(r'^(section|article|rule|order|clause|schedule)\s+\d+', query_lower): return True, 'section_ref'

    legal_kws = [
        'fundamental rights','right to privacy','basic structure','judicial review',
        'anticipatory bail','regular bail','consumer rights','consumer protection',
        'domestic violence','dowry','divorce','maintenance','alimony',
        'landmark case','landmark judgment','supreme court','high court',
        'vishaka','kesavananda','puttaswamy','navtej','maneka gandhi',
        'bharatiya nyaya sanhita','bns','bnss','bharatiya sakshya',
        'rera','consumer protection act','legal aid','legal services',
        'pwdva','protection of women','domestic violence act',
        'jurisdiction','pecuniary jurisdiction','territorial jurisdiction',
        'punishment for','penalty for','offence of','crime of',
        'reliefs','remedies','provisions','features','types of',
        'significance of','importance of','key features','main features',
        'difference between','comparison between','distinction between',
        'replaced','come into effect','enacted','implemented',
        'colonial','new criminal law','law reform','legal reform',
    ]
    for kw in legal_kws:
        if kw in query_lower:
            return True, f'keyword:{kw}'

    wc = len(query.split())
    if wc <= 15 and query.strip().endswith('?'):
        return True, 'short_q'
    if wc <= 30 and not re.search(r'\b(i|my|me|mine|we|our|us|ours)\b', query_lower):
        return True, 'no_personal'
    return False, 'unknown'

questions = [
    ('Q01', 'What is the punishment for murder under the Bharatiya Nyaya Sanhita (BNS)?'),
    ('Q02', 'What are the key differences between IPC and the new Bharatiya Nyaya Sanhita?'),
    ('Q03', 'Has the offence of sedition been removed or modified under the new criminal laws?'),
    ('Q04', 'What is the punishment for theft under Indian law?'),
    ('Q05', 'What is the legal definition and punishment for dowry death in India?'),
    ('Q06', 'What are the fundamental rights guaranteed under Part III of the Indian Constitution?'),
    ('Q07', 'What is the right to privacy in India and which Supreme Court judgment established it as a fundamental right?'),
    ('Q08', 'What is the basic structure doctrine and how did the Kesavananda Bharati case establish it?'),
    ('Q09', 'What are the consumer rights defined under the Consumer Protection Act, 2019?'),
    ('Q10', 'What is the process to file a consumer complaint under the Consumer Protection Act, 2019?'),
    ('Q11', 'What is the jurisdiction of District, State, and National Consumer Disputes Redressal Commissions based on claim value?'),
    ('Q12', 'What are the grounds for divorce under Hindu Marriage Act and Special Marriage Act?'),
    ('Q13', 'What reliefs can a woman seek under the Protection of Women from Domestic Violence Act (PWDVA), 2005?'),
    ('Q14', 'What are the three new criminal law statutes that replaced IPC, CrPC, and Indian Evidence Act?'),
    ('Q15', 'What are the key features of the Bharatiya Nyaya Sanhita that make it different from the colonial-era IPC?'),
    ('Q16', 'How many chapters and sections does the Bharatiya Nyaya Sanhita have?'),
    ('Q17', 'What is the significance of the Vishaka v. State of Rajasthan case for workplace sexual harassment law?'),
    ('Q18', 'What were the Vishaka Guidelines and how did they lead to the POSH Act, 2013?'),
    ('Q19', 'What is the RERA Act and what protections does it provide to homebuyers?'),
    ('Q20', 'Can a woman in a live-in relationship file a domestic violence complaint under PWDVA?'),
    ('Q21', 'A consumer purchased a car worth Rs 15 lakh that turned out to be defective. Which consumer forum should they approach and what remedies are available?'),
    ('Q22', 'What is the process and timeline for registering a complaint under RERA against a builder for delayed possession?'),
    ('Q23', 'What is the doctrine of basic structure and which cases have expanded or limited it since Kesavananda Bharati?'),
    ('Q24', 'What is Section 498A IPC and how has the Supreme Court addressed its misuse in recent judgments?'),
    ('Q25', 'What is anticipatory bail under Indian law and what did the Supreme Court hold in Arnesh Kumar v. State of Bihar?'),
]

print(f"{'QID':<5} {'Result':<10} {'Reason':<30} {'Query':<70}")
print('-' * 120)
bypassed = 0
for qid, q in questions:
    result, reason = _is_simple_query(q)
    status = 'DIRECT' if result else 'CLARIFY'
    if result:
        bypassed += 1
    print(f"{qid:<5} {status:<10} {reason:<30} {q[:70]}")

print(f"\n=> {bypassed}/25 bypass clarification (DIRECT to Agentic RAG)")
print(f"=> {25 - bypassed}/25 enter clarification loop")
