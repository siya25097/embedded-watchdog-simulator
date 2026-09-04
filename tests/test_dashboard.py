from dashboard.app import STATUS_ICONS


def test_dashboard_defines_accessible_status_labels():
    assert STATUS_ICONS["HEALTHY"]
    assert STATUS_ICONS["LATE"]
    assert STATUS_ICONS["STALLED"]
    assert STATUS_ICONS["RECOVERING"]
    assert STATUS_ICONS["INITIALIZING"]
