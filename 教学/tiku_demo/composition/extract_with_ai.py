# -*- coding: utf-8 -*-
"""
扫真题 docx，用 DeepSeek 抽出「仿写/补写」开放题。
每题：{context(语境/例句), task(任务说明), references(2-3 条参考答案), kind('仿写'|'补写')}
"""
import json, sys, re, time, zipfile, urllib.request, urllib.error, os, glob as _g

API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
KEY = open('../deepseek_key.txt', encoding='utf-8').read().strip()

BASE = '/Users/davidryu/教学/初中语文/试题/中考'
SOURCES = (
    _g.glob(BASE + '/备战2024年中考语文真题题源解密（北京专用）/专题04 句子补写*解析版*.docx')
    + _g.glob(BASE + '/5年*中考1年模拟*汇编*北京*/专题06*衔接*补写*仿写*/专题06*解析版*.docx')
    + _g.glob(BASE + '/备战2024年中考语文考点突破（北京专用）/专题07*基础综合*/专题07*解析版*.docx')
    + _g.glob(BASE + '/2024中考语文重难考点通关训练*/专题01：基础运用*解析版*.docx')
    + _g.glob(BASE + '/5年*中考1年模拟*汇编*/专题07*基础综合*/专题07*解析版*.docx')
)
CHUNK_CHARS = 6500


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


def docx_to_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    paras = []
    for p in re.split(r'</w:p>', xml):
        t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
        if t.strip():
            paras.append(t.strip())
    return '\n'.join(paras)


def chunkify(text, size=CHUNK_CHARS, overlap=1500):
    out, i = [], 0
    while i < len(text):
        end = min(i + size, len(text))
        nl = text.rfind('\n', i + size - 800, end)
        if nl > i + 1000:
            end = nl
        out.append(text[i:end])
        if end >= len(text):
            break
        i = max(end - overlap, i + 1)   # 下一块往回退 overlap 字符
    return out


PROMPT = """从下面的中考语文资料文本中，扫出所有「仿写题」或「补写题」开放题。

定义：
- 仿写题：给一个例句/画线句，要求按相同句式/修辞另写一句。
- 补写题：给一段话，里面有横线或挖空，要求补写一个分句/句子使文意连贯。
- 这两种题答案不唯一，是开放题。

跳过：选择题、字音字形题、词语解释、修改病句、默写古诗文（背诗句填空）、对联题。

为每题输出：
- kind：仿写 或 补写
- context：【这是最关键的字段】
  · 补写题：必须把【整段被挖空的语段】完整抽出来（学生没有上下文就没法填空）。原文若有上文铺垫、挖空所在段落、下文承接，都要包含。补写题 context 长度通常 150~600 字。挖空处用「______」（六个下划线）。
  · 仿写题：必须包含被仿照的例句（画线句）以及紧邻的上下文（让学生明白仿照什么句式、表达什么主题）。
  · ❌ 不要只抽题目编号或任务说明、把"请补写一句话"那种当 context。task 字段才放任务说明。
  · ❌ 不要拿"编审即将结束"或纯描述性的题目背景当 context。
- task：任务说明（一句话总结要求，例如「在【乙】处补写一句话，用上"感恩、学习、辉煌"，向同学发出倡议」）。不要把语段塞进 task。
- references：从【答案】里取出的参考答案，2-3 条最好；少于 2 条也可以；如果原文只给了一条「示例：」就只放一条。每条是完整可作答的一句话。

如果资料块里这道题的语段被切到上一块去了、当前块只有题目尾部和答案，那就跳过这道题（输出空 questions）。宁可少抽，不要抽残缺的。

只输出 JSON，不要 markdown：
{"questions":[{"kind":"补写","context":"...","task":"...","references":["...","..."]}]}
"""


def main():
    chunk_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    all_q = []
    for src in SOURCES:
        if not os.path.exists(src):
            continue
        text = docx_to_text(src)
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
                ctx = (q.get('context') or '').strip()
                task = (q.get('task') or '').strip()
                refs = [str(r).strip() for r in (q.get('references') or []) if r and str(r).strip()]
                kind = (q.get('kind') or '').strip()
                if not ctx or not task or not refs or kind not in ('仿写', '补写'):
                    continue
                # 补写题：context 必须 >=120 字且含挖空
                if kind == '补写' and (len(ctx) < 120 or '______' not in ctx):
                    continue
                # 仿写题：context 必须 >=40 字（要含被仿照的句子）
                if kind == '仿写' and len(ctx) < 40:
                    continue
                if len(task) < 4:
                    continue
                all_q.append({'kind': kind, 'context': ctx, 'task': task,
                              'references': refs[:3], 'src': src.split('/')[-1]})
                kept += 1
            print('  块%d/%d 抽到 %d 道' % (ci + 1, len(chunks), kept))

    seen, uniq = set(), []
    for q in all_q:
        k = q['context'][:60]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(q)

    json.dump(uniq, open('仿写补写库.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    from collections import Counter
    print('\n抽到 %d 道（去重）-> 仿写补写库.json' % len(uniq))
    for k, c in Counter(q['kind'] for q in uniq).items():
        print('  %s %d' % (k, c))
    for q in uniq[:2]:
        print('---'); print('[%s] %s' % (q['kind'], q['task'])); print(q['context'][:120])
        for r in q['references']: print('  参考:', r[:80])


if __name__ == '__main__':
    main()
