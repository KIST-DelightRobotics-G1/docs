# KIST DRL G1 — 시스템 문서

KAPEX-G1 협업 시연 프로젝트의 **시스템 요구사항(SYS-REQ) · 인터페이스 정의서(ICD) ·
아키텍처 · 검증 계획**을 [StrictDoc](https://strictdoc.readthedocs.io/)으로 관리한다.

**이 레포지토리가 유일한 원본(SSOT)이다.** Notion의 `SYS-REQ` / `ICD` 데이터베이스는
이관 후 폐기되었다.

사이트: <https://kist-delightrobotics-g1.github.io/docs/>

---

## 빠른 시작

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

```bash
strictdoc export . --output-dir output     # output/html/index.html 을 브라우저로
```

```bash
strictdoc server .                         # 웹 GUI 편집 (선택)
```

---

## 구조

```
docs/
├── strictdoc_config.py          프로젝트 설정 (StrictDoc 0.28+ Python 형식)
├── requirements.txt             strictdoc==0.28.3 고정
├── docs/
│   ├── kist_g1.sgra             공용 문법 — 노드 타입과 필드 스키마 (한 곳만 고친다)
│   ├── 00_overview.sdoc         프로젝트 개요 · 읽는 법
│   ├── 10_sys_req.sdoc          시스템 요구사항 (추적 트리의 ROOT)
│   ├── 20_icd.sdoc              인터페이스 정의서
│   ├── 30_verification.sdoc     검증 계획 — 시연(Demonstration) 기준
│   └── 40_architecture.sdoc     아키텍처 — ICD에서 자동 생성 (직접 편집 금지)
├── tools/
│   ├── gen_arch.py              ICD → Mermaid 다이어그램 생성기
│   ├── fetch_sources.py         개발 레포들을 _src/ 로 체크아웃 (소스 추적성용)
│   └── repos.json               대상 레포 목록
└── .github/workflows/docs.yml   빌드 + GitHub Pages 배포
```

문서마다 DOC / TABLE / TRACE / DEEP-TRACE 화면이 생성되고, 프로젝트 전체 화면
(Project tree, Traceability matrix, Source coverage, Statistics, Search)은 좌측 최상단
아이콘에서 연다.

---

## 문서 규칙

- **필드명 영어 · 본문 한글.** 선택지 값(PRIORITY, STATUS 등)은 `docs/kist_g1.sgra`에 정의된
  토큰만 쓴다. 문법에 없는 값은 빌드가 실패한다.
- **UID 체계**: `SYS-REQ-n` / `ICD-n` / `TC-n`. Notion 시절 번호를 그대로 잇는다.
- **선택지 정규화**: StrictDoc 선택지 값에는 괄호·쉼표를 쓸 수 없다.
  `기능 (FR)` → `FR`, `Getter (Pull)` → `Getter`.
- **검증 방법**: 시연으로 수용을 확인하는 항목은 `METHOD: Demonstration`.
  (`Test` / `Analysis` / `Inspection` / `Review` 중 택1)
- **코드 추적성**: 개발 레포에 마커를 넣지 않는다. 요구사항·ICD 노드가 `File` 관계로
  구현 파일을 가리킨다.

  ```
  RELATIONS:
  - TYPE: File
    VALUE: _src/cortex/src/cortex_perception/cortex_perception/stt_node.py
  ```

---

## 편집 워크플로 (변경 통제)

1. 브랜치를 만들고 `docs/*.sdoc` 을 편집한다 (텍스트 또는 `strictdoc server .`).
2. ICD를 바꿨으면 `python tools/gen_arch.py` 로 아키텍처 문서를 다시 생성한다.
3. `strictdoc export . --output-dir output` 으로 로컬 빌드를 확인한다.
4. PR → 리뷰 1명 → `main` 머지 → CI가 Pages 사이트를 갱신한다.
5. 시연 마일스톤마다 태그를 남긴다. 릴리스 간 변경 리포트:

   ```bash
   strictdoc export . --generate-diff-git "v0.1..v0.2" --output-dir output
   ```

---

## 아키텍처 도면 — 이원화

| 도면 | 원천 | 변경 빈도 | 역할 |
|---|---|---|---|
| `docs/40_architecture.sdoc` | ICD에서 `tools/gen_arch.py` 로 **생성** | 인터페이스 바뀔 때마다 | 경로별 상세. ICD와 어긋날 수 없음 |
| `docs/_assets/c4_container_architecture.svg` | draw.io **수작업** (프로젝트 개요 문서에 첨부) | 컨테이너 추가·삭제 때만 | 전체 그림 · 발표용 |

생성 도면은 직접 편집하지 않는다. `python tools/gen_arch.py --check` 가 "ICD는 바뀌었는데
도면은 안 바뀐" 상태를 잡는다 (CI에서는 경고).

**도면 원본은 `docs/_assets/KIST_DRL_G1_Arch.drawio`** (2페이지 — `C4_Context_Option1` · **`C4_Container_Option1`** = 현행 컨테이너 도면).
draw.io에서 *Open from → GitHub* 로 이 파일을 직접 열어 편집·저장한다.
SVG는 생성물이다:

- 사이트 빌드(`docs.yml`)와 릴리스는 매번 `.drawio` 에서 SVG를 export 한다 (`svg-theme: light`).
- `main` 에서 `.drawio` 가 바뀌면 `drawio-svg.yml` 이 `c4_container_architecture.svg` 를 다시 만들어 커밋한다
  (로컬 빌드용 사본).
- export 대상 페이지 이름은 워크플로의 `C4_PAGE` 에 있다. 페이지 이름을 바꾸면 같이 바꾼다.
- 웹 앱에서 수동 export 한 SVG를 쓸 때는 `python tools/pin_svg_light.py x.svg` 로 다크 테마 반전을 제거한다.

`docs/_assets/` 는 StrictDoc이 자동으로 사이트에 복사한다.

---

## 주간 동기화 (코드 → 문서·도면)

| 단계 | 누가 | 무엇 |
|---|---|---|
| 감지 | `weekly-sync.yml` (매주 월 09:00 KST, 수동 가능) | org 전 레포 main 을 `tools/sync_state.json` 의 마지막 SHA와 비교 → 커밋·새 토픽·pub/sub 코드·파일 이동·**File 관계 파손** 을 Issue 로 |
| 반영 | `/g1-sync` 스킬 (사람이 호출) | Issue 를 읽고 ICD 신규/갱신 · File 관계 · 도면 · TEST_CASE 를 판단해 PR 1개 + `sync_state.json` 갱신 |
| 승인 | 리뷰어 | PR 머지 → Pages · SVG 자동 갱신 |

로컬에서 감지만 해보려면:

```bash
python tools/sync_repos.py --report sync_report.md
```

---

## 소스 추적성

```bash
python tools/fetch_sources.py              # tools/repos.json 의 레포를 _src/ 로 clone
strictdoc export . --output-dir output     # Source coverage 포함 (internal 프로파일)
```

`_src/` 는 빌드 산출물이며 커밋하지 않는다. 릴리스 스냅샷이 필요하면 `repos.json` 의 `ref` 를
커밋 SHA로 고정한다.

> ⚠️ `_src/` 를 `.gitignore` 에 넣지 말 것. StrictDoc은 `.gitignore` 의 패턴을 소스 스캔
> 제외 목록에 그대로 합치므로, 넣는 순간 `File` 관계가 가리키는 파일을 찾지 못해
> 빌드가 실패한다 (`Requirement ... references a file that does not exist`).
> `fetch_sources.py` 가 대신 `.git/info/exclude` (로컬 전용) 에 등록한다.

File 관계는 `REQUIREMENT_TO_SOURCE_TRACEABILITY` 가 켜진 internal 프로파일에서만 검증된다.
public 프로파일(CI)은 소스 스캔을 하지 않으므로 `_src/` 없이도 빌드된다.

CI(Pages)도 같은 방식으로 `_src/` 를 받아 **소스 포함(internal)** 으로 빌드한다 — 모든 개발
레포가 public이라 토큰이 필요 없다. 레포가 비공개로 바뀌면 `docs.yml` 에서 `SDOC_PROFILE=public`
으로 되돌린다.

---

## CI / 릴리스

| 워크플로 | 트리거 | 하는 일 |
|---|---|---|
| `docs.yml` | main push · PR · 수동 | `_src/` 체크아웃 → 소스 포함 빌드 → main이면 Pages 배포 |
| `release.yml` | 태그 `v*` push · 수동 | 직전 태그 대비 **Diff/Changelog** 포함 사이트 + **문서별 PDF** → GitHub Release 첨부 |

**정책**
- **빌드 실패**: 문법(.sgra) 위반, 끊어진 UID 참조, 없는 File 경로 — `strictdoc export` 자체가 검증기다.
- **경고**: 아키텍처 도면 최신성(`gen_arch.py --check`), PDF 생성 실패, 미구현·미검증 요구사항.

**마일스톤 릴리스 절차**

```bash
git tag v0.2 && git push origin v0.2
```

릴리스 페이지에 `site.zip`(diff.html · changelog.html 포함)과 PDF가 올라온다.
로컬에서 변경 리포트만 보려면:

```bash
strictdoc export . --generate-diff-git "v0.1..v0.2" --output-dir output   # output/html/diff.html
```

PDF는 Chrome/Chromium이 있는 환경에서 `strictdoc export . --formats=html2pdf` 로 만든다.

## 버전

`strictdoc==0.28.3` 고정. 설정 파일 형식이 2025-Q4에 TOML → Python으로 바뀐 전례가 있어
버전을 올릴 때는 `requirements.txt` 와 `strictdoc_config.py` 를 함께 검토한다.
