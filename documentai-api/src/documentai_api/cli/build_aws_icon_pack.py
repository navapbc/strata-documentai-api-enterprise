"""Build an iconify-format JSON icon pack from the AWS Architecture Icons zip.

Download the zip from https://aws.amazon.com/architecture/icons/

Usage:
    build-aws-icon-pack <aws-icons.zip> <output.json>
"""

import json
import re
import zipfile
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer()

ICONS = {
    "arch-amazon-api-gateway": "Arch_Amazon-API-Gateway_64.svg",
    "arch-amazon-bedrock": "Arch_Amazon-Bedrock_64.svg",
    "arch-amazon-cloudfront": "Arch_Amazon-CloudFront_64.svg",
    "arch-amazon-cognito": "Arch_Amazon-Cognito_64.svg",
    "arch-amazon-dynamodb": "Arch_Amazon-DynamoDB_64.svg",
    "arch-amazon-eventbridge": "Arch_Amazon-EventBridge_64.svg",
    "arch-amazon-s3": "Arch_Amazon-Simple-Storage-Service_64.svg",
    "arch-amazon-sqs": "Arch_Amazon-Simple-Queue-Service_64.svg",
    "arch-amazon-textract": "Arch_Amazon-Textract_64.svg",
    "arch-aws-glue": "Arch_AWS-Glue_64.svg",
    "arch-aws-lambda": "Arch_AWS-Lambda_64.svg",
}

_SVG_OPEN = re.compile(r"<svg[^>]*>", re.DOTALL)
_SVG_CLOSE = re.compile(r"</svg>")
_XML_DECL = re.compile(r"<\?xml[^?]*\?>")
_TITLE = re.compile(r"<title>[^<]*</title>")


def _extract_body(svg_text: str) -> str:
    body = _XML_DECL.sub("", svg_text)
    body = _SVG_OPEN.sub("", body)
    body = _SVG_CLOSE.sub("", body)
    body = _TITLE.sub("", body)
    return body.strip()


@app.command()
def build(
    zip_path: Annotated[Path, typer.Argument(help="Path to the AWS Architecture Icons zip.")],
    output: Annotated[Path, typer.Argument(help="Output icons.json path.")],
) -> None:
    """Build an iconify JSON icon pack from the AWS Architecture Icons zip."""
    icons: dict[str, dict[str, object]] = {}
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for icon_name, filename in ICONS.items():
            matches = [n for n in names if n.endswith(filename) and "__MACOSX" not in n]
            if not matches:
                typer.echo(f"WARNING: {filename} not found in zip", err=True)
                continue
            svg_text = zf.read(matches[0]).decode("utf-8")
            icons[icon_name] = {"body": _extract_body(svg_text), "width": 80, "height": 80}
            typer.echo(f"  {icon_name} <- {matches[0]}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"prefix": "aws", "icons": icons}, indent=2))
    typer.echo(f"\nWrote {len(icons)} icons to {output}")


if __name__ == "__main__":
    app()
