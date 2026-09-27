# Intent: README Node.js 최소 버전 노출 개선

- **작성자**: taejung3852
- **일자**: 2026-09-25
- **관련 Issue**: 없음
- **상태**: Approved

---

## 1. 문제 및 배경 (Why)

OwnHands README에는 이미 `Node.js 18 이상` 요구사항이 적혀 있지만, `시작하기` 문장 안에 포함되어 있어 README를 빠르게 훑는 사용자가 설치 전제조건을 놓칠 수 있다.

- **대상 사용자**: OwnHands를 처음 설치하거나 설치 방법을 확인하는 사용자.

## 2. 목표 결과 및 가치 (What)

README를 처음 보는 사용자가 설치를 시도하기 전에 **Node.js 18 이상이 필요하다는 사실을 즉시 인지**할 수 있게 한다.

### 변경 방향

- README 상단 badge 영역에 **Node.js 18+** 표시를 추가한다.
- `시작하기`에서 설치 전제조건을 별도의 **요구 사항** 블록으로 분리한다.
- 표시되는 Node.js 버전은 `package.json`의 현재 선언인 `>=18`과 일치시킨다.

### 성공 기준

- README 상단을 훑는 것만으로 Node.js 최소 버전을 확인할 수 있다.
- 설치 명령을 보기 전에 `Node.js 18+`가 요구사항임을 확인할 수 있다.
- README와 `package.json`의 Node.js 요구 버전이 서로 모순되지 않는다.

## 3. 비목표 (Non-goals & Boundaries)

이번 변경에서는 다음을 하지 않는다.

- Node.js 지원 버전 정책 변경
- `package.json`의 `engines.node` 변경
- CLI에 Node.js 버전 검증 로직 추가
- 설치 명령 또는 CLI 동작 변경
- 다른 환경 요구사항의 정책 변경

## 4. 핵심 제약 조건 (Constraints)

- 이번 변경은 README 가독성 개선 범위에 한정한다.
- Node.js 최소 버전의 Source of Truth는 현재 `package.json`의 `engines.node: ">=18"` 선언과 일치해야 한다.

## 확인된 Fact

- `package.json`은 현재 `"node": ">=18"`을 선언한다.
- README `시작하기`에도 현재 `Node.js 18 이상`이라고 적혀 있다.
- 따라서 이번 작업은 새로운 요구사항 추가가 아니라 **기존 요구사항의 가시성 개선**이다.
