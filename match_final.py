"""
最终版多策略匹配算法
覆盖所有已发现的差异规律：
  1. 精确匹配（NFC + 引号统一 + emoji去除）
  2. ? → _  /  / → _
  3. 大小写不敏感
  4. 全标点忽略（只比较字母数字）
  5. 冒号替换：": " → " - "
  6. 多空格 → 单空格
  7. 下划线 → 空格
  8. 去末尾 (n) 重复标记
  9. 组合：去(n) + 全标点忽略
  10. 组合：去(n) + ?→_ /→_
  11. 组合：去(n) + 冒号→连字符
  12. 前缀匹配（local被截断 / local末尾有小噪声）
  13. 组合：去(n) + 前缀匹配
"""

import json, re, unicodedata
from collections import defaultdict

# ===== 加载数据 =====
with open('本地文件11892.json', encoding='utf-8') as f:
    local_files = json.load(f)
with open('视频访问情况.json', encoding='utf-8') as f:
    yt_raw = json.load(f)
with open('youtube_to_keys.json', encoding='utf-8') as f:
    y2k = json.load(f)
with open('files20072.json', encoding='utf-8') as f:
    files20072 = json.load(f)

# ===== 解析 YouTube =====
yt_valid = {}
for url, title in yt_raw.items():
    if not title or '错误' in str(title):
        continue
    m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', url)
    if m:
        vid = m.group(1)
        if vid not in yt_valid:
            yt_valid[vid] = title

print(f"有效 YouTube 条目: {len(yt_valid)}")
print(f"本地文件数: {len(local_files)}")

# ===== 规范化函数 =====
def n0(s):
    """基础：去.mp3, NFC, 统一引号, 去emoji/不可见字符"""
    s = s.strip()
    if s.lower().endswith('.mp3'): s = s[:-4].strip()
    s = unicodedata.normalize('NFC', s)
    s = s.replace('\u2018',"'").replace('\u2019',"'")
    s = s.replace('\u201c','"').replace('\u201d','"')
    s = ''.join(c for c in s if ord(c) < 0x10000)
    s = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]','',s)
    return s.strip()

def strip_suffix_n(s):
    """去掉末尾的 (1), (2), (1).mp3 等"""
    s = re.sub(r'\s*\(\d+\)\s*$', '', s).strip()
    return s

def n_strip(s):
    """n0 + 去末尾(n)"""
    return strip_suffix_n(n0(s))

def n_punct(s):
    """n0 + 全标点忽略，小写"""
    return re.sub(r'[^a-z0-9\u3040-\u9fff\uac00-\ud7af]','', n0(s).lower())

def n_slash(s):
    """n0 + ?→_  /→_"""
    s = n0(s)
    return s.replace('?','_').replace('/','_')

def n_colon(s):
    """n0 + ': '→' - '"""
    s = n0(s)
    return re.sub(r':\s+', ' - ', s)

def n_space(s):
    """n0 + 多空格→单空格"""
    return re.sub(r'\s+',' ', n0(s)).strip()

def n_under(s):
    """n0 + _→空格"""
    return n0(s).replace('_',' ')

# 组合
def n_strip_punct(s):  return n_punct(n_strip(s))
def n_strip_slash(s):  return n_slash(strip_suffix_n(n0(s)))
def n_strip_colon(s):  return n_colon(strip_suffix_n(n0(s)))
def n_strip_space(s):  return re.sub(r'\s+',' ', n_strip(s)).strip()
def n_all(s):
    """最激进：去(n) + ?→_ /→_ + 大小写 + 多空格"""
    s = n_strip(s)
    s = s.replace('?','_').replace('/','_')
    s = re.sub(r'\s+',' ', s).strip()
    return s.lower()

# ===== 构建多级索引 =====
STRATEGIES = [
    (n0,           "精确匹配"),
    (n_slash,      "?→_ /→_"),
    (lambda s: n0(s).lower(), "大小写不敏感"),
    (n_punct,      "全标点忽略"),
    (n_colon,      "冒号→连字符"),
    (n_space,      "多空格→单空格"),
    (n_under,      "下划线→空格"),
    (n_strip,      "去末尾(n)"),
    (n_strip_punct,"去(n)+全标点忽略"),
    (n_strip_slash,"去(n)+?→_/→_"),
    (n_strip_colon,"去(n)+冒号→连字符"),
    (n_strip_space,"去(n)+多空格"),
    (n_all,        "全组合"),
]

indexes = []
for norm_fn, label in STRATEGIES:
    idx = {}
    for vid, title in yt_valid.items():
        key = norm_fn(title)
        if key not in idx:
            idx[key] = vid
    indexes.append((idx, norm_fn, label))

