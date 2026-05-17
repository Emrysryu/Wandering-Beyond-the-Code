# -*- coding: utf-8 -*-
"""
扫描含标点真题的 docx，用 DeepSeek 抽出干净的 4 选 1 标点题。
真题形式：一段话 + 【甲】【乙】挖空 + 4 个标点组合选项 + 答案字母 + 解析。
输出 标点库.json：[{passage, options:[4串], answerIndex, analysis, src}]
用法：
    python3 extract_with_ai.py
    python3 extract_with_ai.py 2     # 测试：每个 docx 只跑前 2 个块
"""
import json, sys, re, time, zipfile, urllib.request, urllib.error, os

API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
KEY = open('../deepseek_key.txt', encoding='utf-8').read().strip()

import glob as _g
BASE = '/Users/davidryu/教学/初中语文/试题/中考'
SOURCES = (
    _g.glob(BASE + '/备战2024年中考语文一轮复习考点帮（北京专用）/考点03 常考标点*解析版*.docx')
    + _g.glob(BASE + '/备战2024年中考语文考点突破（北京专用）/专题04*病句与标点*/专题04*解析版*.docx')
    + _g.glob(BASE + '/备战2024年中考语文一轮复习考点帮（北京专用）/考点02 常考语病*解析版*.docx')
    + _g.glob(BASE + '/2023/一模/分类汇编/*基础*运用*.docx')
    + _g.glob(BASE + '/2022/2022年北京各区二模*/专题01*基础知识*/专题01*解析版*.docx')
)
CHUNK_CHARS = 6000  # 每块约 6000 字交给 DeepSeek


def call_api(messages, temperature=0.0, max_retry=3):
    body = json.dumps({'model': MODEL, 'messages': messages,
                       'temperature': temperature}).encode('utf-8')
    req = urllib.request.Request(API_URL, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    last = None
    for attempt in range(max_retry):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode('utf-8'))['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            last = 'HTTP %s' % e.code
        except Exception as e:
            last = repr(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError('API 失败: ' + str(last))


def extract_json(text):
    text = re.sub(r'^```(?:json)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text)
    s, e = text.find('{'), text.rfind('}')
    if s < 0 or e < 0:
        return None
    try:
        return json.loads(text[s:e + 1])
    except Exception:
        return None


def docx_to_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    paras = []
    for p in re.split(r'</w:p>', xml):
        t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
        if t.strip():
            paras.append(t.strip())
    return '\n'.join(paras)


def chunkify(text, size=CHUNK_CHARS):
    out = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        # 尽量在段落边界切
        nl = text.rfind('\n', i + size - 800, end)
        if nl > i + 1000:
            end = nl
        out.append(text[i:end])
        i = end
    return out


PROMPT = """下面是中考语文资料的一段文本。请从中扫描出所有「标点符号选择题」，并按指定 JSON 输出。

什么是标点符号选择题——同时满足：
  ① 题干给一段话，其中有【甲】【乙】（也可能含【丙】）挖空处；
  ② 4 个选项 A/B/C/D，每个选项都是给出【甲】【乙】等位置应填的标点符号组合；
  ③ 资料给出了答案字母和解析。

跳过：阅读题、文学常识题、字音字形题、词语题、病句题、对联题、仿写题等其他题型。哪怕它们在同一段文本里，也只抽标点选择题。

注意：
- passage 里必须原样保留【甲】【乙】等占位符。
- 【关键】passage【只能是被挖空的那段连贯文字本身】，不许包含：题号（如"12."）、题干问句（如"在【甲】【乙】两处分别填入..."）、ABCD 选项行、答案、解析；这些都剥离干净。
- 4 个选项必须严格 4 个，每个是标点组合字符串，例如「【甲】句号  【乙】分号」（不要带选项前缀 A/B/C/D）。
- answerIndex 是 0-3 的整数：0=A、1=B、2=C、3=D。
- 解析 analysis 简明扼要，把原文解析压缩成 1-3 句。
- 如果整块文本里一道符合条件的题都没有，输出 {"questions":[]}。

只输出 JSON，不要 markdown，不要解释：
{"questions":[{"passage":"...","options":["...","...","...","..."],"answerIndex":0,"analysis":"..."}]}
"""


def main():
    chunk_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    all_q = []
    for src in SOURCES:
        if not os.path.exists(src):
            print('  [跳过-不存在]', src.split('/')[-1])
            continue
        text = docx_to_text(src)
        chunks = chunkify(text)
        if chunk_limit:
            chunks = chunks[:chunk_limit]
        print('=== %s （%d 块）===' % (src.split('/')[-1], len(chunks)))
        for ci, ch in enumerate(chunks):
            try:
                raw = call_api([{'role': 'user',
                                 'content': PROMPT + '\n\n资料文本：\n' + ch}])
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
                if not p or '【甲】' not in p or len(opts) != 4 or not isinstance(ai, int):
                    continue
                if not (0 <= ai <= 3):
                    continue
                # passage 不能含题目残渣
                if re.search(r'[A-D][．.][^a-zA-Z]', p) or '【答案】' in p or '【解析】' in p:
                    continue
                if '填入标点' in p or '（   ）' in p or '(   )' in p:
                    continue
                all_q.append({
                    'passage': p,
                    'options': [str(o).strip() for o in opts],
                    'answerIndex': ai,
                    'analysis': (q.get('analysis') or '').strip(),
                    'src': src.split('/')[-1],
                })
                kept += 1
            print('  块%d/%d 抽到 %d 道' % (ci + 1, len(chunks), kept))

    # 去重(按 passage)
    seen, uniq = set(), []
    for q in all_q:
        if q['passage'] in seen:
            continue
        seen.add(q['passage'])
        uniq.append(q)

    json.dump(uniq, open('标点库.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n标点真题共 %d 道（去重后），已写入 标点库.json' % len(uniq))
    for q in uniq[:2]:
        print('---'); print(q['passage'][:120])
        for i, o in enumerate(q['options']):
            print('  %s %s' % ('ABCD'[i], o))
        print('  答:', 'ABCD'[q['answerIndex']], '|', q['analysis'][:80])


if __name__ == '__main__':
    main()
