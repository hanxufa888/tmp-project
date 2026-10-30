# STEER speccheck-workflow 功能测试

使用 `harbor-speccheck:2.1.304-docx-xlsx-v2`，检查新版
`MET-C_STEER-CSTD-A0-05-A-C0.xlsm`，固定以本地
`MET-C_STEER-CSTD-A0-04-A-C0.xlsm` 为旧版。两份原文件已分别放在
[environment/old](environment/old/) 和 [environment/new](environment/new/)。
未复制原目录中的人工评审结果、已有 Markdown 或差分报告，避免答案泄露。

## 测试范围

- Claude 自行加载 `speccheck-workflow`，执行 Step 1–4；不提供转换包装脚本。
- 仅覆盖文本和表格。旧版含 4 张 EMF + 1 张 PNG，新版含 4 张 EMF + 14 张 PNG；
  **所有图片均不提取或检查**，不是仅跳过 EMF。图片相关未覆盖项必须单独说明。
- v2 基础镜像默认文本模式。直接使用 `speccheck convert` 和
  `speccheck local-diff`，由入口统一关闭图片提取，允许含 EMF 的工作簿。
- 使用镜像自带的项目说明；不需要任务级 CLAUDE.md、解析配置副本或转换包装脚本。
  原有 v1 镜像不变。更新 FROM 后必须重新构建任务镜像。
- MCP 用于关联规格检查，其他规格搜索限定 `MET_COMMON`，不是离线完整检查。
  MCP 认证失败必须记录，不能描述为检查成功。

## 运行

先在当前 shell 中设置 `ANTHROPIC_AUTH_TOKEN` 和 `KGA_MCP_AUTHORIZATION`；
后者包含服务要求的完整 Authorization 值。不要将凭据写入任务文件。
确认 Docker 中已有基础镜像、模型网关可访问，以及本地 OTel/MLflow 服务可用：

```bash
bash examples/tasks/MET-C_STEER-CSTD/run.sh
```

默认使用 Claude Code 2.1.304、模型 `gpt-6.1-sol`，单次 agent 最长 7200 秒。
支持 `MODEL`、`ANTHROPIC_BASE_URL`、`RESULTS_ROOT`、`JOB_NAME`、
`OTEL_ENDPOINT`、`OTEL_EXPERIMENT` 覆盖运行参数。
MCP 地址在 [task.toml](task.toml) 中配置；换环境时同步修改。

默认结果位置：`/mnt/d/harbor-kga-results/<job>/<trial>/`：

```text
artifacts/workflow/
  spec_diff.csv / spec_diff.html / spec_diff.json
  MET-C_STEER-CSTD-A0-05-A-C0_check_results/
  MET-C_STEER-CSTD-A0-05-A-C0_report.md
  MET-C_STEER-CSTD-A0-05-A-C0_report.xlsx
  limitations.md
artifacts/check_spec/                 # 新版原文件及转换后的 Markdown
verifier/reward.txt
verifier/checks.json                  # 验证成功时生成
agent/                               # 轨迹及工具日志
```

本地 OTel 导出位于 `<job>/otel-traces.jsonl`。上传成功不代表任务成功。

## 验证含义与复用

验证器检查输入未改变、成功加载 workflow、本地新旧版差分、Step 2 标签、
Step 3 结果完整性、Markdown/Excel 报告及文本模式限制说明。
`reward=1` **仅表示这些功能性条件满足**，不证明业务判定正确、标签选择正确、
MCP 调用成功或图片检查完成。报告中的“問題あり”本身不是测试失败。
需要结合 `limitations.md` 和实际轨迹人工审核。

该任务可独立复制；两个案例保留相同的自包含验证器，避免跨任务文件依赖。
更换输入时更新两份文件、Dockerfile 的新版目录、instruction.md 和本说明，
并重建任务镜像。不要恢复旧的转换包装脚本，或把输入文件放入目录却忘记 COPY。

准备阶段已验证：v2 任务镜像构建成功；断网容器中通过默认 `speccheck` 入口完成新版 Markdown
转换（151,728 字节）、本地差分（52 条）和 Step 1 JSON 生成（52 条），
输入哈希保持不变。此结果不是 Claude/MCP 的完整 Step 1–4 实跑结果。
迁移后重跑原 Harbor 命令时可加 `--force-build`，确保使用更新后的任务镜像。
