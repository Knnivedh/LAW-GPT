import json

with open('tests/conversational_accuracy_report_20260301_111706.json') as f:
    d = json.load(f)

print('=== ALL QUESTIONS SCORED BELOW 85% ===\n')
problem_qs = [q for q in d['per_question'] if q['composite_score'] < 0.85]
print(f"Total below 85%: {len(problem_qs)}/25\n")

for q in problem_qs:
    n = q['question_number']
    cat = q['category']
    comp = q['composite_score']
    turns = q['total_turns']
    final = q['got_final_answer']
    kw = q['keyword_score']
    sec = q['section_score']
    fact = q['fact_score']
    question = q['question']
    print(f"Q{n:02d} [{cat}] {comp:.0%}  kw={kw:.0%} sec={sec:.0%} fact={fact:.0%}  turns={turns}  got_final={final}")
    print(f"  Q: {question}")
    print(f"  Missed keywords: {q['missed_keywords']}")
    print(f"  Missed sections: {q['missed_sections']}")
    print(f"  Missed facts:    {q['missed_facts']}")
    print(f"  Conversation turns:")
    for t in q['conversation']:
        role = t['role']
        conf = t['confidence']
        lat = t['latency_sec']
        msg = t['message_preview'][:120]
        print(f"    [{role}] conf={conf} lat={lat}s: {msg}")
    print()

print("\n=== Q15 FULL CONVERSATION ===")
q15 = next(q for q in d['per_question'] if q['question_number'] == 15)
for t in q15['conversation']:
    print(f"[{t['role']}] conf={t['confidence']}")
    print(f"  {t['message_preview'][:200]}")
    print()
