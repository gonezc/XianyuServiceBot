# 文档索引

这个目录只保留长期稳定文档，不再承载需求拆解过程。

## 文件边界

| 文件 | 作用 | 什么时候更新 |
| --- | --- | --- |
| `README.md` | 仓库入口、启动方式、项目概览 | 项目定位或启动方式变化时 |
| `docs/INDEX.md` | 文档地图与维护规则 | 文档结构变化时 |
| `docs/SPEC-current.md` | 当前生效的系统设计真相 | 核心流程、模块边界、关键技术方案变化时 |
| `docs/DATABASE.md` | SQLite 与知识文件存储说明 | 表结构、关键字段、存储位置变化时 |
| `docs/RUNBOOK.md` | 运行、调试、排障、恢复手册 | 运维动作或排障路径变化时 |

## 不放在这里的内容

下面这些内容默认不再单独写 Markdown：

- 新需求拆分
- 迭代计划
- 方案讨论草稿
- 验收过程记录
- 临时技术调研

这些统一放到 GitHub Issues 管理。

## 建议的 Issue 用法

- `feature`：新能力或需求
- `design`：方案讨论或 ADR 级取舍
- `bug`：缺陷与根因修复
- `ops`：运行故障、排障、恢复

如果某个 Issue 的结论已经变成长期稳定事实，再回写到这里的 4 份文档。

## 阅读顺序

1. [README.md](../README.md)
2. [SPEC-current.md](SPEC-current.md)
3. [DATABASE.md](DATABASE.md)
4. [RUNBOOK.md](RUNBOOK.md)
