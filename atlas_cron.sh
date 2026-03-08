#!/bin/bash
# Atlas 自动更新脚本 - 用于 OpenClaw Cron
# 每天早上7点和晚上6点运行

cd /Users/streitenjavis/.openclaw/workspace/projects/atlas

# 日志
LOG_FILE="/Users/streitenjavis/.openclaw/logs/atlas_cron.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "========== Atlas 更新开始: $(date) ==========" >> "$LOG_FILE"

# 执行完整流程（抓取 RSS、生成报告、更新网站、生成 PDF、部署）
echo "[$(date +%H:%M:%S)] 执行完整 Atlas 更新流程..." >> "$LOG_FILE"
/opt/homebrew/bin/python3 atlas_auto.py --all >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    echo "[$(date +%H:%M:%S)] ✅ Atlas 更新流程完成" >> "$LOG_FILE"
else
    echo "[$(date +%H:%M:%S)] ❌ Atlas 更新流程失败" >> "$LOG_FILE"
fi

echo "========== Atlas 更新完成: $(date) ==========" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
