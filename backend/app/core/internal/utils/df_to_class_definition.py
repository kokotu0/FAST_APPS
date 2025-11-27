import json
import polars as pl
import re
from typing import Literal, Optional, Type, cast
from enum import Enum, EnumType
import inspect

from pydantic import BaseModel


class DfToClassDefinition:
    def __init__(self, df: pl.DataFrame, class_name: str):
        self.df = df
        self.class_name = class_name
        self._class: Optional[Enum | BaseModel | dict] = None

    def to_string(self) -> str:
        if isinstance(self._class, EnumType):
            return self.enum_to_string(cast(Type[Enum], self._class))
        elif isinstance(self._class, dict):
            return self.dict_to_string(self._class)
        elif isinstance(self._class, BaseModel):
            raise NotImplementedError("basemodel 변환 기능 추가 예정.")
            return self.basemodel_to_string(self._class)
        else:
            raise ValueError("Invalid class type :" + type(self._class).__name__)

    def dict_to_string(self, dict: dict) -> str:
        """
        Dictionary를 Python 코드 문자열로 변환
        """
        return (
            self.class_name + " = " + json.dumps(dict, ensure_ascii=False, indent=4)
        ).replace("null", "None")

    def to_file(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_string())

    @staticmethod
    def _sanitize_member_name(name: str) -> str:
        """
        특수문자가 포함된 멤버 이름을 Python 변수명으로 변환

        예시:
            "수취인우편번호(2)" → "수취인우편번호_2"
            "판매가(수집)*수량(횡대전용)" → "판매가_수집__수량_횡대전용"

        Args:
            name: 원본 멤버 이름

        Returns:
            Python 변수명으로 유효한 이름
        """
        # 한글, 영문, 숫자, 언더스코어만 남기고 나머지는 언더스코어로 치환
        sanitized = re.sub(r"[^\w가-힣a-zA-Z0-9_]", "_", name)

        # 연속된 언더스코어 제거
        sanitized = re.sub(r"_+", "_", sanitized)

        # 앞뒤 언더스코어 제거
        sanitized = sanitized.strip("_")

        # 숫자로 시작하면 언더스코어 추가
        if sanitized and sanitized[0].isdigit():
            sanitized = "_" + sanitized

        return sanitized or "_"

    def enum_to_string(self, enum_class: Type[Enum]) -> str:
        """
        Enum을 Python 코드 문자열로 변환

        특수문자가 포함된 멤버명은 자동으로 Python 변수명으로 변환됨.

        Args:
            enum_class: 변환할 Enum 클래스

        Returns:
            Enum 정의를 나타내는 Python 코드 문자열

        Example:
            >>> enum_code = converter.enum_to_string(status_enum)
            >>> print(enum_code)
            from enum import Enum

            class classname(str, Enum):
                status_active = "Active"
                status_inactive = "Inactive"
        """
        lines = ["from enum import Enum", ""]
        lines.append(f"class {enum_class.__name__}(str, Enum):")

        members = dict(enum_class.__members__)  # type: ignore
        if not members:
            lines.append("    pass")
        else:
            for member_name, member_value in members.items():
                # 멤버 이름 정제 (특수문자 제거)
                clean_name = self._sanitize_member_name(member_name)

                # 문자열 값인 경우 quotes 처리
                if isinstance(member_value.value, str):
                    value_str = f'"{member_value.value}"'
                else:
                    value_str = repr(member_value.value)

                lines.append(f"    {clean_name} = {value_str}")

        return "\n".join(lines)

    def df_to_enum(self, key_col: str, value_col: Optional[str] = None) -> None:
        """
        Polars DataFrame을 Enum으로 변환

        Args:
            key_col: Enum의 멤버 이름으로 사용할 컬럼
            value_col: Enum의 멤버 값으로 사용할 컬럼 (None이면 key_col 사용)

        Returns:
            생성된 Enum 클래스

        Example:
            df = pl.DataFrame({
                'status_name': ['Active', 'Inactive'],
                'status_code': ['A', 'I']
            })
            converter = DfToClassDefinition(df, 'Status')
            # key_col='status_name', value_col='status_code'이면
            # Status.Active = 'A', Status.Inactive = 'I'
        """
        if value_col is None:
            value_col = key_col

        # key와 value 추출
        keys = self.df[key_col].unique().to_list()

        if key_col == value_col:
            # 같은 경우: 키 리스트를 직접 사용
            enum_dict = {str(key): key for key in keys}
        else:
            # 다른 경우: key-value 쌍 매핑
            keys_df = self.df.select([key_col, value_col]).unique()
            enum_dict = {}
            for row in keys_df.iter_rows(named=True):
                enum_dict[str(row[key_col])] = row[value_col]

        self._class = Enum(self.class_name, enum_dict)  # type: ignore

    def df_to_dict(self, key_col: str, value_col: str) -> None:
        """
        Polars DataFrame을 딕셔너리로 변환

        Args:
            key_col: 딕셔너리의 키로 사용할 컬럼
            value_col: 딕셔너리의 값으로 사용할 컬럼

        Returns:
            {key: value} 형식의 딕셔너리

        Example:
            >>> converter = DfToClassDefinition(df, 'Mapping')
            >>> result = converter.df_to_dict('code', 'name')
            >>> result
            {'A': 'Active', 'I': 'Inactive', ...}
        """
        # 중복 제거 후 딕셔너리로 변환
        mapping_df = self.df.select([key_col, value_col]).unique()
        result_dict = {}

        for row in mapping_df.iter_rows(named=True):
            key = str(row[key_col])
            value = row[value_col]
            result_dict[key] = value

        self._class = result_dict


if __name__ == "__main__":
    df = DfToClassDefinition(
        pl.read_excel(
            "api/sales/interpreter/contents/sabang_content_help_list.xlsx",
            read_options={"header_row": 3},
            columns=[
                "항목명",
                "출력 예시",
                "설명",
            ],
        ),
        "SabangContentHelpList",
    )
    # Enum 생성 및 저장

    # 딕셔너리로 변환 테스트
    print("\n=== 딕셔너리로 변환 (처음 5개) ===")
    df.df_to_dict("항목명", "출력 예시")
    print(df.to_string())
    df.to_file("api/sales/interpreter/contents/sabang_content_help_list_schemas.py")
