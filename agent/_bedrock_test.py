"""One-off Amazon Bedrock connectivity check.

Verifies your AWS credentials can reach Bedrock and lists a few available
foundation models. Configure via the standard AWS environment variables:

    set AWS_PROFILE=your-profile        # optional; else default resolution
    set AWS_REGION=us-west-2            # optional; defaults to us-west-2
    set AWS_CA_BUNDLE=C:\\path\\to\\ca.pem  # optional; only if behind a TLS proxy

Then run:  python _bedrock_test.py
Writes the result to ./bedrock_test.log (next to this script).
"""

import json
import os
import traceback
from pathlib import Path

REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-west-2"
PROFILE = os.environ.get("AWS_PROFILE") or None
CA_BUNDLE = os.environ.get("AWS_CA_BUNDLE")  # only if your network needs it

LOG = Path(__file__).with_name("bedrock_test.log")
lines: list[str] = []


def log(s: str) -> None:
    lines.append(str(s))


try:
    import boto3

    session = boto3.Session(profile_name=PROFILE) if PROFILE else boto3.Session()
    creds = session.get_credentials()
    log(f"creds_present={bool(creds)} region={session.region_name or REGION}")

    verify = CA_BUNDLE if (CA_BUNDLE and os.path.exists(CA_BUNDLE)) else None
    log(f"ca_bundle={'set' if verify else 'system default'}")

    try:
        ident = session.client("sts", verify=verify).get_caller_identity()
        log(f"caller_ok={bool(ident.get('Arn'))}")
    except Exception as e:  # noqa: BLE001
        log(f"sts_error={e}")

    try:
        br = session.client("bedrock", region_name=REGION, verify=verify)
        models = br.list_foundation_models().get("modelSummaries", [])
        ids = [m["modelId"] for m in models]
        log(f"total_models={len(models)}")
        log("sample_models=" + json.dumps(ids[:15]))
    except Exception as e:  # noqa: BLE001
        log(f"list_models_error={e}")

except Exception:
    log("FATAL:\n" + traceback.format_exc())

LOG.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print(f"\n(wrote {LOG})")
