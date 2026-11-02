---
name: motion
description: 문서(pptx, docx, pdf, ipynb, md, txt, html)를 지정하면 한국어 내레이션·자막이 입혀진 모션 영상(장면별 애니메이션이 담긴 단일 HTML 플레이어)을 만들고, 장면별 화면 캡처 PNG까지 생성한다. 만든 HTML 플레이어를 MP4로 변환할 수도 있다. "이 문서로 영상 만들어줘", "강의자료를 모션 영상으로", "PPT를 내레이션 영상으로", "슬라이드를 애니메이션으로", "장면 캡처해줘", "문제제기 영상", "docs 폴더 전부 영상화", "HTML을 MP4로 변환해줘"처럼 문서나 강의자료를 설명 영상으로 바꾸거나 기존 영상을 고치고 다시 캡처하려는 요청에는 '영상'이라는 말이 분명하지 않아도 이 스킬을 사용한다. 문서 없이 주제만으로 만드는 영상이나 웹사이트 홍보 영상, HyperFrames 작업에는 사용하지 않는다.
---

# 문서 → 모션 영상 + 화면 캡처

문서 하나가 다음 두 결과물이 되고, 요청하면 MP4도 만든다.

- `<출력>/<output>.html`: 음성·자막·장면이 내장된 단일 파일 플레이어 (재생바, 배속, 음성 보정 포함). 브라우저로 여는 HTML이다. 글꼴만 CDN에서 받고, 오프라인에서는 맑은 고딕으로 대체된다.
- `<출력>/<output>/NN_장면제목.png`: 장면별 완성 화면 캡처 (1280×720)
- `<출력>/<output>.mp4`: 요청할 때만 만드는 일반 동영상 파일 (H.264 + AAC)

장면 하나는 자체 완결된 1280×720 애니메이션 HTML + TTS 음성 + 문장별 자막이다. 도구가 TTS, 조립, 캡처를 맡고, 내가 쓰는 것은 대본과 장면 HTML이다.

## 경로 약속

- `M` = 이 스킬 폴더 (`<skill>/scripts/*.py`를 실행)
- 프로젝트 = `./builds/<영문 슬러그>/` (사용자가 지정하면 그곳)
- 출력 = `./outputs/` (사용자가 지정하면 그곳)
- `output` = 확장자 없는 결과 파일명. 사용자가 정하지 않으면 원본 문서명이다.

사용자가 문서를 지정하지 않았다면 후보를 찾아 묻는다. 강의 대상은 요청이나 문서에서 파악해 대본의 어휘 수준을 맞추고, 알 수 없으면 현업 실무자로 둔다. 필요한 패키지가 없으면 `pip install edge-tts mutagen playwright python-pptx python-docx pymupdf`를 안내한다. 브라우저는 설치된 Edge/Chrome을 쓴다.

## 절차

### 1. 문서 추출

```
python M/scripts/ingest.py "<문서>" <프로젝트>
```

`ref/notes.txt`를 처음부터 끝까지 읽고, `ref/page_NN.jpg`가 있으면 **모든 이미지를 Read로 직접 본다**. 도표와 이미지 슬라이드는 텍스트로 나오지 않기 때문이다. `[NOTES]`의 정정·보충 내용은 대본에 반영한다. docx의 그림은 추출되지 않고 `[image]`로만 표시되므로, 내용에 중요해 보이면 보고에 적는다.

### 2. 대본 작성 → TTS

`<프로젝트>/script.json`을 쓴다. 자막 표기(영어 원문)로 쓰면 내레이션은 자동으로 한글 발음이 된다.

```json
{"title": "강의 제목", "output": "원본 문서명",
 "pron": {"Qdrant": "큐드란트"},
 "scenes": [{"id": "s01", "title": "장면 제목", "lines": ["한 문장.", "또 한 문장."]}]}
```

```
python M/scripts/mk_scenes.py <프로젝트>    # SENTENCE? ENGLISH? SYMBOL? LONGLINE? 경고가 없을 때까지 고친다
python M/scripts/tts.py <프로젝트>          # 문장별 시각 출력. 바뀐 장면만 재합성. LONG? 장면은 나눈다
```

