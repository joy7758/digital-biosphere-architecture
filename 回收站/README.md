# 回收站

本目录是 joy7758 仓库整理的可审计索引，不是删除清单。

主线：Agent Evidence / Operation Accountability Profile，即“智能体执行证据与操作问责配置文件”。

目标是让外部读者和未来智能体先看到主线入口，同时保留历史仓库的迁移状态、复核条件和人工审批证据。当前目录只记录 `migrated`、`archive-candidate`、`needs-assessment` 等状态，不声明任何仓库已经删除。

## 核心状态机

```text
active -> freeze -> migrated -> archived -> observed -> deleted
```

也允许 `retained-as-history`，用于保留有独立引用、论文引用、历史贡献或外部依赖的仓库。

## 当前禁止事项

- 不在本目录授权删除仓库。
- 不把 Pull Request（拉取请求）合并等同于归档完成。
- 不把 archive（归档）等同于 delete（删除）。
- 不对 private（私有）仓库执行自动归档或删除。
