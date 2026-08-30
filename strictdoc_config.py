"""StrictDoc 프로젝트 설정 — KIST DRL G1 데모.

StrictDoc 0.28+ 부터 strictdoc.toml 대신 이 Python 설정 파일이 표준이다.

빌드 프로파일이 두 개다. 환경변수 ``SDOC_PROFILE`` 로 고른다.

    internal (기본)  — 소스 추적성 포함. 사내/비공개 배포용.
    public           — 소스 추적성 제외. 공개 사이트용.

**왜 나누는가.** ``REQUIREMENT_TO_SOURCE_TRACEABILITY`` 를 켜면 StrictDoc이
스캔한 모든 소스 파일을 ``output/html/_source_files/**.html`` 로 **전문 그대로**
렌더링한다. 요구사항 레포를 공개하면서 이 기능을 켜두면, ``_src/`` 로 받아온
비공개 개발 레포의 소스 코드가 통째로 공개 사이트에 실린다.

요구사항·인터페이스를 공개하는 것과 구현 소스를 공개하는 것은 별개의 결정이므로
프로파일로 분리한다. 소스도 공개해도 되는 상황이면 그냥 internal 프로파일로
빌드해서 배포하면 된다.

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
        # 실험 기능 — 데모에서 보여줄 화면들
        "SEARCH",
        "TRACEABILITY_MATRIX_SCREEN",
        "PROJECT_STATISTICS_SCREEN",
    ]

    # @relation 마커를 스캔할 소스 경로.
    #   /src/**   — 이 레포 안의 데모 스텁
    #   /_src/**  — tools/fetch_sources.py 가 받아온 개발 레포들 (멀티레포)
    # 존재하지 않는 경로는 무시된다. 일부 레포만 체크아웃해도 빌드는 성공하고,
    # 빠진 레포는 커버리지에서만 제외된다.
    source_paths = ["/src/**", "/_src/**"]

    if IS_PUBLIC:
        # 소스 전문이 사이트에 실리지 않도록 추적성 기능과 스캔 경로를 모두 끈다.
        # 둘 중 하나만 꺼도 되지만, 실수로 되살아나는 것을 막기 위해 함께 끈다.
        source_paths = []
    else:
        features.append("REQUIREMENT_TO_SOURCE_TRACEABILITY")

    return ProjectConfig(
        project_title="KIST DRL G1 — 요구사항 · 인터페이스 (StrictDoc 데모)",
        project_features=features,
        # 요구사항/인터페이스 문서는 docs/ 아래에만 존재한다.
        include_doc_paths=[
            "/docs/**",
        ],
        include_source_paths=source_paths,
    )
