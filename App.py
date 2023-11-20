import threading
import tkinter as tk
from tkinter import ttk, filedialog
from pytube import YouTube
from pydub import AudioSegment
import os
import datetime
from moviepy.editor import VideoFileClip, AudioFileClip


def download_and_combine_video(yt, resolution, path):
    video_stream = yt.streams.filter(res=resolution, mime_type="video/mp4", progressive=False).order_by(
        'resolution').desc().first()
    audio_stream = yt.streams.filter(only_audio=True).first()

    video_file = video_stream.download(output_path=path, filename_prefix="video_")
    audio_file = audio_stream.download(output_path=path, filename_prefix="audio_")

    video_clip = VideoFileClip(video_file)
    audio_clip = AudioFileClip(audio_file)
    final_clip = video_clip.set_audio(audio_clip)

    final_filename = get_unique_filename(path, yt.title, ".mp4")
    # ここで on_combine_progress 関数を progress_function 引数として渡します
    final_clip.write_videofile(final_filename, progress_function=on_combine_progress)

    # 一時ファイルの削除
    os.remove(video_file)
    os.remove(audio_file)

    reset_progress_and_status()
    return final_filename


def get_unique_filename(path, filename, ext):
    original_filename = os.path.join(path, filename + ext)
    if not os.path.exists(original_filename):
        return original_filename

    # ファイル名にサフィックス（タイムスタンプ）を追加
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = os.path.join(path, f"{filename}_{timestamp}{ext}")
    return new_filename


