import typer
import asyncio
import os
from agents.orchestrator import run_pipeline
from core.database import Database
from core.config import Config
from loguru import logger
import sys

app = typer.Typer()

@app.command()
def run(
    topics: str = typer.Option(None, help="Comma-separated topics"),
    categories: str = typer.Option(None, help="Comma-separated ArXiv categories"),
    days: int = typer.Option(None, help="Days lookback"),
    top_n: int = typer.Option(None, help="Number of top papers"),
):
    """Run the full digest pipeline."""
    topics_list = [t.strip() for t in topics.split(",")] if topics else None
    cats_list = [c.strip() for c in categories.split(",")] if categories else None

    try:
        result = asyncio.run(run_pipeline(
            topics=topics_list,
            categories=cats_list,
            days_lookback=days,
            top_n=top_n,
        ))
    except ValueError as e:
        typer.echo(f"Configuration error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        logger.exception("Pipeline crashed unexpectedly")
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)

    if result.get("errors"):
        logger.error(f"Pipeline completed with {len(result['errors'])} errors")
        for err in result["errors"]:
            logger.error(f"  - {err}")
        sys.exit(1)

    logger.info("Pipeline completed successfully!")
    paths = result.get("report_paths", {})
    if paths:
        logger.info(f"JSON: {paths.get('json', 'N/A')}")
        logger.info(f"Markdown: {paths.get('markdown', 'N/A')}")

@app.command()
def history():
    """List all past digest runs."""
    db = Database()
    runs = db.get_all_runs()
    if not runs:
        typer.echo("No runs found.")
        return
    typer.echo(f"{'Run ID':<40} {'Status':<10} {'Papers':<8} {'Date':<20}")
    typer.echo("-" * 80)
    for r in runs:
        typer.echo(f"{r.run_id:<40} {r.status:<10} {r.paper_count:<8} {r.started_at.strftime('%Y-%m-%d %H:%M'):<20}")

@app.command()
def export(
    run_id: str = typer.Argument(..., help="Run ID to export"),
):
    """Export a digest as markdown."""
    db = Database()
    run = db.get_run(run_id)
    if not run:
        typer.echo(f"Run {run_id} not found.", err=True)
        raise typer.Exit(1)
    if not run.md_path or not os.path.exists(run.md_path):
        typer.echo(f"Markdown file not found for run {run_id}.", err=True)
        raise typer.Exit(1)
    with open(run.md_path) as f:
        typer.echo(f.read())

if __name__ == "__main__":
    app()
