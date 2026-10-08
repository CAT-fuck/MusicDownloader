# 极品网易云歌单下载器 / Ultimate Netease Cloud Music Playlist Downloader

一个 Windows 桌面工具，支持批量下载网易云音乐歌单歌曲，可自定义音质与保存目录。  
A Windows desktop tool for batch downloading songs from Netease Cloud Music playlists, with customizable audio quality and save directory.

<img width="949" height="746" alt="image" src="https://github.com/user-attachments/assets/134fdbcb-8453-4800-bfe6-93e304df630b" />


## 功能特性 / Features

- **歌单批量下载**：输入网易云歌单链接，一键下载全部歌曲  
  **Playlist Batch Download**: Paste a Netease Cloud Music playlist link to download all songs at once

- **多音质可选**：支持标准、较高、极高、无损等音质选项  
  **Multiple Quality Options**: Supports standard, higher, highest, and lossless audio quality

- **自定义保存目录**：可自由选择歌曲保存位置  
  **Custom Save Directory**: Choose where to save your downloaded songs

- **并发数可调**：通过滑块控制同时下载的线程数，平衡速度与稳定性  
  **Adjustable Concurrency**: Control the number of download threads via slider to balance speed and stability

- **实时进度显示**：显示当前下载进度、成功/失败数量  
  **Real-time Progress**: Shows download progress, success/failure counts

- **随时启停**：支持中途停止下载任务  
  **Start/Stop Anytime**: Pause or stop downloads at any point

- **打包即用**：单文件 exe，无需安装 Python 环境  
  **Ready to Use**: Single-file exe, no Python installation required

## 使用说明 / Usage

1. 打开软件，在歌单链接输入框中粘贴网易云音乐歌单链接  
   Open the app and paste a Netease Cloud Music playlist link in the input field

2. 选择想要的音质  
   Select your desired audio quality

3. 点击「📁」按钮选择保存目录  
   Click the "📁" button to choose a save directory

4. 拖动滑块设置并发线程数（默认即可）  
   Drag the slider to set concurrent threads (default is fine)

5. 点击「⬇ 开始下载」按钮开始  
   Click "⬇ Start Download" to begin

6. 下载过程中可随时点击「⏹ 停止」中断任务  
   Click "⏹ Stop" at any time to interrupt the download

## 系统要求 / System Requirements

- Windows 10 / 11（64 位）/ Windows 10 / 11 (64-bit)
- 无需安装任何额外组件 / No additional components required

## 常见问题 / FAQ

**Q：任务栏图标显示为白色方块？**  
**Q: Taskbar icon shows as a white square?**

A：这是 Windows 图标缓存问题。将 exe 复制到桌面运行，或重启资源管理器即可。  
A: This is a Windows icon cache issue. Copy the exe to the desktop or restart Explorer.

**Q：下载速度慢？**  
**Q: Slow download speed?**

A：尝试增大并发线程数，但过高可能导致被限流，建议 3~5 之间。  
A: Try increasing concurrent threads, but too high may cause rate limiting. 3–5 is recommended.

**Q：部分歌曲下载失败？**  
**Q: Some songs fail to download?**

A：可能是版权限制或链接失效，属正常现象，不影响其他歌曲下载。  
A: This may be due to copyright restrictions or expired links. Other songs are unaffected.

## 作者 / Author

- **作者 / Author**：CAT是猫不是喵
- **GitHub**：https://github.com/CAT-fuck/MusicDownloader/
- Bug Report Email: catmiao14514@163.com
