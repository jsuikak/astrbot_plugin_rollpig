---
name: pig-design-and-add
description: 为 astrbot_plugin_rollpig 设计并新增趣味小猪，覆盖“形象与文案设计 -> 调用 OpenAI image_gen 生成图片 -> 写入 resource/pig.json -> 一致性校验”的完整流程。
---

# Pig Design And Add Skill

## 适用场景

当用户提出以下需求时使用本技能：

- 新增一个或多个“趣味小猪”
- 基于某个主题设计小猪形象和文案
- 需要同时完成两件事：生成图片、写入 JSON 数据

## 仓库约束（必须遵守）

- 小猪数据文件：`resource/pig.json`
- 小猪图片目录：`resource/image/`
- JSON 每个条目必须包含且仅包含字段：
  - `id`
  - `name`
  - `description`
  - `analysis`
- 图片文件名必须与 `id` 完全一致（仅后缀可不同）
- 支持图片后缀：`png`、`jpg`、`jpeg`、`webp`、`gif`
- 小猪图片统一分辨率：`240x240`
- 保持 `resource/pig.json` 的 UTF-8 + 2 空格缩进格式，不转义中文（`ensure_ascii=False`）

## 设计规范

### 1) 角色定位

每只小猪要同时具备：

- 明确视觉识别点（例如：职业、元素、道具、情绪）
- 一句短描述（适合聊天场景）
- 一段性格解析（可读、有画面感）

### 2) 字段风格建议

- `id`：推荐小写英文字母 + 数字 + `-`/`_`，且全库唯一
- `name`：2-8 个中文字符，便于展示
- `description`：一句话，偏梗感或记忆点
- `analysis`：2-4 句，强调性格、行为倾向、社交气质

### 3) 一致性要求

- 不复用已有 `id`
- 不与已有小猪“仅换名字不换设定”
- 语气与现有库保持轻松、有趣、可传播
- 图片必须贴近原始小猪图的基础姿态：小猪侧身、四条腿站立在地上、身体圆润横向展开；主题元素应作为装饰、服饰或少量道具叠加，避免改成趴卧、坐姿、双足站立、人形化或复杂场景插画

## 执行流程

### 步骤 1：读取现有素材，避免重复

1. 查看 `resource/pig.json` 现有主题与命名风格
2. 确认 `id` 未被占用
3. 初稿先给出一个 JSON 对象草案（不落库）

草案模板：

```json
{
  "id": "new-pig-id",
  "name": "新小猪名",
  "description": "一句短描述",
  "analysis": "2-4句性格解析。"
}
```

### 步骤 2：调用 image_gen 生成小猪图片（强制参考原始小猪画风）

优先使用 `image_gen` 工具。

#### 生图前置门禁（必须先过）

在 Codex 会话中，用户必须手动上传原图参考（通常是 `resource/image/pig.png`）。

- 如果用户已经上传参考图：继续生图。
- 如果用户没有上传参考图：禁止生图，直接提示用户先上传。

当未上传参考图时，固定返回提示语：

```text
请先在当前 Codex 会话中手动上传原图参考（建议上传 resource/image/pig.png），我再按该图画风生成新小猪。
```

说明：`image_gen` 在本技能中按“会话附件参考图”工作，不走本地路径直传。

提示词模板（按主题替换，必须包含“遵循原图画风”）：

```text
请参考我提供的原始小猪参考图，严格遵循其整体画风（线条风格、配色倾向、可爱程度、角色比例、渲染质感）。
在保持该画风一致的前提下，生成一张“{name}”的小猪形象插画，突出{核心视觉元素}。
风格：与参考图同风格的Q版插画，干净线条，色彩鲜明，表情生动。
背景：默认纯白背景（#FFFFFF），只有当设计主题必须依赖特定背景元素才能成立时，才允许使用非纯白背景（如轻微渐变/场景化背景）。
构图：单角色居中，完整身体，正方形画幅；必须保持原始小猪四条腿站立在地上的侧身姿态，身体横向展开，不要趴卧、坐姿、双足站立或人形化。小猪的角度尽量保持和原图一致。
要求：不要文字、不要水印、不要logo、不要边框、不要多角色、不要复杂背景。
```

如果生成结果不稳定，按以下顺序迭代：

1. 先固定“遵循参考图画风 + 四条腿站立在地上的侧身小猪姿态 + 纯白背景 + 单角色 + 居中 + 正方形 + 无文字”
2. 再强化一个视觉锚点（如“风车背饰”“火花尾迹”）
3. 避免一次塞入过多设定

### 步骤 3：保存图片到插件资源目录

1. 将最终图保存为 `resource/image/{id}.png`（首选 png）
2. 若工具产物不是正方形，先裁剪/补边到 1:1
3. 将图片统一缩放到 `240x240`（优先 `ffmpeg`，缺失时用 Python）
4. 确认目录中只保留该 `id` 的一个主图版本（避免同 id 多后缀并存）

推荐命令（优先 `ffmpeg`）：

```bash
ffmpeg -y -i resource/image/{id}.png -vf scale=240:240:flags=lanczos /tmp/{id}-240.png && mv /tmp/{id}-240.png resource/image/{id}.png
```

无 `ffmpeg` 时使用 Python（Pillow）：

```bash
python3 - <<'PY'
from PIL import Image
img = Image.open("resource/image/{id}.png").convert("RGBA")
img = img.resize((240, 240), Image.Resampling.LANCZOS)
img.save("resource/image/{id}.png")
print("done")
PY
```

### 步骤 4：写入 JSON 条目

1. 在 `resource/pig.json` 末尾追加新对象（不改动其他对象语义）
2. 保持数组合法 JSON 结构
3. 字段顺序固定为：`id`、`name`、`description`、`analysis`

## 校验清单（落库后必须执行）

1. JSON 语法校验通过
2. 新 `id` 在全库唯一
3. `resource/image/` 中存在与 `id` 匹配的图片文件
4. 图片能被插件识别后缀命中（`png/jpg/jpeg/webp/gif`）
5. 图片分辨率为 `240x240`
6. 文案无明显错别字和语义重复

建议本地快速校验命令：

```bash
python3 -m json.tool resource/pig.json >/dev/null
```

```bash
python3 -c "import json, pathlib; pigs=json.loads(pathlib.Path('resource/pig.json').read_text('utf-8')); ids=[p['id'] for p in pigs]; assert len(ids)==len(set(ids)), '存在重复id'; print('id唯一性校验通过')"
```

```bash
sips -g pixelWidth -g pixelHeight resource/image/{id}.png
```

## 可选人工验收

- 启动管理工具：`streamlit run pig_manager.py --server.port 8080`
- 在“📋 小猪列表”确认图片、名称、描述、解析展示正常

## 交付输出格式（每次新增后）

完成新增后，输出应包含：

1. 新增小猪 `id` 与 `name`
2. 图片最终路径
3. 本次生图使用的原始提示词（完整文本）
4. JSON 已追加对象（可贴对象本体）
5. 校验结果（通过/失败 + 原因）
