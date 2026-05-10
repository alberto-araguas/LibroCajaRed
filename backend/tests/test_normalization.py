from app.services.normalization import normalize_name


def test_normalize_name_removes_accents_case_and_extra_spaces() -> None:
    assert normalize_name("  Álvarez   &   Compañía  ") == "alvarez & compania"
