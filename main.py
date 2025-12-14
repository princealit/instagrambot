#!/usr/bin/env python3
"""
Instagram Bot CLI - Demographic-based outreach automation.

Usage:
    python main.py hashtag --tags fitness,gym --gender male --age-min 40 --age-max 60 --message "Hey {name}!"
    python main.py followers --accounts @competitor1 --gender male --age-min 40 --message "Hey {name}!"
    python main.py search --query "business owner" --gender male --age-min 40 --message "Hey!"
    python main.py analyze --usernames user1,user2,user3
"""

import os
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.bot import InstagramBot, BotConfig
from src.models import DemographicCriteria, Gender

app = typer.Typer(help="Instagram Demographic Filter & Outreach Bot")
console = Console()


def create_criteria(
    gender: Optional[str],
    age_min: Optional[int],
    age_max: Optional[int],
    min_followers: Optional[int],
    max_followers: Optional[int],
    min_confidence: float,
) -> DemographicCriteria:
    """Create demographic criteria from CLI args."""
    gender_enum = None
    if gender:
        gender_map = {"male": Gender.MALE, "female": Gender.FEMALE, "m": Gender.MALE, "f": Gender.FEMALE}
        gender_enum = gender_map.get(gender.lower())

    return DemographicCriteria(
        gender=gender_enum,
        age_min=age_min,
        age_max=age_max,
        min_followers=min_followers,
        max_followers=max_followers,
        min_confidence=min_confidence,
    )


def display_results(results: list, title: str = "Results") -> None:
    """Display outreach results in a table."""
    table = Table(title=title)
    table.add_column("Username", style="cyan")
    table.add_column("Gender", style="magenta")
    table.add_column("Age Range", style="green")
    table.add_column("Likes", style="yellow")
    table.add_column("DM Sent", style="blue")
    table.add_column("Status", style="red")

    for result in results:
        profile = result.profile
        age_range = f"{profile.inferred_age_min}-{profile.inferred_age_max}" if profile.inferred_age_min else "?"
        status = "✓" if result.success else f"✗ {result.error or ''}"

        table.add_row(
            profile.username,
            profile.inferred_gender.value,
            age_range,
            str(result.photos_liked),
            "✓" if result.dm_sent else "✗",
            status,
        )

    console.print(table)


