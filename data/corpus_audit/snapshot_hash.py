"""snapshot_hash.py - recompute the frozen-input hashes of the CCI coding corpus.

Usage:  python snapshot_hash.py coding_input.jsonl [coded_input_hashes.csv]

For every line of coding_input.jsonl (the exact, truncated text the round-1 coders saw:
question <= 700 chars, accepted answer <= 500 chars) it computes
  sha256        = SHA-256 of the UTF-8 bytes of the canonical JSON
                  {"accepted_answer": <answer snippet>, "question": <question snippet>}
                  (json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(',', ':')))
  sha256_record = SHA-256 of the canonical JSON of the whole record (cid, pid, title, tags, question, accepted_answer)
and the SHA-256 of the file bytes. With a second argument it verifies every row of the published
hash table and exits with status 1 on any mismatch. Standard library only.
"""
import sys, json, hashlib, csv


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def snippet_hash(rec):
    return hashlib.sha256(canon({'question': rec['question'], 'accepted_answer': rec['accepted_answer']})).hexdigest()


def record_hash(rec):
    return hashlib.sha256(canon({k: rec[k] for k in ('cid', 'pid', 'title', 'tags', 'question', 'accepted_answer')})).hexdigest()


def compute(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            site, qid = r['pid'].split(':', 1)
            rows.append(dict(cid=r['cid'], site=site, question_id=qid, sha256=snippet_hash(r), sha256_record=record_hash(r)))
    with open(path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    return rows, file_hash


if __name__ == '__main__':
    rows, fh = compute(sys.argv[1])
    print('records', len(rows), 'file_sha256', fh)
    if len(sys.argv) > 2:
        ref = {r['cid']: r for r in csv.DictReader(open(sys.argv[2], encoding='utf-8'))}
        bad = [r['cid'] for r in rows if r['cid'] not in ref or ref[r['cid']]['sha256'] != r['sha256']
               or ref[r['cid']]['sha256_record'] != r['sha256_record']]
        bad += [c for c in ref if c not in {r['cid'] for r in rows}]
        print('verified', len(rows) - len(bad), 'mismatched', len(bad), bad[:10])
        sys.exit(1 if bad else 0)
