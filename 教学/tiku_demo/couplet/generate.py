# -*- coding: utf-8 -*-
"""对联题生成器（纯离线）。"""
import json, sys, random
DB = json.load(open('对联库.json', encoding='utf-8'))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(DB)
    pool = list(DB); random.shuffle(pool)
    out = []
    for s in pool[:n]:
        opts = [{'text': t, 'correct': (i == s['answerIndex'])}
                for i, t in enumerate(s['options'])]
        out.append({
            'type': '对联',
            'stem': '请选择最恰当的%s' % s.get('side', '下联'),
            'context': s.get('context', ''),
            'given': s['given'],
            'side': s.get('side', '下联'),
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
    print('写入对联题 %d 道（库共 %d）' % (len(out), len(DB)))


if __name__ == '__main__':
    main()
