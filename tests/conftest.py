# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# src と vendor をパスに追加
root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root / "vendor"))
