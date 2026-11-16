"""Render all six figures from stored numerical inputs; no model training."""
from pathlib import Path
import subprocess,sys
for name in ['phase_and_event_maps','historical_environment_production','event_weather_comparisons','conditional_risk']:
    subprocess.run([sys.executable,str(Path(__file__).with_name(name+'.py'))],check=True)
