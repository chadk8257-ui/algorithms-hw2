# 명세: URL 단축기

이 명세는 URL을 짧은 코드로 바꾸고, 원래 URL을 조회하는 표준 라이브러리 기반 프로그램의 확정 명세다.
저장소는 직접 구현한 해시 테이블을 사용하며 Python 내장 `dict`, `set`, `hash()`는 사용하지 않는다.

## 1. 무엇을 만드는가

사용자는 `shorten(url)`에 HTTP(S) URL을 넣어 base62 코드를 받고, `expand(code)`에 코드를 넣어 원래 URL을 찾는다.
명령줄 테스트와 로컬 웹 인터페이스(`/`, `/table`)를 제공한다.

## 2. base62 인코딩

`src.base62.encode(number)`는 0 이상의 정수를 `0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ` 알파벳으로 표현한다. 0은 `"0"`이다.
`src.base62.decode(code)`는 비어 있지 않은 유효 문자열을 정수로 되돌린다. 음수·빈 문자열·알파벳 밖 문자는 `ValueError`, 잘못된 자료형은 `TypeError`다. 알파벳은 대소문자를 구분한다.

## 3. 해시 테이블

`src.hash_table.HashTable`은 문자열 키와 값을 저장하고 `set(key, value)`, `get(key)`, `__contains__(key)`, `__len__()`을 제공한다. `set`은 새 키를 넣거나 기존 키의 값을 갱신한다. 없는 키의 `get`은 `None`을 돌려준다.

충돌은 **개별 체이닝**으로 처리하며, 각 버킷은 키-값 항목의 연결 리스트다. 키의 해시는 왼쪽에서 오른쪽으로 각 유니코드 코드 포인트에 대해 `h = (31 * h + ord(character)) mod capacity`를 반복해 계산한다. 생성자는 초기 용량(`capacity=8`)과 최대 적재율(`max_load=0.75`)을 인자로 받으며, `max_load=None`이면 리사이즈를 수행하지 않는다. `max_load`가 설정된 경우 삽입 후 적재율(항목 수 / 용량)이 `max_load`를 초과하면 용량을 두 배로 늘리고 모든 항목을 새 버킷에 다시 배치한다.

해시 계산 및 재배치에는 같은 Horner 해시 규칙을 사용한다. 구현은 내장 `dict`, `set`, `hash()`를 사용하지 않는다. 단축기는 URL→코드와 코드→URL 조회를 각각 이 해시 테이블에 저장한다.

## 4. 단축기

`src.shortener.Shortener.shorten(url)`은 앞뒤 공백을 제거한 절대 HTTP 또는 HTTPS URL(호스트 필수)을 받아 코드를 돌려준다. 검증 후 URL 문자열은 별도로 정규화하지 않고 입력된 형태 그대로 저장한다. 같은 저장 URL을 다시 넣으면 기존 코드를 돌려준다.
빈 값, 상대 URL, 미지원 스킴, 호스트가 없는 URL, URL 내부에 공백이 포함된 경우, 길이가 2048자를 초과하는 경우는 `ValueError`로 거부한다. 코드는 0부터 증가하는 정수 ID를 base62로 인코딩해 만든다. `expand(code)`는 등록된 원래 URL을 돌려주고, 등록되지 않은 코드는 `KeyError`를 발생시킨다.

## 5. 웹 서버

`python3 src/server.py --port PORT` 또는 `make serve`로 서버를 시작한다(기본 포트 8000). 표준 라이브러리만 사용한다.
`GET /`은 URL 입력 폼을, URL을 제출하는 `POST /`는 단축 코드와 링크 결과를 보여준다. 잘못된 URL 제출은 오류 안내를 반환한다. `GET /<code>`는 등록된 URL로 리다이렉트하고, 없는 코드는 404로 응답한다. 짧은 링크의 주소를 만들 때는 `X-Forwarded-Host`와 `X-Forwarded-Proto` 헤더를 우선 사용하고, 없을 때만 `Host` 헤더를 사용한다.
`GET /table`은 각 버킷의 연결 리스트와 키별 Horner 해시 계산 근거, 버킷 인덱스를 보여준다. HTML에 삽입되는 값은 이스케이프한다.

## 6. 경계 사례

- base62: 0, 1, 61, 62 및 여러 자릿수, 큰 정수 왕복, 알파벳 대소문자 구분, 잘못된 자료형·음수·빈 문자열·잘못된 글자.
- 해시 테이블: 빈 테이블 조회, 삽입·조회·갱신, 서로 다른 키의 충돌과 체인 조회, 없는 키, 리사이즈 전후 모든 항목 보존과 항목 수, `max_load=None` 설정 시 리사이즈 없이 적재율 1 초과 삽입.
- 단축기: HTTP/HTTPS URL, 앞뒤 공백 제거, 같은 URL 중복, 서로 다른 URL의 코드, 양방향 조회, 없는 코드, 빈 값·상대 URL·미지원 스킴·호스트 누락·URL 내부 공백 포함·2048자 초과 긴 URL.
- 서버: 메인 폼, 성공/오류 제출, 코드 리다이렉트/404, `/table`의 버킷 및 해시 근거 표시, HTML 이스케이프.