# ===== 前缀匹配 =====
yt_norm0_list = [(vid, n0(title)) for vid, title in yt_valid.items()]
yt_strip_list = [(vid, n_strip(title)) for vid, title in yt_valid.items()]

def prefix_match(local_n, yt_list, min_len=18):
    """
    A: yt 以 local 开头（local 被截断）
    B: local 以 yt 开头（local 末尾有小噪声）
    """
    if len(local_n) < min_len:
        return None
    for vid, yt_n in yt_list:
        # A: yt 更长，local 是 yt 的前缀
        if yt_n.startswith(local_n) and len(yt_n) > len(local_n):
            rem = yt_n[len(local_n):].strip()
            if len(rem) <= 4 or not re.search(r'[a-zA-Z0-9\u4e00-\u9fff\uac00-\ud7af]', rem):
                return vid
        # B: local 更长，yt 是 local 的前缀
        if local_n.startswith(yt_n) and len(local_n) > len(yt_n) and len(yt_n) >= min_len:
            rem = local_n[len(yt_n):].strip()
            if len(rem) <= 6 or not re.search(r'[a-zA-Z0-9\u4e00-\u9fff\uac00-\ud7af]', rem):
                return vid
    return None

# ===== 执行匹配 =====
result = {}
strategy_counts = defaultdict(int)

for local_fn in local_files:
    vid = None

    # 策略 1-13：各级索引
    for idx_dict, norm_fn, label in indexes:
        key = norm_fn(local_fn)
        if key in idx_dict:
            vid = idx_dict[key]
            strategy_counts[label] += 1
            break

    if vid is None:
        # 前缀匹配（基础）
        local_n = n0(local_fn)
        vid = prefix_match(local_n, yt_norm0_list)
        if vid:
            strategy_counts["前缀匹配(基础)"] += 1

    if vid is None:
        # 前缀匹配（去末尾(n)后再做）
        local_n = n_strip(local_fn)
        vid = prefix_match(local_n, yt_norm0_list)
        if vid:
            strategy_counts["前缀匹配(去n)"] += 1

    if vid is None:
        # 前缀匹配（去(n) + ?→_ /→_）
        local_n = n_strip_slash(local_fn)
        yt_slash_list = [(v, n_slash(t)) for v, t in yt_valid.items()]
        vid = prefix_match(local_n, yt_slash_list)
        if vid:
            strategy_counts["前缀匹配(去n+slash)"] += 1

    if vid is None:
        # 前缀匹配（去(n) + 冒号→连字符）
        local_n = n_strip_colon(local_fn)
        yt_colon_list = [(v, n_colon(t)) for v, t in yt_valid.items()]
        vid = prefix_match(local_n, yt_colon_list)
        if vid:
            strategy_counts["前缀匹配(去n+colon)"] += 1

    if vid is not None:
        result[local_fn] = vid

unmatched = [fn for fn in local_files if fn not in result]

print(f"\n=== 匹配结果 ===")
for label, cnt in sorted(strategy_counts.items(), key=lambda x: -x[1]):
    print(f"  {label}: {cnt}")
print(f"  总匹配: {len(result)}")
print(f"  未匹配: {len(unmatched)}")

# ===== 验证样本数量 =====
def extract_key(fn):
    return fn.rsplit('.', 1)[0][-11:]

files20072_keys = set(extract_key(f) for f in files20072)
matched_vids = set(result.values())

generated_keys = set()
for vid in matched_vids:
    if vid in y2k:
        generated_keys.update(y2k[vid])

print(f"\n=== 样本数量验证 ===")
print(f"匹配到的 video_id 数:          {len(matched_vids)}")
print(f"通过 y2k 生成的 key 数:        {len(generated_keys)}")
print(f"其中在 files20072 里的:        {len(generated_keys & files20072_keys)}")
print(f"files20072 总 key 数:          {len(files20072_keys)}")
print(f"files20072 里有但生成不了的:   {len(files20072_keys - generated_keys)}")
print(f"生成了但 files20072 没有的:    {len(generated_keys - files20072_keys)}")
print(f"\n目标 20072，当前生成: {len(generated_keys)}")

# ===== 保存结果 =====
with open('local2youtubeid.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

with open('unmatched_local_final.json', 'w', encoding='utf-8') as f:
    json.dump(unmatched, f, ensure_ascii=False, indent=2)

print(f"\n已保存 local2youtubeid.json ({len(result)} 条)")
print(f"已保存 unmatched_local_final.json ({len(unmatched)} 条)")

if unmatched:
    print(f"\n未匹配样本（前20）:")
    for fn in unmatched[:20]:
        print(f"  {fn}")
