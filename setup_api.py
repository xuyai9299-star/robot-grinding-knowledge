# -*- coding: utf-8 -*-
"""
API Key 一键配置脚本。
运行后将 Key 写入 .env 文件，网站自动生效。

用法:
    py -3 setup_api.py
    # 粘贴你的百炼 API Key → 回车 → 完成

之后启动服务器，AI 搜索和知识库更新都会自动使用这个 Key:
    py -3 pipeline_server.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"


def main():
    print("=" * 56)
    print("  机器人磨削知识库 · API Key 配置")
    print("=" * 56)
    print()
    print("  获取 Key: https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen")
    print("  打开「阿里云百炼控制台」→「API-KEY 管理」→ 创建 Key")
    print()

    # 显示现有配置
    existing = ""
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DASHSCOPE_API_KEY="):
                    existing = line.split("=", 1)[1].strip()
                    break

    if existing:
        masked = existing[:8] + "****" + existing[-4:] if len(existing) > 12 else "****"
        print(f"  当前 Key: {masked}")
        print()

    api_key = input("  请输入百炼 API Key（直接回车保留现有配置）: ").strip()

    if not api_key:
        if existing:
            print()
            print("  [OK] 保留现有配置。")
            return 0
        else:
            print()
            print("  [INFO] 未输入 Key。AI 功能将使用规则兜底模式。")
            return 0

    # 写入 .env
    # 保留文件中其他行（如果有）
    lines = []
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = [l for l in f if not l.startswith("DASHSCOPE_API_KEY=") and not l.startswith("BAILIAN_API_KEY=")]

    lines.append(f"DASHSCOPE_API_KEY={api_key}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print()
    print("  ✅ API Key 已保存到 .env 文件")
    print()
    print("  下一步: 启动服务器")
    print("    py -3 pipeline_server.py")
    print("  然后打开 http://localhost:8765")
    print()
    print("  AI 搜索和知识库更新将自动使用此 Key。")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
