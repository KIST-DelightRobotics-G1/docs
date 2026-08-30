#!/usr/bin/env python3
"""개발 레포들을 `_src/` 아래로 얕게 체크아웃한다.

요구사항은 이 레포에 있고 코드는 여러 레포에 흩어져 있다. StrictDoc의
``@relation`` 스캔은 로컬 파일시스템 한 트리를 훑으므로, 빌드 전에 각 레포를
한 디렉터리 아래로 모아야 한다. 레포를 물리적으로 합칠 필요는 없다.

    _src/
    ├── kist-drl-g1-cortex/
    ├── kist-ext-sensor-io/
    └── ...

`_src/` 는 빌드 산출물이므로 .gitignore에 있다. 커밋하지 않는다.

사용법:

    python tools/fetch_sources.py                # repos.json 전체
    python tools/fetch_sources.py --only cortex  # 이름에 'cortex'가 든 것만
    python tools/fetch_sources.py --dry-run      # 실행할 명령만 출력

비공개 레포는 인증이 필요하다. CI에서는 GH_TOKEN 환경변수를 주면
https://x-access-token:$GH_TOKEN@github.com/... 형태로 클론한다.
로컬에서는 이미 설정된 SSH 키나 git credential helper를 그대로 쓴다.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 콘솔 기본 인코딩(cp949)에서 한글 출력이 크래시하는 것을 막는다.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).resolve().parent / "repos.json"


def clone_url(org: str, name: str) -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return f"https://x-access-token:{token}@github.com/{org}/{name}.git"
    if os.environ.get("USE_SSH"):
        return f"git@github.com:{org}/{name}.git"
    return f"https://github.com/{org}/{name}.git"


def redact(url: str) -> str:
    """토큰이 로그에 남지 않도록 가린다."""
    if "x-access-token:" in url:
        head, tail = url.split("x-access-token:", 1)
        _, rest = tail.split("@", 1)
        return f"{head}x-access-token:***@{rest}"
    return url


def run(cmd: list[str], dry_run: bool) -> int:
    printable = " ".join(redact(c) for c in cmd)
    if dry_run:
        print(f"  [dry-run] {printable}")
        return 0
    print(f"  $ {printable}")
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--only", metavar="SUBSTR", help="이름에 SUBSTR이 든 레포만.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="이미 있는 디렉터리를 지우지 않고 건너뛴다.",
    )
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    org = manifest["org"]
    dest_root = ROOT / manifest.get("dest", "_src")
    repos = manifest["repos"]
    if args.only:
        repos = [r for r in repos if args.only in r["name"]]
        if not repos:
            print(f"error: '{args.only}' 와(과) 맞는 레포가 없습니다.", file=sys.stderr)
            return 2

    if not args.dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)

    failed: list[str] = []
    for entry in repos:
        name, ref = entry["name"], entry.get("ref", "main")
        target = dest_root / name
        print(f"{name} @ {ref}")

        if target.exists():
            if args.keep:
                print("  이미 존재 — 건너뜀")
                continue
            if not args.dry_run:
                shutil.rmtree(target)

        cmd = [
            "git", "clone", "--depth", "1", "--branch", ref,
            clone_url(org, name), str(target),
        ]
        if run(cmd, args.dry_run) != 0:
            # 한 레포를 못 받아도 나머지는 계속 받는다. 빠진 레포는 커버리지에서
            # 빠질 뿐 빌드를 깨뜨리지 않는다.
            print(f"  warning: {name} 체크아웃 실패 — 커버리지에서 제외됩니다.")
            failed.append(name)

    print()
    ok = len(repos) - len(failed)
    print(f"체크아웃 완료: {ok}/{len(repos)}")
    if failed:
        print(f"실패: {', '.join(failed)}")
        # 실패해도 종료코드 0. 부분 체크아웃은 정상 상태로 취급한다.
        # 반드시 전부 필요하면 CI에서 이 출력을 검사하도록 바꾼다.
    return 0


if __name__ == "__main__":
    sys.exit(main())
