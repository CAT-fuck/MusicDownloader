# 网易云音乐下载器

## 功能
- 支持歌单/单曲下载
- 音质可选：FLAC无损 / MP3 320k / 192k / 128k
- 多线程并发下载（1-10线程）
- 高清封面嵌入（1417x1417）
- 歌词/专辑标签自动写入

## 安装依赖
```bash
pip install PyQt5 requests mutagen
```

## 使用方法
**图形界面：**
```bash
python gui.py
```

**命令行：**
```bash
python downloader.py <链接或ID> [音质索引] [并发数]
# 示例：
python downloader.py "https://music.163.com/m/playlist?id=18106500345" 0 3
```

## 音质索引
- 0: FLAC 无损
- 1: MP3 320kbps
- 2: MP3 192kbps
- 3: MP3 128kbps

## 注意事项
- 周杰伦等强版权歌曲可能无法下载
- 并发数建议3-5，过高可能被限流
- 已下载的歌曲会自动跳过
