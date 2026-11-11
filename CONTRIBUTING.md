# Contributing

欢迎改进 endpoint-watch。请先在 Issue 中说明具体问题、预期行为和复现命令，再提交范围清晰的 Pull Request。
请勿在公开问题、日志或测试中包含访问令牌、密码或内部服务地址。

开发需要 Python 3.10+，无需第三方运行或测试依赖：

```sh
python3 -m unittest discover -s tests -v
python3 -m endpoint_watch --help
```

修复行为时，请补充能复现问题的本地测试。涉及网络的测试使用回环地址和随机端口，避免依赖外部网站。
请保持 CLI 的退出码约定；变更 JSON 字段时说明兼容性影响。

提交代码表示你有权以本项目的 MIT 许可证贡献该代码。贡献者会保留在 Git 提交历史中。
