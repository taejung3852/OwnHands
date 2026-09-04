# DevHarness

DevHarness는 에이전트 개발 작업의 Event와 Evidence를 로컬에 보존하고, 확보된 근거 범위에서만 검토 가능한 Claim을 만드는 도구다.

## M1 개발 검증

Python 3.12와 표준 라이브러리만 사용한다.

```bash
PYTHONPATH=src uv run --python 3.12 python -m unittest discover -s tests -v
```

비민감 HWPX 합성 fixture로 최소 수직 흐름을 실행한다.

```bash
PYTHONPATH=src uv run --python 3.12 python -m devharness m1-demo \
  --data-root /tmp/devharness-m1-evidence \
  --output /tmp/devharness-m1-review.html
```

Raw Evidence는 지정한 OS user-data 경계에 남고, HTML과 JSON report에는 Evidence ID·hash·scope·판정만 포함된다. 이 HTML은 M1 review artifact이며 M5 Production UI가 아니다.
