import pytest

from pathlib import Path

from my.core.structure import match_structure


structure_data: Path = Path(__file__).parent / "structure_data"

gdpr_expected = ("comments", "messages/index.csv", "profile")


def test_gdpr_structure_exists() -> None:
    with match_structure(structure_data, expected=gdpr_expected) as results:
        assert results == (structure_data / "gdpr_subdirs" / "gdpr_export",)


def test_gdpr_unzip() -> None:

    with match_structure(
        structure_data / "gdpr_export.zip", expected=gdpr_expected
    ) as results:
        assert len(results) == 1
        extracted = results[0]
        index_file = extracted / "messages" / "index.csv"
        assert index_file.read_text().strip() == "test message"

    # make sure the temporary directory this created no longer exists
    assert not extracted.exists()


def test_match_partial() -> None:
    # a partial match should match both the 'broken' and 'gdpr_export' directories
    with match_structure(
        structure_data / "gdpr_subdirs", expected=gdpr_expected, partial=True
    ) as results:
        assert len(results) == 2


def test_not_directory() -> None:
    with pytest.raises(NotADirectoryError, match=r"Expected either a zipfile or a directory"):
        with match_structure(
            structure_data / "messages/index.csv", expected=gdpr_expected
        ):
            pass
