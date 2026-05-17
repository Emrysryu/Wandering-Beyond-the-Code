# -*- coding: utf-8 -*-
"""
从 docx 知识清单 + 易错字汇总.txt 解析出两个结构化库：
  字音库.json  —  {item, reading, wrong_reading, context, src}
  字形库.json  —  错别字混淆对，统一成 {wrong_form, right_char, src}
                  （正词→错字 的条目会先转成 错词→正字 再入库；转不了的标记出来）
解析必有零星错，跑完请人工抽查。
"""
import zipfile, re, json, glob

# ---------- 从 docx 提取纯文本（按段落分行）----------
docx_path = glob.glob('专题02*.docx')[0]
with zipfile.ZipFile(docx_path) as z:
    xml = z.read('word/document.xml').decode('utf-8')
lines = []
for p in re.split(r'</w:p>', xml):
    t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))
    if t.strip():
        lines.append(t.strip())
full = '\n'.join(lines)

# 拼音字符（含声调）—— 只是字符集内容，用到时再套 [ ]
PY = 'a-zü' + 'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ' + 'ńňǹ'
P1 = '[' + PY + ']'          # 单个拼音字符
PYL = P1 + '+'               # 一个音节
PYWORD = PYL + r'(?:\s' + PYL + r')*'   # 一个或多个音节（空格分隔）

def section(text, start_marker, end_marker=None):
    s = text.find(start_marker)
    if s < 0:
        return ''
    s += len(start_marker)
    e = text.find(end_marker, s) if end_marker else len(text)
    return text[s:e if e > 0 else len(text)]

# ================= 字音库 =================
yin = []

# --- 要点一：习惯易误读 —— 成对行：例词行 + 说明行 ---
sec1 = section(full, '中考字音考查要点一：常见常用但习惯上易误读的字音',
                     '中考字音考查要点二：')
sl = [x for x in sec1.split('\n') if x.strip()
      and x not in ('易误读字音', '读音说明')]
i = 0
while i < len(sl):
    m = re.match(r'\d+\.\s*(.+)', sl[i])
    if m and i + 1 < len(sl):
        examples = m.group(1)
        note = sl[i + 1]
        # 例词里抓 字（pinyin）
        for em in re.finditer(r'([一-龥])（(' + PYL + r')）', examples):
            ch, rd = em.group(1), em.group(2)
            # 说明里抓「不读X」或「没有X这个读音」
            wm = re.search(r'不读(' + PYWORD + r')', note) \
                 or re.search(r'没有(' + PYL + r')这个读音', note)
            wrong = wm.group(1) if wm else ''
            ctx = re.sub(r'（[^）]*）', '', examples.split('、')[0]).strip()
            yin.append({'item': ch, 'reading': rd, 'wrong_reading': wrong,
                        'context': ctx, 'src': '要点一·易误读'})
        i += 2
        continue
    i += 1

# --- 要点二：教材较难字音 —— 逗号分隔的 词（pīn yīn）---
sec2 = section(full, '中考字音考查要点二：教材中出现过的个别较难的字音',
                     '中考字音考查要点三：')
for m in re.finditer(r'([一-龥]{1,4})（(' + PYWORD + r')）', sec2):
    word, rd = m.group(1), m.group(2).strip()
    yin.append({'item': word, 'reading': rd, 'wrong_reading': '',
                'context': word, 'src': '要点二·教材较难'})

# --- 要点三：常见多音字 —— N、字：①yīn词 ②yīn词 ---
sec3 = section(full, '中考字音考查要点三：常见常用的多音字',
                     '中考字音考查要点四：')
for line in sec3.split('\n'):
    m = re.match(r'\d+\s*[、.]\s*([一-龥])：(.+)', line)
    if not m:
        continue
    ch, rest = m.group(1), m.group(2)
    for rm in re.finditer(r'[①②③④⑤]\s*(' + PYL + r')([一-龥、]+)', rest):
        rd, words = rm.group(1), rm.group(2)
        yin.append({'item': ch, 'reading': rd, 'wrong_reading': '',
                    'context': words.split('、')[0], 'src': '要点三·多音字'})

# --- 要点六：形近/形声字误读 —— 「X」的「字」误读Y　正读Z ---
sec6 = section(full, '中考字音考查要点六：形近字误读和形声字误读',
                     '中考字形要点考查指导一览表')
