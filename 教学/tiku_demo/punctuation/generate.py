# -*- coding: utf-8 -*-
"""
标点 4 选 1 生成器（纯离线）。
标点真题已经是 4 选 1 形式，这里只做"洗牌选项 + 写题库.js"。
用法：
    python3 generate.py           # 全部入题库
    python3 generate.py 30        # 只取 30 道
"""
import json, sys, random

DB = json.load(open('标点库.json', encoding='utf-8'))


def make_question(src):
    # 把 4 个选项配上 correct 标记（保留生成器侧的 answerIndex 给 HTML 洗牌追踪）
    opts = []
    for i, txt in enumerate(src['options']):
        opts.append({
            'text': txt,
            'correct': (i == src['answerIndex']),
        })
    return {
        'type': '标点',
        'stem': '在【甲】【乙】两处分别填入标点符号，最恰当的一项是',
        'passage': src['passage'],
        'options': opts,
        'answerIndex': src['answerIndex'],
        'analysis': src.get('analysis', ''),
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(DB)
    pool = list(DB)
    random.shuffle(pool)
    out = [make_question(s) for s in pool[:n]]
    json.dump(out, open('题库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open('题库.js', 'w', encoding='utf-8') as f:
        f.write('// 自动生成 by generate.py（纯离线），勿手改。\n')
        f.write('window.TIMU = (window.TIMU || []).concat(')
        json.dump(out, f, ensure_ascii=False)
        f.write(');\n')
    print('写入标点题 %d 道（库共 %d 道）' % (len(out), len(DB)))


if __name__ == '__main__':
    main()
