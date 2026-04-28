# RUNBOOK

## 1. 目的

这份文档只回答三件事：

1. 怎么跑起来
2. 出问题先看哪里
3. 怎么恢复到可继续调试的状态

## 2. 运行前提

### Python 与依赖

```bash
pip install -r requirements.txt
```

### 必需环境变量

| 变量 | 作用 |
| --- | --- |
| `API_KEY` | 聊天模型与 embedding 模型调用凭证 |
| `MODEL_BASE_URL` | 兼容 OpenAI 的模型服务地址 |
| `MODEL_NAME` | 聊天模型名 |
| `COOKIES_STR` | 闲鱼 Web 端 Cookie，生产接入需要 |

### 常用可选环境变量

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `EMBEDDING_MODEL` | `text-embedding-v3` | 向量化模型 |
| `LOG_LEVEL` | `DEBUG` | 日志级别 |
| `FEISHU_WEBHOOK_URL` | 空 | 飞书通知 |
| `MANUAL_MODE_TIMEOUT` | `3600` | 人工接管超时秒数 |
| `THREAD_POOL_SIZE` | 动态计算 | 消息处理线程池大小 |
| `HEARTBEAT_INTERVAL` | `15` | 心跳间隔 |
| `HEARTBEAT_TIMEOUT` | `5` | 心跳超时 |
| `TOKEN_REFRESH_INTERVAL` | `3600` | token 刷新周期 |
| `TOKEN_RETRY_INTERVAL` | `300` | token 刷新失败重试间隔 |
| `MESSAGE_EXPIRE_TIME` | `300000` | 过期消息阈值（毫秒） |

## 3. 启动方式

### 本地调试

```bash
python local_chat.py
```

适用：

- 调提示词
- 看阶段流转
- 看数据库是否写入
- 不依赖闲鱼平台联调

本地调试内置命令：

- `/clear`
- `/emotion`
- `/strategy`
- `/prompt`
- `/tools`
- `/messages`
- `/item`
- `/debug`
- `/history`
- `/order`

### 真实接入

```bash
python main.py
```

适用：

- 验证真实闲鱼消息接入
- 验证 Cookie / token / WebSocket 行为

## 4. 日志与观察点

优先看标准输出日志。

关键观察点：

- WebSocket 是否成功注册
- token 是否刷新成功
- 是否有消息解密失败
- 阶段判断是否异常
- FAISS 是否成功加载或构建
- 飞书通知是否发送

数据观察点：

- `data/chat_history.db`
- `knowledge/.faiss_index`
- `knowledge/.embeddings_cache.pkl`

## 5. 常见问题

### 5.1 `API_KEY` 未配置

现象：

- `local_chat.py` 直接退出
- 或模型调用失败

处理：

- 检查 `.env`
- 确认 `load_dotenv()` 能读到当前目录 `.env`

### 5.2 `COOKIES_STR` 未配置或失效

现象：

- `main.py` 启动时报错退出
- WebSocket 无法建立
- token 获取失败，反复重试

处理：

- 重新从闲鱼网页端获取 Cookie
- 检查 `.env` 中 `COOKIES_STR` 是否完整

### 5.3 FAISS 不可用

现象：

- 日志提示 `FAISS 未安装，使用关键词匹配`

影响：

- 系统仍可运行，但案例检索质量下降

处理：

```bash
pip install faiss-cpu numpy
```

### 5.4 向量索引脏了或案例更新后结果不对

现象：

- 案例检索结果明显不符合当前 `cases.json`

处理：

删除派生缓存后重启：

```powershell
Remove-Item knowledge\.faiss_index -Force
Remove-Item knowledge\.embeddings_cache.pkl -Force
```

### 5.5 飞书通知没发出去

现象：

- 下单或转人工时没有收到卡片

处理：

- 检查 `FEISHU_WEBHOOK_URL`
- 看日志里是否有请求异常
- 没配置 webhook 时，代码会跳过发送但继续主流程

### 5.6 数据库状态看起来乱了

现象：

- 本地调试会话太多
- 历史消息污染当前判断

处理：

先停进程，再删除本地库重新跑：

```powershell
Remove-Item data\chat_history.db -Force
```

## 6. 恢复顺序

遇到故障时，建议按这个顺序排：

1. 看日志
2. 查 `.env`
3. 查 `data/chat_history.db`
4. 查 `knowledge/` 索引缓存
5. 本地用 `local_chat.py` 复现
6. 再去排真实闲鱼接入链路

## 7. 文档边界

这份文档不写未来方案，不写需求计划。

- 运行事实进这里
- 设计真相进 `SPEC-current.md`
- 结构与字段进 `DATABASE.md`
- 演进和需求进 GitHub Issues
