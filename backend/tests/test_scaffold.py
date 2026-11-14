def test_shared_package_importable():
    import shared

    assert shared.__doc__