def display_profiles(profiles: list, title: str = "Analyzed Profiles") -> None:
    """Display analyzed profiles in a table."""
    table = Table(title=title)
    table.add_column("Username", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Gender", style="magenta")
    table.add_column("Conf", style="dim")
    table.add_column("Age Range", style="green")
    table.add_column("Conf", style="dim")
    table.add_column("Followers", style="yellow")
    table.add_column("Bio Snippet", style="dim", max_width=30)

    for profile in profiles:
        age_range = f"{profile.inferred_age_min}-{profile.inferred_age_max}" if profile.inferred_age_min else "?"
        bio_snippet = (profile.biography[:27] + "...") if len(profile.biography) > 30 else profile.biography

        table.add_row(
            profile.username,
            profile.full_name[:20] if profile.full_name else "",
            profile.inferred_gender.value,
            f"{profile.gender_confidence:.0%}",
            age_range,
            f"{profile.age_confidence:.0%}",
            f"{profile.follower_count:,}",
            bio_snippet.replace("\n", " "),
        )

    console.print(table)


@app.command()
def hashtag(
    tags: str = typer.Option(..., "--tags", "-t", help="Comma-separated hashtags (without #)"),
    message: str = typer.Option(..., "--message", "-m", help="DM message template. Use {name} for personalization"),
    gender: Optional[str] = typer.Option(None, "--gender", "-g", help="Target gender: male/female"),
    age_min: Optional[int] = typer.Option(None, "--age-min", help="Minimum age"),
    age_max: Optional[int] = typer.Option(None, "--age-max", help="Maximum age"),
    min_followers: Optional[int] = typer.Option(None, "--min-followers", help="Minimum follower count"),
    max_followers: Optional[int] = typer.Option(None, "--max-followers", help="Maximum follower count"),
    min_confidence: float = typer.Option(0.5, "--confidence", help="Minimum confidence for demographic match"),
    max_outreach: int = typer.Option(10, "--max", "-n", help="Maximum profiles to reach out to"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't perform actual Instagram actions"),
):
    """Run outreach campaign based on hashtags."""
    hashtags_list = [h.strip().lstrip("#") for h in tags.split(",")]
    criteria = create_criteria(gender, age_min, age_max, min_followers, max_followers, min_confidence)

    console.print(f"\n[bold]Hashtag Campaign[/bold]")
    console.print(f"Tags: {', '.join(hashtags_list)}")
    console.print(f"Criteria: {criteria}")
    console.print(f"Message: {message}")
    console.print(f"Dry run: {dry_run}\n")

    config = BotConfig.from_env()
    config.dry_run = dry_run

    bot = InstagramBot(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Running campaign...", total=None)
        results = bot.run_hashtag_campaign(hashtags_list, criteria, message, max_outreach)

    display_results(results, "Campaign Results")

    success_count = sum(1 for r in results if r.success)
    console.print(f"\n[bold green]Completed: {success_count}/{len(results)} successful[/bold green]")


@app.command()
def followers(
    accounts: str = typer.Option(..., "--accounts", "-a", help="Comma-separated source accounts"),
    message: str = typer.Option(..., "--message", "-m", help="DM message template"),
    gender: Optional[str] = typer.Option(None, "--gender", "-g", help="Target gender: male/female"),
    age_min: Optional[int] = typer.Option(None, "--age-min", help="Minimum age"),
    age_max: Optional[int] = typer.Option(None, "--age-max", help="Maximum age"),
    min_followers: Optional[int] = typer.Option(None, "--min-followers", help="Minimum follower count"),
    max_followers: Optional[int] = typer.Option(None, "--max-followers", help="Maximum follower count"),
    min_confidence: float = typer.Option(0.5, "--confidence", help="Minimum confidence for demographic match"),
    max_outreach: int = typer.Option(10, "--max", "-n", help="Maximum profiles to reach out to"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't perform actual Instagram actions"),
):
    """Run outreach campaign targeting followers of specific accounts."""
    accounts_list = [a.strip().lstrip("@") for a in accounts.split(",")]
    criteria = create_criteria(gender, age_min, age_max, min_followers, max_followers, min_confidence)

    console.print(f"\n[bold]Follower Campaign[/bold]")
    console.print(f"Source accounts: {', '.join(accounts_list)}")
    console.print(f"Criteria: {criteria}")
    console.print(f"Dry run: {dry_run}\n")

    config = BotConfig.from_env()
    config.dry_run = dry_run

    bot = InstagramBot(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Running campaign...", total=None)
        results = bot.run_follower_campaign(accounts_list, criteria, message, max_outreach)

    display_results(results, "Campaign Results")


@app.command()
def search(
    query: str = typer.Option(..., "--query", "-q", help="Search query"),
    message: str = typer.Option(..., "--message", "-m", help="DM message template"),
    gender: Optional[str] = typer.Option(None, "--gender", "-g", help="Target gender: male/female"),
    age_min: Optional[int] = typer.Option(None, "--age-min", help="Minimum age"),
    age_max: Optional[int] = typer.Option(None, "--age-max", help="Maximum age"),
    min_followers: Optional[int] = typer.Option(None, "--min-followers", help="Minimum follower count"),
    max_followers: Optional[int] = typer.Option(None, "--max-followers", help="Maximum follower count"),
    min_confidence: float = typer.Option(0.5, "--confidence", help="Minimum confidence for demographic match"),
    max_outreach: int = typer.Option(10, "--max", "-n", help="Maximum profiles to reach out to"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't perform actual Instagram actions"),
):
    """Run outreach campaign based on search query."""
    criteria = create_criteria(gender, age_min, age_max, min_followers, max_followers, min_confidence)

    console.print(f"\n[bold]Search Campaign[/bold]")
    console.print(f"Query: {query}")
    console.print(f"Criteria: {criteria}")
    console.print(f"Dry run: {dry_run}\n")

    config = BotConfig.from_env()
    config.dry_run = dry_run

    bot = InstagramBot(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Running campaign...", total=None)
        results = bot.run_search_campaign(query, criteria, message, max_outreach)

    display_results(results, "Campaign Results")


@app.command()
def analyze(
    usernames: str = typer.Option(..., "--usernames", "-u", help="Comma-separated usernames to analyze"),
    gender: Optional[str] = typer.Option(None, "--gender", "-g", help="Filter by gender"),
    age_min: Optional[int] = typer.Option(None, "--age-min", help="Filter by minimum age"),
    age_max: Optional[int] = typer.Option(None, "--age-max", help="Filter by maximum age"),
):
    """Analyze profiles and show inferred demographics (no outreach)."""
    usernames_list = [u.strip().lstrip("@") for u in usernames.split(",")]

    criteria = None
    if gender or age_min or age_max:
        criteria = create_criteria(gender, age_min, age_max, None, None, 0.3)

    console.print(f"\n[bold]Profile Analysis[/bold]")
    console.print(f"Usernames: {', '.join(usernames_list)}")
    if criteria:
        console.print(f"Filter: {criteria}")
    console.print()

    config = BotConfig.from_env()
    config.dry_run = True  # Analysis doesn't need Instagram login

    bot = InstagramBot(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing profiles...", total=None)
        profiles = bot.analyze_profiles_only(usernames_list, criteria)

    display_profiles(profiles)
    console.print(f"\n[bold]Analyzed {len(profiles)} profiles[/bold]")


@app.command()
def config_check():
    """Check if all required configuration is set."""
    console.print("\n[bold]Configuration Check[/bold]\n")

    checks = [
        ("APIFY_API_TOKEN", os.getenv("APIFY_API_TOKEN"), True),
        ("INSTAGRAM_USERNAME", os.getenv("INSTAGRAM_USERNAME"), True),
        ("INSTAGRAM_PASSWORD", os.getenv("INSTAGRAM_PASSWORD"), True),
        ("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"), False),
    ]

    all_required_set = True
    for name, value, required in checks:
        status = "[green]✓ Set[/green]" if value else "[red]✗ Not set[/red]"
        req = "[yellow](required)[/yellow]" if required else "[dim](optional)[/dim]"

        if required and not value:
            all_required_set = False

        console.print(f"  {name}: {status} {req}")

    console.print()
    if all_required_set:
        console.print("[bold green]All required configuration is set![/bold green]")
    else:
        console.print("[bold red]Missing required configuration. Copy .env.example to .env and fill in values.[/bold red]")


if __name__ == "__main__":
    app()
