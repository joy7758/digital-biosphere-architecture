# Execution Checklist

## PR（Pull Request，拉取请求）前

- [ ] 已运行 `make inventory`。
- [ ] 已运行 `make classify`。
- [ ] 已确认核心主线仓未进入回收站。
- [ ] 已确认试点/论文/产物仓未进入删除或归档候选。
- [ ] 已确认 private（私有）仓库没有被自动标为删除候选。

## archive（归档）前

- [ ] 候选仓已有 `MIGRATED_TO.md`。
- [ ] README（项目说明文件）顶部已有迁移提示。
- [ ] PR（Pull Request，拉取请求）已合并。
- [ ] 无核心仓引用。
- [ ] 无论文、博客、CITATION.cff（Citation File Format，引文文件格式）引用。
- [ ] 无需要保留的独立贡献。

## delete（删除）前

- [ ] 已 archive（归档）。
- [ ] 已观察 2-4 周。
- [ ] 已检查 fork（派生镜像）状态。
- [ ] 已检查本账号独立 commit（提交）。
- [ ] 已检查 issue（议题）和 PR（Pull Request，拉取请求）。
- [ ] 已检查核心仓、论文、博客和外部链接引用。
- [ ] 已获得单独人工批准。
- [ ] 没有把 `delete_repo` 权限交给自动化智能体。
