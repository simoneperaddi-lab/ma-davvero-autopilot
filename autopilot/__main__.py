"""python -m autopilot: simulation by default. Live requires explicit double opt-in."""
import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from autopilot.http import HTTP, RemoteError
from autopilot.instagram import Instagram
from autopilot.pipeline import Pipeline, event, weekly_report
from autopilot.render import render
from autopilot.science import Archive, Unverified
from autopilot.simulation import SimulatedArchive, SimulatedInstagram
from autopilot.state import GitHubState, LocalState, SecretStore


def required(name):
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"Configurazione mancante: {name}")
    return value


def live_settings():
    if required("MAD_PUBLISH_ENABLED") != "true":
        raise ValueError("Pubblicazione disattivata")
    if required("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Pubblicazione consentita soltanto da main")
    return required("IG_USER_ID"), required("IG_ACCESS_TOKEN"), required("GH_SECRET_UPDATER")


def main(argv=None):
    parser = argparse.ArgumentParser(description="MA DAVVERO? — autopilota gratuito")
    parser.add_argument("--mode", choices=["simulate", "verify", "preflight", "publish", "report"], default="simulate")
    parser.add_argument("--output", type=Path, default=Path("data/autopilot"))
    parser.add_argument("--no-audio", action="store_true")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    store = None
    try:
        renderer = lambda fact, path: render(fact, path, audio=not args.no_audio)
        if args.mode == "simulate":
            store = LocalState(args.output / "simulation-ledger.json")
            ig = SimulatedInstagram()
            status = Pipeline(store, SimulatedArchive(), ig, renderer).run(args.output)
            # Execute a second complete run to assert durable duplicate prevention.
            second = Pipeline(store, SimulatedArchive(), ig, renderer).run(args.output)
            if second != "already_published_today" or ig.publishes > 1:
                raise ValueError("Test di idempotenza fallito")
            report = "SIMULAZIONE: nessuna rete e nessuna pubblicazione reale.\n\n" + weekly_report(store.load())
        elif args.mode in {"verify", "preflight"}:
            http = HTTP()
            if args.mode == "preflight":
                Instagram(http, required("IG_USER_ID"), required("IG_ACCESS_TOKEN"),
                          os.environ.get("IG_API_VERSION", "v24.0")).identity()
            fact = Archive(http).select(set())
            renderer(fact, args.output)
            status = "verified_not_published"
            report = "Verifica fonte e rendering completati. Nessun container creato o Reel pubblicato.\n"
        else:
            live = live_settings() if args.mode == "publish" else None
            repo = required("GITHUB_REPOSITORY")
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
                raise ValueError("Repository non valido")
            http = HTTP()
            store = GitHubState(http, repo, required("GITHUB_TOKEN"))
            if args.mode == "publish":
                user, token, updater = live
                ig = Instagram(http, user, token, os.environ.get("IG_API_VERSION", "v24.0"))
                status = Pipeline(store, Archive(http), ig, renderer, SecretStore(http, repo, updater)).run(args.output)
            else:
                status = "report"
            report = weekly_report(store.load())
        report = f"Esito: {status}\n\n" + report
        (args.output / "report.md").write_text(report, encoding="utf-8")
        if path := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(path, "a", encoding="utf-8") as summary:
                summary.write(report)
        print(f"MA DAVVERO? {args.mode}: {status}")
        if status == "skipped":
            print("::warning::Pubblicazione saltata: controllare il riepilogo")
        return 0
    except Exception as exc:
        # HTTP exceptions may contain access tokens in request URLs. Never print str(exc).
        message = f"Operazione interrotta ({type(exc).__name__}). Consultare docs/ANDROID.md e il registro; nessun retry di pubblicazione."
        if isinstance(exc, RemoteError):
            message += f" HTTP: {exc.status or 'connessione'}."
        if isinstance(exc, Unverified):
            message += " " + str(exc)  # Only locally defined rejection reasons, never response bodies.
        if store is not None:
            try:
                state = store.load()
                event(state, datetime.now(timezone.utc), "error", message)
                store.save(state)
            except Exception:
                pass  # Never mask the original failure or reset a damaged ledger.
        report = f"# MA DAVVERO? — errore\n\n{message}\n"
        (args.output / "report.md").write_text(report, encoding="utf-8")
        if path := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(path, "a", encoding="utf-8") as summary:
                summary.write(report)
        print("::error::" + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
