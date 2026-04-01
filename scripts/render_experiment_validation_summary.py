from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any



def load_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))



def _track_line(track: dict[str, Any]) -> str:
    parts = [f"`{track.get('track_id', 'unknown')}`"]
    if track.get("profile_name"):
        parts.append(str(track["profile_name"]))
    if track.get("pool_size") is not None:
        parts.append(f"pool_size={track['pool_size']}")
    if track.get("release_index_path"):
        parts.append(f"index={track['release_index_path']}")
    return "- " + " · ".join(parts)



def build_summary_markdown(payload: dict[str, Any], shadow_summary: dict[str, Any] | None) -> str:
    lines = [
        "## Monthly Experiment Validation",
        "",
        f"- Issue: #{payload['issue_number']} {payload['issue_title']}",
        f"- Experiment-only tasks: `{payload['experiment_task_count']}`",
        f"- Validation executed: `{'yes' if payload['should_run'] else 'no'}`",
    ]
    if payload.get("skip_reason"):
        lines.append(f"- Skip reason: {payload['skip_reason']}")

    actions = payload.get("experiment_actions", [])
    if actions:
        lines.extend(["", "### Selected Tasks"])
        for action in actions:
            flags = f" [{', '.join(action['flags'])}]" if action.get("flags") else ""
            lines.extend(
                [
                    f"- `{action['risk_level']}` {action['title']}{flags}",
                    f"  - Summary: {action.get('summary', 'No summary provided.')}",
                ]
            )

    if shadow_summary is not None:
        official = shadow_summary.get("official_baseline", {})
        shadow_tracks = shadow_summary.get("shadow_candidate_tracks", {}).get("tracks", [])
        lines.extend(
            [
                "",
                "### Validation Results",
                f"- As of date: `{shadow_summary.get('as_of_date', 'unknown')}`",
                f"- Official baseline version: `{official.get('version', 'unknown')}`",
                f"- Official baseline mode: `{official.get('mode', 'unknown')}`",
                f"- Official baseline pool size: `{official.get('pool_size', 'unknown')}`",
                f"- Shadow candidate tracks generated: `{len(shadow_tracks)}`",
            ]
        )
        if official.get("publish_manifest_path"):
            lines.append(f"- Publish manifest path: `{official['publish_manifest_path']}`")
        if shadow_tracks:
            lines.extend(["", "### Shadow Tracks"])
            lines.extend(_track_line(track) for track in shadow_tracks)
    elif payload.get("should_run"):
        lines.extend(["", "### Validation Results", "- No shadow-build summary artifact was found."])

    return "\n".join(lines).strip() + "\n"



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render experiment validation markdown for the monthly optimization task issue.")
    parser.add_argument("--payload-file", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    parser.add_argument("--shadow-summary-file", type=Path)
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    payload = json.loads(args.payload_file.read_text(encoding="utf-8"))
    shadow_summary = load_optional_json(args.shadow_summary_file)
    args.output_file.write_text(build_summary_markdown(payload, shadow_summary), encoding="utf-8")
    print(f"summary_file={args.output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
