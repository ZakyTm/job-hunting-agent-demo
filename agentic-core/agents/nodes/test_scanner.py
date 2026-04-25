"""Quick test — paste a real job post and see what scanner extracts."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print("Starting test_scanner.py...", flush=True)
from agents.nodes.scanner import scanner_node
print("Imports successful!", flush=True)

# Paste a REAL job post from your Telegram channel here
test_post = """
📢 إعلان توظيف – Ingénieur HSE
تعلن مؤسسة عن فتح باب التوظيف للمنصب التالي:
🔹 المسمى الوظيفي:
• مهندس HSE (Hygiène, Sécurité, Environnement)
📍 مكان العمل: بسكرة – القنطرة
👤 الملف المطلوب:
• شهادة في هندسة HSE
✉️ للتقديم: recutement.hse@example.dz
"""

result = scanner_node({"raw_text": test_post})

print("\n📋 Scanner Output:")
for key, value in result.items():
    print(f"  {key}: {value}")
