# 小幂：同板小智摄像头候选固件云编译

这是待编译的最小上传包，不是可以烧录的 bin。目标为 GOOUUU ESP32-S3-CAM V1.5 N16R8、用户确认 OV3660、ST7789 240×240。相机板族 GPIO 与官方小智配置已交叉核对；尚未完成实机验证。

## 在 GitHub 编译

1. 新建一个空仓库，或使用你有写权限的专用仓库。
2. 上传本文件夹内的 `.github`、`firmware`、`.gitattributes` 和 `README.md`，保留目录结构。不要只把 ZIP 当成单个文件上传。
3. 在仓库 Actions 中找到 **Mebot camera compile-only validation**，点击 **Run workflow**。如果工作流没有出现，确认 `.github/workflows/mebot-camera-build.yml` 在默认分支。
4. 完成后查看日志和候选 artifact。失败则保留首个构建错误日志交给开发者处理，不要关闭校验来绕过错误。

工作流从官方指定 commit 拉取源码，严格应用补丁，用 ESP-IDF 5.4.2 编译和合并镜像。没有连接设备或烧录步骤。完整 SDK 在云端，不需要装到这台电脑。

## 固件边界

- `UPSTREAM-PINS-UNVERIFIED` 名称保留为醒目的实机未验收标记；它不否认已完成的板族 GPIO 文档核验。
- 编译成功只能证明源码能在该工具链构建；固件大小、镜像地址、备份恢复、语音/屏幕/相机功能都需要随后核验。
- 上传包故意不携带全部参考源码，所以包内不能单独执行 `--reference-check`；完整离线审阅材料在本机主工程 `firmware/xiaozhi-camera/`。云端 `--source ... --apply` 会校验远端完整源码中的21个原文件。
- 未更改现有设备固件；音乐、人脸模型、MCP 接入点、Wi-Fi 信息和接线视频均不在本包。

此文件夹由 `tools/prepare_camera_cloud_bundle.py` 生成，脚本不上传、不运行工作流、不下载 SDK。
