"""Deprecated compatibility module."""

from face_workbench.legacy import has_suffix, read_all_images


def readAllImg(path: str, *suffix: str) -> list:
    return read_all_images(path, *suffix)


def endwith(value: str, *suffixes: str) -> bool:
    return has_suffix(value, suffixes)


__all__ = ["endwith", "readAllImg"]
