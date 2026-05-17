# -*- coding: utf-8 -*-
"""扫真题 docx，抽出「对联 4 选 1」真题。
形式：给上联（或下联），4 个候选下联（或上联），选最对仗工整、内容契合的一项。
"""
import json, sys, re, time, zipfile, urllib.request, urllib.error, os, glob as _g

API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
KEY = open('../deepseek_key.txt', encoding='utf-8').read().strip()

BASE = '/Users/davidryu/教学/初中语文/试题/中考'
SOURCES = (
    _g.glob(BASE + '/**/*基础*运用*解析*.docx', recursive=True)
    + _g.glob(BASE + '/**/*基础综合*解析*.docx', recursive=True)
    + _g.glob(BASE + '/**/*基础积累*解析*.docx', recursive=True)
    + _g.glob(BASE + '/**/*对联*解析*.docx', recursive=True)
)
SOURCES = list(set(SOURCES))[:14]
CHUNK = 6500; OVERLAP = 1500


def call_api(messages, temperature=0.0, max_retry=3):
    body = json.dumps({'model': MODEL, 'messages': messages,
                       'temperature': temperature}).encode('utf-8')
    req = urllib.request.Request(API_URL, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    last = None
    for a in range(max_retry):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode('utf-8'))['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            last = 'HTTP %s' % e.code
        except Exception as e:
            last = repr(e)
        time.sleep(2 * (a + 1))
    raise RuntimeError(str(last))


def extract_json(t):
    t = re.sub(r'^```(?:json)?\s*', '', t.strip())
    t = re.sub(r'\s*```$', '', t)
    s, e = t.find('{'), t.rfind('}')
    try:
        return json.loads(t[s:e + 1]) if s >= 0 else None
    except Exception:
        return None


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    paras = []
    for p in re.split(r'</w:p>', xml):
        t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
        if t.strip():
            paras.append(t.strip())
    return '\n'.join(paras)


def chunkify(text):
    out, i = [], 0
    while i < len(text):
        end = min(i + CHUNK, len(text))
        nl = text.rfind('\n', i + CHUNK - 800, end)
        if nl > i + 1000:
            end = nl
        out.append(text[i:end])
        if end >= len(text):
            break
        i = max(end - OVERLAP, i + 1)
    return out


PROMPT = """从下面的中考语文资料里，扫出「对联选择题」——形式特征：

  ① 给出一句对联（通常是上联，少数是下联），让选最合适的对句；
  ② 题里有"对联""上联""下联"等字样；
  ③ 4 个选项分别是候选对句（完整的一句对联）；
  ④ 资料给出了答案字母和解析。

跳过：
  ✗ 选填上联里某个词的（那是词语题）
  ✗ 自己写对联的开放题
  ✗ 其他题型

为每题输出：
- context：题目背景说明（如「为庆贺端午节，同学写了一副对联，请你选最恰当的下联」）。可以包含相关语境或主题。
- given：原文给出的那句（如「上联：解剖透视为骨，方寸能藏千里势」）。完整含「上联：」/「下联：」前缀。
- side：「下联」或「上联」——表示要选的是哪一边。
- options：4 个候选对句，每个是完整一句话，不要带 ABCD 前缀。
- answerIndex：0-3 整数。
- analysis：解析（说明对仗工整在哪、为什么对、其他选项为什么不对，1-3 句）。

只输出 JSON：
{"questions":[{"context":"...","given":"...","side":"下联","options":["...","...","...","..."],"answerIndex":0,"analysis":"..."}]}
"""


def main():
    chunk_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    all_q = []
    for src in SOURCES:
        if not os.path.exists(src):
            continue
        text = docx_text(src)
        chunks = chunkify(text)
        if chunk_limit:
            chunks = chunks[:chunk_limit]
        print('=== %s（%d 块）===' % (src.split('/')[-1], len(chunks)))
        for ci, ch in enumerate(chunks):
            try:
                raw = call_api([{'role': 'user', 'content': PROMPT + '\n\n资料：\n' + ch}])
                obj = extract_json(raw) or {}
                qs = obj.get('questions') or []
            except Exception as e:
                print('  块%d 失败: %s' % (ci + 1, e))
                continue
            kept = 0
            for q in qs:
                given = (q.get('given') or '').strip()
                opts = q.get('options') or []
                ai = q.get('answerIndex')
                side = (q.get('side') or '下联').strip()
                if not given or len(opts) != 4 or not isinstance(ai, int):
                    continue
                if not (0 <= ai <= 3):
                    continue
                if side not in ('上联', '下联'):
                    side = '下联'
                all_q.append({
                    'context': (q.get('context') or '').strip(),
                    'given': given,
                    'side': side,
                    'options': [str(o).strip() for o in opts],
                    'answerIndex': ai,
                    'analysis': (q.get('analysis') or '').strip(),
                    'src': src.split('/')[-1],
                })
                kept += 1
            print('  块%d/%d 抽 %d 道' % (ci + 1, len(chunks), kept))

    seen, uniq = set(), []
    for q in all_q:
        k = q['given']
        if k in seen:
            continue
        seen.add(k)
        uniq.append(q)

    json.dump(uniq, open('对联库.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n抽到对联题 %d 道 -> 对联库.json' % len(uniq))


if __name__ == '__main__':
    main()
