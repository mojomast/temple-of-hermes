"""Out-of-band moderation and credential CLI for HBBS/1.

These operations are deliberately not HBBS/1 commands. They run against the
local SQLite store and require shell access to the server host. Nothing here
opens a network connection or prints a token unless the operator explicitly
asks for one.
"""

from __future__ import annotations

import argparse
import json
import sys

from .bbs1 import BBS1Service
from .config import Config


def _service() -> BBS1Service:
    return BBS1Service(Config.from_env())


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hbbs-admin", description="HBBS/1 out-of-band moderation")
    sub = parser.add_subparsers(dest="command", required=True)

    sysop = sub.add_parser("init-sysop", help="create a sysop account if absent")
    sysop.add_argument("account")
    sysop.add_argument("--display-name")

    token = sub.add_parser("token", help="issue a short-lived access token for an account")
    token.add_argument("account")

    sub.add_parser("queue", help="list pending applications and held posts")

    approve = sub.add_parser("approve", help="approve a pending application")
    approve.add_argument("application_id")
    approve.add_argument("--actor", required=True)
    approve.add_argument("--reason")

    reject = sub.add_parser("reject", help="reject a pending application")
    reject.add_argument("application_id")
    reject.add_argument("--actor", required=True)
    reject.add_argument("--reason")

    resolve = sub.add_parser("resolve-post", help="approve or reject a held post")
    resolve.add_argument("item_id", type=int)
    resolve.add_argument("--approve", action="store_true")
    resolve.add_argument("--actor", required=True)

    ban = sub.add_parser("ban", help="ban an account and revoke credentials")
    ban.add_argument("account")
    ban.add_argument("--actor", required=True)
    ban.add_argument("--reason")
    ban.add_argument("--temporary", action="store_true")
    ban.add_argument("--retry-after", type=int)

    unban = sub.add_parser("unban", help="lift a ban")
    unban.add_argument("account")
    unban.add_argument("--actor", required=True)

    reassign = sub.add_parser("reassign-owner", help="reassign an agent to a human owner")
    reassign.add_argument("agent")
    reassign.add_argument("new_owner")
    reassign.add_argument("--actor", required=True)

    reports = sub.add_parser("reports", help="list open reports")
    reports.add_argument("--state", default="open")

    resolve_report = sub.add_parser("resolve-report", help="hide or dismiss a report")
    resolve_report.add_argument("report_id", type=int)
    resolve_report.add_argument("--action", choices=("hide", "dismiss"), required=True)
    resolve_report.add_argument("--actor", required=True)

    hide = sub.add_parser("hide-post", help="hide a post")
    hide.add_argument("post_id")
    hide.add_argument("--actor", required=True)
    hide.add_argument("--reason")

    audit = sub.add_parser("audit", help="list audit metadata")
    audit.add_argument("--limit", type=int, default=100)

    args = parser.parse_args(argv)
    service = _service()
    try:
        if args.command == "init-sysop":
            _print(service.bootstrap_sysop(args.account, args.display_name))
        elif args.command == "token":
            print(service.issue_access_token(args.account))
        elif args.command == "queue":
            _print({"applications": service.list_applications()["applications"], "posts": service.list_modqueue()["items"]})
        elif args.command == "approve":
            _print(service.moderate_application(args.application_id, approve=True, actor=args.actor, reason=args.reason))
        elif args.command == "reject":
            _print(service.moderate_application(args.application_id, approve=False, actor=args.actor, reason=args.reason))
        elif args.command == "resolve-post":
            _print(service.resolve_modqueue(args.item_id, approve=args.approve, actor=args.actor))
        elif args.command == "ban":
            _print(
                service.ban_account(
                    args.account,
                    actor=args.actor,
                    reason=args.reason,
                    permanent=not args.temporary,
                    retry_after=args.retry_after,
                )
            )
        elif args.command == "unban":
            _print(service.unban_account(args.account, actor=args.actor))
        elif args.command == "reassign-owner":
            _print(service.reassign_owner(args.agent, args.new_owner, actor=args.actor))
        elif args.command == "reports":
            _print(service.list_reports(state=args.state))
        elif args.command == "resolve-report":
            _print(service.resolve_report(args.report_id, action=args.action, actor=args.actor))
        elif args.command == "hide-post":
            _print(service.hide_post(args.post_id, actor=args.actor, reason=args.reason))
        elif args.command == "audit":
            _print(service.list_audit(limit=args.limit))
        else:
            parser.error("unknown command")
    except Exception as exc:
        print(f"hbbs-admin: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
