
# -*- coding: utf-8 -*-
"""网易云音乐下载器 - PyQt5 GUI (多线程+音质选择)"""
import sys
import os
import ctypes

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QProgressBar, QLabel,     QFileDialog, QGroupBox, QComboBox, QSpinBox, QSlider
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

import downloader


# ==================== 资源路径(打包后兼容) ====================
def _get_resource_path(relative_path):
    """获取资源文件路径，兼容PyInstaller打包环境"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ==================== 下载线程 ====================
class DownloadWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int, int, int)  # done, total, ok, fail
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, output_dir, quality_idx, concurrency, parent=None):
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.quality_idx = quality_idx
        self.concurrency = concurrency
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            # 获取歌曲列表
            if self.url.strip().isdigit():
                s = downloader.get_song(self.url.strip())
                songs = [s] if s else []
            else:
                pid = downloader.extract_playlist_id(self.url.strip())
                if not pid:
                    self.error.emit("无法解析链接，请检查是否为网易云歌单链接或歌曲ID")
                    return
                self.log.emit("正在获取歌单...")
                songs = downloader.get_playlist(pid)

            if not songs:
                self.error.emit("歌单为空或无法访问")
                return

            self.log.emit("获取到 %d 首歌曲，开始下载..." % len(songs))

            result = downloader.download_batch(
                songs,
                self.output_dir,
                quality_idx=self.quality_idx,
                concurrency=self.concurrency,
                stop_flag=lambda: self._stop,
                log=lambda t: self.log.emit(t),
                progress=lambda d, t, o, f: self.progress.emit(d, t, o, f),
            )
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.output_dir = os.path.join(os.path.expanduser("~"), "Music", "downloads")
        os.makedirs(self.output_dir, exist_ok=True)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("网易云音乐下载器")
        self.setMinimumSize(680, 620)
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; color: #eee; }
            QWidget { color: #eee; }
            QGroupBox { border: 1px solid #444; border-radius: 8px; margin-top: 10px; padding-top: 6px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #64ffda; }
            QLineEdit { background: #16213e; border: 1px solid #0f3460; border-radius: 4px; padding: 7px; }
            QLineEdit:focus { border: 1px solid #64ffda; }
            QPushButton { background: #0f3460; border: none; border-radius: 4px; padding: 8px 18px; color: #eee; }
            QPushButton:hover { background: #533483; }
            QPushButton:pressed { background: #e94560; }
            QPushButton:disabled { background: #333; color: #777; }
            QPushButton#stopBtn { background: #6e2b2b; }
            QPushButton#stopBtn:hover { background: #e94560; }
            QPushButton#dirBtn { background: #2d4a2d; }
            QPushButton#dirBtn:hover { background: #3d6a3d; }
            QTextEdit { background: #0f3460; border: 1px solid #533483; border-radius: 4px; }
            QProgressBar { border: 1px solid #533483; border-radius: 4px; background: #16213e; text-align: center; }
            QProgressBar::chunk { background: #64ffda; border-radius: 3px; }
            QComboBox, QSpinBox { background: #16213e; border: 1px solid #0f3460; border-radius: 4px; padding: 5px; min-width: 80px; color: #eee; }
            QComboBox QAbstractItemView { background: #16213e; border: 1px solid #0f3460; selection-background-color: #533483; }
            QSlider::groove:horizontal { border: 1px solid #533483; height: 8px; background: #16213e; margin: 2px 0; }
            QSlider::handle:horizontal { background: #64ffda; border: 1px solid #0f3460; width: 18px; margin: -6px 0; border-radius: 3px; }
            QLabel { border: none; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        # ===== 链接输入 =====
        link_group = QGroupBox("歌单链接 / 歌曲ID")
        lv = QVBoxLayout(link_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://music.163.com/m/playlist?id=... 或直接输入歌曲ID")
        self.url_input.setFont(QFont("", 11))
        self.url_input.returnPressed.connect(self._start)
        lv.addWidget(self.url_input)
        layout.addWidget(link_group)

        # ===== 设置区 =====
        set_group = QGroupBox("下载设置")
        sv = QVBoxLayout(set_group)

        # 音质选择
        row1 = QHBoxLayout()
        quality_label = QLabel("音质:")
        quality_label.setStyleSheet("color: #64ffda;")
        row1.addWidget(quality_label)
        self.quality_combo = QComboBox()
        for q in downloader.QUALITIES:
            self.quality_combo.addItem(q["label"])
        row1.addWidget(self.quality_combo)

        row1.addSpacing(20)

        # 并发数: QSlider + QSpinBox (codi_1的设计)
        concurrency_label = QLabel("并发数:")
        concurrency_label.setStyleSheet("color: #64ffda;")
        row1.addWidget(concurrency_label)

        self.concurrency_slider = QSlider(Qt.Horizontal)
        self.concurrency_slider.setRange(1, 10)
        self.concurrency_slider.setValue(3)
        self.concurrency_slider.valueChanged.connect(self._on_concurrency_changed)
        row1.addWidget(self.concurrency_slider)

        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, 10)
        self.concurrency_spin.setValue(3)
        self.concurrency_spin.valueChanged.connect(self._on_concurrency_spin_changed)
        row1.addWidget(self.concurrency_spin)

        self.concurrency_text = QLabel("3 个同时下载")
        self.concurrency_text.setStyleSheet("color: #aaa; font-size: 12px;")
        row1.addWidget(self.concurrency_text)

        row1.addStretch()

        # 目录选择
        self.dir_label = QLabel("保存目录: " + self.output_dir)
        self.dir_label.setStyleSheet("color: #64ffda; font-size: 12px;")
        row1.addWidget(self.dir_label)

        dir_btn = QPushButton("📁 改目录")
        dir_btn.setObjectName("dirBtn")
        dir_btn.clicked.connect(self._choose_dir)
        row1.addWidget(dir_btn)

        sv.addLayout(row1)
        layout.addWidget(set_group)

        # ===== 按钮 =====
        btn_row = QHBoxLayout()
        self.download_btn = QPushButton("⬇ 开始下载")
        self.download_btn.setFont(QFont("", 12))
        self.download_btn.clicked.connect(self._start)
        btn_row.addWidget(self.download_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setEnabled(False)
        btn_row.addWidget(self.stop_btn)
        layout.addLayout(btn_row)

        # ===== 进度条 =====
        self.progress = QProgressBar()
        self.progress.setFormat("%v / %m   (%p%)")
        layout.addWidget(self.progress)

        # ===== 状态标签 (codi_2的设计) =====
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #64ffda;")
        layout.addWidget(self.status_label)

        # ===== 日志 =====
        log_group = QGroupBox("下载日志")
        glv = QVBoxLayout(log_group)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFont(QFont("Consolas", 9))
        glv.addWidget(self.log_edit)
        layout.addWidget(log_group, 1)

        # ===== 关于 (codi_2的设计) =====
        about_group = QGroupBox("关于")
        av = QVBoxLayout(about_group)

        about_text = (
            '<p style="margin: 4px 0;">注意:此项目仅用于学习和研究,请勿用于商业用途,使用者的任何行为均由其自行承担</p>'
            '<p style="margin: 4px 0;">作者：CAT是猫不是喵</p>'
            '<p style="margin: 4px 0;">BUG反馈邮箱：<a href="mailto:catmiao14514@163.com">catmiao14514@163.com</a>(小兽太也可以通过这个邮箱找我扩列哦🐾)</p>'
            '<p style="margin: 4px 0;">GitHub：<a href="https://github.com/CAT-fuck/MusicDownloader">https://github.com/CAT-fuck/MusicDownloader</a></p>'
            '<p style="margin: 4px 0;">可以在GitHub上给这个项目点个免费的Star吗? 这对我真的很重要! 谢谢喵!</p>'
        )

        about_label = QLabel(about_text)
        about_label.setOpenExternalLinks(True)
        about_label.setTextFormat(Qt.RichText)
        about_label.setWordWrap(True)
        about_label.setStyleSheet("""
            color: #ccc;
            font-size: 14px;
            padding: 6px;
        """)
        av.addWidget(about_label)

        layout.addWidget(about_group)

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存目录", self.output_dir)
        if d:
            self.output_dir = d
            self.dir_label.setText("保存目录: " + d)

    def _on_concurrency_changed(self, value):
        self.concurrency_spin.setValue(value)
        self.concurrency_text.setText("%d 个同时下载" % value)

    def _on_concurrency_spin_changed(self, value):
        self.concurrency_slider.setValue(value)
        self.concurrency_text.setText("%d 个同时下载" % value)

    def _log(self, text):
        self.log_edit.append(text)
        c = self.log_edit.textCursor()
        c.movePosition(c.End)
        self.log_edit.setTextCursor(c)

    def _progress(self, done, total, ok, fail):
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.status_label.setText("进度 %d/%d | 成功 %d | 失败 %d" % (done, total, ok, fail))

    def _start(self):
        url = self.url_input.text().strip()
        if not url:
            self._log("请输入歌单链接或歌曲ID")
            return
        if self.worker and self.worker.isRunning():
            self._log("正在下载中，请等待完成或点击停止")
            return

        self._set_busy()
        self.log_edit.clear()
        self.progress.setValue(0)

        self.worker = DownloadWorker(
            url, self.output_dir,
            self.quality_combo.currentIndex(),
            self.concurrency_spin.value(),
        )
        self.worker.log.connect(self._log)
        self.worker.progress.connect(self._progress)
        self.worker.done.connect(self._done)
        self.worker.error.connect(self._err)
        self.worker.start()

    def _stop(self):
        if self.worker:
            self.worker.stop()
            self._log("正在停止（等待当前歌曲结束）...")

    def _done(self, result):
        self._set_idle()
        self._log("全部结束。保存目录: " + self.output_dir)
        self.status_label.setText(
            "完成! 成功 %d | 失败 %d | 共 %d" % (result["ok"], result["fail"], result["total"]))

    def _err(self, msg):
        self._set_idle()
        self._log("[错误] " + msg)
        self.status_label.setText("错误: " + msg)

    def _set_busy(self):
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.url_input.setEnabled(False)
        self.quality_combo.setEnabled(False)
        self.concurrency_spin.setEnabled(False)
        self.concurrency_slider.setEnabled(False)

    def _set_idle(self):
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.url_input.setEnabled(True)
        self.quality_combo.setEnabled(True)
        self.concurrency_spin.setEnabled(True)
        self.concurrency_slider.setEnabled(True)


def main():
    # 设置AppUserModelID(修复任务栏图标合并问题)
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CAT.MusicDownloader")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置窗口图标(兼容打包环境)
    icon_path = _get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()