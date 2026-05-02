def test_manifest_package_exports_dev2_service_surface():
    from backend.app.manifests import (
        apply_approved_patches,
        build_manifest,
        build_manifest_from_plan,
        load_manifest,
        write_manifest,
    )

    assert callable(build_manifest)
    assert callable(build_manifest_from_plan)
    assert callable(apply_approved_patches)
    assert callable(load_manifest)
    assert callable(write_manifest)

