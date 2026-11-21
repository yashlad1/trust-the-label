# Runs dev/pipeline.py with nemotron35 as the live gate; every argument passes through unchanged.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import dev.pipeline as p

p.LIVE_GATE = "nemotron35"
sys.argv = [sys.argv[0], *sys.argv[1:]]
p.main()
