# JWT 인증 관련 Q&A

## Q: JWT 토큰이 무엇이고 왜 사용하나요?
A: JWT(JSON Web Token)는 당사자 간에 정보를 JSON 객체로 안전하게 전송하기 위한 방법입니다. 백엔드에서 토큰을 발급하고, 프론트엔드는 이 토큰을 사용해 인증된 요청을 보냅니다.

## Q: 토큰타입(token_type)을 같이 주는 이유는 무엇인가요?
A: OAuth 2.0 스펙을 따르기 위해서입니다. 토큰 타입(보통 "Bearer")을 명시함으로써:
- 인증 헤더 포맷 지정 가능
- 다양한 인증 방식 구분 가능 (Bearer, Basic, Digest 등)
- 다른 인증 시스템과의 호환성 유지

## Q: 프론트엔드에서 JWT 토큰을 어떻게 활용하나요?
A: 주로 다음과 같은 방식으로 활용합니다:

```typescript
// 로그인 후 토큰 저장
localStorage.setItem('token', response.data.access_token);

// API 요청시 토큰 포함
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

## Q: AuthContext에서 login/logout 함수를 함께 제공하는 이유는 무엇인가요?
A: 상태 관리의 일관성과 재사용성을 위해서입니다:
1. 상태 변경 로직을 한 곳에서 관리
2. 여러 컴포넌트에서 동일한 로그인/로그아웃 로직 재사용
3. 상태(user)와 상태 변경 함수들의 응집도 향상
4. 로직 변경 시 사용하는 컴포넌트들의 수정 불필요

## Q: 토큰 기반 권한 체크를 전역적으로 적용하는 방법은?
A: FastAPI에서는 의존성 주입(Dependency Injection)을 사용하여 전역적으로 인증을 적용할 수 있습니다:

```python
async def verify_token(token: str = Depends(security.OAuth2PasswordBearer(tokenUrl="login"))):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
        return payload
    except JWTError:
        raise HTTPException(status_code=401)

# FastAPI 앱에 전역 의존성 추가
app = FastAPI(dependencies=[Depends(verify_token)])
```

이렇게 하면:
- 모든 엔드포인트에 자동으로 인증 적용
- 필요한 경우 특정 라우트만 예외 처리 가능
- 코드 중복 없이 일관된 인증 로직 적용

## Q: 토큰을 네트워크 요청에서 숨길 수 있나요?
A: 완전히 숨기는 것은 불가능합니다. 대신 다음과 같은 보안 강화 방법을 사용할 수 있습니다:
1. HttpOnly 쿠키 사용
2. 토큰 암호화
3. 짧은 만료 시간 설정
4. 토큰 회전(rotation) 구현
5. 필요한 최소한의 권한만 포함

## Q: 프론트엔드에서 보호된 라우트는 어떻게 구현하나요?
A: React Router와 함께 ProtectedRoute 컴포넌트를 사용합니다:

```typescript
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  return <>{children}</>;
};

// 사용 예시
const routes: RouteObject[] = [
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    )
  }
];
```

## 보안 관련 추가 고려사항
1. 토큰 만료 시간 적절히 설정
2. 리프레시 토큰 구현 고려
3. HTTPS 사용 필수
4. XSS, CSRF 대비
5. 에러 처리 철저