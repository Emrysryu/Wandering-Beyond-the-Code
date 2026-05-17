# -*- coding: utf-8 -*-
"""从各题型 题库.json 抽前 3 条，生成对应文件夹的 示例.js（committed 进 git，让 clone 之后无需配数据就能 demo）。
本地脚本，开发者用，不会跑在用户那边。"""
import json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for folder in sorted(os.listdir(ROOT)):
    path = os.path.join(ROOT, folder, '题库.json')
    if not os.path.isfile(path):
        continue
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception:
        continue
    sample = data[:3]
    # 去掉 src 字段（含原 docx 文件名）
    for q in sample:
        q.pop('src', None)
    out = os.path.join(ROOT, folder, '示例.js')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('// 示例数据（committed 进 git，仅供 demo）。运行 generate.py 后真题库由 题库.js 接管。\n')
        f.write('window.TIMU = (window.TIMU || []).concat(')
        json.dump(sample, f, ensure_ascii=False)
        f.write(');\n')
    print('写入', out, ' ', len(sample), '条')
