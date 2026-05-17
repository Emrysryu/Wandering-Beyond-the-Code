# -*- coding: utf-8 -*-
"""扫真题 docx，抽出「词语（语境填词）4 选 1」真题。
形式：一段话有 1~3 处挖空（用 ①② 或 ____），4 个选项给挖空处的词语组合。
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
    + _g.glob(BASE + '/**/*考点02*解析版*.docx', recursive=True)
)
SOURCES = list(set(SOURCES))[:14]   # 去重，限上限
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


PROMPT = """从下面的中考语文资料里，扫出「词语（语境填词）选择题」——形式特征：

  ① 一段连贯的话，里面有 1~3 处挖空，挖空处用 ①② 或 横线 ______ 标记；
  ② 4 个选项分别给挖空处填入的词语组合（如「A. ①耳濡目染 ②仿照」「B. ①耳熟能详 ②按照」）；
  ③ 资料给出了答案字母和解析。

跳过：
  ✗ 标点选择题（选项是标点）
  ✗ 字音字形题（选项是注音或单字字形对错）
  ✗ 病句、修改题、补写、对联、古诗默写
  ✗ 翻译、文学常识

为每题输出：
- passage：完整语段，保留挖空处原样标记（① / ② / ______）。passage 至少 80 字。
- options：4 个字符串，每个是一种填词组合（含 ①② 等前缀），例如「①耳濡目染 ②仿照」。
- answerIndex：0-3 整数。
- analysis：简短解析（说明每个词的含义差别，1-2 句）。

只输出 JSON：
{"questions":[{"passage":"...","options":["...","...","...","..."],"answerIndex":0,"analysis":"..."}]}
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
                p = (q.get('passage') or '').strip()
                opts = q.get('options') or []
                ai = q.get('answerIndex')
                if not p or len(p) < 80 or len(opts) != 4 or not isinstance(ai, int):
                    continue
                if not (0 <= ai <= 3):
                    continue
                # 挖空：①/② 或 ______
                if '①' not in p and '______' not in p and '____' not in p:
                    continue
                all_q.append({
                    'passage': p,
                    'options': [str(o).strip() for o in opts],
                    'answerIndex': ai,
                    'analysis': (q.get('analysis') or '').strip(),
                    'src': src.split('/')[-1],
                })
                kept += 1
            print('  块%d/%d 抽 %d 道' % (ci + 1, len(chunks), kept))

    seen, uniq = set(), []
    for q in all_q:
        k = q['passage'][:80]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(q)

    json.dump(uniq, open('词语库.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n抽到词语题 %d 道 -> 词语库.json' % len(uniq))


if __name__ == '__main__':
    main()
