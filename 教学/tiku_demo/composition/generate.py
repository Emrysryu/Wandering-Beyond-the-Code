# -*- coding: utf-8 -*-
"""仿写/补写开放题生成器（纯离线）。直接把库里每条转成题，写 题库.js。"""
import json, sys, random

DB = json.load(open('仿写补写库.json', encoding='utf-8'))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(DB)
    pool = list(DB)
    random.shuffle(pool)
    out = []
    for s in pool[:n]:
        out.append({
            'type': '仿写补写',
            'kind': s['kind'],
            'context': s['context'],
            'task': s['task'],
            'references': s['references'],
        })
    json.dump(out, open('题库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open('题库.js', 'w', encoding='utf-8') as f:
        f.write('// 自动生成 by generate.py（纯离线），勿手改。\n')
        f.write('window.TIMU = (window.TIMU || []).concat(')
        json.dump(out, f, ensure_ascii=False)
        f.write(');\n')
    print('写入仿写补写题 %d 道（库共 %d）' % (len(out), len(DB)))


if __name__ == '__main__':
    main()
