# endpoint-watch

轻量的 HTTP 服务健康检查工具。输入一个或多个服务地址，查看可达性、最终状态码和响应耗时，支持文本与 JSON 报告。
适用于开发自检、部署验证和 CI 检查。

## 功能

- 检查一个或多个 HTTP / HTTPS 地址，自动跟随重定向。
- 最终响应为 `2xx` 时判定健康；HTTP 错误、连接失败、超时和重定向循环判定失败。
- 显示状态码、最终 URL、获取响应头的耗时和错误原因。
- 输出易读文本或 JSON 报告，用进程退出码接入 CI。
- 仅使用 Python 标准库，无第三方运行依赖；HTTPS 使用系统证书校验。

## 快速开始

需要 Python 3.10 或更新版本。克隆后即可运行，无需安装依赖：

```sh
git clone https://github.com/sainentl/endpoint-watch.git
cd endpoint-watch
python3 -m endpoint_watch https://example.com
```

Windows 中可将 `python3` 换成 `python`。

检查多个服务，并将 socket 超时设为 3 秒：

```sh
python3 -m endpoint_watch http://localhost:8080/health https://example.com --timeout 3
```

文本报告示例，耗时随环境变化：

```text
OK https://example.com [200, 126.58 ms]
1/1 healthy
```

输出 JSON，适合 CI 读取或保存：

```sh
python3 -m endpoint_watch https://example.com --json > report.json
```

报告结构：

```json
{
  "results": [
    {
      "url": "https://example.com",
      "final_url": "https://example.com",
      "ok": true,
      "status_code": 200,
      "elapsed_ms": 126.58,
      "error": null
    }
  ],
  "summary": {"total": 1, "healthy": 1, "unhealthy": 0}
}
```

也可以在虚拟环境安装本地项目，使用短命令：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/endpoint-watch https://example.com --json
```

Windows 对应命令为 `.venv\Scripts\python -m pip install .` 和 `.venv\Scripts\endpoint-watch`。
项目尚未发布到 PyPI，安装时请使用本仓库源码。

## 退出码与行为

| 退出码 | 含义 |
| --- | --- |
| `0` | 所有地址均健康 |
| `1` | 至少一个地址检查失败 |
| `2` | 命令参数无效 |

检查按输入顺序串行执行，发送 GET 请求，收到响应头后关闭连接，不读取响应体。
`--timeout` 默认 5 秒，允许大于 0 且不超过 86400 秒；约束连接和 socket 操作，不是整个批次或重定向链的总时限。
耗时包括连接、TLS 和重定向，不衡量页面内容加载速度。
工具检查可达性，不检查响应体是否符合业务预期，也不提供后台持续监控。

URL 不支持内嵌用户名和密码。中文域名请使用 IDNA 形式，非 ASCII 路径请进行百分号编码。
网络连接失败时 `status_code` 和 `final_url` 为 `null`；收到 HTTP 错误响应时保留状态码和最终 URL。

## 开发与测试

```sh
python3 -m unittest discover -s tests -v
```

测试使用本地临时 HTTP 服务，覆盖正常响应、重定向、HTTP 错误、重定向循环、连接失败、超时、JSON 输出和参数校验，不依赖外部网站。
GitHub Actions 在 Linux / Windows、Python 3.10 / 3.14 上运行测试，并验证安装后的命令入口。

欢迎提交可复现的问题和代码改进，请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE)
