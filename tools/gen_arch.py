#!/usr/bin/env python3
"""ICD 문서에서 아키텍처 다이어그램(Mermaid)을 생성한다.

`docs/20_icd.sdoc` 의 각 [ICD] 노드는 이미 다음을 갖고 있다.

    SOURCE  → TARGET      : 화살표의 양 끝
    TOPIC / MSG_TYPE      : 상세표의 엔드포인트
    COMM_TYPE             : 선 모양 (DDS 실선 / 그 외 점선)
    STATUS                : 구현 상태 (색상)

즉 ICD 데이터베이스 자체가 아키텍처 그래프이므로, 다이어그램을 따로 그릴 필요 없이
여기서 생성한다. 손으로 그린 도면과 ICD가 어긋날 여지가 사라진다.

다이어그램은 ICD 문서의 **섹션 단위로 쪼개서** 생성한다. 전체를 한 장에 그리면
그래프 자연폭이 1500px를 넘어 문서 칼럼(보통 600~1000px)에서 심하게 축소되어
글씨를 읽을 수 없기 때문이다. 경로별로 나누면 각 그림이 원본 크기로 렌더링된다.

사용법:

    python tools/gen_arch.py            # docs/40_architecture.sdoc 갱신
    python tools/gen_arch.py --check    # 갱신 필요 여부만 확인 (CI용, 종료코드 1)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Windows 콘솔 기본 인코딩(cp949)에서 한글·em-dash 출력이 크래시하는 것을 막는다.
# CI(Linux)에서는 그대로 UTF-8이다.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ICD_DOC = ROOT / "docs" / "20_icd.sdoc"
ARCH_DOC = ROOT / "docs" / "40_architecture.sdoc"

# 컨테이너를 배치 구역으로 묶는다. PDF의 C4 Container 다이어그램과 동일한 구획이다.
# 여기가 이 스크립트에서 유일하게 사람이 관리하는 정보이다.
ZONES: list[tuple[str, str, list[str]]] = [
    (
        "onboard",
        "Unitree G1 (NX) — Onboard",
        ["G1", "ext-sensor-io", "speaker_node"],
    ),
    (
        "workstation",
        "PC (RTX 4090) — Workstation",
        [
            "stt_node",
            "vlm_node",
            "orchestrator_node",
            "tts_node",
            "gui_bridge_node",
            "gearsonic",
            "nav-planner",
            "Cortex",
        ],
    ),
    (
        "external",
        "External",
        ["Google Cloud STT", "Naver CLOVA TTS", "VLM API", "Display Renderer"],
    ),
]

STATUS_CLASS = {"완료": "done", "진행 중": "wip", "시작 전": "todo"}
STATUS_SEVERITY = {"완료": 0, "진행 중": 1, "시작 전": 2}

SINGLE_LINE_FIELDS = {
    "UID",
    "TITLE",
    "COMM_TYPE",
    "SOURCE",
    "TARGET",
    "TOPIC",
    "MSG_TYPE",
    "QOS",
    "FREQUENCY",
    "STATUS",
}

DASHED_COMM_TYPES = {"HTTPS", "gRPC", "WebSocket"}


@dataclass
class Interface:
    uid: str = ""
    title: str = ""
    comm_type: str = ""
    source: str = ""
    target: str = ""
    topic: str = ""
    msg_type: str = ""
    status: str = ""
    section: str = ""
    parents: list[str] = field(default_factory=list)


def parse_icd(path: Path) -> list[Interface]:
    """[ICD] 노드를 훑어 인터페이스 목록을 만든다.

    각 노드가 속한 [[SECTION]] 제목도 함께 기록한다. 이 제목이 다이어그램을
    쪼개는 단위가 된다. 멀티라인 필드(>>> ... <<<)는 통째로 건너뛴다.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    interfaces: list[Interface] = []
    current: Interface | None = None
    section_stack: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("[[SECTION]]"):
            current = None
            # 바로 뒤따르는 TITLE: 줄이 이 섹션의 제목이다.
            title = ""
            j = i + 1
            while j < len(lines) and lines[j].strip():
                tm = re.match(r"^TITLE: (.+)$", lines[j])
                if tm:
                    title = tm.group(1).strip()
                    break
                j += 1
            section_stack.append(title)
            i += 1
            continue

        if line.startswith("[[/SECTION]]"):
            current = None
            if section_stack:
                section_stack.pop()
            i += 1
            continue

        if line.startswith("[ICD]"):
            current = Interface(section=section_stack[-1] if section_stack else "기타")
            interfaces.append(current)
            i += 1
            continue

        if line.startswith("[") and not line.startswith("[ICD]"):
            current = None

        if current is None:
            i += 1
            continue

        if re.match(r"^[A-Z_]+: >>>$", line):
            i += 1
            while i < len(lines) and lines[i].strip() != "<<<":
                i += 1
            i += 1
            continue

        if line.startswith("RELATIONS:"):
            i += 1
            while i < len(lines) and lines[i].startswith(
                ("- TYPE:", "  VALUE:", "  ROLE:")
            ):
                vm = re.match(r"^  VALUE: (.+)$", lines[i])
                if vm:
                    current.parents.append(vm.group(1).strip())
                i += 1
            continue

        m = re.match(r"^([A-Z_]+): (.*)$", line)
        if m and m.group(1) in SINGLE_LINE_FIELDS:
            setattr(current, m.group(1).lower(), m.group(2).strip())

        i += 1

    return interfaces


