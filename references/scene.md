# 장면 HTML 작성

`src/sNN.html`은 조각 파일이다. `gen.py`가 공통 CSS, 배경(`.dots`, `.bloom`), HTML 뼈대를 씌운다. 완성 예시는 `assets/example_fragment.html`, 흐름도·도넛·카운터·막대 예시는 `assets/example_devices.html`이다.

```html
<style>
.bloom{--bx:290px;--by:60px;}
.box{position:absolute;left:72px;top:200px;width:540px;height:320px;padding:22px;}
</style>
<!--body-->
<div class="cam">
<div class="kicker">Ⅰ · 절 이름</div>
<h1 class="h1">장면 제목</h1>
<div class="box glass in" style="--d:{c2}s">[[search cy]] 두 번째 문장과 함께 등장</div>
</div>
```

## 배치

kicker는 top 46, h1은 top 70, lead는 top 132다. 좌우 여백은 72~1208, 본문 영역은 lead가 없으면 약 top 150~650, 있으면 170~650이다. `.cam`이 끝까지 1.03배 커지므로 끝 화면에서 left 72는 x=55쯤에 보인다. 가장자리는 이 값보다 안쪽에 둔다.

## 타이밍

`{cN}`은 N번째 문장 시작, `{eN}`은 끝, `{end}`는 음성 끝, `{dur}`은 음성 + 1초다. 실제 장면 길이는 이를 초 단위로 올림한 값이다. `{c3+0.6}`처럼 오프셋을 붙인다. 각 요소는 그것을 말하는 문장이 시작될 때 나타나고, 모든 요소는 음성이 끝나기 전에 자리 잡아야 한다. `.cam`은 `--T`(음성 길이) 동안 천천히 확대되므로 장면 전체를 감싼다.

## 지켜야 할 규칙

플레이어는 `document.getAnimations()`로 일시정지, 이동, 배속을 처리한다. 그래서 다음을 지킨다.

- 움직임은 CSS 애니메이션이나 Web Animations API(`el.animate`, `delay` 사용)로만 만든다. `setTimeout`, `setInterval`, `requestAnimationFrame`, GSAP 같은 라이브러리는 멈출 수 없으므로 쓰지 않는다.
- 시작 상태는 `animation-fill-mode: both`로 숨긴다. 공통 클래스가 이미 처리한다.
- 외부 이미지와 슬라이드 이미지를 넣지 않는다. 내용을 인라인 SVG와 HTML로 다시 그린다.
- 1280×720 안에 전부 들어가야 한다. 자막은 플레이어가 프레임 밖에 표시하므로 프레임 전체를 쓸 수 있다.
- 내레이션 문장을 화면에 문단으로 옮기지 않는다. 화면에는 키워드, 숫자, 라벨만 둔다.
- 최소 글자 크기는 18px이다. 그보다 작으면 로드 시 강제로 커져 레이아웃이 깨질 수 있다. SVG는 viewBox 축척까지 곱한 크기로 따진다. 제목은 40~56px이다.
- JetBrains Mono에는 한글이 없다. `.mono` 안의 단위는 `<span class="unit">건</span>`으로 분리한다. 그대로 두면 한글만 대체 글꼴로 나와 간격이 벌어진다.
- 코드 창은 8줄 이내로 한다.


## 공통 클래스 (`assets/common.css`)

| 용도 | 클래스 |
|---|---|
| 뼈대 | `.cam` `.kicker` `.h1` `.lead` `.ab` `svg.st` |
| 패널 | `.glass` `.tint` `.chip` `.tag` `.win`(`.bar`) `.code`(`.cm .k .s .n`) |
| 등장 (`--d` 지연) | `.in` `.inL` `.fi` `.pop` |
| 강조 | `.in.lit` `.pop.lit`(`--l` 시각, `--lc` 색) `.in.dimout`(`--o`) `.tlit`(글자, `--l`) `.hl`(`--h`) |
| 그리기 | `.draw`(`pathLength="100"`, `--len:100`) `.gx` `.gy`(막대 성장) |
| 색 | `.cy .pu .bl .wr .am .gr` / `--c` 지정: `.ok .ng .cau .fe .be .db` + `.cc .bd` |
| 글꼴 | `.mono` `.unit` `.pk` |
| 아이콘 | `[[search]]`, `[[search cy]]` (`assets/icons.json`) |

강조 클래스는 표에 적힌 조합으로만 동작한다. `.lit` 단독이나 `.fi.lit`은 아무 효과가 없다. CSS `animation`은 하나만 적용되므로 한 요소에 등장 클래스를 둘 쓰지 말고, 직접 조합이 필요하면 `.in.lit`처럼 `animation`을 나열한 규칙을 장면 `<style>`에 만든다. `.tlit`, `.draw` 같은 단일 효과도 등장 클래스와 같은 요소에 쓰지 않고 요소를 감싼다.

## 시각 스타일

모든 영상이 같은 모습을 유지하도록 공통 토큰을 쓴다. `--bg #05070f`, `--surface #0c1224`, `--primary #3d7bff`, `--secondary #22e1ff`, `--accent #8b7bff`, `--text #eaf4ff`, 위험 `--warn #ff5d73`, 주의 `--amber #ffb547`. 글꼴은 Pretendard Variable, 숫자와 코드는 JetBrains Mono다. 플레이어가 CDN에서 글꼴을 받으므로 오프라인에서는 맑은 고딕으로 대체된다.

슬라이드에 효과를 입힌 것이 아니라 모션 영상이어야 한다. 장면마다 스스로 그려지는 차트, 카운터, 선이 이어지는 흐름도, 게이지, 매트릭스, 타임라인, 체크리스트, 변형되는 비교, 하이라이트 중 하나 이상의 시각 장치를 쓰고 인접 장면끼리 겹치지 않게 바꾼다. 표는 비교나 매트릭스로, 콜아웃은 강조 패널로, 절차는 흐름도로 바꾼다.
