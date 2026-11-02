# motion

문서(pptx, docx, pdf, ipynb, md, txt, html)를 한국어 내레이션·자막이 있는 모션 영상과 장면별 화면 캡처로 바꾸는 Claude Code 스킬입니다.

## 설치

```
git clone https://github.com/bjkim2004/motion ~/.claude/skills/motion
pip install edge-tts mutagen playwright python-pptx python-docx pymupdf
```

Edge 또는 Chrome이 필요합니다. 없으면 `python -m playwright install chromium`을 실행합니다. pptx 슬라이드 이미지는 PowerPoint(Windows) 또는 LibreOffice로 뽑습니다.

## 사용

Claude Code에서 `/motion docs/강의자료.pptx` 또는 "이 문서로 모션 영상 만들어줘"라고 요청합니다.

## 결과물

- `outputs/<제목>.html`: 음성·자막·장면이 내장된 단일 파일 플레이어 (브라우저로 재생, MP4 아님)
- `outputs/<제목>/NN_장면제목.png`: 장면별 1280×720 캡처

## 구성

| 경로 | 역할 |
|---|---|
| `SKILL.md` | 전체 절차 |
| `references/` | 대본과 장면 작성 규칙 |
| `scripts/` | ingest, mk_scenes, tts, gen, check, build, capture |
| `assets/` | 플레이어, 공통 CSS, 아이콘, 발음 사전, 예제 장면 |
