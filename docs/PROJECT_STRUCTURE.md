# 项目目录与清理说明

| 路径 | 用途 | 上传仓库 / 公开源码 |
| --- | --- | --- |
| web/ | 网页 UI、简历与 Markdown 编辑、同步码 | 是 |
| portable/ | 无服务器离线 API、资源打包和测试 | 是 |
| android-client/src、res、tools | Android 客户端、图标和构建脚本 | 是 |
| server.py 与根目录校验模块 | 本地 Python / SQLite 服务 | 是 |
| tests.py、test_*.py | 临时数据库测试，不读用户资料 | 是 |
| tools/、.github/、docs/ | 发布脚本、自动构建和说明 | 是 |
| data/ | 用户数据库、会话、原始业务备份 | 否，保留本机 |
| android-client/.signing/ | 原有签名密钥与密码 | 否，保留本机；CI 仅使用授权的加密 Secrets |
| android-client/build/ | 编译中间文件 | 否，可重建 |
| releases/、dist/ | 生成的安装包与压缩包 | 不入 Git；仅经白名单打包的产物进入 Releases |
| .local-history/ | 历史发布包和本机旧资料备份 | 否 |

已清理的内容：过期编译中间文件、Python 缓存、旧预览截图和过期生成包。历史发布中的个人备份移到本机忽略目录，不上传、不删除用户原始数据。公开版本从源码重建，不复用含个人迁移备份的旧压缩包。

上传前使用 `python3 tools/audit_release.py` 检查源码白名单和生成包。签名证书的 SHA-256 公共指纹可以公开，私钥与密码不能进入 Git、源码包、日志或 Releases。

网页样式已按原加载顺序合并为 `web/app.css`，保留级联效果，删除分散的历史覆盖文件。JavaScript 按功能保留独立模块。
