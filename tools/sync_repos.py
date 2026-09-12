#!/usr/bin/env python3
"""org 전 레포의 main 변경을 지난 동기화 이후 기준으로 수집해 리포트를 만든다.

GitHub API(gh CLI)만 쓰므로 클론이 필요 없다. 레포별 마지막 동기화 SHA는
``tools/sync_state.json`` 에 있고, 리포트에는 커밋 목록과 함께 문서/도면에
영향을 줄 만한 **신호**를 뽑아 준다.

    신호
    - 새/삭제/이동 파일 (src·include·msg·idl·scenarios)
    - 추가된 줄에 나타난 DDS/ROS 토픽 문자열 (rt/…, /cortex/…, /bridge/…)
    - publisher / subscriber 생성 코드
    - docs 레포 ICD/SYS-REQ 의 File 관계가 가리키는 파일의 삭제·이동 (추적성 파손)
    - README / docs 도식(svg) 변경

사용법:

    python tools/sync_repos.py --report sync_report.md          # 리포트만
    python tools/sync_repos.py --report sync_report.md --update-state   # 상태 파일도 갱신
    python tools/sync_repos.py --init                           # 최초: 현재 main SHA를 상태로 기록

상태 갱신은 문서 반영 PR 에서만 한다 (리포트 = "이 SHA 이후의 변경").
"""
from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "tools" / "sync_state.json"
ORG = "KIST-DelightRobotics-G1"

# 문서·도면 범위 밖 (학습/데이터/문서 레포) — 리포트엔 싣되 "범위 밖" 표시
OUT_OF_SCOPE = {"docs", ".github", "data-collector", "vision-training"}

TOPIC_RE = re.compile(r"(?<![\w/])(rt/[A-Za-z0-9_/{}<>.,-]+|/(?:cortex|bridge|onboard)/[A-Za-z0-9_/]+)")
PUBSUB_RE = re.compile(
    r"ChannelPublisher|ChannelSubscriber|create_publisher|create_subscription|"
    r"DataWriter|DataReader|Publisher<|Subscriber<|rclpy\.|\.publish\(|subscribe"
)
CODE_DIRS = ("src/", "include/", "msg/", "idl/", "config/", "scripts/")
SKIP_FILE_RE = re.compile(r"(^|/)(test|tests|docker|thirdparty)/|\.(md|txt|lock)$")


def gh(*args: str):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


def gh_json(*args: str):
    return json.loads(gh(*args))


def list_repos() -> list[str]:
    names = gh("api", f"orgs/{ORG}/repos", "--paginate", "--jq", ".[].name").split()
    return sorted(n for n in names if n != ".github")


def head_sha(repo: str) -> str:
    return gh("api", f"repos/{ORG}/{repo}/commits/main", "--jq", ".sha").strip()


def compare(repo: str, base: str, head: str) -> dict:
    return gh_json("api", f"repos/{ORG}/{repo}/compare/{base}...{head}")


def file_relations() -> dict[str, list[str]]:
    """docs 의 File 관계 → {repo: [경로(레포 기준)]}"""
    rel: dict[str, list[str]] = {}
    for sdoc in (ROOT / "docs").glob("*.sdoc"):
        text = io.open(sdoc, encoding="utf-8").read()
        for m in re.finditer(r"- TYPE: File\n  VALUE: _src/([^/\n]+)/([^\n]+)", text):
            rel.setdefault(m.group(1), []).append(m.group(2).strip())
    return rel


def analyse(repo: str, cmp: dict, rels: dict[str, list[str]]) -> dict:
    commits = [
        {"sha": c["sha"][:7], "msg": c["commit"]["message"].splitlines()[0]}
        for c in cmp.get("commits", [])
        if not c["commit"]["message"].startswith("Merge ")
    ]
    added, removed, renamed, modified = [], [], [], []
    topics: dict[str, set[str]] = {}
    pubsub: list[str] = []
    docs_changed: list[str] = []
    for f in cmp.get("files", []):
        name, status = f["filename"], f["status"]
        if name.endswith((".svg", ".drawio")) or name.lower().startswith("readme"):
            docs_changed.append(f"{status}: {name}")
        if SKIP_FILE_RE.search(name) or not name.startswith(CODE_DIRS):
            continue
        if status == "added":
            added.append(name)
        elif status == "removed":
            removed.append(name)
        elif status == "renamed":
            renamed.append(f"{f.get('previous_filename')} -> {name}")
        else:
            modified.append(name)
        patch = f.get("patch") or ""
        for line in patch.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            for t in TOPIC_RE.findall(line):
                topics.setdefault(t, set()).add(name)
            if PUBSUB_RE.search(line) and ("publish" in line.lower() or "subscri" in line.lower() or "Writer" in line or "Reader" in line):
                pubsub.append(f"{name}: {line.strip()[:110]}")
    # File 관계 파손
    gone = set(removed) | {r.split(" -> ")[0] for r in renamed}
    broken = [p for p in rels.get(repo, []) if p in gone]
    return {
        "commits": commits,
        "added": added, "removed": removed, "renamed": renamed, "modified": modified,
        "topics": {t: sorted(v) for t, v in topics.items()},
        "pubsub": pubsub[:20],
        "docs_changed": docs_changed,
        "broken_file_relations": broken,
        "stat": f"{len(cmp.get('files', []))} files, +{cmp.get('ahead_by', 0)} commits",
    }


