# -*- coding: utf-8 -*-
# 从「初中阶段易误用成语清单.txt」解析出结构化成语库
import re, json

src = open('初中阶段易误用成语清单.txt', encoding='utf-8-sig').read()
src = src.replace('\r', '')

# 段落标题 -> 设误机制类型
section_map = [
    ('第一部分：适用对象很窄', '对象误用'),
    ('第二部分：感情色彩或语用方向反直觉', '褒贬误用'),
    ('一、望文生义', '望文生义'),
    ('二、语义重复', '语义重复'),      # 格式不同, 跳过
    ('三、谦敬错位', '谦敬错位'),
    ('四、大词小用', '大词小用'),
    ('五、轻重错位', '轻重错位'),
    ('六、语法搭配错位', '搭配错位'),
    ('七、对象可用但方向错', '方向误用'),
    ('八、近义成语细差', '近义混淆'),  # 格式不同, 跳过
    ('九、套题训练法', '__END__'),
]

# 找每个 section 的起止位置
marks = []
for title, typ in section_map:
    idx = src.find(title)
    if idx >= 0:
        marks.append((idx, typ))
marks.sort()

entries = []
# 条目正则: 「数字. 成语：释义... 易错：错句  （可用|稳妥|改法）：对句」
pat = re.compile(
    r'(\d+)\.\s*([一-龥]{3,8})：(.+?)'
    r'[-\s]*易错：(.+?)[。\.]'
    r'[-\s]*(?:可用|稳妥)：(.+?)[。\.]'
)

for i, (start, typ) in enumerate(marks):
    if typ in ('__END__', '语义重复', '近义混淆'):
        continue
    end = marks[i+1][0] if i+1 < len(marks) else len(src)
    chunk = src[start:end]
    for m in pat.finditer(chunk):
        idiom = m.group(2).strip()
        meaning = m.group(3).strip()
        wrong = m.group(4).strip()
        right = m.group(5).strip()
        # 句子里去掉残留的「- 」
        wrong = wrong.lstrip('- ').strip()
        right = right.lstrip('- ').strip()
        # 过滤不规范条目: 例句里必须真的出现这个成语
        if idiom not in wrong or idiom not in right:
            continue
        entries.append({
            'idiom': idiom,
            'meaning': meaning,
            'type': typ,
            'wrong': wrong + '。',
            'right': right + '。',
        })

# 去重(同一成语可能出现多次, 保留第一次)
seen = set()
uniq = []
for e in entries:
    if e['idiom'] in seen:
        continue
    seen.add(e['idiom'])
    uniq.append(e)

json.dump(uniq, open('chengyu_db.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ========== 解析「600个高频成语」==========
raw600 = open('600个高频成语.txt', encoding='utf-8-sig').read()
# 去掉重复页眉、换页符
raw600 = raw600.replace('600个高频成语', '').replace('\x0c', '')
# 整篇拼成一行(消除 OCR 换行)
flat = re.sub(r'\s+', '', raw600)
# 抽条目: 数字.成语：释义...(到下一个 数字.成语： 之前)
pat600 = re.compile(r'(\d+)\.([一-龥]{2,8})：(.+?)(?=\d{1,3}\.[一-龥]{2,8}：|$)')
db600 = []
seen600 = set()
for m in pat600.finditer(flat):
    idiom = m.group(2).strip()
    meaning = m.group(3).strip()
    # 砍掉夹在条目后的近义辨析评论段(评论多以引号开头)
    for q in ('“', '”', '‘'):
        p = meaning.find(q)
        if p > 8:
            meaning = meaning[:p]
            break
    # 释义只保留前两句, 太长截断
    parts = re.split(r'(?<=。)', meaning)
    meaning = ''.join(parts[:2]).strip('。') + '。'
    if not idiom or idiom in seen600 or len(meaning) < 4:
        continue
    seen600.add(idiom)
    db600.append({'idiom': idiom, 'meaning': meaning})

json.dump(db600, open('chengyu_600.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('解析出 600 高频成语条目:', len(db600))
print('--- 600 样例 ---')
for e in db600[:3]:
    print(json.dumps(e, ensure_ascii=False))
print()

print('解析出成语条目:', len(uniq))
from collections import Counter
for t, c in Counter(e['type'] for e in uniq).items():
    print(f'  {t}: {c}')
print('--- 样例 ---')
for e in uniq[:3]:
    print(json.dumps(e, ensure_ascii=False))
