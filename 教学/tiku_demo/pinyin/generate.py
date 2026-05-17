# -*- coding: utf-8 -*-
"""
字音字形题生成器（纯离线，不调 API）。
题型：下列加点字注音和词语书写全都正确的一项 —— 4 选 1。
  每个选项 = 一个「例词(注音)」+ 一个「词语」
  全对的一项 = 注音正确 且 词语书写正确
数据全部来自本地库，瞬间生成、零成本、可靠。
用法：
    python3 generate.py            # 默认生成 150 题（覆盖式）
    python3 generate.py 80         # 生成 80 题
"""
import json, sys, random

YIN = json.load(open('字音库.json', encoding='utf-8'))
XING = json.load(open('字形库.json', encoding='utf-8'))            # 错词+正字
XING_REVIEW = json.load(open('字形库_待定.json', encoding='utf-8'))  # 正词(错字)，正词可当"正确词"用

# ---- 字音可用池：必须能凑出"错误读音" ----
YIN_USABLE = [e for e in YIN if e.get('wrong_reading') and len(e['context']) >= 2]
# 多音字：同字的另一个读音可当错误读音
duo = {}
for e in YIN:
    if e['src'] == '要点三·多音字' and len(e['context']) >= 2:
        duo.setdefault(e['item'], []).append(e)
for ch, lst in duo.items():
    if len(lst) >= 2:
        for e in lst:
            others = [x['reading'] for x in lst if x['reading'] != e['reading']]
            if others:
                YIN_USABLE.append({**e, 'wrong_reading': others[0]})

# ---- 正确词池（给字形选项当"书写正确"的词）----
# 来源：字音库的例词、字形待定库里的正确成语
CORRECT_WORDS = list({e['context'] for e in YIN if len(e['context']) >= 2})
CORRECT_WORDS += list({e['right_form'] for e in XING_REVIEW if len(e['right_form']) >= 2})
CORRECT_WORDS = list(set(CORRECT_WORDS))

LETTERS = ['A', 'B', 'C', 'D']


def make_question():
    yin = random.choice(YIN_USABLE)
    xing = random.choice(XING)
    wrong_word = xing['wrong_form']
    # 正确词：随便挑一个已知正确的词，且不能跟错词一样
    while True:
        right_word = random.choice(CORRECT_WORDS)
        if right_word != wrong_word:
            break

    # 4 个组合：{对音,错音} × {正确词,错词}
    combos = []
    for rd, rd_ok in [(yin['reading'], True), (yin['wrong_reading'], False)]:
        for w, w_ok in [(right_word, True), (wrong_word, False)]:
            combos.append({
                'word_yin': yin['context'],   # 注音考查的例词
                'char': yin['item'],          # 加点字
                'reading': rd,
                'word_xing': w,               # 字形考查的词语
                'reading_ok': rd_ok,
                'word_ok': w_ok,
                'correct': rd_ok and w_ok,
            })
    random.shuffle(combos)
    answer = next(i for i, c in enumerate(combos) if c['correct'])
    return {
        'type': '字音字形',
        'stem': '下列加点字的注音和词语的书写，全都正确的一项是',
        'options': combos,
        'answerIndex': answer,
        'explain': {
            'yin': '「%s」在「%s」中读 %s（误读为 %s）'
                   % (yin['item'], yin['context'], yin['reading'], yin['wrong_reading']),
            'xing': '「%s」是错误写法，其中一个字应改成「%s」；「%s」书写正确'
                    % (wrong_word, xing['right_char'], right_word),
            'yin_src': yin['src'],
        },
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    seen = set()
    out = []
    guard = 0
    while len(out) < n and guard < n * 20:
        guard += 1
        q = make_question()
        key = (q['options'][q['answerIndex']]['word_yin'],
               q['explain']['xing'])
        if key in seen:
            continue
        seen.add(key)
        out.append(q)

    json.dump(out, open('题库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open('题库.js', 'w', encoding='utf-8') as f:
        f.write('// 自动生成 by generate.py（纯离线），勿手改。\n')
        f.write('window.TIMU = (window.TIMU || []).concat(')
        json.dump(out, f, ensure_ascii=False)
        f.write(');\n')
    print('生成字音字形题 %d 道，已写入 题库.js' % len(out))
    print('字音可用池 %d 条，字形错词库 %d 条，正确词池 %d 条'
          % (len(YIN_USABLE), len(XING), len(CORRECT_WORDS)))
    print('--- 样例 ---')
    for q in out[:2]:
        print(q['stem'])
        for i, c in enumerate(q['options']):
            print('  %s %s(%s)  %s  %s' % (LETTERS[i], c['word_yin'], c['reading'],
                                            c['word_xing'], '★' if c['correct'] else ''))
        print('  ', q['explain']['yin'], '|', q['explain']['xing'])


if __name__ == '__main__':
    main()
