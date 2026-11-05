# 旧仓库备份与恢复

2026 年 11 月 5 日，五个独立 GitHub 仓库完成整合后已删除，日常维护和分发统一使用私有仓库 `cgvcingcing/agent-skills`。

删除前已核对总仓库中的 82 个导入源文件，五个旧远程的默认分支均与导入基准一致。每个旧远程已保存 Git 镜像和完整 bundle，核对全部远程分支与标签，并从 bundle 创建独立恢复副本，通过 `git fsck --full` 校验。

| 原仓库 | 备份提交数 | 删除后接口状态 |
| --- | ---: | --- |
| `doc2html-skill` | 4 | 404 |
| `interaction-flow` | 2 | 404 |
| `spec2testplan-skill` | 3 | 404 |
| `test-analysis-framework` | 3 | 404 |
| `test-handoff` | 7 | 404 |

五个仓库均无 Issue、PR、Release、已创建的 Wiki、star 或 fork。仓库元数据仍保存为 JSON，便于查阅原配置。

## 备份位置

备份位于完成迁移的本机总仓库目录中：

```text
.state/legacy-repositories/20261105T075846580346Z/
├── manifest.json
├── source-lock.json
├── deletion-status.json
├── restore-verification.json
├── RESTORE.md
└── <原仓库名>/
    ├── <原仓库名>.bundle
    ├── <原仓库名>.git/
    ├── refs.json
    ├── backup-result.json
    └── *.json
```

`.state/` 仅保存在本机，不随 Git 推送；在其他设备克隆总仓库时，不会自动下载这些历史备份。本次交付另有一份包含五个 bundle、校验清单和元数据的 ZIP。备份摘要和删除核验时间见 [source-retirement.json](../source-retirement.json)。

原独立本地工作区和未提交修改也继续保留。原本地仓库的 `origin` 地址已失效，日常修改与推送请使用总仓库。

## 恢复一个旧仓库

在本机总仓库根目录执行，目标目录应尚不存在：

```bash
git clone .state/legacy-repositories/20261105T075846580346Z/doc2html-skill/doc2html-skill.bundle ../recovered-doc2html-skill
git -C ../recovered-doc2html-skill fsck --full
```

其他仓库使用对应名称替换。也可以解压交付 ZIP 后，使用其中 bundle 的实际路径执行 `git clone`。bundle 保存远程 Git 历史；未提交修改保留在原本地工作区，已确认的技能源码版本也已纳入总仓库。

如确需恢复独立 GitHub 仓库，创建空仓库，设置相应可见性，再推送恢复副本中的分支和标签。bundle 不会自动恢复 GitHub 的设置、讨论、工作流运行记录等服务端数据。
