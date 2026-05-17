# -*- coding: utf-8 -*-
"""
从「考点02 常考语病类型（解析版）」docx 解析出病句库。
docx 正文是表格：直接按 表格行<w:tr> / 单元格<w:tc> 解析，每行 = [类型, 病例, 诊断修改]。
输出 病句库.json：{sentence(病句), type(大类), subtype, diagnosis, correct(能抽到的正确句)}
解析必有零星错，跑完请抽查。
"""
import zipfile, re, json, glob

path = (glob.glob('考点02*.docx') or glob.glob('*.docx'))[0]
with zipfile.ZipFile(path) as z:
    xml = z.read('word/document.xml').decode('utf-8')


def cell_text(tc_xml):
    # 一个单元格里所有段落文字，按段落用换行连起来
    paras = []
    for p in re.split(r'</w:p>', tc_xml):
        t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
        if t.strip():
            paras.append(t.strip())
    return '\n'.join(paras)


def row_cells(tr_xml):
    return [cell_text(tc) for tc in re.findall(r'<w:tc>.*?</w:tc>', tr_xml, re.S)]


# 正文里穿插着「模块N + 类型名」的标题段落，和一个个表格。
# 策略：顺序扫描 document.xml，遇到「模块标题」记下当前大类，遇到 <w:tbl> 解析其行。
big_type = ''
entries = []

# 把 document body 按 模块标题段 和 表格 切块，顺序处理
# 先拿到所有「模块」标题文字出现的位置
tokens = re.split(r'(<w:tbl>.*?</w:tbl>)', xml, flags=re.S)
for tok in tokens:
    if tok.startswith('<w:tbl>'):
        # 表格：逐行
        for tr in re.findall(r'<w:tr\b.*?</w:tr>', tok, re.S):
            cells = row_cells(tr)
            if len(cells) < 3:
                continue
            # 病例和诊断永远是最后两列；前面的所有列拼起来当子类型(模块一是4列, 其余3列)
            c_case, c_diag = cells[-2], cells[-1]
            c_type = ' · '.join(c.strip() for c in cells[:-2] if c.strip())
            if c_case == '病例呈现' or c_diag == '诊断修改':
                continue  # 表头行
            subs = [x for x in c_type.split('\n') if x.strip()]
            cases = [x for x in c_case.split('\n') if x.strip()]
            diags = [x for x in c_diag.split('\n') if x.strip()]
            n = max(len(cases), 1)
            for i in range(n):
                case = cases[i] if i < len(cases) else (cases[-1] if cases else '')
                diag = diags[i] if i < len(diags) else (diags[-1] if diags else '')
                sub = subs[i] if i < len(subs) else (subs[0] if subs else '')
                if len(case) < 6:
                    continue
                entries.append({'sentence': case, 'type': big_type,
                                 'subtype': re.sub(r'^\d+\s*[、.]\s*', '', sub),
                                 'diagnosis': diag})
    else:
        # 普通段落块：找最后一个「模块N」后面的类型名
        paras = []
        for p in re.split(r'</w:p>', tok):
            t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
            if t.strip():
                paras.append(t.strip())
        for k, ln in enumerate(paras):
            if re.match(r'^模块[一二三四五六]$', ln):
                # 类型名 = 后面第一个非「模块N」段
                for nxt in paras[k + 1:]:
                    if not re.match(r'^模块', nxt):
                        big_type = nxt
                        break


def extract_correct(diag):
    for pat in (r'应?改为[:：]\s*([^"”。\n]+)',
                r'应?改为[“"]([^"”]+)[”"]',
                r'可改为[:：]\s*([^"”。\n]+)'):
        m = re.search(pat, diag)
        if m:
            c = m.group(1).strip().rstrip('。')
            if len(c) >= 6:
                return c + '。'
    return ''


# 去重 + 抽正确句
seen = set()
uniq = []
for e in entries:
    s = e['sentence']
    if s in seen or len(s) > 120:
        continue
    seen.add(s)
    e['correct'] = extract_correct(e['diagnosis'])
    uniq.append(e)

json.dump(uniq, open('病句库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

from collections import Counter
print('解析出病句条目:', len(uniq))
print('  能抽到完整正确句的:', sum(1 for e in uniq if e['correct']))
for t, c in Counter(e['type'] for e in uniq).items():
    print('  %-16s %d' % (t or '(无类型)', c))
print('--- 样例 ---')
for e in uniq[:8]:
    print(json.dumps(e, ensure_ascii=False))