def node_id(container: str) -> str:
    return "n_" + re.sub(r"[^0-9A-Za-z]+", "_", container).strip("_")


def esc(text: str) -> str:
    """Mermaid 라벨에서 문제를 일으키는 문자를 정리한다.

    - ``|`` 는 엣지 라벨 구분자이므로 가운뎃점으로 바꾼다.
    - ``<`` / ``>`` 는 mermaid가 HTML 태그로 해석해 내용이 사라지므로 엔티티로 바꾼다.
    """
    return (
        text.replace('"', "'")
        .replace("|", "·")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", " ")
    )


def build_mermaid(interfaces: list[Interface]) -> str:
    """주어진 인터페이스 집합에 대한 mermaid flowchart 소스를 만든다."""
    used: set[str] = set()
    for itf in interfaces:
        used.add(itf.source)
        used.add(itf.target)

    placed: set[str] = set()
    # 문서 칼럼은 좁고 세로로 길다. TB(세로) 배치가 폭을 덜 먹는다.
    # subgraph 안에는 direction을 지정하지 않는다 (바깥 방향과 충돌해 간선이 엉킨다).
    out: list[str] = ["flowchart TB"]

    for zone_id, zone_label, members in ZONES:
        present = [c for c in members if c in used]
        if not present:
            continue
        out.append(f'  subgraph {zone_id}["{esc(zone_label)}"]')
        for container in present:
            out.append(f'    {node_id(container)}["{esc(container)}"]')
            placed.add(container)
        out.append("  end")

    # ZONES에 등록되지 않은 컨테이너는 누락이므로 눈에 띄게 표시한다.
    for container in sorted(used - placed):
        out.append(f'  {node_id(container)}["{esc(container)} (구역 미지정)"]')

    out.append("")

    for itf in interfaces:
        # 라벨은 UID만 쓴다. 토픽 문자열을 라벨에 넣으면 그래프 폭이 크게 늘어난다.
        arrow = "-.->" if itf.comm_type in DASHED_COMM_TYPES else "-->"
        out.append(
            f'  {node_id(itf.source)} {arrow}|"{esc(itf.uid)}"| {node_id(itf.target)}'
        )

    out.append("")
    out.append("  classDef done fill:#d5efdc,stroke:#3d8f5f,color:#123;")
    out.append("  classDef wip fill:#fdf0d0,stroke:#c99a2e,color:#123;")
    out.append("  classDef todo fill:#f2d5d5,stroke:#b45c5c,color:#123;")

    # 컨테이너 색상은 그 컨테이너가 관여하는 인터페이스 중 가장 뒤처진 상태를 따른다.
    worst: dict[str, str] = {}
    for itf in interfaces:
        for container in (itf.source, itf.target):
            prev = worst.get(container)
            if prev is None or STATUS_SEVERITY.get(itf.status, 0) > STATUS_SEVERITY.get(
                prev, 0
            ):
                worst[container] = itf.status

    by_class: dict[str, list[str]] = {}
    for container, status in worst.items():
        cls = STATUS_CLASS.get(status)
        if cls:
            by_class.setdefault(cls, []).append(node_id(container))
    for cls, ids in sorted(by_class.items()):
        out.append(f"  class {','.join(sorted(ids))} {cls};")

    return "\n".join(out)


