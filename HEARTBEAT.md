# Atlas 定时任务处理

## 系统事件处理

当收到以下系统事件时，执行 Atlas 更新：

- `atlas-morning-run` → 早上 7:00 运行
- `atlas-evening-run` → 晚上 18:00 运行

## 执行命令

```bash
cd /Users/maxim/.openclaw/workspace/projects/atlas && python3 atlas_auto.py --all
```

## 其他心跳检查

（保持为空，Atlas 由定时任务驱动）
