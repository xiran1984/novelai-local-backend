# NovelAI Local Backend

License: [MIT](LICENSE). Copyright (c) 2026 xiran1984.

一个很小的本地 HTTP 服务：接收提示词，按顺序调用 NovelAI 官方图像接口出图，并把 PNG 和参数记录保存到本地。也支持把本地图片重新上传给 NovelAI 做高清放大。

设计初衷是让 AI 助手（例如 Grok Bot）在它自己的电脑上替你批量出图：你用自然语言描述画面，助手写成 NovelAI 提示词、调用这个服务出图、发缩略图给你挑，再把选中的图放大交付。

## 功能

- `POST /generate`：一个提示词出 1～20 张图，每张随机种子，张与张之间间隔约 6 秒，避免触发限流
- `POST /generate/batch`：一次提交多组提示词，依次执行
- `POST /upscale`：按文件名找到本地原图，上传到 NovelAI 放大，保存为「原文件名 + 高清放大版.png」
- `GET /health`：检查服务是否运行、是否配置了 API key（不会回显 key）
- 每张图旁边都会生成同名 `.json`，记录提示词、负面词、种子、尺寸、步数等，方便复现

## 目录结构

```
novelai-local-backend/
├── app.py            # 全部逻辑（FastAPI）
├── requirements.txt  # 依赖
├── .env.example      # 环境变量示例，复制为 .env 后填写
├── .gitignore        # 已忽略 .env、outputs/、.venv/、日志
└── outputs/          # 运行后自动生成，存放图片和参数记录
```

## 第一步：获取 NovelAI API key

1. 登录 [novelai.net](https://novelai.net)。图像生成需要有效的付费订阅，调用接口会按官方规则消耗 Anlas，具体以 NovelAI 官方说明为准。
2. 进入图像生成页面，打开「设置」（齿轮图标）。
3. 找到 **Account** 标签页，点击 **Get Persistent API Token**，复制生成的 token（一般以 `pst-` 开头）。
4. 这个 token 等同于账号密码，**不要**发到聊天记录、截图或提交到 GitHub。如果泄露了，回到同一位置重新生成即可让旧的失效。

> NovelAI 的界面可能会调整，如果找不到入口，请以官网当前的设置页为准。

## 第二步：本地安装运行

需要 Python 3.10 或更高版本。

```bash
git clone <你的仓库地址> novelai-local-backend
cd novelai-local-backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

配置 API key，二选一：

```bash
# 方式 A：写进 .env（推荐，已被 .gitignore 忽略）
cp .env.example .env
# 然后编辑 .env，把 NOVELAI_API_KEY 改成你自己的 token

# 方式 B：直接设环境变量
export NOVELAI_API_KEY="pst-你的token"
```

启动：

```bash
uvicorn app:app --host 127.0.0.1 --port 8787
# 或在后台运行并写日志
nohup uvicorn app:app --host 127.0.0.1 --port 8787 >> server.log 2>&1 &
```

检查：

```bash
curl http://127.0.0.1:8787/health
# {"ok":true,"has_api_key":true}
```

可选环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `NOVELAI_API_KEY` | 无（必填） | NovelAI 的 Persistent API Token |
| `NOVELAI_OUTPUT_DIR` | `./outputs` | 图片输出目录 |
| `NOVELAI_HOST` / `NOVELAI_PORT` | `127.0.0.1` / `8787` | 仅在 `python app.py` 启动时生效 |

## 接口示例

### 出图

```bash
curl -s http://127.0.0.1:8787/generate -H 'Content-Type: application/json' -d '{
  "prompt": "masterpiece, best quality, 1girl, solo, pink hair, upper body, looking at viewer, smile, blurred background",
  "negative_prompt": "lowres, bad anatomy, bad hands, text, watermark",
  "n": 2,
  "label": "01_test"
}'
```

参数：`prompt`（必填）、`negative_prompt`（不填用内置默认负面词）、`n`（1～20）、`seed`、`width`/`height`（默认 832×1216）、`steps`（默认 28）、`scale`（默认 5）、`model`（默认 `nai-diffusion-5-full`）、`label`（会写进文件名）。

返回：

```json
{
  "ok": true,
  "images": [
    {"path": ".../outputs/20260101_120000_01_test_0.png", "seed": 123456, "index": 0, "filename": "20260101_120000_01_test_0.png"}
  ],
  "errors": []
}
```

文件名格式：`{时间戳}_{label}_{序号}.png`。

### 批量出图

```bash
curl -s http://127.0.0.1:8787/generate/batch -H 'Content-Type: application/json' -d '{
  "jobs": [
    {"prompt": "1girl, cat ears", "label": "a"},
    {"prompt": "1girl, fox ears", "label": "b", "n": 2}
  ]
}'
```

### 高清放大

```bash
curl -s http://127.0.0.1:8787/upscale -H 'Content-Type: application/json' -d '{
  "filename": "20260101_120000_01_test_0.png",
  "scale": 4
}'
```

`filename` 可以是 `outputs/` 里的文件名、绝对路径，或者只写末尾序号（如 `"0"`，取最新的 `*_0.png`）。结果保存为 `20260101_120000_01_test_0高清放大版.png`。

> 实测：即使传 `scale: 4`，NovelAI 目前返回的也是 2 倍（832×1216 放大到 1664×2432）。

## 配合 Grok Bot 使用

Grok Bot 有一台自己的 Linux 电脑，可以在上面跑这个服务，你只需要在聊天里说话。

**1. 部署。** 把仓库地址发给 Grok Bot，让它克隆到自己的电脑上，按「第二步」建虚拟环境、装依赖、启动服务。

**2. 交 API key。** 让 Grok Bot 用「安全输入框」向你索取 `NOVELAI_API_KEY`。它会弹出一个打码的输入卡片，值直接存成它电脑上的环境变量，聊天记录里看不到，助手本身也读不到明文。**不要把 key 直接粘贴在聊天里。** 填好后让它重启服务，并用 `/health` 确认 `has_api_key: true`。

**3. 日常出图流程。**

1. 你描述画面，或发参考图
2. Grok Bot 把它写成 NovelAI 提示词（固定的画质、画风前缀 + 精简的英文 tag）
3. 它调用 `/generate` 出图，把缩略图连同文件名和提示词发给你
4. 你说哪里要改，它改提示词重跑；或者你直接挑一张
5. 它调用 `/upscale` 放大选中的那张，再把高清图发给你，或拷到你电脑上的指定文件夹

可以这样跟它说：

- 「帮我把这个仓库部署到你电脑上，然后用安全输入框问我要 NovelAI 的 API key」
- 「出一张：雨夜便利店门口，她回头看镜头，半身近景，背景虚化，出两个种子」
- 「第二张背景再暗一点，重跑」
- 「第一张高清放大，发给我」

**4. 出问题时。**

- `/health` 连不上：服务没启动或虚拟环境丢了，让它重新建 `.venv` 并启动
- `has_api_key: false`：key 没配置，让它重新走一次安全输入
- 返回 `401`：key 错误或已失效，去 NovelAI 重新生成
- 返回 `429`：被限流，多半是你同时在网页端出图。**按 NovelAI 要求不要自动重试**，稍等一会儿再跑

## 注意事项

- 请遵守 NovelAI 的服务条款。本项目只调用官方接口 `image.novelai.net`，默认一次只跑一张、张与张之间有间隔。
- 服务默认只监听 `127.0.0.1`，不要在没有鉴权的情况下暴露到公网，否则任何人都能用你的额度出图。
- 生成的图片、参数记录和 `.env` 默认都不会被 git 提交。
- 本项目与 NovelAI 官方无关。
