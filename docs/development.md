# 开发说明

## 开发依赖安装

```bash
python -m pip install -r requirements-dev.txt
```

## 提交前建议执行

```bash
make format
make lint
make test
```

或者直接：

```bash
make check
```

## pre-commit

安装：

```bash
pre-commit install
```

之后每次提交前会自动执行基础检查。

## 测试策略

当前测试覆盖的是基础设施与核心流程中最容易回归的部分：

- 配置加载
- 日报调度
- 数据库存取与汇总
- 日报生成
- 环境诊断

## 后续建议补充的测试

- 模型返回异常 JSON 的解析测试
- 摄像头不可用时的降级测试
- `xdotool` 不存在时的上下文采集测试
- 主循环单轮执行的集成测试
