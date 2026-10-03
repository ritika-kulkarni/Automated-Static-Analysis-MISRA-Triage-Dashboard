"""Click CLI entrypoint for CI / local post-build triage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from misra_triage import __version__
from misra_triage.models.config import load_config
from misra_triage.service import TriageService
from misra_triage.utils.logging import setup_logging

console = Console()


def _collect_reports(reports: tuple[str, ...], report_dir: str | None) -> list[Path]:
    paths: list[Path] = [Path(p) for p in reports]
    if report_dir:
        root = Path(report_dir)
        if not root.is_dir():
            raise click.ClickException(f"Report directory not found: {root}")
        for pattern in ("*.sarif", "*.json", "*.xml"):
            paths.extend(sorted(root.glob(pattern)))
    # Deduplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    if not unique:
        raise click.ClickException("No report files provided. Use --report and/or --report-dir.")
    return unique


@click.group()
@click.version_option(__version__, prog_name="misra-triage")
def main() -> None:
    """Automated Static Analysis & MISRA Triage Dashboard CLI."""


@main.command("triage")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--report", "reports", multiple=True, type=click.Path(path_type=str))
@click.option("--report-dir", type=click.Path(path_type=str), default=None)
@click.option("--no-jira/--jira", default=False, help="Skip Jira ticket creation.")
@click.option("--json-out", is_flag=True, help="Print triage summary as JSON to stdout.")
def triage_cmd(
    config_path: Path | None,
    reports: tuple[str, ...],
    report_dir: str | None,
    no_jira: bool,
    json_out: bool,
) -> None:
    """
    Parse Polyspace/QAC reports, diff against baseline, gate the merge,
    and optionally create categorized Jira tickets.
    """
    config = load_config(config_path)
    setup_logging(config.log_level)
    service = TriageService(config)
    paths = _collect_reports(reports, report_dir)

    try:
        report, decision = service.run(paths, create_tickets=not no_jira)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Triage failed:[/bold red] {exc}")
        raise SystemExit(2) from exc

    if json_out:
        click.echo(json.dumps(report.to_dashboard_dict(), indent=2))
    else:
        _print_summary(report)

    raise SystemExit(decision.exit_code)


@main.command("update-baseline")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--report", "reports", multiple=True, type=click.Path(path_type=str))
@click.option("--report-dir", type=click.Path(path_type=str), default=None)
@click.option("--note", default="", help="Optional note stored with the baseline.")
def update_baseline_cmd(
    config_path: Path | None,
    reports: tuple[str, ...],
    report_dir: str | None,
    note: str,
) -> None:
    """Accept current findings as the new technical-debt baseline."""
    config = load_config(config_path)
    setup_logging(config.log_level)
    service = TriageService(config)
    paths = _collect_reports(reports, report_dir)
    try:
        count = service.update_baseline(paths, note=note)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Baseline update failed:[/bold red] {exc}")
        raise SystemExit(2) from exc
    console.print(f"[green]Baseline updated[/green] with {count} violation(s) → {config.baseline_path}")


@main.command("validate-config")
@click.option("--config", "config_path", type=click.Path(path_type=Path), required=True)
def validate_config_cmd(config_path: Path) -> None:
    """Validate YAML configuration and mapping files."""
    try:
        config = load_config(config_path)
        setup_logging(config.log_level)
        # Force enricher load to surface missing map files as warnings, not hard fails.
        TriageService(config)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Invalid config:[/bold red] {exc}")
        raise SystemExit(2) from exc
    console.print("[green]Configuration OK[/green]")


def _print_summary(report) -> None:
    s = report.summary
    table = Table(title="MISRA Triage Summary")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Total findings", str(s.total))
    table.add_row("Baseline (known debt)", str(s.baseline))
    table.add_row("New", str(s.new))
    table.add_row("Resolved since baseline", str(s.resolved))
    table.add_row("Blocking new", str(s.blocking_new))
    table.add_row("Jira tickets", str(s.tickets_created))
    table.add_row("Gate", "PASSED" if s.gate_passed else "FAILED")
    console.print(table)

    if report.blocking_violations:
        console.print("\n[bold red]Blocking violations:[/bold red]")
        for v in report.blocking_violations[:20]:
            console.print(
                f"  • {v.rule_id} @ {v.location()} "
                f"[{v.misra_category.value}/{v.asil_level.value}] owner={v.owner}"
            )
        if len(report.blocking_violations) > 20:
            console.print(f"  …and {len(report.blocking_violations) - 20} more")

    if report.jira_issues:
        console.print("\n[bold]Jira issues:[/bold]")
        for issue in report.jira_issues:
            mode = "dry-run" if issue.get("dry_run") else "created"
            console.print(f"  • {issue['key']} ({mode}) {issue.get('url', '')}")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
