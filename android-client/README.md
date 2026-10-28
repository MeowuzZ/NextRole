# NextRole Android

Android 8.0+，系统 WebView 110+。Java Activity + 离线 WebView，应用私有 SQLite 保存资料，无联网权限。

构建、签名和自动发布见 [发布说明](../docs/RELEASING.md)。保留原应用包名与证书以支持覆盖升级，界面统一显示 NextRole。

```sh
python3 android-client/tools/build.py
```

输出 `releases/NextRole-Android-<VERSION>.apk`，包含当前全部网页资源。安装包完成签名指纹和对齐校验；未宣称完成完整真机验收。
