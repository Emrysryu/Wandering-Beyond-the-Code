# -*- coding: utf-8 -*-
"""扫真题 docx，抽出「一段话里多个标号句选有语病的一项」这种语段版病句题。"""
import json, sys, re, time, zipfile, urllib.request, urllib.error, os, glob as _g

API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
KEY = open('../deepseek_key.txt', encoding='utf-8').read().strip()

BASE = '/Users/davidryu/教学/初中语文/试题/中考'
SOURCES = (
    _g.glob(BASE + '/备战2024年中考语文一轮复习考点帮（北京专用）/考点02 常考语病*解析版*.docx')
    + _g.glob(BASE + '/备战2024年中考语文真题题源解密（北京专用）/专题03 病句修改*解析版*.docx')
    + _g.glob(BASE + '/备战2024年中考语文考点突破（北京专用）/专题04*病句与标点*/专题04*解析版*.docx')
    + _g.glob(BASE + '/5年*中考1年模拟*汇编*/专题04*病句*标点*/专题04*解析版*.docx')
    + _g.glob(BASE + '/2026年中考语文一轮复习讲练测/第03讲*病句*/第03讲*解析版*.docx')
    + _g.glob(BASE + '/2024年中考语文*热点*难点*/热点/热点03*病句*解析版*.docx')
    + _g.glob(BASE + '/2025年中考语文二轮*/专题04*病句辨析*/专题04*解析版*.docx')
)
CHUNK = 6500
OVERLAP = 1500


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


PROMPT = """从下面的中考语文资料里，扫出「语段版病句题」——形式特征：

  ① 题干给一段完整的话（通常 150~400 字），围绕一个主题；
  ② 段里有 4 处明确标号的句子，标号用 ①②③④ 或 (1)(2)(3)(4) 或 [1][2][3][4]；
  ③ 4 个选项分别对应这 4 句，问哪一句有语病；
  ④ 资料给出了答案字母（A/B/C/D 或①②③④）和解析。

跳过：
  ✗ 单句病句 4 选 1（4 个独立句子选有语病的一项，没有共同语段的）
  ✗ 修改题（画线句改写、写出修改方案）
  ✗ 选择"没有语病的一项"（只要句子，没有共同语段串起来的）
  ✗ 其他题型

为每题输出：
- passage：完整语段，里面的 4 句话前要原样保留 ①②③④ 标号（如果原文用 (1) 等其他标号，统一替换成 ①②③④）。
- options：4 句话，从语段里抽出，分别对应①②③④。每项是完整一句话，不带①等编号。
- answerIndex：0~3 整数，对应①②③④中哪一句有语病。
- analysis：把原文解析压成 1-3 句（说明哪句病、是什么类型）。
- fix：修改后的正确句（若解析里有）。

只输出 JSON：
{"questions":[{"passage":"...","options":["...","...","...","..."],"answerIndex":0,"analysis":"...","fix":"..."}]}
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
                if not p or len(opts) != 4 or not isinstance(ai, int) or not (0 <= ai <= 3):
                    continue
                if len(p) < 100:
                    continue
                if not all('①' in p or '②' in p or '③' in p or '④' in p for _ in [0]):
                    continue
                marks = sum(p.count(m) for m in '①②③④')
                if marks < 4:
                    continue
                all_q.append({
                    'passage': p,
                    'options': [str(o).strip() for o in opts],
                    'answerIndex': ai,
                    'analysis': (q.get('analysis') or '').strip(),
                    'fix': (q.get('fix') or '').strip(),
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

    json.dump(uniq, open('病句语段库.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n抽到 %d 道（去重）-> 病句语段库.json' % len(uniq))
    for q in uniq[:1]:
        print('---'); print(q['passage'][:200]+'...')
        for i, o in enumerate(q['options']):
            print('  %s %s' % ('ABCD'[i], o[:60]))
        print('  答:', 'ABCD'[q['answerIndex']], '|', q['analysis'][:80])


if __name__ == '__main__':
    main()
