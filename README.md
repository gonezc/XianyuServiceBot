# XianyuAgentBot

闲鱼 AI 售前客服原型，面向软件开发与程序定制场景。

它当前解决的是一条很具体的链路：接入闲鱼消息，维护对话状态，结合案例库给出回复，并把关键会话、议价和成交信息沉淀下来。

## 当前实现

- 工作流：`LangGraph` 驱动多阶段售前对话
- 接入：闲鱼 `WebSocket` 实时消息
- 存储：`SQLite` 保存消息、线程、商品和调用指标
- 案例检索：当前代码使用 `FAISS` 优先，失败时降级关键词匹配
- 支撑能力：情绪分析、人工接管、飞书通知、本地调试

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置 `.env`

至少需要：

```env
API_KEY=你的模型服务密钥
MODEL_BASE_URL=模型兼容接口地址
MODEL_NAME=qwen-max
COOKIES_STR=闲鱼网页端 Cookie
```

常用可选项：

```env
EMBEDDING_MODEL=text-embedding-v3
FEISHU_WEBHOOK_URL=
LOG_LEVEL=DEBUG
MANUAL_MODE_TIMEOUT=3600
THREAD_POOL_SIZE=8
HEARTBEAT_INTERVAL=15
HEARTBEAT_TIMEOUT=5
TOKEN_REFRESH_INTERVAL=3600
TOKEN_RETRY_INTERVAL=300
MESSAGE_EXPIRE_TIME=300000
```

3. 本地调试

```bash
python local_chat.py
```

4. 连接闲鱼运行

```bash
python main.py
```

## 文档入口

- [文档索引](docs/INDEX.md)
- [当前设计真相](docs/SPEC-current.md)
- [数据与存储](docs/DATABASE.md)
- [运行与排障](docs/RUNBOOK.md)

## 需求与迭代管理

仓库内不再维护大量需求/实现拆分文档。

- 长期稳定事实保留在 `README.md` 和 `docs/*.md`
- 新需求、方案讨论、演进计划、验收项统一放到 GitHub Issues

## 目录概览

```text
main.py                生产入口
local_chat.py          本地对话调试入口
agent/                 LangGraph 工作流、知识检索、情绪分析、通知
core/                  闲鱼 WebSocket 接入与消息处理
storage/               SQLite 存储
knowledge/             案例与技能数据、FAISS 索引缓存
prompts/               系统提示词
docs/                  长期设计与运行文档
```

## 效果图

![开场](images/开场.png)

![需求收集](images/需求收集.png)

![定价议价](images/定价议价.png)

![下单引导](images/下单引导.png)

## 致谢

- 原项目：[shaxiu/XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent)

## 声明

本项目仅供学习交流，请遵守平台规则与账号安全要求。
