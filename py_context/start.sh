#!/bin/bash

# 固定の解像度を指定して Xvfb を起動
Xvfb :99 -ac -screen 0 1280x1024x16 &

# DISPLAY 環境変数を設定
export DISPLAY=:99

# Xvfb が完全に起動するまで待機
sleep 5

# Python スクリプトを実行
python /work/scrap.py
