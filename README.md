# Study Agent MVP

这是一个面向 PC 端的本地学习监督 Agent 原型，目标是：

- 定时抓取屏幕截图
- 采集系统上下文，例如前台窗口标题
- 调用本地多模态模型判断当前学习状态
- 将观测与判断结果存入 SQLite
- 每天北京时间 `23:00` 自动生成学习日报
 - 自动清理过期截图，避免图片无限堆积

## 适合谁

- 想快速验证“屏幕 + 本地多模态模型”方案的人
- 想在本地搭一个可调试、可扩展的学习状态 Agent 的人
- 想基于这个仓库继续加桌面端、规则引擎、提醒系统的人

## 项目结构

- `src/study_agent/config.py`：配置加载
- `src/study_agent/capture/`：屏幕截图
- `src/study_agent/system/`：系统上下文采集
- `src/study_agent/model/`：本地多模态模型客户端
- `src/study_agent/storage/`：SQLite 持久化
- `src/study_agent/reporting/`：日报生成与调度
- `src/study_agent/cleanup.py`：过期截图清理
- `src/study_agent/agent.py`：主 Agent 循环
- `src/study_agent/main.py`：CLI 入口
- `tests/`：基础自动化测试
- `docs/`：架构说明、调试指南与开发说明

## 快速开始

### 1. 进入环境

如果你已经有 `conda` 环境 `agent`：

```bash
conda activate agent
cd /home/zeke/data/project/qmx_project
```

### 2. 安装依赖

```bash
python -m pip install -r requirements-dev.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

然后按你的本地模型实际情况修改 `.env`。

### 4. 先做环境诊断

```bash
make doctor
```

这个命令会检查：

- Python 版本
- 关键路径是否可写
- `xdotool` 是否可用
- 截图模式与保留策略是否合理
- 模型配置是否启用
- 数据库与截图目录配置

### 5. 初始化并运行

```bash
make init-db
make run-once
make run
```

## 常用开发命令

```bash
make install-dev   # 安装开发依赖
make doctor        # 环境诊断
make init-db       # 初始化数据库
make run-once      # 运行一次采集与判断
make run           # 持续运行 Agent
make report        # 生成日报
make format        # 代码格式化
make lint          # 代码检查
make test          # 运行测试
make check         # 运行 lint + test
```

## 调试建议

第一次运行建议按下面顺序：

1. `make doctor`
2. `make init-db`
3. `make run-once`
4. 查看 `data/`、`reports/` 与终端输出

如果模型不返回 JSON、窗口标题为空、或者截图清理行为不符合预期，优先看：

- `docs/debugging.md`
- `docs/architecture.md`
- `.env.example`

如果你用的是 VS Code，也可以直接使用：

- `.vscode/launch.json:1`

里面已经准备好了这些调试入口：

- `Study Agent: Run`
- `Study Agent: Run Once`
- `Study Agent: Doctor`
- `Study Agent: Report Today`

## 开发基础设施

这个仓库已经补齐了基础设施，方便快速上手、调试和协作：

- `pyproject.toml`：打包、测试、lint、format 配置
- `requirements-dev.txt`：开发依赖入口
- `Makefile`：常用命令统一入口
- `.editorconfig`：编辑器风格约束
- `.pre-commit-config.yaml`：提交前自动检查
- `.github/workflows/ci.yml`：CI 自动执行 lint 和测试
- `tests/`：关键链路回归测试
- `docs/`：架构、调试、开发说明

## 环境变量

详见 `.env.example`。

默认模型接口采用 OpenAI 兼容风格，适配 LM Studio、Ollama、vLLM 网关时会比较方便。

## 当前限制

- Ubuntu/Linux 下活动窗口标题依赖 `xdotool`
- Ubuntu/Linux 下空闲时间检测依赖 `xprintidle`
- Windows 下会自动使用 Win32 API 获取前台窗口与空闲时间
- 当前默认是纯屏幕模式，不再抓拍摄像头
- 估算学习时长基于采样间隔推断，不是逐秒精确计时
- 当前启用了严格规则：连续 3 张截图几乎无变化时，直接判定为 `away`
- 这是一个 MVP，更适合验证方案，不是生产级成品
