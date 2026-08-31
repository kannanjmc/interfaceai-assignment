"""
Main entry point for the computer-use automation system.

This module provides the CLI interface for running discovery and replay.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import get_settings
from .agent.discovery import DiscoveryAgent
from .replay.engine import ReplayEngine
from .core.models import CapabilityArtifact
from .core.surface import SurfaceType
from .evidence.collector import EvidenceCollector
from .handoff.coordinator import HandoffCoordinator
from .safety.guardrails import AllowlistPolicy, ActionType as SafetyActionType

app = typer.Typer()
console = Console()


@app.command()
def discover(
    goal: str = typer.Argument(..., help="Natural language goal to accomplish"),
    target_url: str = typer.Option(None, help="Target application URL"),
    headless: bool = typer.Option(True, help="Run browser in headless mode"),
    output: str = typer.Option("artifact.json", help="Output file for the artifact"),
    evidence_dir: str = typer.Option("evidence/discovery", help="Directory for evidence")
):
    """
    Run discovery to learn how to accomplish a goal.
    
    Uses an LLM to drive the application and learn the flow, then saves
    a structured capability artifact.
    """
    asyncio.run(_discover(goal, target_url, headless, output, evidence_dir))


async def _discover(
    goal: str,
    target_url: Optional[str],
    headless: bool,
    output: str,
    evidence_dir: str
):
    """Async implementation of discover command."""
    settings = get_settings()
    
    # Use configured URL if not provided
    if not target_url:
        target_url = settings.target_app_url
    
    console.print(f"[bold blue]Starting Discovery[/bold blue]")
    console.print(f"Goal: {goal}")
    console.print(f"Target: {target_url}")
    console.print(f"Headless: {headless}")
    console.print()
    
    # Initialize evidence collector
    evidence = EvidenceCollector(base_dir="evidence")
    session_id = f"discovery_{goal.replace(' ', '_')[:20]}"
    evidence.start_session(session_id, "discovery")
    
    # Initialize discovery agent
    agent = DiscoveryAgent(
        llm_provider=settings.llm_provider,
        model=settings.get_model(),
        api_key=settings.get_llm_key()
    )
    
    try:
        # Run discovery
        console.print("[yellow]Running LLM-driven discovery...[/yellow]")
        artifact, result = await agent.discover(
            goal=goal,
            target_url=target_url,
            surface_type=SurfaceType.LEGACY_WEB,
            headless=headless,
            evidence_dir=evidence_dir
        )
        
        # Save artifact
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(artifact.model_dump(), f, indent=2)
        
        # Finish evidence collection
        evidence.finish_session(result)
        
        # Display results
        console.print()
        console.print("[bold green]Discovery Complete![/bold green]")
        console.print(f"Status: {result.status}")
        console.print(f"Steps executed: {result.steps_executed}")
        console.print(f"Execution time: {result.execution_time_seconds:.2f}s")
        console.print(f"Artifact saved to: {output_path}")
        console.print(f"Evidence saved to: {evidence_dir}")
        
        if result.status == "success":
            console.print(f"[green]Outputs: {result.outputs}[/green]")
        else:
            console.print(f"[red]Error: {result.error_message}[/red]")
        
        # Display artifact summary
        console.print()
        console.print("[bold]Artifact Summary:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("ID", artifact.artifact_id)
        table.add_row("Name", artifact.name)
        table.add_row("Description", artifact.description)
        table.add_row("Steps", str(len(artifact.steps)))
        table.add_row("Input Parameters", str(len(artifact.input_parameters)))
        table.add_row("Outputs", str(len(artifact.outputs)))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Discovery failed:[/bold red] {str(e)}")
        sys.exit(1)


@app.command()
def replay(
    artifact_file: str = typer.Argument(..., help="Path to artifact JSON file"),
    member_id: str = typer.Option(None, help="Member ID parameter (if needed)"),
    headless: bool = typer.Option(True, help="Run browser in headless mode"),
    evidence_dir: str = typer.Option("evidence/replay", help="Directory for evidence")
):
    """
    Replay a capability artifact deterministically.
    
    Executes a saved artifact without LLM involvement, using the provided
    input parameters.
    """
    asyncio.run(_replay(artifact_file, member_id, headless, evidence_dir))


async def _replay(
    artifact_file: str,
    member_id: Optional[str],
    headless: bool,
    evidence_dir: str
):
    """Async implementation of replay command."""
    console.print(f"[bold blue]Starting Replay[/bold blue]")
    console.print(f"Artifact: {artifact_file}")
    console.print(f"Headless: {headless}")
    console.print()
    
    # Load artifact
    artifact_path = Path(artifact_file)
    if not artifact_path.exists():
        console.print(f"[bold red]Artifact file not found: {artifact_file}[/bold red]")
        sys.exit(1)
    
    with open(artifact_path, 'r') as f:
        artifact_data = json.load(f)
    
    artifact = CapabilityArtifact(**artifact_data)
    
    console.print(f"[bold]Artifact:[/bold] {artifact.name}")
    console.print(f"Description: {artifact.description}")
    console.print(f"Steps: {len(artifact.steps)}")
    console.print()
    
    # Build parameters
    parameters = {}
    if member_id:
        parameters["member_id"] = member_id
    
    # Add any other required parameters
    for param_def in artifact.input_parameters:
        if param_def.name not in parameters and param_def.required:
            # In a real CLI, we'd prompt for these
            console.print(f"[yellow]Warning: Missing required parameter: {param_def.name}[/yellow]")
    
    # Initialize evidence collector
    evidence = EvidenceCollector(base_dir="evidence")
    session_id = f"replay_{artifact.artifact_id}"
    evidence.start_session(session_id, "replay")
    
    # Initialize replay engine
    engine = ReplayEngine()
    
    try:
        # Run replay
        console.print("[yellow]Running deterministic replay...[/yellow]")
        result = await engine.execute(
            artifact=artifact,
            parameters=parameters,
            headless=headless,
            evidence_dir=evidence_dir
        )
        
        # Finish evidence collection
        evidence.finish_session(result)
        
        # Display results
        console.print()
        console.print("[bold green]Replay Complete![/bold green]")
        console.print(f"Status: {result.status}")
        console.print(f"Steps executed: {result.steps_executed}")
        console.print(f"Execution time: {result.execution_time_seconds:.2f}s")
        console.print(f"Evidence saved to: {evidence_dir}")
        
        if result.status == "success":
            console.print(f"[green]Outputs: {result.outputs}[/green]")
        elif result.status == "business_outcome":
            console.print(f"[yellow]Business Outcome: {result.business_outcome}[/yellow]")
            console.print(f"Outputs: {result.outputs}")
        else:
            console.print(f"[red]Error Type: {result.error_type}[/red]")
            console.print(f"[red]Error Message: {result.error_message}[/red]")
            if result.failed_step:
                console.print(f"[red]Failed at step: {result.failed_step}[/red]")
        
    except Exception as e:
        console.print(f"[bold red]Replay failed:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@app.command()
def demo():
    """
    Run a complete demo: discovery and replay.
    
    This is the fastest way to see the system in action.
    """
    asyncio.run(_demo())


async def _demo():
    """Run the complete demo flow."""
    console.print("[bold blue]Computer-Use Automation Demo[/bold blue]")
    console.print()
    
    settings = get_settings()
    
    # Demo goal
    goal = "Look up member 12345 and read their current savings balance"
    target_url = settings.target_app_url
    
    console.print(f"Demo Goal: {goal}")
    console.print(f"Target: {target_url}")
    console.print()
    
    # Step 1: Discovery
    console.print("[bold cyan]Step 1: Discovery[/bold cyan]")
    console.print("-" * 50)
    
    evidence = EvidenceCollector(base_dir="evidence")
    session_id = "demo_discovery"
    evidence.start_session(session_id, "discovery")
    
    agent = DiscoveryAgent(
        llm_provider=settings.llm_provider,
        model=settings.get_model(),
        api_key=settings.get_llm_key()
    )
    
    try:
        artifact, result = await agent.discover(
            goal=goal,
            target_url=target_url,
            surface_type=SurfaceType.LEGACY_WEB,
            headless=False,  # Show browser for demo
            evidence_dir="evidence/demo_discovery"
        )
        
        evidence.finish_session(result)
        
        # Save artifact
        artifact_path = Path("artifact.json")
        with open(artifact_path, 'w') as f:
            json.dump(artifact.model_dump(), f, indent=2)
        
        console.print(f"[green]✓ Discovery complete[/green]")
        console.print(f"  Status: {result.status}")
        console.print(f"  Steps: {result.steps_executed}")
        console.print(f"  Artifact: {artifact_path}")
        console.print()
        
        if result.status != "success":
            console.print(f"[red]Discovery did not succeed. Cannot continue with replay.[/red]")
            return
        
        # Step 2: Replay
        console.print("[bold cyan]Step 2: Deterministic Replay[/bold cyan]")
        console.print("-" * 50)
        
        evidence = EvidenceCollector(base_dir="evidence")
        session_id = "demo_replay"
        evidence.start_session(session_id, "replay")
        
        engine = ReplayEngine()
        
        replay_result = await engine.execute(
            artifact=artifact,
            parameters={"member_id": "12345"},
            headless=False,  # Show browser for demo
            evidence_dir="evidence/demo_replay"
        )
        
        evidence.finish_session(replay_result)
        
        console.print(f"[green]✓ Replay complete[/green]")
        console.print(f"  Status: {replay_result.status}")
        console.print(f"  Steps: {replay_result.steps_executed}")
        console.print(f"  Outputs: {replay_result.outputs}")
        console.print()
        
        # Step 3: Error scenario replay
        console.print("[bold cyan]Step 3: Error Scenario Replay[/bold cyan]")
        console.print("-" * 50)
        console.print("Replaying with invalid member ID to demonstrate error handling...")
        
        evidence = EvidenceCollector(base_dir="evidence")
        session_id = "demo_error"
        evidence.start_session(session_id, "replay")
        
        error_result = await engine.execute(
            artifact=artifact,
            parameters={"member_id": "99999"},  # Invalid member
            headless=False,
            evidence_dir="evidence/demo_error"
        )
        
        evidence.finish_session(error_result)
        
        console.print(f"[green]✓ Error replay complete[/green]")
        console.print(f"  Status: {error_result.status}")
        if error_result.status == "business_outcome":
            console.print(f"  Business Outcome: {error_result.business_outcome}")
        else:
            console.print(f"  Error: {error_result.error_message}")
        console.print()
        
        console.print("[bold green]Demo Complete![/bold green]")
        console.print()
        console.print("Evidence saved to:")
        console.print("  - evidence/demo_discovery/")
        console.print("  - evidence/demo_replay/")
        console.print("  - evidence/demo_error/")
        console.print()
        console.print("Artifact saved to: artifact.json")
        
    except Exception as e:
        console.print(f"[bold red]Demo failed:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@app.command()
def start_target_app():
    """
    Start the target application (legacy bank admin console).
    
    This runs the Flask app that mimics a legacy bank system.
    """
    import subprocess
    from src.target_app.app import app
    
    console.print("[bold blue]Starting Target Application[/bold blue]")
    console.print("Legacy Bank Admin Console will be available at http://localhost:5000")
    console.print("Press Ctrl+C to stop")
    console.print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == "__main__":
    app()
