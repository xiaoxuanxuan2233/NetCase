# 读懂 NetCase 的第一条诊断

## 输入、API 和任务

`core/targets.py` 与 `models/schemas.py` 先把域名、IP、URL、端口、超时变成明确类型，拒绝凭据和越界参数；`main.py` 启动最多两个异步任务。Pydantic 的 validator 负责边界检查，`asyncio` 让页面轮询时服务仍能响应。验证方法：提交包含账号密码的 URL，应获得 422；用 `/api/diagnoses/{id}` 查看每一步状态。若表单报错，先看前端 Network 面板请求状态，再看后端模型错误。

## DNS

`diagnostics/dns.py` 默认读取本机解析器，发送 A、AAAA、CNAME 查询，记录响应码和时间。UDP 报文可能截断，届时改用 TCP；NXDOMAIN 与 SERVFAIL 有不同含义。Python 的 `struct`、`socket` 和字节偏移用于解包，`asyncio.to_thread` 使阻塞 DNS socket 不挡住事件循环。验证：阅读 `test_dns_wire_parser_reads_address_cname_and_rcode`；实机对比系统 DNS 与显式选用的公开解析器。出错先看记录里的解析器 IP、RCODE、超时及系统 DNS 配置。不同 IP 常由 CDN 调度造成，不能单凭差异判断污染。

## TCP 与 TLS

`diagnostics/tcp.py` 对最多八个解析地址分别连接所选端口，标明 IPv4/IPv6、拒绝或超时；`tls.py` 在验证证书的默认 SSLContext 中单独握手。`asyncio.wait_for` 是单次上限；证书名称验证由 Python SSL 库完成，不关闭安全检查。验证：Mock 拒绝、超时、证书过期，或在你控制的测试服务上运行。TCP 成功只证明三次握手可建立；TLS 失败还要看证书链、主机名或协议。先检查目标端口和系统时间，再看模块证据。

## HTTP 与系统命令

`http.py` 逐跳解析并固定连接到已验证的地址，至多五次跳转，只读取最多 32 KiB 响应头，不存正文。HTTP 503 是服务端响应，不是 TCP 不通。`commands.py` 对 Ping / traceroute 使用固定参数数组，限制跳数、样本数和运行时间。验证：Mock 503 与私网重定向；在有系统工具的 Windows/macOS/Linux 主机手工对照命令输出。无 ICMP 回复不等于网页打不开；先看工具是否安装以及权限和原始节选。

## 规则、数据库与报告

`analyzers/rules.py` 把测量和解释分开：每项结论携带证据、可能原因、信心类别和下一步，避免凭空猜测。`storage/database.py` 用 SQLAlchemy 模型写入本地 SQLite，`reports/export.py` 在输出前脱敏。验证：对照 API 记录与导出，确认备注和私网地址没有泄露；比较两次结果时核对网络标记、DNS、地址族、端口和时间。记录为空先看本地数据目录权限；报告异常先找对应记录 ID 与模块证据，不要分享未检查的原始数据库。

## 前端

React 的 state 存放表单和进度，Effect 异步读取设置与任务，TypeScript 类型与后端数据结构对应；不同页面复用同源 API。验证：`npm test` 检查错误输入、加载、历史空态、结果证据、设置保存；`npm run build` 同时做严格类型检查。页面一直加载时先确认本地服务、浏览器 Network 请求和返回码，再核对 Job ID 是否过期。

## 小练习

1. 给 DNS 规则增加一条针对 SERVFAIL 的下一步建议，并写 Mock 测试确认引用了原始错误类型。
2. 用本地 HTTP 测试服务产生一次 302，再改为跳到回环地址，观察为什么重定向被阻断。
3. 在设置里修改超时为 5 秒，重新打开新建诊断，确认默认值和实际 API 参数一致。
