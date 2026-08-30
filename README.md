# KIST DRL G1 — StrictDoc 데모

KAPEX-G1 협업 시연 프로젝트의 요구사항·인터페이스를 [StrictDoc](https://strictdoc.readthedocs.io/)으로
관리할 경우의 결과물을 보여주는 **검토용 데모**입니다.

Notion의 `SYS-REQ` / `ICD` 데이터베이스 일부를 발췌해 옮기고, 여기에 구현 코드와 검증 항목을
연결하여 요구사항 → 인터페이스 → 코드 → 검증의 추적성이 어떻게 표현되는지 확인할 수 있습니다.

---

## 빠른 실행

```bash
pip install -r requirements.txt
```

```bash
strictdoc export . --output-dir output
```

생성된 `output/html/index.html`을 브라우저로 엽니다.

웹 편집 GUI로 띄우려면:

```bash
strictdoc server .
```

> `strictdoc` 명령을 찾지 못하면 `python -m pip show strictdoc`로 설치 경로를 확인하고
> `Scripts` 디렉터리를 PATH에 추가하세요.
> Windows 사용자 설치 기준 경로는 보통
> `%APPDATA%\Python\Python313\Scripts` 입니다.

---

## 데모 범위

Notion 전체가 아니라 **음성 인터랙션 · 시나리오 실행 · 안전 · 모니터링** 수직 단면만 옮겼습니다.

| 문서 | 건수 | 출처 |
|---|---|---|
| 시스템 요구사항 (SYS-REQ) | 7건 | Notion `SYS-REQ` DB (전체 14건 중 발췌) |
| 인터페이스 정의서 (ICD) | 15건 | Notion `ICD` DB (전체 22건 중 발췌) |
| 검증 계획 (TEST CASE) | 6건 | **데모용 가상 예시** — Notion에 원본 없음 |
| 구현 코드 스텁 | 7개 파일 | **데모용 스텁** — 실제 레포 코드 아님 |

**실데이터는 요구사항·인터페이스 본문뿐입니다.** `src/`의 코드와 검증 계획은 추적성 표현을
보이기 위해 작성한 것으로, 실제 레포지토리의 코드가 아닙니다. 각 노드의 `Notion 원본` 필드에서
원본 레코드로 이동할 수 있습니다.

---

## 디렉터리 구조

```
kist-drl-g1-strictdoc-demo/
├── strictdoc_config.py          프로젝트 설정 (StrictDoc 0.28+ Python 형식)
├── requirements.txt             strictdoc==0.28.3 고정
├── docs/
│   ├── kist_g1.sgra             공용 문법 — 노드 타입과 필드 스키마 정의
│   ├── 00_overview.sdoc         프로젝트 개요 및 데모 안내
│   ├── 10_sys_req.sdoc          시스템 요구사항 (추적 트리의 ROOT)
│   ├── 20_icd.sdoc              인터페이스 정의서
│   ├── 30_verification.sdoc     검증 계획 (데모용 예시)
│   └── 40_architecture.sdoc     아키텍처 — ICD에서 자동 생성 (직접 편집 금지)
├── tools/
│   ├── gen_arch.py              ICD -> Mermaid 다이어그램 생성기
│   ├── check_markers.py         @relation 마커 UID 검증 (멀티레포용)
│   ├── fetch_sources.py         개발 레포들을 _src/ 로 체크아웃
│   ├── repos.json               대상 레포 목록
│   └── dev-repo-workflow.example.yml
├── .github/workflows/docs.yml   빌드 + 배포 CI (예시)
└── src/                         @relation 마커를 가진 구현 코드 스텁
    ├── cortex/                  stt / tts / orchestrator / vlm / gui_bridge
    ├── ext_sensor_io/           mic_publisher
    └── safety/                  estop_monitor
```

`docs/kist_g1.sgra`가 이 프로젝트의 **스키마**입니다. 세 문서가 모두 이 파일을
`IMPORT_FROM_FILE`로 공유하므로, 필드를 추가·변경할 때 한 곳만 고치면 됩니다.

---

## 화면 안내

문서마다 네 가지 화면이 생성됩니다 (문서 상단 탭에서 전환).

| 화면 | 용도 |
|---|---|
| **DOC** | 사람이 읽는 문서. 리뷰 회의에서 띄우는 화면 |
| **TABLE** | 요구사항을 표로. 필드가 컬럼이 된다. 엑셀 시트 대체 |
| **TRACE** | 좌우 2단. 각 노드의 부모·자식을 한 단계 확인 |
| **DEEP-TRACE** | 요구사항 → 인터페이스 → 코드 → 검증 전 체인을 한 화면에 |

프로젝트 전체 화면은 좌측 최상단 아이콘에서 접근합니다 — Project tree,
Traceability matrix, Source coverage, Project statistics, Search.

---

## 확인해 볼 만한 지점

**1. 미구현 요구사항 자동 검출** — `SYS-REQ-32`에는 의도적으로 구현 코드를 연결하지
않았습니다. **Source coverage** 화면에서 이 요구사항이 코드에 연결되지 않았음이 자동으로
드러납니다. Notion·엑셀에서는 사람이 대조하지 않으면 알 수 없는 항목입니다.

**2. 코드에서 요구사항으로 역추적** — `src/`의 각 파일은 주석에
`@relation(SYS-REQ-27, scope=function)` 형태의 마커를 갖습니다. Source coverage에서
파일을 열면 코드가 렌더링되고 각 함수 옆에 요구사항 링크가 붙습니다.

**3. 스키마 강제** — `우선순위: P3`처럼 문법에 없는 값을 쓰면 빌드가 실패합니다.
아래를 실행해 직접 확인할 수 있습니다.

```bash
python -c "import io,re; p='docs/10_sys_req.sdoc'; s=io.open(p,encoding='utf-8').read(); io.open(p,'w',encoding='utf-8',newline='\n').write(s.replace('PRIORITY: P1','PRIORITY: P3',1)); print('P1 -> P3 주입 완료. 이제 export를 실행하세요.')"
```

**4. 인터페이스 ↔ 요구사항 연결** — `SYS-REQ-27`의 DEEP-TRACE를 열면 이를 구현하는
인터페이스 4건(ICD-3, ICD-33, ICD-64, ICD-42)과 구현 코드, 검증 항목 2건이 한 화면에
나타납니다.

**5. 변경 이력이 곧 git 이력** — 릴리스 간 요구사항 변경 리포트를 자동 생성할 수 있습니다.

```bash
strictdoc export . --generate-diff-git "HEAD~1..HEAD" --output-dir output
```

---

## 도입 시 검토가 필요한 사항

- **Notion과의 SSOT 정리가 선행되어야 합니다.** 병행하면 진실 원천이 둘이 되어 반드시
  어긋납니다. 어느 쪽이 원본이고 어느 쪽이 미러인지 먼저 정해야 하며, 협업기관의 Notion
  접근 빈도가 핵심 변수입니다.
- **비개발자의 편집 경로가 필요합니다.** `.sdoc` 텍스트 편집을 시스템 엔지니어·PM에게
  강요할 수 없으므로 `strictdoc server .` 운용 방안을 함께 정해야 합니다.
- **선택지 값 정규화가 필요했습니다.** StrictDoc 문법은 선택지 값에 괄호·쉼표를 허용하지
  않아 `기능 (FR)` → `FR`, `Getter (Pull)` → `Getter`로 정규화했습니다. 실제 이관 시
  이 매핑 규칙을 문서화해야 합니다.
- **요구사항 서술문을 신규 작성해야 합니다.** Notion DB에는 *요구사항명*과 *수용 기준*만
  있고 서술문 필드가 없습니다. 본 데모에서는 수용 기준을 근거로 "~하여야 한다" 형식의
  서술문을 작성했으며, 실제 이관 시에도 동일한 작업이 필요합니다.
- **버전을 고정해야 합니다.** 설정 파일 형식이 2025-Q4에 TOML → Python으로 바뀐 전례가
  있어 `requirements.txt`에서 `0.28.3`으로 핀했습니다.

---

## 아키텍처 다이어그램

StrictDoc에는 작도 기능이 없습니다. 대신 **Mermaid가 0.28부터 기본 활성화**되어 있고
`mermaid.min.js`가 패키지에 번들되어 있어(CDN 불필요) 텍스트로 쓴 다이어그램이 그대로
렌더링됩니다.

이 데모는 한 걸음 더 나아가 **다이어그램을 ICD에서 생성**합니다.

```bash
python tools/gen_arch.py
```

`docs/20_icd.sdoc`의 각 `[ICD]` 노드는 이미 다이어그램에 필요한 모든 정보를 갖고 있습니다.

| ICD 필드 | 다이어그램에서 |
|---|---|
| `SOURCE` / `TARGET` | 화살표의 양 끝 |
| `TOPIC` (없으면 `MSG_TYPE`) | 화살표 라벨 |
| `COMM_TYPE` | 선 모양 (DDS는 실선, HTTPS/gRPC/WebSocket은 점선) |
| `STATUS` | 컨테이너 색상 (초록 완료 / 노랑 진행 중 / 빨강 시작 전) |

컨테이너를 배치 구역으로 묶는 규칙만 `tools/gen_arch.py`의 `ZONES`에 있습니다.
나머지는 전부 ICD에서 나옵니다.

### 왜 여러 장으로 나누는가

다이어그램은 **ICD 문서의 섹션(데이터 경로) 단위로 쪼개서** 생성합니다.
15개 인터페이스를 한 장에 그리면 그래프 자연폭이 2000px를 넘는데, StrictDoc 본문
칼럼은 보통 600~1000px입니다. mermaid가 칼럼에 맞춰 축소하면서 글씨가 뭉개집니다.

경로별로 나누면 각 그림의 자연폭이 220~700px가 되어 **축소 없이** 렌더링됩니다.
쪼개는 기준은 ICD 문서에 이미 있는 `[[SECTION]]` 제목이라 별도 설정이 없습니다.

같은 이유로 화살표 라벨에는 ICD 번호만 넣고, 토픽·메시지 타입은 각 그림 아래
생성 표로 뺐습니다. 긴 토픽 문자열이 그래프 폭을 결정하기 때문입니다.

CI에서 어긋남을 잡을 수 있습니다.

```bash
python tools/gen_arch.py --check
```

ICD를 고치고 다이어그램을 다시 만들지 않으면 종료코드 1로 빌드가 실패합니다.
**"도면과 실제가 다른" 상태가 구조적으로 불가능해집니다.**

`docs/40_architecture.sdoc`은 생성 산출물이므로 직접 편집하지 마세요.

---

## 배포 — 상시 서버가 필요한가?

**아니오.** `strictdoc export`의 결과물은 정적 HTML 파일입니다. 웹서버 프로세스가
계속 떠 있을 필요가 없습니다. (이 README의 `python -m http.server`는 로컬 확인용일 뿐
배포 방식이 아닙니다.)

| 용도 | 방식 | 상시 프로세스 |
|---|---|---|
| **읽기 (대다수)** | CI가 빌드 → GitHub Pages 등 정적 호스팅 | 불필요 |
| **편집 (비개발자)** | 필요할 때만 `strictdoc server .` 로컬 실행 → 커밋 | 불필요 |
| **상시 편집 서버** | `strictdoc server`를 사내 호스트에 상주 | 필요 |

권장은 **정적 배포 + 편집은 로컬 서버**입니다. 시스템 엔지니어·PM이 요구사항을
고쳐야 할 때만 자기 PC에서 `strictdoc server .`를 띄워 GUI로 편집하고, 결과 `.sdoc`을
커밋하면 CI가 사이트를 갱신합니다. 서버를 24시간 띄워두고 인증·백업을 관리할 필요가
없습니다.

### GitHub Pages 설정

이 레포는 **공개(public)** 를 전제로 한다. 공개 레포는 GitHub Free를 포함한
모든 플랜에서 Pages를 쓸 수 있다.

1. 요구사항 레포를 **public** 으로 만들고 push
2. **Settings → Pages → Build and deployment → Source = `GitHub Actions`**
   (`gh-pages` 브랜치 불필요. `.github/workflows/docs.yml`이 이미 이 방식)
3. main에 push → Actions 실행 → `https://<org>.github.io/<repo>/`

토큰 설정이 필요 없다. CI가 비공개 레포를 건드리지 않기 때문이다 (아래 참고).

### ⚠️ 공개 빌드는 소스를 싣지 않는다

`REQUIREMENT_TO_SOURCE_TRACEABILITY` 를 켜면 StrictDoc은 스캔한 **모든 소스 파일을
전문 그대로** `_source_files/**.html` 로 렌더링한다. 요구사항 레포가 공개인데 이
기능이 켜져 있으면 비공개 개발 레포의 소스가 통째로 공개된다.

요구사항·인터페이스를 공개하는 것과 구현 소스를 공개하는 것은 별개의 결정이므로
빌드 프로파일을 나눴다.

```bash
SDOC_PROFILE=public strictdoc export . --output-dir output   # 공개용
strictdoc export . --output-dir output                       # 사내용 (기본값)
```

| | `public` | `internal` (기본) |
|---|---|---|
| 페이지 수 | 23 | 31 |
| `_source_files/` | 없음 | 있음 |
| `source_coverage.html` | 없음 | 있음 |
| 소스 코드 노출 | 없음 | 전문 포함 |

CI는 `public` 프로파일로만 빌드하며, 배포 직전에 `_source_files/` 가 생겼는지
검사해 실수로 프로파일이 바뀌면 배포를 막는다.

**소스 커버리지 화면이 필요하면 사내에서 로컬로 빌드한다.**

```bash
python tools/fetch_sources.py
strictdoc export . --output-dir output
```

> 공개 레포에서는 workflow 아티팩트도 누구나 다운로드할 수 있다. 그래서 CI는
> 비공개 소스를 아예 체크아웃하지 않는다. 사내 빌드는 로컬에서만 한다.

### Vercel에 올리기

결과물이 순수 정적 파일이라 Vercel에도 그대로 올라간다. **가장 빠른 방법은 CLI다.**

```bash
npx vercel deploy output/html --prod
```

첫 실행 시 로그인과 프로젝트 이름을 물어보고, 끝나면 URL을 준다. GitHub 연동도
빌드 설정도 필요 없다. 고객사에 급히 보여줄 때 이 방법이 가장 짧다.

자동 배포가 필요하면 `.github/workflows/vercel.yml` 을 쓴다. Vercel 빌드 이미지의
Python 환경에 의존하지 않도록 **GitHub Actions에서 빌드한 뒤 결과 디렉터리만
올리는** 구성이다. Secrets 3개(`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`)가
필요하며, 뒤의 두 개는 로컬에서 `npx vercel link` 를 한 번 돌리면
`.vercel/project.json` 에 생긴다.

`vercel.json` 은 `cleanUrls` 를 **끈다.** 켜면 `/foo.html → /foo` 리다이렉트가
생기는데 StrictDoc의 내부 링크는 `.html` 을 명시하므로 불필요한 리다이렉트가 붙는다.

### ⚠️ Vercel Hobby(무료)는 이 용도로 못 쓴다

Vercel의 공정 이용 정책상 **Hobby 플랜은 비상업적 개인 사용 전용**이다.
상업적 사용의 정의가 넓다 — *"프로젝트 제작의 어떤 부분에든 관여한 사람의 금전적
이득을 목적으로 하는 배포. **급여를 받는 직원이나 컨설턴트가 코드를 작성한 경우 포함**."*

수주 프로젝트의 산출물을 고객사에 보여주는 용도이므로 상업적 사용에 해당한다.
**Pro 플랜(약 $20/user/월)이 필요하다.** 사이트를 공개로 두는 것과는 무관한 문제다.

참고로 Vercel의 비밀번호 보호는 Enterprise 이거나 Pro + **$150/월** 애드온이
필요하다. Hobby에서는 팀 멤버 대상 Vercel Authentication만 가능하다.

### GitHub Pages vs Vercel

| | GitHub Pages | Vercel |
|---|---|---|
| 비용 | **무료** (공개 레포, 모든 플랜) | Pro $20/user/월 필요 |
| 설정 | Settings에서 Source 지정 | CLI 한 줄 또는 Secrets 3개 |
| PR 프리뷰 | 없음 | 있음 |
| 커스텀 도메인 | 가능 | 가능 |
| 워크플로 | `.github/workflows/docs.yml` | `.github/workflows/vercel.yml` |

**공개 정적 문서 사이트라면 GitHub Pages로 충분하고 비용이 들지 않는다.**
Vercel은 PR마다 프리뷰 URL이 생기는 이점이 있으나, 요구사항 문서 리뷰에서 그
가치가 월 $20을 넘는지는 판단이 필요하다.

### 결과물은 자립형이다

빌드 결과물에는 CDN 참조가 전혀 없다 (mermaid.js도 번들). 폐쇄망 포함 어떤
정적 호스팅에도 그대로 올릴 수 있다.

> zip으로 전달할 때는 `index.html`을 더블클릭하지 말고 로컬 서버로 열 것.
> JS가 `fetch()`를 쓰기 때문에(turbo 내비게이션, 검색) 브라우저가 `file://`에서
> 이를 차단한다.
>
> ```
> cd html && python -m http.server 8000
> ```

---

## 멀티레포 운영

코드는 8개 레포에 흩어져 있고 요구사항은 이 레포에 있습니다. **레포를 합칠 필요는
없습니다.** StrictDoc의 마커 스캔이 로컬 파일시스템 한 트리를 훑을 뿐이므로,
빌드 시점에만 한 디렉터리 아래로 모으면 됩니다.

```
요구사항 레포                        개발 레포 (8개)
├── docs/          요구사항·ICD      kist-drl-g1-cortex
├── tools/                          kist-ext-sensor-io
└── _src/          ← 빌드 시 clone   kist-gearsonic-inference
    ├── kist-drl-g1-cortex/         ...
    └── ...                         각 레포 코드에 @relation 마커
```

`_src/`는 `.gitignore`에 있는 빌드 산출물입니다. 커밋하지 않습니다.

```bash
python tools/fetch_sources.py
```

대상 레포와 ref는 `tools/repos.json`에 있습니다. 릴리스 스냅샷이 필요하면 ref를
커밋 SHA로 고정합니다.

### 개발자 작업 흐름

개발자는 **자기 레포에서만** 작업합니다. 요구사항 레포를 clone 하거나 StrictDoc을
설치할 필요가 없습니다.

1. 개발자가 자기 레포에서 코드를 고치고 `@relation(SYS-REQ-27, scope=function)` 마커를 답니다.
2. 그 레포 CI가 마커의 UID가 실제로 존재하는지 검증합니다 (`tools/check_markers.py`).
   오타나 삭제된 요구사항을 가리키면 PR이 막힙니다.
3. main에 머지되면 `repository_dispatch`로 요구사항 레포에 재빌드를 요청합니다.
4. 요구사항 레포 CI가 전 레포를 다시 받아 사이트를 갱신합니다.

3번을 붙이지 않아도 야간 스케줄 빌드가 하루 한 번 최신화하므로, 단계적으로 도입할 수
있습니다.

```bash
python tools/check_markers.py --export-uids uids.txt   # 요구사항 레포: UID 목록 배포
python tools/check_markers.py --uids uids.txt --scan . # 개발 레포: 자기 코드 검증
```

워크플로 예시는 두 개입니다.

- `.github/workflows/docs.yml` — 요구사항 레포 (수집 → 검증 → 빌드 → 배포)
- `tools/dev-repo-workflow.example.yml` — 각 개발 레포에 복사해서 쓰는 예시

> 두 워크플로는 비공개 레포 토큰과 Pages 설정이 필요해 **실제 실행 검증은 하지
> 않았습니다.** 조직 환경에 맞게 조정이 필요합니다.

### 일부 레포만 있어도 빌드는 성공한다

이 성질이 멀티레포 운영을 가능하게 합니다. 검증해 본 결과, 소스 트리가 통째로 없어도
`strictdoc export`는 **종료코드 0으로 성공**하고 커버리지만 비어 나옵니다.

즉 한 레포의 접근 권한이 없거나 클론이 실패해도 전체 빌드가 무너지지 않습니다.
새 레포를 `repos.json`에 추가하는 것도 무해합니다.

---

## 다음 단계 (고객 승인 시)

1. Notion `SYS-REQ` 14건 + `ICD` 22건 전량 이관
2. GitHub Projects의 Test 항목을 `TEST_CASE` 노드로 이관 (또는 검증 문서 제외 결정)
3. 실제 레포(`kist-drl-g1-cortex`, `kist-ext-sensor-io` 등)에 `@relation` 마커 삽입
4. GitHub Actions로 export 자동화 + GitHub Pages 배포 (`gen_arch.py --check` 포함)
5. `strictdoc server` 상시 운용 여부 결정
6. 기존 C4 Container 도면(`KIST_DRL_G1_Container_Arch.pdf`)의 처리 방향 결정 —
   전체 조감도는 SVG로 첨부하고, 인터페이스 상세는 생성 다이어그램에 맡기는 이원화를 권장
