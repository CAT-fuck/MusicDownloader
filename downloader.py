# -*- coding: utf-8 -*-
"""
网易云音乐下载器核心库（多线程 + 音质可选）
- FLAC无损 / MP3 320k / 192k / 128k
- 多线程并发下载
- 高清封面、歌词、专辑标签嵌入
"""

import os
import re
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from mutagen.id3 import TIT2, TPE1, TALB, APIC, USLT

METING_API = "https://api.qijieya.cn/meting/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://music.163.com/",
}

QUALITIES = [
    {"br": "2000", "label": "FLAC 无损", "prefer": "flac"},
    {"br": "320",  "label": "MP3 320kbps HQ", "prefer": "mp3"},
    {"br": "192",  "label": "MP3 192kbps", "prefer": "mp3"},
    {"br": "128",  "label": "MP3 128kbps", "prefer": "mp3"},
]

# 默认下载目录：用户目录下的 Music\downloads
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Music", "downloads")


# ---------------- 工具 ----------------

def safe_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()


def detect_format(head):
    if head[:4] == b"fLaC":
        return "flac"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    return "unknown"


def extract_playlist_id(url):
    for p in [r'playlist\?id=(\d+)', r'id=(\d+)', r'/(\d{5,})/?$']:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def get_playlist(playlist_id):
    r = requests.get(METING_API, params={
        "server": "netease", "type": "playlist", "id": playlist_id,
    }, headers=HEADERS, timeout=30)
    songs = r.json()
    return songs if isinstance(songs, list) else []


def get_song(song_id):
    r = requests.get(METING_API, params={
        "server": "netease", "type": "song", "id": song_id,
    }, headers=HEADERS, timeout=15)
    data = r.json()
    return data[0] if (isinstance(data, list) and data) else None


def _song_detail(song_id):
    try:
        r = requests.post("https://music.163.com/api/song/detail",
                          data={"id": song_id, "ids": "[%s]" % song_id},
                          headers=HEADERS, timeout=15)
        songs = r.json().get("songs", [])
        return songs[0] if songs else None
    except Exception:
        return None


def get_album(song_id):
    d = _song_detail(song_id)
    if d:
        return d.get("album", {}).get("name", "") or ""
    return ""


def get_hd_cover(song_id):
    d = _song_detail(song_id)
    if d:
        pic_url = d.get("album", {}).get("picUrl", "")
        if pic_url:
            try:
                r = requests.get(pic_url, headers=HEADERS, timeout=15)
                if r.status_code == 200 and len(r.content) > 1000:
                    return r.content
            except Exception:
                pass
    return b""


def get_lyric(lrc_url):
    if not lrc_url:
        return ""
    try:
        r = requests.get(lrc_url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.text) > 10:
            return r.text
    except Exception:
        pass
    return ""


def embed_tags(path, fmt, title, artist, album, cover, lyric):
    mime = "image/png" if cover[:4] == b"\x89PNG" else "image/jpeg"
    if fmt == "flac":
        audio = FLAC(path)
        audio["title"] = title
        audio["artist"] = artist
        if album:
            audio["album"] = album
        if lyric:
            audio["lyrics"] = lyric
        if cover:
            pic = Picture()
            pic.type = 3
            pic.mime = mime
            pic.desc = "Cover"
            pic.data = cover
            audio.clear_pictures()
            audio.add_picture(pic)
        audio.save()
    else:
        audio = MP3(path)
        if audio.tags is None:
            audio.add_tags()
        t = audio.tags
        t.add(TIT2(encoding=3, text=title))
        t.add(TPE1(encoding=3, text=artist))
        if album:
            t.add(TALB(encoding=3, text=album))
        if cover:
            t.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover))
        if lyric:
            t.add(USLT(encoding=3, lang="zho", desc="", text=lyric))
        audio.save()


# ---------------- 单首下载 ----------------

