# -*- coding: utf-8 -*-
"""
用 DeepSeek 把病句素材补成 {病句, 正确句, 类型, 子类型} 的成对结构。
两件事一起做：
  ① 给已有 病句库.json 里没有 correct 的条目补"修改后正确句"
  ② 扫 xlsx 真题（每条带答案+解析），把里面的画线病句和修改后版本提取出来
最后合并成 病句库_全.json（每条一定有 sentence + correct + type）。

用法：
    python3 extract_with_ai.py          # 全跑
    python3 extract_with_ai.py 5        # 测试：xlsx 只跑前 5 条
"""
import json, sys, re, html, time, os, zipfile, urllib.request, urllib.error

API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
KEY = open('../deepseek_key.txt', encoding='utf-8').read().strip()


def call_api(messages, temperature=0.0, max_retry=3):
    body = json.dumps({'model': MODEL, 'messages': messages,
                       'temperature': temperature}).encode('utf-8')
    req = urllib.request.Request(API_URL, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    last = None
    for attempt in range(max_retry):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
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


# ============= ① 补全 考点02 清单里没正确句的条目 =============
def enrich_existing():
    db = json.load(open('病句库.json', encoding='utf-8'))
    out = []
    for i, e in enumerate(db):
        if e.get('correct'):
            out.append(e)
            continue
        prompt = (
            '我有一个病句和它的诊断说明，请你给出修改后的正确句子。\n'
            '病句：%s\n诊断：%s\n类型：%s（%s）\n\n'
            '只输出 JSON：{"correct":"修改后完整正确的句子（一句话）"}'
            % (e['sentence'], e['diagnosis'], e['type'], e.get('subtype', ''))
        )
        try:
            raw = call_api([{'role': 'user', 'content': prompt}])
            obj = extract_json(raw) or {}
            c = (obj.get('correct') or '').strip()
            if len(c) >= 6:
                e['correct'] = c if c.endswith(('。', '？', '！')) else c + '。'
                print('  [补%d/%d] %s -> %s' % (i + 1, len(db), e['sentence'][:30], e['correct'][:40]))
        except Exception as ex:
            print('  [补失败]', ex)
        out.append(e)
    return out


# ============= ② 从 xlsx 真题提取病句对 =============
def read_xlsx(path):
    with zipfile.ZipFile(path) as z:
        sh = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
    rows = re.findall(r'<row\b[^>]*>(.*?)</row>', sh, re.S)
    out = []
    for row in rows:
        vals = []
        for cm in re.finditer(r'<c\b([^>]*)>(.*?)</c>', row, re.S):
            attrs, inner = cm.group(1), cm.group(2)
            tm = re.search(r'\bt="(\w+)"', attrs)
            t = tm.group(1) if tm else ''
            if t == 'inlineStr':
                ts = re.findall(r'<t[^>]*>([^<]*)</t>', inner)
                vals.append(html.unescape(''.join(ts)))
            else:
                m = re.search(r'<v>([^<]*)</v>', inner)
                vals.append(m.group(1) if m else '')
        out.append(vals)
    return out


def extract_xlsx_entries(limit=None):
    rows = read_xlsx('病句真题_答案解析提取_修正版.xlsx')
    rows = [r for r in rows if len(r) >= 6 and r[3] and r[4]]  # 去表头/空行
    rows = rows[1:]  # 跳表头
    if limit:
        rows = rows[:limit]
    out = []
    for i, r in enumerate(rows):
        stem, answer, analysis = r[3], r[4], r[5]
        prompt = (
            '下面是一道中考病句修改题的题干、答案和解析。请你抽出题目里被改的【原病句】和【修改后的正确句】。'
            '题干可能含很长情境，只抽病句本身；如果题目里有多个画线句被改，每个都抽。\n\n'
            '题干：%s\n答案：%s\n解析：%s\n\n'
            '只输出 JSON，不要 markdown：\n'
            '{"pairs":[{"sentence":"原病句一句话","correct":"修改后一句话",'
            '"type":"语序不当/搭配不当/成分残缺/结构混乱/表意不明/不合逻辑/用词不当 中的一种"}]}'
            % (stem[:1500], answer[:400], analysis[:1500])
        )
        try:
            raw = call_api([{'role': 'user', 'content': prompt}])
            obj = extract_json(raw) or {}
            for p in (obj.get('pairs') or []):
                s = (p.get('sentence') or '').strip()
                c = (p.get('correct') or '').strip()
                t = (p.get('type') or '').strip()
                if len(s) < 8 or len(c) < 8:
                    continue
                if not s.endswith(('。', '？', '！')):
                    s += '。'
                if not c.endswith(('。', '？', '！')):
                    c += '。'
                out.append({'sentence': s, 'correct': c, 'type': t,
                            'subtype': '', 'diagnosis': '',
                            'src': 'xlsx真题'})
            print('  [%d/%d] 抽到 %d 对' % (i + 1, len(rows), len(obj.get('pairs') or [])))
        except Exception as ex:
            print('  [%d 失败]' % (i + 1), ex)
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print('=== ① 补全考点02 清单缺失的正确句 ===')
    enriched = enrich_existing()
    print('=== ② 从 xlsx 真题提取病句对 ===')
    xlsx_entries = extract_xlsx_entries(limit)

    # 合并 + 去重(按 sentence)
    seen = set()
    merged = []
    for e in enriched + xlsx_entries:
        s = e['sentence']
        if s in seen or not e.get('correct'):
            continue
        seen.add(s)
        merged.append(e)

    json.dump(merged, open('病句库_全.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n合并后病句库（带正确句）共 %d 条 -> 病句库_全.json' % len(merged))
    from collections import Counter
    for t, c in Counter(e.get('type', '') for e in merged).items():
        print('  %-12s %d' % (t or '(无类型)', c))


if __name__ == '__main__':
    main()
