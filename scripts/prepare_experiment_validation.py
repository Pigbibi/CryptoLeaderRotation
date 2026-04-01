from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.prepare_auto_optimization_pr import parse_actions
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from prepare_auto_optimization_pr import parse_actions


SHADOW_BUILD_MARKERS = (
    "shadow build",
    "challenger",
    "official_baseline",
    "track_summary",
)
WALKFORWARD_MARKERS = (
    "walk-forward",
    "walkforward",
    "leader capture",
    "backtest",
    "validation window",
)


def _combined_text(action: dict[str, object]) -> str:
    return f"{action.get('title', '')} {action.get('summary', '')}".lower()


def build_payload(issue_context: dict[str, object]) -> dict[str, object]:
    issue_number = int(issue_context["number"])
    issue_title = str(issue_context["title"]).strip()
    parsed_actions = parse_actions(str(issue_context.get("body", "")))
    experiment_actions = [action for action in parsed_actions if "experiment-only" in action.get("flags", [])]
    run_shadow_build = any(any(marker in _combined_text(action) for marker in SHADOW_BUILD_MARKERS) for action in experiment_actions)
    run_walkforward_validation = any(
        any(marker in _combined_text(action) for marker in WALKFORWARD_MARKERS) for action in experiment_actions
    )

    should_run = bool(experiment_actions) and (run_shadow_build or run_walkforward_validation)
    skip_reason = ""
    if not experiment_actions:
        skip_reason = "No experiment-only tasks were found in this monthly optimization issue."
    elif not should_run:
        skip_reason = "No supported upstream experiment validation target was found in the selected tasks."

    return {
        "issue_number": issue_number,
        "issue_title": issue_title,
        "should_run": should_run,
        "experiment_task_count": len(experiment_actions),
        "run_shadow_build": run_shadow_build,
        "run_walkforward_validation": run_walkforward_validation,
        "experiment_actions": experiment_actions,
        "skip_reason": skip_reason,
    }



def render_task_summary(payload: dict[str, object]) -> str:
    lines = [
        "# Experiment Validation Candidate Tasks",
        "",
        f"- Issue: #{payload['issue_number']} {payload['issue_title']}",
        f"- Experiment-only tasks: `{payload['experiment_task_count']}`",
        f"- Shadow build selected: `{str(payload['run_shadow_build']).lower()}`",
        f"- Walk-forward validation selected: `{str(payload['run_walkforward_validation']).lower()}`",
    ]
    actions = payload["experiment_actions"]
    if not actions:
        lines.extend(["", payload["skip_reason"]])
        return "\n".join(lines).strip() + "\n"

    lines.extend(["", "## Selected Tasks"])
    for action in actions:
        flag_suffix = f" [{', '.join(action['flags'])}]" if action.get("flags") else ""
        lines.extend(
            [
                f"- `{action['risk_level']}` {action['title']}{flag_suffix}",
                f"  - Summary: {action.get('summary', 'No summary provided.')}",
                f"  - Source: {action.get('source_label', 'Unknown source')} ({action.get('source_url', 'n/a')})",
            ]
        )

    if payload["skip_reason"]:
        lines.extend(["", payload["skip_reason"]])
    return "\n".join(lines).strip() + "\n"



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare metadata for experiment-only monthly optimization validation.")
    parser.add_argument("--issue-context-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    issue_context = json.loads(args.issue_context_file.read_text(encoding="utf-8"))
    payload = build_payload(issue_context)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload_file = args.output_dir / "payload.json"
    task_summary_file = args.output_dir / "task_summary.md"
    if payload["skip_reason"]:
        (args.output_dir / "skip_reason.txt").write_text(str(payload["skip_reason"]) + "\n", encoding="utf-8")
    payload_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    task_summary_file.write_text(render_task_summary(payload), encoding="utf-8")
    print(f"should_run={'true' if payload['should_run'] else 'false'}")
    print(f"issue_number={payload['issue_number']}")
    print(f"run_shadow_build={'true' if payload['run_shadow_build'] else 'false'}")
    print(f"run_walkforward_validation={'true' if payload['run_walkforward_validation'] else 'false'}")
    print(f"payload_file={payload_file}")
    print(f"task_summary_file={task_summary_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
