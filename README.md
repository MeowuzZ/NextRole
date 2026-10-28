# NextRole

A local-first job search board for the web and Android. We hope everyone has a successful job search. Suggestions are welcome.

NextRole 是一个离线求职工作台：用一份总表关联岗位、投递进度、简历、面试安排和经验记录。网页与 Android 的资料均存储在设备本地。

## 下载

从 [最新发布](https://github.com/MeowuzZ/NextRole/releases/latest) 获取：

- [本地网页版](https://github.com/MeowuzZ/NextRole/releases/latest/download/NextRole-Web.zip)：完整解压后，使用 Chrome / Edge 打开 `NextRole-Web/index.html`，不需要服务器。
- [Android APK](https://github.com/MeowuzZ/NextRole/releases/latest/download/NextRole.apk)：Android 8.0+，Android System WebView 110+。
- [完整源码](https://github.com/MeowuzZ/NextRole/releases/latest/download/NextRole-Source.zip)及 `SHA256SUMS.txt` 校验文件。

发布包不包含使用者资料、账号密码、签名私钥或演示备份。首次打开为空白，可手动载入演示数据。

## 功能

- 求职总表、看板和日程共享一份数据；点击序号打开详情，阶段可以在表格中直接修改。
- 五类阶段及子阶段：投递简历、笔试／测评、面试、Offer Call、终止流程。支持多项测评截止时间、面试安排、提醒和进度撤销；已撤销记录不展示。
- 简历编辑、预览、必填校验、多段经历与本地照片；可选经历允许删除至零项，预览不遮蔽文字。保存按钮位于页面底部。
- 经验表单以阶段变动前的一级阶段为主体；面试记录区分群面／Solo 面，人数为 1–20 循环滚轮，中央选框固定。
- Markdown 所见即所得编辑，支持标题、列表、加粗、斜体、引用与行内代码；兼容已有 Markdown 笔记。
- 同步码以较新版本覆盖较旧版本，保留来源修改时间；同步前自动保留恢复快照。
- 明亮的 Liquid Glass 风格、圆角文字按钮、移动端底部导航和减少动态效果适配。

## 数据与同步

资料不会自动上传到 GitHub 或其他服务器。网页与 Android 各自保存独立资料，通过总表的“生成同步码”和“导入同步码”迁移。同步包含简历、照片、岗位、流程、经验、提醒和回收站，不包含登录凭据。

只有资料实际变更才推进最后修改时间。查看、筛选、导出、预检和未改变内容的保存不会推进时间；旧资料首次启用时建立一次基线。导入时间较旧或相同的同步码会被拒绝，只有较新时间可以覆盖，且导入前备份可以在设置页下载、恢复。

同步码使用 GZIP 压缩、Base64URL 编码和 SHA-256 校验，复制粘贴允许空格与换行；选填同步密码后采用 PBKDF2-SHA256（210000 次）与 AES-256-GCM 加密。未设置密码的同步码不保密，持码者可以恢复其中资料。同步码没有独立的文本长度上限，实际容量受浏览器和设备限制。

更新网页版文件位置、换浏览器或换设备前，请先生成同步码留存资料。Android 沿用原有应用包名和签名证书，支持覆盖升级。

## 从源码运行

依赖：Python 3.10+、Node.js 22+（测试和同步码测试使用）。本地网页服务无需第三方 Python 库。

```sh
python3 server.py
```

打开 `http://127.0.0.1:18080`，首次创建本机账号。macOS 也可双击 `启动工作台.command`。资料存储在忽略上传的 `data/` 目录。

```sh
python3 -m unittest tests.py test_experience.py test_sync.py
node portable/tests.cjs
node portable/sync-tests.cjs
```

## 打包与自动发布

详见 [发布说明](docs/RELEASING.md)。主分支更新、推送 `v*` 标签或手动运行 Actions 后，自动测试、构建 APK、制作干净的网页与源码压缩包，并发布到 Releases。只有当前主分支对应的构建标记为 Latest，避免旧任务覆盖新版本。

- `VERSION`：产品版本。
- `android-client/`：Java Activity、私有 SQLite 与离线 WebView 构建。
- `portable/`：纯本地 API、IndexedDB / Android 桥接和资源打包。
- `web/`：共享界面与交互。
- `tools/`：发布打包与签名配置辅助脚本。
- [更新日志](CHANGELOG.md)：完整的实现与版本变化。
- [设计规则](docs/DESIGN.md)：配色、层级、间距、控件与反馈规范。
- [目录与清理说明](docs/PROJECT_STRUCTURE.md)：源码、用户资料和构建产物的边界。

界面已做代码与功能测试；历史模拟器操作工具存在窗口识别限制，不能将其视为完整的逐屏视觉或真机验收。
