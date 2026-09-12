#!/usr/bin/env python3
"""draw.io SVG의 adaptive(dark) 색상 규칙을 제거해 항상 라이트로 렌더링되게 한다.

draw.io 웹 앱의 SVG export는 <svg style="color-scheme: light dark"> 와
CSS light-dark(밝은값, 어두운값) 를 박아 넣어, 다크 테마 브라우저에서 도면이
반전되어 보인다. 밝은값만 남긴다.

    python tools/pin_svg_light.py in.svg [out.svg]      # out 생략 시 제자리
"""
import io
import re
import sys
from pathlib import Path


def pin_light(svg: str) -> tuple[str, dict]:
    stats = {}
    # 웹 export: "color-scheme: light dark;" / 데스크톱(CLI) export: 세미콜론·공백이 다르거나
    # 속성(color-scheme="light dark")으로 나온다. 모든 형태를 지운다.
    svg, n_style = re.subn(r"color-scheme\s*:\s*light\s+dark\s*;?", "", svg)
    svg, n_attr = re.subn(r'\s+color-scheme="[^"]*"', "", svg)
    stats["color-scheme"] = n_style + n_attr

    def first_arg(m: re.Match) -> str:
        inner, depth, first = m.group(1), 0, ""
        for ch in inner:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                break
            first += ch
        return first.strip()

    svg, stats["light-dark()"] = re.subn(
        r"light-dark\(((?:[^()]|\([^()]*\))*)\)", first_arg, svg
    )
    stats["adaptive-bg"] = svg.count("var(--ge-adaptive-bg, #ffffff)")
    svg = svg.replace("var(--ge-adaptive-bg, #ffffff)", "#ffffff")
    svg, stats["var(--ge-)"] = re.subn(r"var\(--ge-[a-z-]+,\s*([^)]+)\)", r"\1", svg)
    svg = re.sub(
        r"@supports \(color: light-dark\(#000, #fff\)\) \{[^{}]*\{[^{}]*\}\s*\}", "", svg
    )
    svg = re.sub(r'<style type="text/css">\s*</style>', "", svg)
    return svg, stats


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src
    svg = io.open(src, encoding="utf-8").read()
    out, stats = pin_light(svg)
    dst.parent.mkdir(parents=True, exist_ok=True)
    io.open(dst, "w", encoding="utf-8", newline="\n").write(out)
    left = [w for w in ("light-dark(", "var(--ge-", "color-scheme") if w in out]
    print(f"{src} -> {dst}: {stats}; remaining dark refs: {left or 'none'}")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
