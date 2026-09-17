# Chat API Endpoint Logic (`app/api/chat.py`)

이 파일은 Antigravity 에이전트가 `app/api/chat.py`의 `chat_endpoint` 로직을 수정하거나 이해할 때 참조하는 문서입니다.

## 1. 개요 (Overview)
`chat_endpoint`는 AI 에이전트 서비스의 핵심 진입점입니다. 클라이언트로부터 메시지를 수신하고, 인증을 거쳐 LangGraph 기반의 에이전트 로직(`process_message`)을 실행한 후 응답을 반환합니다.

## 2. 주요 구성 요소 (Components)

### 2.1 의존성 (Dependencies)
- **`current_user: dict = Depends(decode_access_token)`**
  - JWT 토큰을 검증하고 디코딩하여 사용자 정보를 반환합니다.
  - `id`, `email` 등의 사용자 정보가 포함됩니다.
- **`token: str = Depends(oauth2_scheme)`**
  - 요청 헤더의 Raw Bearer 토큰 문자열을 추출합니다.
  - 백엔드 API (YouTube, TikTok 등) 호출 시 인증을 위해 사용됩니다.

### 2.2 컨텍스트 관리 (Context Management)
- **`user_token_var.set(token)`**
  - 추출한 Raw Token을 `contextvars`에 저장합니다.
  - 이는 `app/tools/*` 모듈의 검색 도구들이 별도의 파라미터 전달 없이 토큰에 접근하여 백엔드 API를 호출할 수 있게 합니다.

### 2.3 프로세싱 로직 (Processing Logic)
1. **사용자 식별**: `current_user` 딕셔너리에서 `id`를 추출하려 `user_id` (String)로 변환합니다.
2. **에이전트 실행**: 
   - `process_message(request, thread_id=user_id)` 함수를 호출합니다.
   - `thread_id`는 세션 메모리(MemorySaver)의 키로 사용되어 사용자별 대화 기록을 유지합니다.
3. **응답 반환**: `ChatResponse` 모델(answer, intent, tool_used 등)을 반환합니다.

## 3. 에러 처리 (Error Handling)
- 모든 예외는 `try-except` 블록으로 포착됩니다.
- 예외 발생 시 `HTTPException(status_code=500)`을 발생시켜 클라이언트에게 500 에러를 반환합니다.

## 4. 수정 가이드 (Update Guide)
이 엔드포인트의 로직을 수정할 때는 다음 사항을 고려해야 합니다:
1. **인증 유지**: `current_user`와 `token` 의존성은 제거하지 마십시오 (보안 및 기능 필수).
2. **컨텍스트 설정**: 토큰을 백엔드로 전달해야 하므로 `user_token_var.set(token)` 호출은 에이전트 실행 전 필수입니다.
3. **스레드 ID**: 세션 메모리가 작동하려면 `process_message`에 고유한 `thread_id`를 반드시 전달해야 합니다.
