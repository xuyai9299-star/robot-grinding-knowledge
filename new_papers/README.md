# 新论文入库文件夹

1. 从 Zotero 导出 CSV（与 `华中武大.csv` 相同列格式即可）
2. 将 CSV 放入本目录，文件名可含学校名（如 `重庆大学_2026.csv`）
3. 提交并 push 到 GitHub，Actions 会自动运行 `ingest.py`
4. 处理完成后 CSV 会移到 `archive/`

本地测试：

```bash
set DASHSCOPE_API_KEY=你的密钥
python ingest.py
```

无 API Key 时：

```bash
set SKIP_LLM=1
python ingest.py
```
