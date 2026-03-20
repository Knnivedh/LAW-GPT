import json
d = json.load(open('tests/results/t10_robustness_20260305_010251.json', encoding='utf-8'))
print('Summary:', d['summary']['passed'], '/', d['summary']['total'])
print()
for q in d['details']:
    variants = q.get('variants', [])
    v_pass = sum(1 for v in variants if v.get('passed'))
    qid = q.get('q_id') or q.get('id') or '?'
    print(f"  {qid}  {v_pass}/3 pass")
    for v in variants:
        status = 'PASS' if v.get('passed') else 'FAIL'
        kw = v.get('kw_score', v.get('keyword_score', 0))
        print(f"    V{v.get('variant','?')} {status}  kw={kw:.2f}  '{v.get('text','')[:50]}'")
        print(f"      ans: {v.get('answer_excerpt','')[:120]}")