# ダウンロードの進行状況を更新する関数
def progress_function(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage_of_completion = bytes_downloaded / total_size * 100
    progress_var.set(percentage_of_completion)
    status_var.set("Downloading... {}%".format(int(percentage_of_completion)))
    root.update_idletasks()


def update_status(status_message):
    status_var.set(status_message)
    root.update_idletasks()


def on_combine_progress(current, total):
    percentage_of_completion = (current / total) * 100
    progress_var.set(percentage_of_completion)
    status_var.set(f"Combining audio and video... {int(percentage_of_completion)}%")
    root.update_idletasks()


def download_media_thread(url, media_type, resolution, format, path, bitrate):
    threading.Thread(target=download_media, args=(url, media_type, resolution, format, path, bitrate),
                     daemon=True).start()


# メディアのダウンロードと変換
def download_media(url, media_type, resolution, format, path, bitrate):
    try:
        yt = YouTube(url, on_progress_callback=progress_function)
        if media_type == "Video":
            if resolution == "1080p":
                # ビデオとオーディオを結合する場合
                new_file = download_and_combine_video(yt, resolution, path)
            else:
                # 解像度に基づいてビデオストリームを選択
                video_stream = yt.streams.filter(res=resolution, mime_type="video/mp4").first()
                output_file = video_stream.download(output_path=path)
                new_file = get_unique_filename(path, os.path.splitext(os.path.basename(output_file))[0], '.mp4')
                os.rename(output_file, new_file)

            root.update_idletasks()
            reset_progress_and_status()
            return new_file
        else:
            # 音声ストリームを選択し、音声ビットレートで変換
            audio_stream = yt.streams.filter(only_audio=True).first()
            output_file = audio_stream.download(output_path=path)
            base, ext = os.path.splitext(output_file)
            new_file = get_unique_filename(path, base, '.' + format)
            audio = AudioSegment.from_file(output_file, format=ext.replace(".", ""))
            audio.export(new_file, format=format, bitrate=bitrate)
            os.remove(output_file)

            root.update_idletasks()
            reset_progress_and_status()
            return new_file
    except Exception as e:
        return f"Error: {e}"


# ダウンロード開始関数（GUI用）
def start_download():
    url = url_entry.get()
    media_type = media_type_var.get()
    resolution = resolution_var.get() if media_type == "Video" else None
    format = format_var.get() if media_type == "Audio" else None
    path = path_entry.get()
    bitrate = bitrate_var.get() if media_type == "Audio" else None
    download_media_thread(url, media_type, resolution, format, path, bitrate)


def reset_progress_and_status():
    progress_var.set(0)  # プログレスバーを0にリセット
    status_var.set("Status: Waiting for input...")  # ステータスラベルを初期状態に戻す
    root.update_idletasks()  # GUIを更新


# ウィジェットの配置を更新するための関数
def on_media_type_changed(event=None):
    media_type = media_type_var.get()
    if media_type == "Video":
        resolution_label.grid()
        resolution_dropdown.grid()
        format_label.grid_remove()
        format_dropdown.grid_remove()
    else:  # "Audio"が選択されたとき
        resolution_label.grid_remove()
        resolution_dropdown.grid_remove()
        format_label.grid()
        format_dropdown.grid()
        bitrate_label.grid()
        bitrate_dropdown.grid()


# GUIの初期化
root = tk.Tk()
root.title("YouTube Downloader")
root.geometry("600x400")
root.resizable(False, False)  # サイズ変更不可に設定

# 変数の初期化
progress_var = tk.DoubleVar()
status_var = tk.StringVar(value="Status: Waiting for input...")

# URL入力フィールド
url_label = tk.Label(root, text="YouTube URL:")
url_label.grid(row=0, column=0, sticky="e", padx=10, pady=10)
url_entry = tk.Entry(root, width=50)
url_entry.grid(row=0, column=1, padx=10, pady=10)

# ダウンロード先パス入力フィールド
path_label = tk.Label(root, text="Download Path:")
path_label.grid(row=1, column=0, sticky="e", padx=10, pady=10)
path_entry = tk.Entry(root, width=50)
path_entry.grid(row=1, column=1, padx=10, pady=10)
browse_button = tk.Button(root, text="Browse", command=lambda: path_entry.insert(0, filedialog.askdirectory()))
browse_button.grid(row=1, column=2, padx=10, pady=10)

# メディアタイプ選択ドロップダウン
media_type_var = tk.StringVar(value="Audio")
media_type_label = tk.Label(root, text="Select Media Type:")
media_type_label.grid(row=2, column=0, sticky="e", padx=10, pady=10)
media_type_dropdown = ttk.Combobox(root, textvariable=media_type_var, values=["Audio", "Video"])
media_type_dropdown.grid(row=2, column=1, padx=10, pady=10)
media_type_dropdown.bind('<<ComboboxSelected>>', on_media_type_changed)

# 解像度選択ドロップダウン（動画用）
resolution_var = tk.StringVar(value="720p")
resolution_label = tk.Label(root, text="Select Resolution:")
resolution_label.grid(row=3, column=0, sticky="e", padx=10, pady=10)
resolution_dropdown = ttk.Combobox(root, textvariable=resolution_var,
                                   values=["144p", "240p", "360p", "480p", "720p", "1080p"])
resolution_dropdown.grid(row=3, column=1, padx=10, pady=10)

# 形式選択ドロップダウン（音声用）
format_var = tk.StringVar(value="mp3")
format_label = tk.Label(root, text="Select Format:")
format_label.grid(row=4, column=0, sticky="e", padx=10, pady=10)
format_dropdown = ttk.Combobox(root, textvariable=format_var, values=["mp3", "wav", "ogg"])
format_dropdown.grid(row=4, column=1, padx=10, pady=10)

# 音声ビットレート選択ドロップダウン（音声用）
bitrate_var = tk.StringVar(value="128k")
bitrate_label = tk.Label(root, text="Select Bitrate:")
bitrate_label.grid(row=5, column=0, sticky="e", padx=10, pady=10)
bitrate_dropdown = ttk.Combobox(root, textvariable=bitrate_var, values=["128k", "192k", "256k", "320k"])
bitrate_dropdown.grid(row=5, column=1, padx=10, pady=10)

# ダウンロードボタン
download_button = tk.Button(root, text="Download", command=start_download)
download_button.grid(row=6, column=0, columnspan=3, pady=10)

# ステータス表示ラベル
status_label = tk.Label(root, textvariable=status_var)
status_label.grid(row=7, column=0, columnspan=3, pady=10)

# プログレスバーの追加
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", variable=progress_var)
progress_bar.grid(row=8, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

audio_bitrate_label = tk.Label(root, text="Select Audio Bitrate:")
audio_bitrate_var = tk.StringVar(value="128k")
audio_bitrate_dropdown = ttk.Combobox(root, textvariable=audio_bitrate_var, values=["128k", "192k", "256k", "320k"])


# 最初のメディアタイプに応じたウィジェットの表示を更新
on_media_type_changed()

# グリッドの列と行のサイズ設定
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(8, weight=1)

# GUIを実行
root.mainloop()
