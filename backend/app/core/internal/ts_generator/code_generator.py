"""
TypeScript 생성기 - TypeScript 코드 생성 로직
"""

import re
from typing import Dict, Any
from .type_converter import get_type_name
from .base_types import Authorization


def generate_router_content(routers: Dict[str, Dict], name: str, base_url: str) -> str:
    """
    라우터 정의를 TypeScript 클래스로 변환
    
    Args:
        routers: 라우트 정의 딕셔너리
        name: 라우터 클래스 이름
        base_url: API 베이스 URL
        
    Returns:
        TypeScript 클래스 코드
    """
    if not isinstance(name, str) or len(name) == 0:
        raise ValueError("Name의 형식이 적절치 않거나 길이가 0입니다.")
    
    def format_request_type(params: Dict, method: str) -> str:
        """요청 파라미터를 TypeScript 타입으로 변환"""
        if not params:
            return "{variance?:null}"
        
        ispatch = True if method == "PATCH" else False
        param_defs = []
        for param_name, annotation in params.items():
            ts_type, is_nullable = get_type_name(annotation)
            
            # 배열 타입이고 patch 요청인 경우 Partial 처리
            if ispatch and ts_type.endswith("[]"):
                base_type = ts_type[:-2]  # 배열 표시 제거
                ts_type = f"Partial<{base_type}>[]"
            
            param_defs.append(f'{param_name}{"?" if is_nullable else ""}: {ts_type}')
        
        if len(param_defs) == 1:
            return f"{{ {param_defs[0]} }}"
        return f"{{ {', '.join(param_defs)} }}"
    
    def format_response_type(response_model) -> str:
        """응답 모델을 TypeScript 타입으로 변환"""
        if response_model is None:
            return "void"
        return get_type_name(response_model)[0]
    
    def generate_method_body(route_def: Dict) -> str:
        """HTTP 메서드에 따른 fetch 호출 코드 생성"""
        method = route_def["method"]
        path = route_def["path"]
        
        # FastAPI 경로 패턴({변수:타입} 또는 {변수})을 추출
        path_param_pattern = re.compile(r"\{([^:}]+)(?::[^}]+)?\}")
        path_param_matches = path_param_pattern.findall(path)
        
        # Path parameter 처리
        path_params = {
            param
            for param in route_def["request"].keys()
            if param in path_param_matches
        }
        query_params = {
            k: v for k, v in route_def["request"].items() if k not in path_params
        }
        
        # URL 템플릿 생성
        url = f"`${{BASE_URL}}{path}`"
        # Path parameter가 있으면 URL에 직접 삽입
        for param in path_params:
            url = url.replace(f"{{{param}:path}}", f"${{params.{param}}}")
            url = url.replace(f"{{{param}}}", f"${{params.{param}}}")
        
        if method == "GET":
            # 쿼리 파라미터 처리 코드 부분
            query_params_code = ""
            fetch_url = url
            
            if query_params:
                query_params_code = """const queryParams = new URLSearchParams();\n"""
                for param_name in query_params:
                    query_params_code += f"""
                        if (params.{param_name} !== undefined) {{
                            if (typeof params.{param_name} === 'object' && params.{param_name} !== null) {{
                                Object.entries(params.{param_name}).forEach(([key, value]) => {{
                                    if (value !== undefined) {{
                                        queryParams.append(key, String(value));
                                    }}
                                }});
                            }} else {{
                                queryParams.append('{param_name}', String(params.{param_name}));
                            }}
                        }}"""
                fetch_url = f"{url} + (queryParams.toString() ? '?' + queryParams : '')"
            
            return f"""
                    {query_params_code}
                    
                    const response = await fetch({fetch_url}, {{
                        method: 'GET',
                        headers: {{'Authorization': {Authorization}}}
                    }});
                    const data = await response.json();

                    if (!response.ok) {{
                        throw data
                    }}
                    
                    return data;"""
        else:
            # POST, PUT, PATCH, DELETE 메서드 처리
            path_params_exclusion = ", ".join([f"{param}" for param in sorted(path_params)])
            if path_params_exclusion:
                params_expression = (
                    f"const {{ {path_params_exclusion}, ...bodyParams }} = params;"
                )
            else:
                params_expression = "const bodyParams = params;"
            
            # 파일 파라미터 감지 (FormData 필요 여부)
            has_file = route_def.get("has_file", False) or "file" in str(route_def.get("request", "")).lower()
            
            if has_file:
                # multipart/form-data 형식 (파일 업로드)
                return f"""
                    {params_expression}
                    const formData = new FormData();
                    
                    // bodyParams의 각 필드를 FormData에 추가
                    Object.entries(bodyParams).forEach(([key, value]) => {{
                        if (value instanceof File) {{
                            formData.append(key, value);
                        }} else if (value != null) {{
                            formData.append(key, String(value));
                        }}
                    }});
                    
                    const response = await fetch({url}, {{
                        method: '{method}',
                        headers: {{
                            'Authorization': {Authorization}
                            // Content-Type을 명시하지 않음 (브라우저가 자동으로 설정)
                        }},
                        body: formData
                    }});
                    
                    const data = await response.json();
                    
                    if (!response.ok) {{
                        throw data;
                    }}
                    
                    return data;"""
            else:
                # JSON 형식
                return f"""
                    {params_expression}
                    const requestBody = Object.keys(bodyParams).length === 1 ? Object.values(bodyParams)[0] : bodyParams;
                    const response = await fetch({url}, {{
                        method: '{method}',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': {Authorization}
                        }},
                        body: JSON.stringify(requestBody)
                    }});
                    
                    const data = await response.json();
                    
                    if (!response.ok) {{
                        throw data;
                    }}
                    
                    return data;"""
    
    def format_jsdoc(description: str | None) -> str:
        """Python docstring을 TypeScript JSDoc 형식으로 변환"""
        if not description:
            return ""
        description = description.strip()
        lines = description.split('\n')
        if len(lines) == 1:
            return f"    /** {description} */"
        else:
            jsdoc_lines = ["    /**"]
            for line in lines:
                jsdoc_lines.append(f"     * {line.strip()}")
            jsdoc_lines.append("     */")
            return "\n".join(jsdoc_lines)
    
    content = []
    content.append(f"\nexport class {name} {{")
    
    # 각 라우트에 대한 static 메서드 생성
    for route_name, route_def in routers.items():
        response_type = format_response_type(route_def["response"])
        method_body = generate_method_body(route_def)
        method = route_def["method"]
        request_type = format_request_type(route_def["request"], method)
        
        # JSDoc 주석 생성
        jsdoc = format_jsdoc(route_def.get("description"))
        
        method_def = f"""    static async {route_name}(params: {request_type},method="{method}"): Promise<{response_type}> {{{method_body}
    }}"""
        
        # JSDoc이 있으면 메서드 앞에 추가
        if jsdoc:
            method_def = f"{jsdoc}\n{method_def}"
        
        content.append(method_def)
    
    content.append("}")
    return "\n\n".join(content)
