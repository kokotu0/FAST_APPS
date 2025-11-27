import json
import pprint
from typing import Optional,Any
from ..types import TableRequest, TEXT_OPERATORS, NUMBER_OPERATORS, DATE_OPERATORS, LIST_OPERATORS
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class RequestInterpreter:
    """MRT 요청 데이터 인터프리터"""
    def interpret(self, request_json:str)->TableRequest:
        request_json = request_json or '{}'
        data = json.loads(request_json)
        return self._normalize_mrt_data(data)
    def interpretDict(self, data: dict) -> TableRequest:
        return self._normalize_mrt_data(data)
    def _normalize_mrt_data(self, data: dict) -> TableRequest:
        """MRT 데이터를 TableRequest 형태로 정규화"""
        normalized = data.copy()
        
        # globalFilter 처리 (누락시 빈 문자열)
        if 'globalFilter' not in normalized:
            normalized['globalFilter'] = ""
        
        # globalfilterFns vs globalFilterFn 필드명 통일
        if 'globalFilterFn' in normalized:
            normalized['globalfilterFns'] = 'fuzzy'
        elif 'globalfilterFns' not in normalized:
            normalized['globalfilterFns'] = "contains"
        
        # null 값 필터 처리
        if 'columnFilters' in normalized:
            valid_filters = []
            for filter_item in normalized['columnFilters']:
                if self._is_valid_filter_value(filter_item.get('value')):
                    valid_filters.append(filter_item)
                else:
                    logger.debug(f"필터 제외됨: {filter_item['id']} - 값이 null이거나 비어있음")
            normalized['columnFilters'] = valid_filters
        
        # 기본값 설정
        # equals2를 equals로 변경
        if 'columnFilterFns' in normalized:
            for key, value in normalized['columnFilterFns'].items():
                if value == 'equals2':
                    normalized['columnFilterFns'][key] = 'equals'   
        from pprint import pformat
        logger.debug(pformat(normalized))
        normalized.setdefault('columnFilterFns', {})
        normalized.setdefault('sorting', [])
        normalized.setdefault('pagination', {})
        
        return TableRequest(**normalized)
    
    def _is_valid_filter_value(self, value) -> bool:
        """필터 값이 유효한지 확인"""
        if value is None:
            return False
        
        if isinstance(value, list):
            # 배열의 모든 값이 null이거나 빈 문자열이면 무효
            valid_items = [item for item in value if item is not None and str(item).strip() != ""]
            return len(valid_items) > 0
        
        if isinstance(value, str):
            return value.strip() != ""
        
        return True