def render(results: dict[str, dict], state: dict, heads: dict) -> str:
    today = date.today().isoformat()
    week = date.today().isocalendar()
    out = [f"# Weekly sync {today} (W{week[1]:02d})", ""]
    changed = {r: v for r, v in results.items() if v is not None}
    if not changed:
        out.append("모든 레포의 main 에 변경이 없습니다.")
        return "\n".join(out)
    out.append("| repo | base → head | 커밋 | 범위 |")
    out.append("|---|---|---|---|")
    for repo, v in changed.items():
        scope = "범위 밖" if repo in OUT_OF_SCOPE else "**대상**"
        out.append(f"| {repo} | `{state.get(repo, '')[:7]}` → `{heads[repo][:7]}` | {len(v['commits'])} | {scope} |")
    out.append("")
    for repo, v in changed.items():
        out.append(f"## {repo}  ({v['stat']})")
        if repo in OUT_OF_SCOPE:
            out.append("_문서·도면 범위 밖 (학습/데이터/문서 레포)_")
        out.append("")
        out.append("**커밋**")
        for c in v["commits"][:30]:
            out.append(f"- `{c['sha']}` {c['msg']}")
        if v["broken_file_relations"]:
            out.append("")
            out.append("**⚠️ File 관계 파손 (docs 갱신 필수)**")
            for p in v["broken_file_relations"]:
                out.append(f"- `_src/{repo}/{p}`")
        if v["topics"]:
            out.append("")
            out.append("**새로 등장한 토픽 문자열 (추가된 줄 기준)**")
            for t, files in sorted(v["topics"].items()):
                out.append(f"- `{t}` — {', '.join(files[:3])}")
        if v["pubsub"]:
            out.append("")
            out.append("**publisher / subscriber 코드**")
            for line in v["pubsub"][:12]:
                out.append(f"- `{line}`")
        if v["added"] or v["removed"] or v["renamed"]:
            out.append("")
            out.append("**파일**")
            for p in v["added"][:25]:
                out.append(f"- ➕ {p}")
            for p in v["removed"][:25]:
                out.append(f"- ➖ {p}")
            for p in v["renamed"][:25]:
                out.append(f"- ↪ {p}")
        if v["docs_changed"]:
            out.append("")
            out.append("**README / 도식 변경**")
            for p in v["docs_changed"][:10]:
                out.append(f"- {p}")
        out.append("")
    out.append("---")
    out.append("반영 절차: `/g1-sync` 스킬 (ICD · File 관계 · 도면 · TEST_CASE 판단 → PR). 반영 PR 에서 `tools/sync_state.json` 을 갱신한다.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", help="markdown 리포트 출력 경로")
    ap.add_argument("--json", help="원시 결과 JSON 출력 경로")
    ap.add_argument("--update-state", action="store_true", help="상태 파일을 현재 head 로 갱신")
    ap.add_argument("--init", action="store_true", help="최초 상태 기록 (변경 비교 없음)")
    args = ap.parse_args()

    state = json.loads(io.open(STATE, encoding="utf-8").read()) if STATE.exists() else {}
    repos = list_repos()
    heads = {r: head_sha(r) for r in repos}

    if args.init:
        io.open(STATE, "w", encoding="utf-8", newline="\n").write(json.dumps(heads, indent=2, sort_keys=True) + "\n")
        print(f"state initialised for {len(heads)} repos -> {STATE.relative_to(ROOT)}")
        return 0

    rels = file_relations()
    results: dict[str, dict | None] = {}
    for repo in repos:
        base = state.get(repo)
        if base is None:
            print(f"{repo}: no baseline (new repo) -> head {heads[repo][:7]} recorded on --update-state")
            results[repo] = None
            continue
        if base == heads[repo]:
            results[repo] = None
            continue
        print(f"{repo}: {base[:7]} -> {heads[repo][:7]}")
        results[repo] = analyse(repo, compare(repo, base, heads[repo]), rels)

    report = render(results, state, heads)
    if args.report:
        io.open(args.report, "w", encoding="utf-8", newline="\n").write(report + "\n")
        print(f"report -> {args.report}")
    else:
        print(report)
    if args.json:
        io.open(args.json, "w", encoding="utf-8", newline="\n").write(json.dumps({"heads": heads, "results": results}, ensure_ascii=False, indent=2))
    if args.update_state:
        io.open(STATE, "w", encoding="utf-8", newline="\n").write(json.dumps(heads, indent=2, sort_keys=True) + "\n")
        print(f"state updated -> {STATE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
