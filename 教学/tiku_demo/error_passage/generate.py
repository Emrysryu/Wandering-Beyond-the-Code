# -*- coding: utf-8 -*-
"""病句·语段版 题生成器（纯离线）。选项顺序对应①②③④，不能洗牌。"""
import json, sys, random

DB = json.load(open('病句语段库.json', encoding='utf-8'))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(DB)
    pool = list(DB); random.shuffle(pool)
    out = []
    for s in pool[:n]:
        opts = []
        for i, sentence in enumerate(s['options']):
            opts.append({
                'sentence': sentence,
                'correct': (i != s['answerIndex']),
            })
        out.append({
            'type': '病句语段',
            'stem': '下列文段中标号句子有语病的一项是',
            'passage': s['passage'],
            'options': opts,
            'answerIndex': s['answerIndex'],   # 与①②③④ 顺序绑定，HTML 不再洗牌
            'analysis': s.get('analysis', ''),
            'fix': s.get('fix', ''),
            'fixedOrder': True,
        })
    json.dump(out, open('题库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open('题库.js', 'w', encoding='utf-8') as f:
        f.write('// 自动生成 by generate.py（纯离线），勿手改。\n')
        f.write('window.TIMU = (window.TIMU || []).concat(')
        json.dump(out, f, ensure_ascii=False)
        f.write(');\n')
    print('写入病句·语段题 %d 道（库共 %d）' % (len(out), len(DB)))


if __name__ == '__main__':
    main()
