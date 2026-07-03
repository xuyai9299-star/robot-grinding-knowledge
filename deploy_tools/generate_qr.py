# -*- coding: utf-8 -*-
"""答辩二维码生成工具。Vercel 部署后运行此脚本更新二维码。"""
import qrcode, sys, os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

url = sys.argv[1] if len(sys.argv) > 1 else None
if not url:
    url = input("输入 Vercel 部署地址（如 https://xxx.vercel.app）: ").strip()
    if not url:
        print("未输入地址，退出。")
        sys.exit(1)

img = qrcode.make(url, error_correction=qrcode.constants.ERROR_CORRECT_H)
img = img.resize((500, 500))
path = os.path.join(OUT_DIR, "qr_defense.png")
img.save(path)
print(f"✅ 答辩二维码已生成: {path}")
print(f"   地址: {url}")
print(f"   放入 PPT 最后一页即可。")
