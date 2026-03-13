# 调试指南

## 一、先跑环境诊断

推荐先执行：

```bash
make doctor
```

如果你在 VS Code 里调试，可以直接打开：

- `Run and Debug`
- 选择 `.vscode/launch.json:1` 里的配置

最常用的是：

- `Study Agent: Run`
- `Study Agent: Run Once`
- `Study Agent: Doctor`

如果这里有异常，先修环境，不要急着跑主循环。

## 二、常见问题

### 1. 窗口标题拿不到

Ubuntu/Linux 下依赖 `xdotool`。

如果没安装，系统会自动降级，但前台应用判断能力会变弱。

Windows 下默认通过 Win32 API 获取，不需要 `xdotool`。

### 2. 本地模型调用失败

优先检查：

- `STUDY_AGENT_MODEL_ENABLED`
- `STUDY_AGENT_MODEL_BASE_URL`
- `STUDY_AGENT_MODEL_NAME`
- 本地模型服务是否真的启动

### 3. 模型返回不是标准 JSON

项目已经做了几层兼容：

- 直接 JSON
- 包裹在 Markdown code fence 的 JSON
- 带额外解释文本时提取首个 JSON 对象

如果仍然不稳定，建议固定你的模型 system prompt。

### 4. 日报没有生成

检查：

- 当前时区是不是 `Asia/Shanghai`
- 当前时间是否已过 `23:00`
- 是否有采样数据写入数据库

### 5. 截图没有自动清理

检查：

- `STUDY_AGENT_CAPTURE_RETENTION_HOURS`
- `data/captures/screen/` 中截图的修改时间
- 主循环是否仍在正常运行

## 三、推荐调试顺序

```bash
make doctor
make init-db
make run-once
make report
```

## 四、调试时重点看哪些地方

- `.env`
- 终端打印的 `state`、`focus`、`reason`
- `idle_seconds`
- `data/study_agent.db`
- `reports/`
- `data/captures/`