for m in re.finditer(r'[“"]([一-龥]+)[”"]的[“"]([一-龥])[”"]误读(' + PYL + r')\s*正读(' + PYL + r')', sec6):
    word, ch, wrong, right = m.groups()
    yin.append({'item': ch, 'reading': right, 'wrong_reading': wrong,
                'context': word, 'src': '要点六·形近误读'})
# 要点六开头那批形近对：崇（chóng）高/作祟（suì） —— 取「字（拼音）后跟一个汉字」做例词
for m in re.finditer(r'([一-龥])（(' + PYL + r')）([一-龥])', sec6):
    yin.append({'item': m.group(1), 'reading': m.group(2), 'wrong_reading': '',
                'context': m.group(1) + m.group(3), 'src': '要点六·形近组'})

# 去重
seen = set()
yin_uniq = []
for e in yin:
    k = (e['item'], e['reading'], e['context'])
    if k in seen:
        continue
    seen.add(k)
    yin_uniq.append(e)

# ================= 字形库 =================
# 统一目标：每条都是「错词 wrong_form + 该被改成的正字 right_char」
xing = []

def add_wrong_right(wrong_form, right_char, src):
    wrong_form = wrong_form.strip()
    right_char = right_char.strip()
    if not wrong_form or not right_char or len(right_char) != 1:
        return
    xing.append({'wrong_form': wrong_form, 'right_char': right_char, 'src': src})

# --- 字形要点三：常见错别字 300 个 —— 错词(正字) ---
sec_x3 = section(full, '中考字形要点考查指导三：中考语文常见错别字',
                       '中考字音考查要点四：音同形似')
for m in re.finditer(r'[\d]{2,3}\.\s*([一-龥]{2,8})\(([一-龥√=.]+)\)', sec_x3):
    add_wrong_right(m.group(1), m.group(2)[-1], '字形要点三·常见错别字300')

# --- 字形要点一：易错字集锦 —— 正词(错字)，需翻转 ---
# 「深孚众望(负)」= 正词 深孚众望，错字 负。错字替换正词里某个位置→错词。
# 位置无法可靠确定，这里保留原始形态，标记 needs_review，交人工/生成时处理。
sec_x1 = section(full, '中考字形要点考查指导一：七—九年级常见的易错字集锦',
                       '中考字形要点考查指导二：')
xing_review = []
for m in re.finditer(r'([一-龥]{2,8})\(([一-龥]+)\)', sec_x1):
    xing_review.append({'right_form': m.group(1), 'wrong_char': m.group(2),
                        'src': '字形要点一·易错字集锦', 'note': '正词(错字)格式,错字位置待定'})

# --- 易错字汇总.txt —— 错词(正字) ---
raw = open('初中语文必须掌握易错字汇总.txt', encoding='utf-8-sig').read()
for m in re.finditer(r'([一-龥]{2,8})（([一-龥.]+)）', raw):
    add_wrong_right(m.group(1), m.group(2)[-1], '易错字汇总')

# 去重
seen = set()
xing_uniq = []
for e in xing:
    k = (e['wrong_form'], e['right_char'])
    if k in seen:
        continue
    seen.add(k)
    xing_uniq.append(e)

# ---------- 写出 ----------
json.dump(yin_uniq, open('字音库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(xing_uniq, open('字形库.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(xing_review, open('字形库_待定.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- 报告 ----------
print('=== 字音库 ===  共 %d 条' % len(yin_uniq))
from collections import Counter
for s, c in Counter(e['src'] for e in yin_uniq).items():
    print('  %-16s %d' % (s, c))
print('  样例:')
for e in yin_uniq[:5]:
    print('   ', json.dumps(e, ensure_ascii=False))

print('\n=== 字形库（可直接用：错词+正字）===  共 %d 条' % len(xing_uniq))
for s, c in Counter(e['src'] for e in xing_uniq).items():
    print('  %-22s %d' % (s, c))
print('  样例:')
for e in xing_uniq[:5]:
    print('   ', json.dumps(e, ensure_ascii=False))

print('\n=== 字形库_待定（正词(错字)格式，错字位置需人工/生成时定）===  共 %d 条' % len(xing_review))
for e in xing_review[:5]:
    print('   ', json.dumps(e, ensure_ascii=False))
