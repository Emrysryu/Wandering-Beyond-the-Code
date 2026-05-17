# -*- coding: utf-8 -*-
"""
病句 4 选 1 题生成器（纯离线，不调 API）。
题型：下列句子中有语病的一项是 —— 1 个病句 + 3 个别的病句"改后的正确句" 作干扰。
数据来自 病句库_全.json（每条都有 sentence + correct）。
用法：
    python3 generate.py            # 默认 100 题
    python3 generate.py 50         # 50 题
"""
import json, sys, random, re

# —— 清理：去掉句子里「只是语法术语标注」的括号，保留信息性括号 ——
GRAMMAR_TERMS = {
    '表领属', '表时间', '表处所', '表对象', '表范围', '表状态', '表程度',
    '数量', '名词', '动词', '形容词', '副词', '代词', '介词', '连词', '助词', '量词', '虚词',
    '名词短语', '动词短语', '形容词短语', '介词短语', '名词性', '动词性',
    '主语', '谓语', '宾语', '定语', '状语', '补语', '中心语',
    '并列', '修饰', '限制',
}
def clean(s):
    if not s: return s
    # 中文/英文括号里如果只含语法术语，整段去掉
    def rep(m):
        inner = m.group(1).strip()
        return '' if inner in GRAMMAR_TERMS else m.group(0)
    s = re.sub(r'（([^（）]{1,8})）', rep, s)
    s = re.sub(r'\(([^()]{1,8})\)', rep, s)
    # 去掉多余空格
    return re.sub(r'\s+', '', s).strip()

raw = json.load(open('病句库_全.json', encoding='utf-8'))
DB = []
for e in raw:
    e['sentence'] = clean(e.get('sentence', ''))
    e['correct'] = clean(e.get('correct', ''))
    if e['correct'] and 8 <= len(e['sentence']) <= 80 and 8 <= len(e['correct']) <= 80:
        DB.append(e)
CORRECT_POOL = [e['correct'] for e in DB]


def make_question():
    wrong = random.choice(DB)
    # 3 个正确句：从其他条目的 correct 抽，不能跟病句本身或彼此重复
    rights = []
    tries = 0
    while len(rights) < 3 and tries < 30:
        tries += 1
        c = random.choice(CORRECT_POOL)
        if c == wrong['sentence'] or c == wrong['correct'] or c in rights:
            continue
        rights.append(c)
    if len(rights) < 3:
        return None
    options = [{'sentence': wrong['sentence'], 'correct': False,
                'btype': wrong.get('type', ''), 'subtype': wrong.get('subtype', ''),
                'fix': wrong['correct'], 'diagnosis': wrong.get('diagnosis', '')}]
    for r in rights:
        options.append({'sentence': r, 'correct': True})
    random.shuffle(options)
    return {
        'type': '病句',
        'stem': '下列句子中有语病的一项是',
        'options': options,
        'answerIndex': next(i for i, o in enumerate(options) if not o['correct']),
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    out = []
    seen = set()
    guard = 0
    while len(out) < n and guard < n * 30:
        guard += 1
        q = make_question()
        if not q:
            continue
        wrong = q['options'][q['answerIndex']]['sentence']
        if wrong in seen:
            continue
        seen.add(wrong)
        out.append(q)
    json.dump(out, open('题库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open('题库.js', 'w', encoding='utf-8') as f:
        f.write('// 自动生成 by generate.py（纯离线），勿手改。\n')
        f.write('window.TIMU = (window.TIMU || []).concat(')
        json.dump(out, f, ensure_ascii=False)
        f.write(');\n')
    print('生成病句题 %d 道，已写入 题库.js（病句库共 %d 条可用）'
          % (len(out), len(DB)))
    if out:
        q = out[0]
        print('--- 样例 ---')
        print(q['stem'])
        for i, o in enumerate(q['options']):
            mark = '★病' if not o['correct'] else ''
            print('  %s %s %s' % ('ABCD'[i], o['sentence'][:60], mark))
        ans = q['options'][q['answerIndex']]
        print('  解析:', ans.get('btype'), '|', ans.get('subtype'), '|', '改→', ans.get('fix'))


if __name__ == '__main__':
    main()
