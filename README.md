# Study Agent MVP

一个面向 PC 端的本地学习状态监督 Agent MVP：

- 定时捕获屏幕截图
- 定时抓拍摄像头图像
- 采集系统上下文（活动窗口、键鼠空闲状态占位）
- 调用本地多模态模型判断当前学习状态
- 将观测和判断写入 SQLite
- 每天北京时间 23:00 自动生成当日学习总结报告

## 架构

- `src/study_agent/config.py`：配置加载
- `src/study_agent/capture/`：屏幕与摄像头采集
- `src/study_agent/system/`：系统上下文采集
- `src/study_agent/model/`：本地多模态模型客户端
- `src/study_agent/storage/`：SQLite 持久化
- `src/study_agent/reporting/`：日报生成与调度
- `src/study_agent/agent.py`：主 Agent 循环
- `src/study_agent/main.py`：CLI 入口

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m study_agent.main init-db
python -m study_agent.main run-once
python -m study_agent.main run
```

## 环境变量

见 `.env.example`。

默认模型接口按 OpenAI Responses/Chat Completions 风格的本地兼容服务设计，适配 Ollama、LM Studio、vLLM 网关时只需要调整 URL 与模型名。

## 说明

- 当前版本优先保证架构完整与可运行。
- Linux 下活动窗口标题通过 `xdotool` 获取；若不可用则自动降级。
- 键鼠空闲时间当前为占位实现，可按目标平台补充系统 API。
- 若未配置模型，系统会使用启发式降级判断，保证日报链路可用。