def download_one(song, output_dir, quality, stop_flag=None):
    """
    下载单首歌曲。
    返回 dict: {ok, skip, msg, name}
    """
    name = song.get("name", "未知")
    artist = song.get("artist", "未知")
    base = safe_filename("%s - %s" % (name, artist))

    # 已存在则跳过
    for ext in ("flac", "mp3"):
        p = os.path.join(output_dir, base + "." + ext)
        if os.path.exists(p) and os.path.getsize(p) > 100_000:
            return {"ok": True, "skip": True, "msg": "已存在", "name": name}

    m = re.search(r'id=(\d+)', song.get("url", ""))
    if not m:
        return {"ok": False, "skip": False, "msg": "无歌曲ID", "name": name}
    song_id = m.group(1)

    # 请求音频流
    try:
        r = requests.get(METING_API, params={
            "server": "netease", "type": "url", "id": song_id, "br": quality["br"],
        }, headers=HEADERS, timeout=60, stream=True)
        first = next(r.iter_content(65536), b"")
        fmt = detect_format(first)
        if fmt == "unknown" or not first:
            r.close()
            return {"ok": False, "skip": False, "msg": "无可用音源(可能是版权锁定?)", "name": name}

        filepath = os.path.join(output_dir, base + "." + fmt)
        tmp_path = filepath + ".part"
        total = len(first)
        with open(tmp_path, "wb") as f:
            f.write(first)
            for chunk in r.iter_content(65536):
                if stop_flag and stop_flag():
                    r.close()
                    f.close()
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                    return {"ok": False, "skip": False, "msg": "已停止", "name": name}
                f.write(chunk)
                total += len(chunk)
        r.close()

        if total < 500_000:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return {"ok": False, "skip": False, "msg": "文件过小(可能是试听)", "name": name}

        os.replace(tmp_path, filepath)
    except Exception as e:
        return {"ok": False, "skip": False, "msg": "下载出错: %s" % e, "name": name}

    # 元数据
    album = get_album(song_id)
    cover = get_hd_cover(song_id)
    lyric = get_lyric(song.get("lrc", ""))
    try:
        embed_tags(filepath, fmt, name, artist, album, cover, lyric)
    except Exception as e:
        return {"ok": True, "skip": False,
                "msg": "完成(标签写入失败: %s)" % e, "name": name}

    return {"ok": True, "skip": False,
            "msg": "%s %s %.1fMB" % (fmt.upper(), quality["label"], total / 1024 / 1024),
            "name": name}


# ---------------- 批量下载 ----------------

def download_batch(songs, output_dir, quality_idx=0, concurrency=3,
                   stop_flag=None, log=None, progress=None):
    """
    批量下载。
    log(text) 输出日志, progress(done, total, ok, fail) 输出进度
    """
    if log is None:
        log = lambda t: None
    if progress is None:
        progress = lambda d, t, o, f: None

    quality = QUALITIES[quality_idx % len(QUALITIES)]
    os.makedirs(output_dir, exist_ok=True)
    total = len(songs)
    done = ok = fail = 0
    lock = threading.Lock()

    log("音质: %s | 并发: %d | 共 %d 首" % (quality["label"], concurrency, total))

    def worker(idx, song):
        if stop_flag and stop_flag():
            return idx, {"ok": False, "skip": False, "msg": "已停止", "name": song.get("name", "?")}
        res = download_one(song, output_dir, quality, stop_flag)
        return idx, res

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [pool.submit(worker, i, s) for i, s in enumerate(songs)]
        for fut in as_completed(futures):
            idx, res = fut.result()
            with lock:
                done += 1
                if res["ok"]:
                    ok += 1
                else:
                    fail += 1
                tag = "跳过" if res.get("skip") else ("OK" if res["ok"] else "失败")
                log("[%d/%d] [%s] %s - %s" % (done, total, tag, res["name"], res["msg"]))
                progress(done, total, ok, fail)
            if stop_flag and stop_flag():
                break

    log("=" * 40)
    log("下载完成喵! 成功 %d | 失败 %d | 共 %d" % (ok, fail, total))
    return {"total": total, "ok": ok, "fail": fail}


# ---------------- CLI 入口 ----------------

if __name__ == "__main__":
    import sys
    print("CAT的网易云音乐下载器 (FLAC无损优先)")
    print("=" * 40)
    if len(sys.argv) < 2:
        print('用法: python downloader.py <歌单链接|歌曲ID> [音质0-3] [并发1-10]')
        print('示例: python downloader.py "https://music.163.com/m/playlist?id=18106500345" 0 3')
        sys.exit(0)

    url = sys.argv[1]
    q = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    c = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    if url.isdigit():
        songs = get_song(url)
        songs = [songs] if songs else []
    else:
        pid = extract_playlist_id(url)
        songs = get_playlist(pid) if pid else []

    if not songs:
        print("错误: 无法获取歌曲列表!")
        sys.exit(1)

    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    download_batch(songs, DEFAULT_OUTPUT_DIR, q, c)