# 명세: URL 단축기

이 명세는 URL을 짧은 코드로 바꾸고, 원래 URL을 조회하는 표준 라이브러리 기반 프로그램을 정의한다.
모든 공개 동작은 결정적이며 명시된 입력 오류를 예외로 알린다.

## 1. 무엇을 만드는가

사용자는 `shorten(url)`에 HTTP(S) URL을 넣어 base62 코드를 받고, `expand(code)`에 코드를 넣어 원래 URL을 찾는다.
명령줄 테스트와 로컬 웹 인터페이스(`/`, `/table`)를 제공한다.

## 2. base62 인코딩

`src.base62.encode(number)`는 0 이상의 정수를 `0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ` 알파벳으로 표현한다. 0은 `"0"`이다.
`decode(code)`는 비어 있지 않은 유효 문자열을 정수로 되돌린다. 음수·빈 문자열·알파벳 밖 문자는 `ValueError`, 잘못된 자료형은 `TypeError`다.

## 3. 해시 테이블

`HashTable`은 문자열 키와 값을 저장하고 `set`, `get`, `__contains__`, `__len__`을 제공한다. 충돌은 연결 리스트 체이닝으로 처리한다.
키의 해시는 각 유니코드 코드 포인트에 대해 `h = (31 * h + ord(character)) mod capacity`로 계산한다. 초기 용량은 8이고 항목 수/용량이 0.75를 초과하면 2배로 늘려 재배치한다.
내장 `dict`, `set`, `hash()`는 구현에 사용하지 않는다. 테이블은 항목이 없으면 `get`에서 `None`을 돌려준다.

## 4. 단축기

`Shortener.shorten(url)`은 절대 HTTP 또는 HTTPS URL(호스트 필수)을 받아 코드를 돌려준다. 같은 URL을 다시 넣으면 같은 코드를 돌려준다.
`expand(code)`는 등록되지 않은 코드에 `KeyError`를 발생시킨다. 잘못된 URL은 `ValueError`로 거부한다. 코드는 순차 ID를 base62로 인코딩하며 해시 테이블은 URL→코드와 코드→URL 조회에 사용한다.

## 5. 웹 서버

`python3 src/server.py --port PORT` 또는 `make serve`로 서버를 시작한다(기본 포트 8000).
`GET /`은 URL 입력 폼을, URL을 제출하는 `POST /`는 단축 코드와 링크 결과를 보여준다. `GET /<code>`는 등록된 URL로 리다이렉트하고, 없는 코드는 404로 응답한다.
`GET /table`은 해시 테이블의 각 버킷, 연결 리스트, 키의 Horner 해시 계산 과정 및 방문한 버킷을 보여준다. HTML 출력은 이스케이프한다.

## 6. 경계 사례

* base62: 0, 61/62 경계, 큰 정수 왕복, 잘못된 자료형·음수·빈 문자열·잘못된 글자.
* 해시 테이블: 빈 테이블, 삽입/조회/갱신, 충돌 체인, 없는 키, 리사이즈 뒤 모든 항목 유지.
* 단축기: 유효 URL, 같은 URL 중복, 없는 코드, 빈 값·상대 URL·지원하지 않는 스킴·호스트 없는 URL.
* 서버: 메인 폼, 성공/오류 제출, 코드 리다이렉트/404, 버킷 표시와 HTML 이스케이프.
