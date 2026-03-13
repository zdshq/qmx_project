# 调试指南

## 一、先跑环境诊断

推荐先执行：

```bash
make doctor
```

如果这里有异常，先修环境，不要急着跑主循环。

## 二、常见问题

### 1. 摄像头打不开

可能原因：

- 当前机器没有摄像头
- 摄像头不是 `0` 号设备
- 摄像头被别的程序占用
- 当前环境无法访问宿主机摄像头

建议：

- 修改 `.env` 中的 `STUDY_AGENT_CAMERA_INDEX`
- 先执行 `make doctor`
- 再执行 `make run-once`

### 2. 窗口标题拿不到

Linux 下依赖 `xdotool`。

如果没安装，系统会自动降级，但前台应用判断能力会变弱。

### 3. 本地模型调用失败

优先检查：

- `STUDY_AGENT_MODEL_ENABLED`
- `STUDY_AGENT_MODEL_BASE_URL`
- `STUDY_AGENT_MODEL_NAME`
- 本地模型服务是否真的启动

### 4. 模型返回不是标准 JSON

项目已经做了几层兼容：

- 直接 JSON
- 包裹在 Markdown code fence 的 JSON
- 带额外解释文本时提取首个 JSON 对象

如果仍然不稳定，建议固定你的模型 system prompt。

### 5. 日报没有生成

检查：

- 当前时区是不是 `Asia/Shanghai`
- 当前时间是否已过 `23:00`
- 是否有采样数据写入数据库

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
- `data/study_agent.db`
- `reports/`
- `data/captures/`
