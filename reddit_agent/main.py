import sys
from orchestrator import run_pipeline
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich import box


console = Console()


def display_results(result: dict):
    if "error" in result:
        console.print(f"\n[red]Error: {result['error']}[/red]")
        return

    summary = result.get("summary", {})
    contradictions = result.get("contradictions", {})
    fact_check = result.get("fact_check", {})
    kg = result.get("knowledge_graph", {})
    perspectives = result.get("perspectives", [])
    posts = result.get("scored_posts", [])

    # Answer
    answer = f"""## Answer\n\n{summary.get('consensus', 'No consensus available')}"""
    if summary.get("key_insights"):
        answer += "\n\n### Key Insights\n"
        for ins in summary["key_insights"]:
            answer += f"- {ins}\n"
    if summary.get("recommendations"):
        answer += "\n### Recommendations\n"
        for r in summary["recommendations"]:
            answer += f"- {r}\n"
    if summary.get("caveats"):
        answer += "\n### Caveats\n"
        for c in summary["caveats"]:
            answer += f"- {c}\n"

    console.print()
    console.print(Panel.fit(
        Markdown(answer),
        title="[bold green]Reddit Intelligence Report[/bold green]",
        border_style="green",
    ))

    # Contradictions
    if contradictions.get("has_contradictions"):
        table = Table(title="Community Sentiment Breakdown", box=box.ROUNDED)
        table.add_column("Stance", style="cyan")
        table.add_column("%", style="yellow")
        table.add_column("Summary")
        for v in contradictions.get("viewpoints", []):
            table.add_row(
                v.get("stance", ""),
                f"{v.get('percentage', 0)}%",
                v.get("summary", "")[:100],
            )
        console.print()
        console.print(table)
    elif contradictions.get("consensus"):
        console.print(f"\n[dim]Consensus: {contradictions['consensus']}[/dim]")

    # Perspectives
    if perspectives:
        console.print("\n[bold cyan]Stakeholder Perspectives:[/bold cyan]")
        for p in perspectives:
            console.print(f"  • [bold]{p.get('group', '')}[/bold]: {p.get('angle', '')}")

    # Knowledge Graph
    if kg.get("entities"):
        table = Table(title="Key Entities Found", box=box.SIMPLE)
        table.add_column("Entity", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Sentiment")
        for e in kg["entities"][:8]:
            table.add_row(e.get("name", ""), e.get("type", ""), e.get("sentiment", ""))
        console.print()
        console.print(table)

    # Fact Check
    fc = fact_check
    if fc.get("overall_assessment"):
        assessment_colors = {
            "reddit_is_generally_correct": "green",
            "reddit_has_mixed_accuracy": "yellow",
            "reddit_is_misleading": "red",
        }
        color = assessment_colors.get(fc.get("overall_assessment", ""), "white")
        console.print(f"\n[bold]Fact Check:[/bold] [[{color}]{fc.get('overall_assessment', 'N/A')}[/{color}]]")
        if fc.get("recommendation"):
            console.print(f"  [dim]{fc['recommendation']}[/dim]")
        if fc.get("questionable_claims"):
            for c in fc["questionable_claims"]:
                console.print(f"  [yellow]! {c}[/yellow]")

    # Sources
    console.print(f"\n[bold cyan]Sources ({len(posts)}):[/bold cyan]")
    for i, p in enumerate(posts[:5], 1):
        cred = p.get("credibility", "")
        cred_str = f" | Credibility: {cred}/10" if cred else ""
        console.print(f"  {i}. [link={p['url']}]{p['title']}[/link]")
        console.print(f"     [dim]r/{p['subreddit']}{cred_str}[/dim]")
    console.print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        console.print(Panel.fit(
            "[bold]Reddit Intelligence Engine[/bold]\nMulti-agent Reddit research system",
            title="Welcome",
            border_style="blue",
        ))
        result = run_pipeline(question)
        display_results(result)
    else:
        console.print(Panel.fit(
            "[bold]Reddit Intelligence Engine[/bold]\nMulti-agent Reddit research system",
            title="Welcome",
            border_style="blue",
        ))

        while True:
            try:
                question = console.input("\n[bold yellow]Ask a question (or 'quit'):[/bold yellow] ")
                if question.lower() in ["quit", "exit", "q"]:
                    break
                if not question.strip():
                    continue
                result = run_pipeline(question)
                display_results(result)
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