def mermaid_block(interfaces: list[Interface]) -> str:
    """mermaid 소스를 RST raw html 블록으로 감싼다.

    StrictDoc은 RST를 쓰므로 ```mermaid 펜스가 아니라 raw html + <pre class="mermaid">
    경로를 써야 한다. (Markdown 문서라면 펜스를 그대로 쓸 수 있다.)

    폭이 넘칠 때를 대비해 가로 스크롤 래퍼를 두되 min-width는 주지 않는다.
    min-width를 주면 mermaid가 칼럼 폭에 맞춰 축소하지 못하고 그림이 잘린다.
    """
    src = build_mermaid(interfaces)
    indented = "\n".join(("      " + ln) if ln else "" for ln in src.splitlines())
    return (
        ".. raw:: html\n"
        "\n"
        '   <div style="overflow-x:auto; max-width:100%;">\n'
        '   <pre class="mermaid">\n'
        f"{indented}\n"
        "   </pre>\n"
        "   </div>\n"
    )


def detail_table(interfaces: list[Interface]) -> str:
    rows: list[str] = []
    for itf in interfaces:
        endpoint = itf.topic or itf.msg_type or "—"
        rows.append(f"   * - {itf.uid}")
        rows.append(f"     - {itf.source}")
        rows.append(f"     - {itf.target}")
        rows.append(f"     - ``{endpoint}``")
        rows.append(f"     - {itf.status}")
    body = "\n".join(rows)
    return (
        ".. list-table::\n"
        "   :widths: 10 20 20 34 16\n"
        "   :header-rows: 1\n"
        "\n"
        "   * - ID\n"
        "     - 송신\n"
        "     - 수신\n"
        "     - 토픽 / 엔드포인트\n"
        "     - 상태\n"
        f"{body}\n"
    )


def group_by_section(interfaces: list[Interface]) -> list[tuple[str, list[Interface]]]:
    """ICD 문서에 나타난 순서를 유지하며 섹션별로 묶는다."""
    order: list[str] = []
    buckets: dict[str, list[Interface]] = {}
    for itf in interfaces:
        if itf.section not in buckets:
            buckets[itf.section] = []
            order.append(itf.section)
        buckets[itf.section].append(itf)
    return [(name, buckets[name]) for name in order]


