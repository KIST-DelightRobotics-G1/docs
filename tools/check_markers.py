#!/usr/bin/env python3
"""소스코드의 @relation 마커가 실제 요구사항 UID를 가리키는지 검증한다.

멀티레포 환경을 위한 도구다. 요구사항은 이 레포(요구사항 레포)에 있고,
``@relation`` 마커는 각 개발 레포의 코드 안에 흩어져 있다. 개발자가 자기 레포에서
마커를 달 때 오타를 내거나 삭제된 요구사항을 가리켜도, 그 레포의 CI만으로는
알 수 없다. 이 스크립트가 그 간극을 메운다.

두 가지 방식으로 쓴다.

**1) 요구사항 레포에서 — 유효한 UID 목록을 배포한다**

    python tools/check_markers.py --export-uids uids.txt

    생성된 uids.txt를 CI 아티팩트나 릴리스로 올려두면 개발 레포가 받아 쓴다.

**2) 개발 레포에서 — 자기 코드의 마커를 검증한다**

    python check_markers.py --uids uids.txt --scan src/ include/

    알 수 없는 UID를 가리키는 마커가 있으면 종료코드 1.

요구사항 레포 안에서 직접 검증할 수도 있다 (uids 없이 docs를 바로 읽는다).

    python tools/check_markers.py --scan src/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Windows 콘솔 기본 인코딩(cp949)에서 한글·em-dash 출력이 크래시하는 것을 막는다.
# CI(Linux)에서는 그대로 UTF-8이다.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"

# 마커 전체를 잡은 뒤, scope=/role= 앞의 UID 목록만 떼어낸다.
# StrictDoc이 허용하는 UID 문자 집합을 그대로 따른다.
MARKER_RE = re.compile(r"@relation\(([^)]*)\)")
UID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_/.\\-]+$")

# .sdoc 안에서 노드의 UID를 선언하는 줄.
SDOC_UID_RE = re.compile(r"^UID: (.+)$")

# 텍스트로 훑을 소스 확장자. 그 외(바이너리 등)는 건너뛴다.
SOURCE_SUFFIXES = {
    ".py", ".c", ".h", ".cc", ".cpp", ".hpp", ".hh", ".cxx",
    ".rs", ".go", ".java", ".ts", ".tsx", ".js", ".jsx",
    ".sh", ".bash", ".cmake", ".yaml", ".yml", ".toml",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "build", "dist",
    "output", ".venv", "venv", ".mypy_cache", ".pytest_cache",
}


def collect_document_uids(docs_dir: Path) -> set[str]:
    """docs/*.sdoc 에 선언된 모든 노드 UID를 모은다."""
    uids: set[str] = set()
    for path in sorted(docs_dir.rglob("*.sdoc")):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = SDOC_UID_RE.match(line)
            if m:
                uids.add(m.group(1).strip())
    return uids


def load_uids(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def iter_source_files(paths: list[Path]):
    for base in paths:
        if base.is_file():
            yield base
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in SOURCE_SUFFIXES:
                yield path


def extract_markers(path: Path) -> list[tuple[int, str]]:
    """(줄번호, UID) 목록을 뽑는다."""
    found: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return found

    for lineno, line in enumerate(text.splitlines(), start=1):
        for body in MARKER_RE.findall(line):
            for token in body.split(","):
                token = token.strip()
                if not token or token.startswith(("scope=", "role=")):
                    continue
                if UID_RE.match(token):
                    found.append((lineno, token))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description="@relation 마커의 UID가 실제 요구사항을 가리키는지 검증한다."
    )
    parser.add_argument(
        "--export-uids",
        metavar="FILE",
        help="docs/ 의 모든 노드 UID를 FILE로 내보내고 종료한다.",
    )
    parser.add_argument(
        "--uids",
        metavar="FILE",
        help="유효한 UID 목록 파일. 생략하면 docs/ 를 직접 읽는다.",
    )
    parser.add_argument(
        "--docs",
        metavar="DIR",
        default=str(DOCS_DIR),
        help="요구사항 문서 디렉터리 (기본: 이 레포의 docs/).",
    )
    parser.add_argument(
        "--scan",
        metavar="PATH",
        nargs="*",
        default=[],
        help="마커를 찾을 소스 경로들.",
    )
    args = parser.parse_args()

    if args.export_uids:
        uids = collect_document_uids(Path(args.docs))
        out = Path(args.export_uids)
        out.write_text(
            "\n".join(sorted(uids)) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"exported {len(uids)} UIDs -> {out}")
        return 0

    if not args.scan:
        parser.error("--scan 경로를 하나 이상 지정하거나 --export-uids 를 쓰세요.")

    known = load_uids(Path(args.uids)) if args.uids else collect_document_uids(
        Path(args.docs)
    )
    if not known:
        print("error: 유효한 UID를 하나도 찾지 못했습니다.", file=sys.stderr)
        return 2

    scan_paths = [Path(p) for p in args.scan]
    missing_paths = [p for p in scan_paths if not p.exists()]
    scan_paths = [p for p in scan_paths if p.exists()]
    for p in missing_paths:
        # 멀티레포에서는 일부 레포만 체크아웃된 상태가 정상이다. 경고만 남긴다.
        print(f"warning: 경로 없음, 건너뜀: {p}")

    unknown: list[tuple[Path, int, str]] = []
    referenced: set[str] = set()
    marker_count = 0

    for path in iter_source_files(scan_paths):
        for lineno, uid in extract_markers(path):
            marker_count += 1
            referenced.add(uid)
            if uid not in known:
                unknown.append((path, lineno, uid))

    if unknown:
        print(
            f"error: 알 수 없는 요구사항 UID를 가리키는 마커 {len(unknown)}건:",
            file=sys.stderr,
        )
        for path, lineno, uid in unknown:
            print(f"  {path}:{lineno}: {uid}", file=sys.stderr)
        print(
            "\n요구사항이 삭제·개명되었거나 마커에 오타가 있습니다.",
            file=sys.stderr,
        )
        return 1

    covered = len(referenced)
    print(
        f"ok: 마커 {marker_count}건 / 참조 요구사항 {covered}건 — 모두 유효 "
        f"(알려진 UID {len(known)}건)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
