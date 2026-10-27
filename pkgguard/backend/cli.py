# backend/cli.py
import subprocess, sys, httpx, typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="PkgGuard: Behavioral Supply-Chain Firewall for pip & npm")
console = Console()
API_URL = "http://localhost:8000/api/scan"

@app.command()
def install(
    package: str = typer.Argument(..., help="Package name or path to scan and install"),
    ecosystem: str = typer.Option("pypi", "--eco", "-e", help="Ecosystem: pypi or npm"),
    force_rescan: bool = typer.Option(False, "--rescan", "-r", help="Bypass Supabase cache")
):
    """Scans a package's runtime behavior against its README before allowing installation."""
    with console.status(f"[bold cyan]Sandboxing & analyzing '{package}' ({ecosystem})...[/bold cyan]", spinner="dots"):
        try:
            resp = httpx.post(
                API_URL,
                json={"ecosystem": ecosystem, "name": package, "force_rescan": force_rescan},
                timeout=90.0
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            console.print(f"[bold red]Error contacting PkgGuard backend:[/bold red] {e}")
            raise typer.Exit(code=1)

    claimed = data["claimed_intent"]
    fp = data["behavioral_fingerprint"]
    verdict = data["verdict"]
    score = verdict["risk_score"]

    # 1. Render Behavioral Diff Table
    table = Table(title=f"Behavioral Fingerprint vs. README Claims: [bold]{data['package']}@{data['version']}[/bold]")
    table.add_column("Dimension", style="bold")
    table.add_column("README Claimed", style="cyan")
    table.add_column("Install-Time Observed", style="yellow")
    table.add_column("Import-Time Observed", style="magenta")

    table.add_row(
        "Network Calls",
        "Allowed" if claimed["expects_network"] else "None Expected",
        ", ".join(fp["install_time"]["network_calls"]) or "None",
        ", ".join(fp["import_time"]["network_calls"]) or "None"
    )
    table.add_row(
        "Files Touched",
        "Outside Pkg" if claimed["expects_file_read_outside_pkg"] else "Local Only",
        ", ".join(fp["install_time"]["files_touched"]) or "None",
        ", ".join(fp["import_time"]["files_touched"]) or "None"
    )
    table.add_row(
        "Env Vars Read",
        ", ".join(claimed["expects_env_reads"]) or "None Expected",
        ", ".join(fp["install_time"]["env_vars_read"]) or "None",
        ", ".join(fp["import_time"]["env_vars_read"]) or "None"
    )
    table.add_row(
        "Subprocesses",
        "Expected" if claimed["expects_subprocess"] else "None Expected",
        ", ".join(fp["install_time"]["subprocesses_spawned"]) or "None",
        ", ".join(fp["import_time"]["subprocesses_spawned"]) or "None"
    )
    console.print(table)

    # 2. Render Mismatch Flags & Verdict Panel
    color = "red" if score >= 70 else ("yellow" if score >= 35 else "green")
    flags_text = "\n".join(f"• {flag}" for flag in verdict["mismatch_flags"]) or "• Zero behavioral mismatches detected."
    panel_body = (
        f"[bold]Risk Score:[/bold] [{color}]{score}/100 ({verdict['verdict'].upper()})[/{color}]\n"
        f"[bold]Claim Summary:[/bold] {claimed['summary']}\n\n"
        f"[bold]Forensic Findings:[/bold]\n{flags_text}\n\n"
        f"[italic]{verdict['llm_explanation']}[/italic]"
    )
    console.print(Panel(panel_body, title="PkgGuard Security Verdict", border_style=color))

    # 3. Gate the Real Installation
    if score >= 70:
        console.print("[bold red]🚫 INSTALLATION BLOCKED:[/bold red] Package behavior severely violates its documentation claims.")
        if not typer.confirm("Do you want to override security policy and install anyway?", default=False):
            raise typer.Exit(code=1)

    console.print(f"[bold green]✔ Proceeding with {ecosystem} installation of {package}...[/bold green]")
    install_cmd = ["pip", "install", package] if ecosystem == "pypi" else ["npm", "install", package]
    subprocess.run(install_cmd)

if __name__ == "__main__":
    app()
