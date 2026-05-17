# -*- coding: utf-8 -*-
"""词语题生成器（纯离线）。真题已是 4 选 1，仅做格式转换。"""
import json, sys, random
DB = json.load(open('词语库.json', encoding='utf-8'))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(DB)
    pool = list(DB); random.shuffle(pool)
    out = []
    for s in pool[:n]:
        opts = [{'text': t, 'correct': (i == s['answerIndex'])}
                for i, t in enumerate(s['options'])]
        out.append({
            'type': '词语',
            'stem': '依次填入文中横线处的词语，最恰当的一项是',
            'passage': s['passage'],
            'options': opts,
            'answerIndex': s['answerIndex'],
            'analysis': s.get('analysis', ''),
        })
    json.dump(out, open('题库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open('题库.js', 'w', encoding='utf-8') as f:
        f.write('// 自动生成 by generate.py（纯离线），勿手改。\n')
        f.write('window.TIMU = (window.TIMU || []).concat(')
        json.dump(out, f, ensure_ascii=False)
        f.write(');\n')
    print('写入词语题 %d 道（库共 %d）' % (len(out), len(DB)))


if __name__ == '__main__':
    main()
