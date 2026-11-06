"""Optional S3 upload for exported CSVs.

Needs the ``aws`` extra (``pip install -e '.[aws]'`` → boto3). Credentials come from
the standard AWS chain (env vars / shared credentials file / ``--profile`` / instance
role); none are read or stored here.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """``s3://bucket/some/prefix`` → ``("bucket", "some/prefix")`` (prefix may be "")."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"expected s3://bucket[/prefix], got {uri!r}")
    return parsed.netloc, parsed.path.lstrip("/")


def upload_files(
    paths: list[Path],
    bucket: str,
    key_prefix: str = "",
    profile: str | None = None,
    region: str | None = None,
) -> list[str]:
    """Upload each file to ``s3://bucket/<key_prefix>/<filename>``; return the URIs."""
    try:
        import boto3
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "S3 upload needs boto3 — install the aws extra: pip install -e '.[aws]'"
        ) from exc

    session = boto3.Session(profile_name=profile, region_name=region)
    client = session.client("s3")
    prefix = key_prefix.strip("/")
    uris: list[str] = []
    for path in paths:
        path = Path(path)
        key = f"{prefix}/{path.name}" if prefix else path.name
        client.upload_file(str(path), bucket, key)
        uris.append(f"s3://{bucket}/{key}")
    return uris
