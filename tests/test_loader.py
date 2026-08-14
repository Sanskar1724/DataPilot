import pandas as pd
import pytest

from app.data.loader import load_dataframe, load_dataframe_from_bytes


@pytest.fixture
def csv_bytes() -> bytes:
    return b"a,b,c\n1,x,1.5\n2,y,\n3,z,2.5\n"


def test_load_dataframe_from_csv(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    df = load_dataframe(p)
    assert df.shape == (2, 2)
    assert list(df.columns) == ["a", "b"]


def test_load_dataframe_missing_file():
    with pytest.raises(FileNotFoundError):
        load_dataframe("does_not_exist.csv")


def test_load_dataframe_unsupported_extension(tmp_path):
    p = tmp_path / "t.xyz"
    p.write_text("x")
    with pytest.raises(ValueError, match="Unsupported file type"):
        load_dataframe(p)


def test_load_dataframe_from_bytes(csv_bytes):
    df = load_dataframe_from_bytes("t.csv", csv_bytes)
    assert df.shape == (3, 3)


def test_load_dataframe_from_bytes_bad_ext(csv_bytes):
    with pytest.raises(ValueError):
        load_dataframe_from_bytes("t.txt", csv_bytes)