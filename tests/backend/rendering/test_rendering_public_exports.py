def test_rendering_package_exports_dev2_service_surface():
    from backend.app.rendering import render_project, summarize_render

    assert callable(render_project)
    assert callable(summarize_render)