장면 구성과 대본 규칙은 `references/script.md`를 읽고 따른다.

### 3. 장면 작성 → 검사

`references/scene.md`, `assets/example_fragment.html`, `assets/example_devices.html`을 읽은 뒤, 장면을 `<프로젝트>/src/sNN.html` 조각으로 쓴다. 타이밍은 `{c3+0.6}` 같은 토큰으로 문장에 묶는다. 대본을 고쳐도 애니메이션이 음성을 따라가게 하기 위해서다.

```
python M/scripts/gen.py <프로젝트>          # src → 독립 실행 sNN.html
python M/scripts/check.py <프로젝트>        # 전 장면 후반부 스냅샷 + 문제 목록
python M/scripts/check.py <프로젝트> s03:8,15,L   # 특정 시점 확인
```

장면이 10개를 넘으면 5개 단위로 쓰고 검사한다. `CLEAN`이 나올 때까지 `OVERFLOW?`, `CLIPPED?`, `TIMING?`, `ERROR`, `RULE`을 해결하고, 자동 검사가 못 잡는 겹침과 어색한 배치를 보려고 **모든 장면의 `snaps/*.png`를 Read로 본다.** 깨끗해질 때까지 반복한다.

### 4. 조립 → 캡처

```
python M/scripts/build.py <프로젝트> --out <출력>
python M/scripts/capture.py <프로젝트> --out <출력>
```

캡처는 장면 끝 직전의 완성 화면을 찍는다. 대표 캡처 몇 장을 열어 글꼴과 레이아웃을 확인한다. 장면을 수정한 뒤에는 `gen → check → build → capture`를 다시 실행해 영상과 캡처를 맞춘다.

### 5. MP4 변환 (요청할 때만)

```
python M/scripts/mp4.py <출력>/<output>.html           # 같은 폴더에 .mp4 생성
python M/scripts/mp4.py <출력>/<output>.html --no-subs # 자막 없는 1280×720
```

`build.py`가 만든 플레이어 HTML만 변환할 수 있고 프로젝트 폴더는 없어도 된다. 다른 HTML은 오류로 거부된다. 기본 화면은 1280×804다. 장면을 가리지 않도록 플레이어처럼 720 높이 아래에 자막 띠를 붙이기 때문이다. 옵션은 `-o 파일`, `--fps`(기본 30), `--jobs`(동시 렌더 장면 수, 기본 CPU 절반)다. 프레임을 하나씩 찍으므로 시간이 걸린다. 8코어에서 기본 설정으로 영상 길이의 약 1.4배였으니 긴 영상은 `run_in_background`로 실행한다. ffmpeg가 없으면 `pip install imageio-ffmpeg`를 안내한다. 장면을 고친 뒤에는 `build` 후 다시 변환한다. 변환 뒤 대표 프레임을 하나 뽑아 확인한다.

### 6. 보고

출력 경로, 장면 수, 총 길이(`build.py`가 출력한 값), 해결하지 못한 것을 짧게 보고한다. 음성은 직접 들을 수 없으니 발음을 확인하지 못했다는 점도 밝힌다.

## 여러 문서를 한꺼번에

문서마다 프로젝트를 나누고 문서당 서브에이전트 하나를 병렬로 띄운다. 각 에이전트에는 이 SKILL.md 경로, 문서 경로, 프로젝트 경로, 출력 경로, 강의 대상을 전달한다. 자기 프로젝트 폴더와 출력 파일만 건드리게 한다.

## 기존 영상 수정

프로젝트 폴더가 남아 있으면 `script.json`이나 `src/sNN.html`을 고치고 필요한 단계부터 다시 실행한다. 대본을 고쳤으면 `mk_scenes → tts → gen → check → build → capture`, 장면만 고쳤으면 `gen → check → build → capture`다. MP4를 만들었다면 `mp4`까지 다시 실행한다. `script.json` 없이 `scenes.json`만 있는 옛 프로젝트는 `scenes.json`을 직접 고치고 `mk_scenes`는 건너뛴다.
