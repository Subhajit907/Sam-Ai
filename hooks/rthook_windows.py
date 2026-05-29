"""
Runtime hook for Windows — adds the MEIPASS directory to PATH so that
ffplay.exe, ffmpeg.exe, and portaudio_x64.dll are found automatically
when Alia AI runs as a frozen bundle.
"""
import os
import sys

if hasattr(sys, '_MEIPASS'):
    os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ.get('PATH', '')
