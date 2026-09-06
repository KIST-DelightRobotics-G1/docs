"""StrictDoc 프로젝트 설정 — KIST DRL G1 시스템 문서.

StrictDoc 0.28+ 부터 strictdoc.toml 대신 이 Python 설정 파일이 표준이다.

빌드 프로파일이 두 개다. 환경변수 ``SDOC_PROFILE`` 로 고른다.

    internal (기본)  — 소스 추적성 포함. ``tools/fetch_sources.py`` 로 ``_src/`` 를
                       채운 뒤 빌드하면 Source coverage 화면이 생긴다.
    public           — 소스 추적성 제외. 스캔한 소스 파일이 사이트에 전문 렌더링되는
                       것을 막는다. 개발 레포가 비공개일 때 쓴다.

    SDOC_PROFILE=public strictdoc export . --output-dir output
"""

import os

from strictdoc.core.project_config import ProjectConfig

PROFILE = os.environ.get("SDOC_PROFILE", "internal").strip().lower()
IS_PUBLIC = PROFILE == "public"


def create_config() -> ProjectConfig:
    features = [
        # 안정 기능
        "TABLE_SCREEN",
        "TRACEABILITY_SCREEN",
        "DEEP_TRACEABILITY_SCREEN",
        # 실험 기능
        "SEARCH",
        "TRACEABILITY_MATRIX_SCREEN",
        "PROJECT_STATISTICS_SCREEN",
        # 릴리스 간 변경 리포트: strictdoc export . --generate-diff-git "v0.1..v0.2"
        "DIFF",
        # PDF 납품본: strictdoc export . --formats=html2pdf (Chrome/Chromium 필요)
        "HTML2PDF",
    ]

    # File 관계가 가리키는 소스 경로. tools/fetch_sources.py 가 개발 레포들을
    # _src/<repo>/ 로 체크아웃한다. 존재하지 않는 경로는 무시되므로 일부 레포만
    # 체크아웃해도 빌드는 성공하고, 빠진 레포는 커버리지에서만 제외된다.
    source_paths = ["/_src/**"]

    if IS_PUBLIC:
        source_paths = []
    else:
        features.append("REQUIREMENT_TO_SOURCE_TRACEABILITY")

    return ProjectConfig(
        project_title="KIST DRL G1 — 시스템 문서",
        project_features=features,
        include_doc_paths=[
            "/docs/**",
        ],
        include_source_paths=source_paths,
    )
