# -*- coding: utf-8 -*-
"""
语段题生成器：调 DeepSeek 批量生成中考成语辨析语段题，自检后追加进 题库.js
用法：
    python3 generate.py            # 默认新生成 30 道, 追加到现有题库
    python3 generate.py 10         # 新生成 10 道, 追加
    python3 generate.py 10 fresh   # 清空旧题库, 重新只生成 10 道
"""
import json, sys, random, re, time, os, urllib.request, urllib.error

API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
KEY = open('../deepseek_key.txt', encoding='utf-8').read().strip()  # key 在根目录, 各题型共享

L1 = open('prompt_layer1_format.txt', encoding='utf-8').read()
L2 = open('prompt_layer2_task.txt', encoding='utf-8').read()
L3 = open('prompt_layer3_voice.txt', encoding='utf-8').read()

DB_TRAP = json.load(open('chengyu_db.json', encoding='utf-8'))      # 带设误机制
DB_600  = json.load(open('chengyu_600.json', encoding='utf-8'))     # 用对的成语池
MEANING = {e['idiom']: e['meaning'] for e in DB_600}
for e in DB_TRAP:
    MEANING.setdefault(e['idiom'], e['meaning'])
# 用对的 3 个成语只从「600 高频成语」里选（易误用清单只供"用错的那一个"）
RIGHT_POOL = [e['idiom'] for e in DB_600]


def call_api(messages, temperature=1.0, max_retry=3):
    body = json.dumps({
        'model': MODEL, 'messages': messages,
        'temperature': temperature,
    }).encode('utf-8')
    req = urllib.request.Request(API_URL, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + KEY,
        'Content-Type': 'application/json',
    })
    last = None
    for attempt in range(max_retry):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            last = 'HTTP %s: %s' % (e.code, e.read().decode('utf-8', 'ignore')[:200])
        except Exception as e:
            last = repr(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError('API 调用失败: ' + str(last))


def extract_json(text):
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    s, e = text.find('{'), text.rfind('}')
    return json.loads(text[s:e + 1])


def gen_one():
    """生成一道题，自检通过返回 question dict，失败返回 None"""
    trap = random.choice(DB_TRAP)
    rights = []
    while len(rights) < 3:
        c = random.choice(RIGHT_POOL)
        if c != trap['idiom'] and c not in rights:
            rights.append(c)

    spec = (
        L2 + '\n\n' + L3 + '\n\n'
        + '【本题的 4 个成语】\n'
        + '用错的成语：%s\n' % trap['idiom']
        + '  它的意思：%s\n' % trap['meaning']
        + '  设误机制：%s\n' % trap['type']
        + '  错误示范（学会这种错法，但要放进你写的语段里）：%s\n\n' % trap['wrong']
        + '用对的 3 个成语：\n'
        + ''.join('  %s：%s\n' % (r, MEANING[r]) for r in rights)
    )
    messages = [
        {'role': 'system', 'content': L1},
        {'role': 'user', 'content': spec},
    ]
    raw = call_api(messages, temperature=1.1)
    try:
        passage = extract_json(raw)['passage'].strip()
    except Exception:
        return None

    all4 = [trap['idiom']] + rights
    if any(w not in passage for w in all4):
        return None  # 有成语没嵌进去

    # ===== 自检：让 DeepSeek 当阅卷老师判每个成语用得对不对 =====
    check_sys = '你是严格的中考语文阅卷老师，逐个判断语段中加点成语使用是否恰当。只输出 JSON，不要解释。'
    check_user = (
        '语段：\n%s\n\n' % passage
        + '请逐个判断下列成语在该语段中的使用是否恰当：\n'
        + '、'.join(all4) + '\n'
        + '输出格式：{"results":[{"idiom":"成语","ok":true或false}]}'
    )
    chk_raw = call_api(
        [{'role': 'system', 'content': check_sys},
         {'role': 'user', 'content': check_user}],
        temperature=0.0)
    try:
        results = {r['idiom']: r['ok'] for r in extract_json(chk_raw)['results']}
    except Exception:
        return None

    # 用错的那个必须被判 不恰当；用对的 3 个必须被判 恰当
    if results.get(trap['idiom'], True) is not False:
        return None
    if any(results.get(r, False) is not True for r in rights):
        return None

    # ===== 4 个成语随机排成 ABCD（不按出现顺序，避免错项位置偏置）=====
    ordered = shuffle(all4)
    options = []
    for w in ordered:
        is_trap = (w == trap['idiom'])
        options.append({
            'idiom': w,
            'meaning': trap['meaning'] if is_trap else MEANING[w],
            'correct': not is_trap,
            'trapType': trap['type'] if is_trap else '',
        })
    answer_index = ordered.index(trap['idiom'])
    return {
        'type': '成语',
        'passage': passage,
        'options': options,
        'answerIndex': answer_index,
    }


JSON_FILE = '题库.json'
JS_FILE = '题库.js'


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    fresh = len(sys.argv) > 2 and sys.argv[2] == 'fresh'

    # 追加模式: 读入现有题库
    existing = []
    if not fresh and os.path.exists(JSON_FILE):
        existing = json.load(open(JSON_FILE, encoding='utf-8'))
    seen_passages = {q['passage'] for q in existing}
    print('现有题库 %d 道，本次目标新增 %d 道%s'
          % (len(existing), n, '（fresh: 清空重建）' if fresh else ''))

    out = []
    fails = 0
    while len(out) < n and fails < n * 4:
        try:
            q = gen_one()
        except Exception as e:
            print('  [错误]', e)
            fails += 1
            continue
        if q is None:
            fails += 1
            print('  [自检未过，丢弃重来]  已成 %d / %d' % (len(out), n))
            continue
        if q['passage'] in seen_passages:   # 去重
            print('  [语段重复，丢弃]')
            continue
        seen_passages.add(q['passage'])
        out.append(q)
        print('  [%d/%d] OK  错项=%s（%s）'
              % (len(out), n, q['options'][q['answerIndex']]['idiom'],
                 q['options'][q['answerIndex']]['trapType']))

    full = existing + out
    json.dump(full, open(JSON_FILE, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    with open(JS_FILE, 'w', encoding='utf-8') as f:
        f.write('// 自动生成 by generate.py，勿手改。\n')
        f.write('// 各题型的题库.js 都往 window.TIMU 里追加，主界面汇总后出题。\n')
        f.write('window.TIMU = (window.TIMU || []).concat(')
        json.dump(full, f, ensure_ascii=False)
        f.write(');\n')
    print('完成：本次成功新增 %d 道，丢弃 %d 次。题库共 %d 道，已写入 %s'
          % (len(out), fails, len(full), JS_FILE))


if __name__ == '__main__':
    main()
