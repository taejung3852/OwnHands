# M0-07 Brand & Dashboard Design Foundation Spike

이 디렉터리는 M5 Dashboard 구현 전 디자인 방향을 검토한 **비프로덕션 Spike**다. M0에서는 **B — Warm Paper Neutral + Ledger Indigo 색상 방향만 승인**했다. 화면 구조·글쓰기·상호작용은 M5에서 이 시안을 참고해 이어서 설계하며, 별도 승인 전에는 M5 Production Dashboard를 시작하지 않는다.

## 먼저 볼 것

- [Interactive HTML 시안](index.html)
- [세 방향 비교와 추천](design-evaluation.md)
- [UI/UX 참고 조사](research.md)
- [Probe 결과](probe-results.md)

HTML 상단에서 다음을 바꿀 수 있다.

- A — Signal Graphite
- B — Ledger Indigo (승인된 색상 방향, 기본값)
- C — Slate Violet
- Light / Dark
- Task Review / Harness Status / Evidence Detail

현재 참고 시안은 결론·확인 범위·주의점을 먼저 세 칸으로 보여 주고, 표·그림·원시 출력은 사용자가 native disclosure를 선택할 때만 펼친다. 이 정보 구조와 상호작용은 승인된 제품 계약이 아니며 M5에서 다시 판단한다. 시안은 JavaScript와 framework 없이 동작한다. 화면 데이터는 commit `ba7394f`에서 capture한 M0-06 합성 Probe의 여섯-check snapshot 한 벌만 사용한다. 이후 M0 audit에서 storage Probe가 확장돼도 세 방향과 18 screenshot의 동등 비교를 유지하기 위해 이 디자인 Fixture는 해당 snapshot에 고정한다.

## 화면 Capture

`screenshots/`에 다음 18개 조합이 있다.

```text
{signal,ledger,slate}-{light,dark}-{task,harness,evidence}.png
```

## 재현 Probe

```bash
node docs/design/m0-07/probes/m0-07-design-probe.mjs
node docs/design/m0-07/probes/m0-07-browser-probe.mjs
node docs/design/m0-07/probes/m0-07-browser-probe.mjs --write-screenshots
python3 /Users/parktaejung/.agents/skills/diagram-design/scripts/self_check.py docs/design/m0-07/index.html
```

## 경계

- Production UI code가 아니다.
- 승인 범위는 B 색상 방향뿐이다. 문구·정보 위계·상호작용은 M5 참고안이다.
- 최종 logo, icon set, illustration, Brand Asset이 아니다.
- M0-06의 합성 Evidence를 제품 성공 데이터로 주장하지 않는다.
- 특정 참고 제품의 색상·layout·Asset을 복제하지 않는다.
- 원격 push·PR·Issue #8 종료는 별도 승인 전 수행하지 않는다.
