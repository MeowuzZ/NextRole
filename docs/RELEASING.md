# 构建与发布

## 本地打包

需要 Python 3.10+、Node.js 22+、JDK 11 或以上，以及 Android SDK：`platforms;android-34` 和 `build-tools;34.0.0`。

```sh
python3 -m unittest tests.py test_experience.py test_sync.py
node portable/tests.cjs
node portable/sync-tests.cjs
python3 android-client/tools/build.py
python3 tools/package_release.py --output dist
python3 tools/audit_release.py
```

设置 `ANDROID_SDK_ROOT` 或 `ANDROID_HOME`，Java 通过 `JAVA_HOME` 或已安装的 java 定位。macOS 本机已有 SDK / JDK 的默认位置也可使用。

产物：`dist/NextRole-Web.zip`、`dist/NextRole.apk`、`dist/NextRole-Source.zip`、`dist/SHA256SUMS.txt`。网页版与 APK 初次运行均无个人资料，使用同步码迁移。

## 签名与覆盖升级

应用显示名称为 NextRole，保留 `com.qitu.local` 包名和原签名证书，避免丢失覆盖升级兼容性。`.signing/` 中保留的历史文件名和内部桥接名属于兼容性实现，不是界面品牌。

现有私钥保留在本地忽略目录。CI 仅从两个仓库 Actions Secrets 中恢复临时文件：

- `ANDROID_KEYSTORE_BASE64`：现有 PKCS12 密钥的 Base64。
- `ANDROID_KEYSTORE_PASSWORD`：该密钥的密码。

仅在获授权后运行 `python3 tools/configure_signing.py`，通过已登录的 GitHub CLI 加密上传，脚本不输出凭据。Secrets 只授权给本仓库发布流程。缺少凭据时 CI 明确失败，不会生成随机密钥冒充可升级版本。签名指纹与 `android-client/signing-certificate.sha256` 必须一致。

## 自动发布

`.github/workflows/release.yml` 在主分支更新、推送 `v*` 标签或手动触发时执行：

1. 使用固定 SHA 的 GitHub 官方动作准备 Python、Node 和 Java。
2. 运行后端、离线存储及同步码测试，检查 JavaScript 语法。
3. 安装固定 Android SDK 组件，从 Secrets 恢复原签名。
4. 构建 APK，验证签名指纹和 zipalign 对齐。
5. 仅打包白名单源码与空白网页，生成 SHA-256 校验文件。
6. 生成不可变的版本 Release；主分支最新提交对应的构建标记为 Latest。
7. 删除 runner 临时签名文件。

`VERSION` 控制版本名称。自动构建使用 `100000 + github.run_number` 作为 Android versionCode，以便主分支持续更新时仍可覆盖安装。需要手动安装较低代码的本地构建时，应显式设置更高的 `NEXTROLE_VERSION_CODE`；不要卸载含未备份资料的旧应用来绕过版本限制。

发布地址：`https://github.com/MeowuzZ/NextRole/releases/latest`。固定下载链接的资产名保持不变，因此链接会随 Latest 更新。
