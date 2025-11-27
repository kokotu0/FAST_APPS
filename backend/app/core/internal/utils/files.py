import io
from typing import Optional
from enum import Enum
from pathlib import Path
from fastapi import UploadFile
import msoffcrypto
import polars as pl
import pandas as pd
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class FileExt(str, Enum):
    """파일 확장자 열거형"""

    csv = "csv"
    xlsx = "xlsx"
    xls = "xls"


class FileDecrypter:
    """Office 파일 암호화 해제"""

    def __init__(self, file):
        """
        Args:
            file: 파일 객체 (file-like object, UploadFile, BytesIO 등)
        """
        self.file = file

    def decrypt(self, password: str) -> io.BytesIO:
        """
        파일 복호화

        Args:
            password: 파일 암호

        Returns:
            복호화된 파일 (BytesIO)

        Raises:
            ValueError: 패스워드 오류 또는 복호화 실패
            RuntimeError: 파일 읽기 오류
        """
        if not password:
            raise ValueError("패스워드가 제공되지 않았습니다")

        try:
            # 파일 포인터 처음으로
            if hasattr(self.file, "seek"):
                self.file.seek(0)

            decrypted_file = io.BytesIO()
            office_file = msoffcrypto.OfficeFile(self.file)
            office_file.load_key(password=password)
            office_file.decrypt(decrypted_file)

            decrypted_file.seek(0)  # 파일 포인터를 처음으로
            return decrypted_file

        except Exception as e:
            if "password" in str(e).lower() or "invalid" in str(e).lower():
                raise ValueError(f"패스워드가 잘못되었습니다") from e
            else:
                raise RuntimeError(f"파일 복호화 실패: {str(e)}") from e

    def is_encrypted(self) -> bool:
        """파일이 암호화되어 있는지 확인"""
        try:
            # 파일 포인터 처음으로
            if hasattr(self.file, "seek"):
                self.file.seek(0)

            office_file = msoffcrypto.OfficeFile(self.file)
            return office_file.is_encrypted()
        except Exception as e:
            logger.warning(f"암호화 여부 확인 실패: {str(e)}")
            return False


class ExcelReader:
    """Excel/CSV 파일을 읽어 DataFrame으로 변환"""

    @classmethod
    def read_file(cls, file: UploadFile, password: str | None = None) -> "ExcelReader":
        """파일을 읽어 DataFrame으로 변환"""
        file_decrypter = FileDecrypter(file.file)
        if file_decrypter.is_encrypted():
            if password:
                decrypted_file = file_decrypter.decrypt(password)
            else:
                raise ValueError("패스워드가 제공되지 않았습니다")
        else:
            decrypted_file = file.file
        if not file.filename:
            raise ValueError("파일명이 없습니다")
        file_ext = file.filename.split(".")[-1]
        if file_ext not in [FileExt.xlsx.value, FileExt.xls.value, FileExt.csv.value]:
            raise ValueError(f"지원하지 않는 파일 확장자: {file_ext}")
        return cls(decrypted_file, file_ext)

    def __init__(
        self,
        file,
        file_ext: str,
    ):
        """
        Args:
            file: 파일 객체 (BytesIO, 또는 열린 파일 객체)
            file_ext: 파일 확장자 (.xlsx, .xls, .csv 또는 확장자 없이 xlsx)
        """
        self.file = file
        # 확장자 정규화 (앞의 점 제거)
        self.suffix = file_ext.lower()
        # 확장자 검증
        self._validate_file_ext()

    def _validate_file_ext(self):
        """지원하는 파일 확장자인지 검증"""
        valid_exts = [ext.value for ext in FileExt]
        if self.suffix not in valid_exts:
            raise ValueError(
                f"지원하지 않는 파일 확장자: {self.suffix} (지원: {valid_exts})"
            )
        return True

    def to_polars(self):
        """파일을 Polars DataFrame으로 변환"""
        try:
            # BytesIO를 bytes로 변환하여 Polars에 직접 전달
            if hasattr(self.file, "getvalue"):
                # BytesIO 또는 유사 객체
                file_bytes = self.file.getvalue()
            elif hasattr(self.file, "read"):
                # 일반 file 객체
                if hasattr(self.file, "seek"):
                    self.file.seek(0)
                file_bytes = self.file.read()
            else:
                raise ValueError("파일 객체가 지원되지 않습니다")

            if self.suffix in (FileExt.xlsx.value, FileExt.xls.value):
                return pl.read_excel(file_bytes)
            elif self.suffix == FileExt.csv.value:
                return pl.read_csv(file_bytes)
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {self.suffix}")

        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(
                f"파일 형식이 손상되었거나 읽을 수 없습니다: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Polars 읽기 실패: {str(e)}") from e

    def to_pandas(self):
        """파일을 Pandas DataFrame으로 변환"""
        try:
            if self.suffix in (FileExt.xlsx.value, FileExt.xls.value):
                return pd.read_excel(self.file)
            elif self.suffix == FileExt.csv.value:
                self.file.seek(0)  # 파일 포인터 리셋
                return pd.read_csv(self.file)
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {self.suffix}")
        except pd.errors.ParserError as e:
            raise ValueError(
                f"파일 형식이 손상되었거나 읽을 수 없습니다: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Pandas 읽기 실패: {str(e)}") from e
