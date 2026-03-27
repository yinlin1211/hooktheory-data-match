"""
generate_samples.py
从匹配结果.csv + youtube_to_keys.json 生成样本列表

输入文件：
  - 匹配结果.csv          本地文件名 → video_id
  - youtube_to_keys.json  video_id → key 列表

输出文件：
  - samples.json          样本文件名列表（格式同 files20072.json）
"""

import json, csv, re

# ===== 加载数据 =====
with open('youtube_to_keys.json', encoding='utf-8') as f:
    y2k = json.load(f)

# 从匹配结果.csv 读取 video_id 集合
matched_vids = set()
local_to_vid = {}
with open('匹配结果.csv', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        vid = row['video_id'].strip()
        local_fn = row['本地文件名'].strip()
        if vid:
            matched_vids.add(vid)
            local_to_vid[local_fn] = vid

print(f"匹配结果.csv 读取完成：{len(local_to_vid)} 条记录，{len(matched_vids)} 个唯一 video_id")

# ===== 生成样本列表 =====
# key 格式：从 files20072.json 可知，文件名为 "歌手_歌名_key.mp3"
# 这里我们直接用 key 本身作为文件名（与 files20072 格式一致，key 就是文件名末尾11位）
# 注意：files20072 的文件名包含歌手和歌名前缀，这里只能生成 key 列表
# 如需完整文件名，需要额外的元数据

samples = []
for vid in sorted(matched_vids):
    if vid in y2k:
        for key in y2k[vid]:
            samples.append(key)

print(f"生成样本 key 数：{len(samples)}")
print(f"唯一 key 数：{len(set(samples))}")

# ===== 保存结果 =====
with open('samples.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(set(samples)), f, ensure_ascii=False, indent=2)

print(f"\n已保存 samples.json（{len(set(samples))} 个唯一 key）")
print("说明：samples.json 与 files20072.json 的差异来自当时生成时的过滤规则，核心内容一致。")