def render_document(interfaces: list[Interface]) -> str:
    counts = {"완료": 0, "진행 중": 0, "시작 전": 0}
    for itf in interfaces:
        if itf.status in counts:
            counts[itf.status] += 1

    parts: list[str] = [
        f"""[DOCUMENT]
TITLE: KIST DRL G1 아키텍처
UID: DOC-ARCH
VERSION: 0.1
DATE: 2026-09-05
CLASSIFICATION: Internal
OPTIONS:
  MARKUP: RST
  AUTO_LEVELS: On

[TEXT]
STATEMENT: >>>
.. warning::

   본 문서는 ``tools/gen_arch.py`` 가 ``docs/20_icd.sdoc`` 에서 **자동 생성** 한다.
   직접 편집하지 말 것. 편집해도 다음 생성 시 덮어써진다.

본 문서는 시스템의 컨테이너 구성과 컨테이너 간 데이터 흐름을 정의한다.
아래 다이어그램은 손으로 그린 것이 아니라 인터페이스 정의서(ICD)에서 생성된다.
각 ``[ICD]`` 노드의 ``송신 컨테이너`` / ``수신 컨테이너`` 가 화살표의 양 끝이고,
``통신 방식`` 이 선 모양, ``상태`` 가 색상이 된다.

.. code-block:: text

   python tools/gen_arch.py

ICD를 수정한 뒤 위 명령을 다시 실행하면 다이어그램이 갱신된다.
CI에서 ``python tools/gen_arch.py --check`` 를 돌리면
"ICD는 바뀌었는데 다이어그램은 안 바뀐" 상태를 빌드 실패로 잡을 수 있다.

현재 인터페이스 {len(interfaces)}건 — 완료 {counts["완료"]} · 진행 중 {counts["진행 중"]} · 시작 전 {counts["시작 전"]}.
<<<"""
    ]

    parts.append(
        """[[SECTION]]
TITLE: 읽는 법

[TEXT]
STATEMENT: >>>
다이어그램은 ICD 문서의 섹션(데이터 경로) 단위로 나누어 그린다.
전체를 한 장에 그리면 문서 폭에서 글씨를 읽을 수 없기 때문이다.

**선 모양**

- 실선 — DDS 토픽
- 점선 — DDS 외 통신 (HTTPS · gRPC · WebSocket)

**컨테이너 색상** — 그 컨테이너가 관여하는 인터페이스 중 가장 뒤처진 상태를 따른다.

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - 색
     - 의미
   * - 초록
     - 관여 인터페이스가 모두 ``완료``
   * - 노랑
     - ``진행 중`` 인터페이스 포함
   * - 빨강
     - ``시작 전`` 인터페이스 포함 — 아직 배선되지 않은 경로가 있다

즉 어디까지 실제로 연결되었는지가 그림에 그대로 드러난다.
정적 이미지로 그린 도면은 이 정보를 담을 수 없고, 담더라도 곧 실제와 어긋난다.

화살표 라벨은 ICD 번호이며, 토픽 상세는 각 그림 아래 표에 있다.
<<<

[[/SECTION]]"""
    )

    for section_name, group in group_by_section(interfaces):
        parts.append(
            f"""[[SECTION]]
TITLE: {section_name}

[TEXT]
STATEMENT: >>>
{mermaid_block(group)}
{detail_table(group)}
<<<

[[/SECTION]]"""
        )

    return "\n\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="갱신이 필요하면 종료코드 1을 반환한다 (파일은 쓰지 않는다).",
    )
    args = parser.parse_args()

    interfaces = parse_icd(ICD_DOC)
    if not interfaces:
        print(f"error: {ICD_DOC} 에서 [ICD] 노드를 찾지 못했습니다.", file=sys.stderr)
        return 2

    rendered = render_document(interfaces)
    existing = ARCH_DOC.read_text(encoding="utf-8") if ARCH_DOC.exists() else None
    sections = len(group_by_section(interfaces))

    if args.check:
        if existing != rendered:
            print(
                f"error: {ARCH_DOC.name} 이(가) ICD와 어긋납니다. "
                "`python tools/gen_arch.py` 를 실행하세요.",
                file=sys.stderr,
            )
            return 1
        print(
            f"ok: {ARCH_DOC.name} 은(는) ICD와 일치합니다 (인터페이스 {len(interfaces)}건)."
        )
        return 0

    ARCH_DOC.write_text(rendered, encoding="utf-8", newline="\n")
    print(
        f"generated: {ARCH_DOC.relative_to(ROOT)} "
        f"(인터페이스 {len(interfaces)}건 / 다이어그램 {sections}장)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
