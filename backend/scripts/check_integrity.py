from __future__ import annotations
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.recovery import check_integrity


def main():
	"""CLI integrity check for startup verification."""
	try:
		report = check_integrity()
		
		if report.ok:
			print("✅ System integrity check passed")
			sys.exit(0)
		else:
			print("❌ System integrity check failed:")
			for reason in report.reasons:
				print(f"  - {reason}")
			
			if "License" in " ".join(report.reasons):
				print("\n🔒 Recovery Mode: License issues detected")
				sys.exit(2)  # Recovery mode
			elif "Database" in " ".join(report.reasons):
				print("\n🗄️ Recovery Mode: Database issues detected")
				sys.exit(2)  # Recovery mode
			else:
				print("\n⚠️ Warnings detected but system can continue")
				sys.exit(1)  # Warnings
				
	except Exception as e:
		print(f"❌ Integrity check error: {e}")
		sys.exit(3)  # Error


if __name__ == "__main__":
	main() 