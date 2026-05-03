"""Gemini integration package for Scenerio.

Public surface:
    from backend.app.integrations.gemini import service
    service.analyze_scenes(project_path)
    service.generate_plan(project_path)
    service.generate_tts_assets(project_path)
    service.generate_background_assets(project_path)
    service.precritique_manifest(project_path)
"""
from . import client, service, settings

__all__ = ["client", "service", "settings"]
