# 나중에 환경변수로 옮기도록.

import time
from typing import Dict, List, TypedDict
import requests,os
from pprint import pprint
# API_key = 'Ikks%2FYlcllC%2B35REfwEjr%2BvMrSbEV7PPOkgrJ1Eev3OuzHlU4UcLtqejZcTXIcHPO%2BKA7en0aZA6Gx0qb%2FjV5g%3D%3D'
API_key= 'Ikks/YlcllC+35REfwEjr+vMrSbEV7PPOkgrJ1Eev3OuzHlU4UcLtqejZcTXIcHPO+KA7en0aZA6Gx0qb/jV5g=='
API_key = os.getenv('HOLIDAY_API_KEY',API_key)

import requests
import xmltodict
import json
from datetime import datetime, timedelta
from pprint import pprint
# 현재 날짜 기준으로 데이터 수집 범위 계산

class Holiday(TypedDict):
    date: datetime
    name: str
    rest: bool
    

def fetch_and_update_holidays(year_month_pairs):
    '''year_month_pairs ==> 요청할 연-월 조합'''
    # 현재 날짜
    # API 호출
    url = 'http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo'
    holiday_data = []

    for year, month in year_month_pairs:
        params = {
            'serviceKey': API_key,
            'solYear': str(year),
            'solMonth': str(month).zfill(2)
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # 에러 발생 시 예외 발생
            
            decoded_xml = response.content.decode('utf-8')
            xml_dict = xmltodict.parse(decoded_xml)
            
            # 공휴일 데이터 추출
            try:
                items = xml_dict['response']['body']['items']
                if items and 'item' in items:
                    if isinstance(items['item'], list):
                        for item in items['item']:
                            holiday_data.append(item)
                    else:
                        holiday_data.append(items['item'])
            except (KeyError, TypeError) as e:
                print(f"No holiday data found for {year}-{month}: {e}")
        
        except Exception as e:
            print(f"Error fetching data for {year}-{month}: {e}")
        
        # API 호출 간 간격
        time.sleep(0.5)
    
    # 데이터 변환
    result: List[Holiday] = list(map(
        lambda x: {
            'date': datetime.strptime(x['locdate'], '%Y%m%d'),
            'name': x['dateName'],
            'rest': True
        },
        holiday_data
    ))

    return result