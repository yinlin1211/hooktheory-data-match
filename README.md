# Hooktheory 样本匹配分析

本仓库记录了将本地音乐文件与 YouTube video_id 进行匹配，进而通过 `youtube_to_keys.json` 生成 Hooktheory 样本 ID 的完整过程。

---

## 文件说明

| 文件 | 说明 |
|---|---|
| `match_final.py` | 最终版多策略匹配算法（主脚本） |
| `local2youtubeid.json` | 最终匹配结果：本地文件名 → YouTube video_id（11,766 条） |
| `unmatched_local_final.json` | 无法匹配的本地文件列表（60 条） |
| `youtube2key_missing570.json` | files20072 中有但当前 xlsx 缺失的 570 个 video_id 及其 key |

---

## 数据来源

- **11892.json**：本地音乐文件列表（11,892 个 .mp3 文件名）
- **总json.json**：YouTube URL → 视频标题的映射（12,463 条有效记录）
- **youtube_to_keys.json**（y2k）：YouTube video_id → 样本 key 列表
- **files20072.json**：目标样本列表（20,072 个样本文件名）

---

## 匹配算法说明

### 核心思路

本地文件名几乎就是 YouTube 视频标题直接保存的，但存在以下几类系统性差异：

| 差异类型 | 示例 |
|---|---|
| 文件系统不允许 `?` | `How Bad Can I Be?` → `How Bad Can I Be_` |
| 文件系统不允许 `/` | `AC/DC` → `AC_DC` |
| 末尾重复标记 | `Don't Hug Me I'm Scared 6 (1).mp3` |
| 全标点差异（引号、冒号等）| `"Here Comes a Thought"` → `'Here Comes a Thought'` |
| 多空格 | `Skubas   "Over the rising hills"` |

### 匹配策略优先级

```
1. 精确匹配（NFC + 引号统一 + 去 emoji）
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
12. 组合：去(n) + 多空格
13. 全组合（去(n) + 标点 + 大小写）
14. 前缀匹配（local 被截断 / local 末尾有小噪声）
```

---

## 最终结果统计

| 指标 | 数值 |
|---|---|
| 本地文件总数 | 11,892 |
| 成功匹配到 video_id | **11,766** |
| 未匹配（真实无法对应）| 60 |
| 通过 y2k 生成的 key 数 | **20,113** |
| 其中在 files20072 里的 | 20,065 |
| files20072 总 key 数（目标）| 20,072 |
| **覆盖率** | **99.97%** |
| 多出来的 key（正确匹配，files20072 未收录）| 48 |
| files20072 里有但本地缺失的 key | 7 |

### 各策略命中数

| 策略 | 命中数 |
|---|---|
| 精确匹配 | 10,123 |
| 全标点忽略 | 1,211 |
| `?→_` / `→_` | 286 |
| 去末尾(n) | 184 |
| 去(n)+全标点忽略 | 27 |
| 前缀匹配 | 1 |

---

## 差距分析：为何只有 20,065 而非 20,072？

### 缺少 7 个 key

这 7 个 key 对应的 video_id 在 `youtube_to_keys` 里有记录，但本地 11,892 个文件中**找不到对应的文件名**，说明这些视频当时被下载过但现在本地已不存在，属于真实缺失。

### 多出 48 个 key

`files20072` 当初生成时，对含特殊字符（单引号、双引号、竖线等）文件名的 video_id 做了过滤，导致这 30 个 video_id 的部分 key 没有进入 files20072。现在重新匹配时这些 video_id 被正确识别，所有 key 都被生成出来，因此多出 48 个。

**经逐条核查：0 条误匹配。** 所有多出的 key 均来自内容正确对应的本地文件。

---

## 误匹配风险分析

重点检查了「全标点忽略」策略下的歧义情况（同一个去标点 key 对应多个 video_id）：

- 歧义组数：**15 组**
- 其中涉及本地文件的歧义：**3 条**
- 最终判定误匹配：**0 条**

歧义案例均为同一首歌的不同上传版本（如 `The Beatles - "A Hard Day's Night"` 和 `The Beatles - A Hard Day's Night`），两个 video_id 都在 files20072 里，不影响结果。

---

## 复现方法

```bash
# 1. 准备数据文件（放在同目录）
#    - 11892.json
#    - 总json.json
#    - youtube_to_keys.json
#    - files20072.json

# 2. 运行匹配脚本
python3 match_final.py

# 3. 输出文件
#    - local2youtubeid.json   （本地文件 → video_id）
#    - unmatched_local_final.json  （未匹配文件）
```
