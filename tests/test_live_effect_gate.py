"""Offline tests for scripts/live-effect-gate.py.

Runs the gate exactly as the hook does: as a subprocess with the pending tool call piped as JSON
on stdin. The verdict is carried by the EXIT CODE as well as stdout (42 no decision / 43 deny /
44 indeterminate / 45 ask), so the hook can tell the real gate from a stand-in interpreter that
merely exits 0; `decision()` asserts the two agree on every call.

The gate is registered SESSION-WIDE (hooks/hooks.json), so it must no-op for every caller it does
not name. A payload WITHOUT `agent_type` therefore exercises nothing: `bash_call` supplies the
gated agent by default, or the whole roster below would pass while testing the short-circuit.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts import validate_fleet

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "live-effect-gate.py"
gate = validate_fleet.load_gate(REPO)
guard = validate_fleet.load_guard(REPO)

HOMELAB = "sde-agents:homelab-platform"


def run_gate(stdin_text: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", "-S", str(GATE)],
        input=stdin_text.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )


def bash_call(command: str, agent_type: str | None = HOMELAB, mode: str | None = "default") -> str:
    data: dict = {
        "hook_event_name": "PreToolUse",
        "session_id": "s-1",
        "cwd": str(REPO),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    if mode is not None:
        data["permission_mode"] = mode
    if agent_type is not None:
        data["agent_id"] = "a-1"
        data["agent_type"] = agent_type
    return json.dumps(data)


def decision(proc: subprocess.CompletedProcess) -> str:
    """'none' / 'deny' / 'ask' / 'indeterminate', asserting exit code and stdout agree."""
    out = proc.stdout.decode("utf-8").strip()
    if proc.returncode == gate.EXIT_ALLOW:
        assert not out, f"EXIT_ALLOW but stdout was not empty: {out!r}"
        return "none"
    if proc.returncode == gate.EXIT_INDETERMINATE:
        assert not out, f"EXIT_INDETERMINATE but stdout was not empty: {out!r}"
        return "indeterminate"
    assert proc.returncode in (gate.EXIT_DENY, gate.EXIT_ASK), (
        f"unexpected exit {proc.returncode}: stdout={out!r} stderr={proc.stderr.decode('utf-8')!r}"
    )
    verdict = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    expected = {gate.EXIT_DENY: "deny", gate.EXIT_ASK: "ask"}[proc.returncode]
    assert verdict == expected, f"exit {proc.returncode} but stdout said {verdict!r}"
    return verdict


def reason(proc: subprocess.CompletedProcess) -> str:
    return json.loads(proc.stdout.decode("utf-8"))["hookSpecificOutput"]["permissionDecisionReason"]


class ConstantsPinnedToTheGuard(unittest.TestCase):
    def test_exit_codes_and_plugin_name_match_the_guard(self) -> None:
        # The hook shell string translates BOTH scripts' codes; drift here is a disarmed hook.
        self.assertEqual(guard.EXIT_ALLOW, gate.EXIT_ALLOW)
        self.assertEqual(guard.EXIT_DENY, gate.EXIT_DENY)
        self.assertEqual(guard.EXIT_INDETERMINATE, gate.EXIT_INDETERMINATE)
        self.assertEqual(45, gate.EXIT_ASK)
        self.assertNotIn(gate.EXIT_ASK, {guard.EXIT_ALLOW, guard.EXIT_DENY, guard.EXIT_INDETERMINATE})
        self.assertEqual(guard.PLUGIN_NAME, gate.PLUGIN_NAME)

    def test_gated_and_guarded_rosters_are_disjoint(self) -> None:
        # A read-only agent gets the guard; a live-effect agent gets the gate. Both on one agent
        # would deny every live verb before the gate could ask.
        self.assertFalse(set(gate.GATED_AGENT_NAMES) & set(guard.GUARDED_AGENT_NAMES))


class Scoping(unittest.TestCase):
    LIVE = "/usr/bin/docker compose -f /srv/media/docker-compose.yml up -d jellyfin"

    def test_main_loop_is_never_gated(self) -> None:
        self.assertEqual("none", decision(run_gate(bash_call(self.LIVE, agent_type=None))))

    def test_other_agents_are_never_gated(self) -> None:
        for other in ("sde-agents:sde-fullstack", "sde-agents:code-reviewer", "sde-fullstack"):
            with self.subTest(agent=other):
                self.assertEqual("none", decision(run_gate(bash_call(self.LIVE, agent_type=other))))

    def test_bare_and_namespaced_names_are_both_gated(self) -> None:
        for name in ("homelab-platform", HOMELAB):
            with self.subTest(agent=name):
                self.assertEqual("ask", decision(run_gate(bash_call(self.LIVE, agent_type=name))))

    def test_non_bash_tools_get_no_decision(self) -> None:
        payload = json.loads(bash_call(self.LIVE))
        payload["tool_name"] = "Write"
        self.assertEqual("none", decision(run_gate(json.dumps(payload))))

    def test_malformed_payload_is_indeterminate(self) -> None:
        self.assertEqual("indeterminate", decision(run_gate(bash_call(self.LIVE)[:-1])))
        self.assertEqual("indeterminate", decision(run_gate("[]")))


class Modes(unittest.TestCase):
    LIVE = "sudo systemctl restart jellyfin"

    def test_prompting_modes_ask(self) -> None:
        for mode in ("default", "acceptEdits", "plan"):
            with self.subTest(mode=mode):
                out = run_gate(bash_call(self.LIVE, mode=mode))
                self.assertEqual("ask", decision(out))
                self.assertIn("matched rule `systemctl restart`", reason(out))

    def test_suppressed_modes_deny_with_operator_handoff(self) -> None:
        for mode in sorted(gate.SUPPRESSED_MODES):
            with self.subTest(mode=mode):
                out = run_gate(bash_call(self.LIVE, mode=mode))
                self.assertEqual("deny", decision(out))
                self.assertIn(mode, reason(out))
                self.assertIn("operator handoff", reason(out))

    def test_missing_mode_fails_closed_for_a_live_verb_only(self) -> None:
        self.assertEqual("deny", decision(run_gate(bash_call(self.LIVE, mode=None))))
        self.assertIn("permission_mode", reason(run_gate(bash_call(self.LIVE, mode=None))))
        self.assertEqual("none", decision(run_gate(bash_call("git status", mode=None))))


class Roster(unittest.TestCase):
    ASKS = (
        "docker compose -f /srv/media/docker-compose.yml up -d jellyfin",
        "docker-compose up -d",
        "docker compose down",
        "docker restart jellyfin",
        "docker volume rm media_cache",
        "docker system prune -f",
        "podman compose up -d",
        "systemctl restart jellyfin",
        "systemctl --user enable --now syncthing",
        "systemctl daemon-reload",
        "sudo -u root systemctl reload caddy",
        "ssh nuc-01 'systemctl restart jellyfin'",
        "ssh -p 2222 admin@nuc-01 docker compose up -d",
        "reboot",
        "shutdown -r now",
        "apt-get install -y caddy",
        "apt upgrade -y",
        "dnf remove -y nginx",
        "pacman -Syu",
        "ufw allow 443/tcp",
        "nft add rule inet filter input tcp dport 22 accept",
        "iptables -A INPUT -p tcp --dport 22 -j ACCEPT",
        "firewall-cmd --add-service=https --permanent",
        "ip link set eth0 down",
        "ip route add 10.0.0.0/24 via 10.0.0.1",
        "nmcli con up lan",
        "wg-quick up wg0",
        "zfs destroy tank/media@old",
        "zpool export tank",
        "lvremove /dev/vg0/old",
        "mkfs.ext4 /dev/sdb1",
        "wipefs -a /dev/sdb",
        "dd if=/dev/zero of=/dev/sdb bs=1M",
        "mount /dev/sdb1 /mnt/backup",
        "rm -rf /srv/media/jellyfin-cache",
        "rm -f /etc/caddy/Caddyfile",
        "chown -R jellyfin:jellyfin /srv/media",
        "qm stop 104",
        "pct destroy 200",
        "virsh shutdown ci-runner",
        "kubectl apply -f deploy.yaml",
        "kubectl rollout restart deployment/jellyfin",
        "helm upgrade --install grafana grafana/grafana",
        "ansible-playbook site.yml",
        "terraform apply",
        "caddy reload --config /etc/caddy/Caddyfile",
        "nginx -s reload",
        "certbot renew",
        "crontab /tmp/new-cron",
        "kill -9 4242",
        "pkill -f jellyfin",
        "useradd -m operator",
        "passwd operator",
        "bash -c 'docker compose up -d'",
        "sh -c \"systemctl restart jellyfin\"",
        "eval \"$CMD\"",
        "docker compose -f \"$(pwd)/docker-compose.yml\" up -d",
        "find /srv -name '*.log' -exec rm {} \\;",
        "ssh nuc-01",
        "sudo -i",
        "docker compose ps && docker compose up -d",
        "echo 'unbalanced",
    )
    NO_DECISION = (
        "git status",
        "git commit -am 'pin jellyfin'",
        "git push origin main",
        "docker compose -f /srv/media/docker-compose.yml ps",
        "docker compose logs --tail 100 jellyfin",
        "docker compose config",
        "docker image ls | grep jellyfin",
        "docker inspect jellyfin",
        "systemctl status jellyfin",
        "systemctl is-active caddy",
        "journalctl -u jellyfin -n 200",
        "apt list --upgradable",
        "dnf check-update",
        "ufw status verbose",
        "nft list ruleset",
        "iptables -L -n",
        "firewall-cmd --list-all",
        "ip addr show",
        "ip route",
        "zfs list -t snapshot",
        "zpool status",
        "lsblk -f",
        "df -h",
        "rm /tmp/scratch.txt",
        "qm list",
        "kubectl get pods -A",
        "kubectl describe deployment jellyfin",
        "ansible-playbook site.yml --check --diff",
        "terraform plan",
        "caddy validate --config /etc/caddy/Caddyfile",
        "nginx -t",
        "certbot certificates",
        "crontab -l",
        "ssh nuc-01 'systemctl status jellyfin'",
        "sudo systemctl status jellyfin",
        "curl -fsS http://localhost:8096/health",
        "dig jellyfin.lan",
        "ps aux | grep jellyfin",
        "cat /srv/media/docker-compose.yml",
        "docker compose logs jellyfin 2>&1 | tail -50",
    )

    def test_live_effects_ask(self) -> None:
        for command in self.ASKS:
            with self.subTest(command=command):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_readers_get_no_decision(self) -> None:
        for command in self.NO_DECISION:
            with self.subTest(command=command):
                self.assertEqual("none", decision(run_gate(bash_call(command))))

    def test_generated_coverage_of_the_whole_roster(self) -> None:
        """Every table entry must drive the classifier; a typo'd or orphaned entry fails here.

        ASKS above is the curated behavioral sample; this test walks the tables themselves so
        that an executable added to a roster without ever being exercised cannot pass silently.
        """
        flag_probe = {
            "rm": "rm -rf /srv/x", "chown": "chown -R a:a /srv/x", "chmod": "chmod -R 755 /srv/x",
            "iptables": "iptables -A INPUT -j DROP", "ip6tables": "ip6tables -F",
            "nginx": "nginx -s reload", "pacman": "pacman -Syu",
            "ansible": "ansible all -m shell -a id", "pihole": "pihole -g",
        }
        for exe in sorted(gate.ALWAYS_LIVE):
            with self.subTest(always=exe):
                self.assertEqual("ask", decision(run_gate(bash_call(f"{exe} x"))))
        for prefix, live in sorted(gate.LIVE_SUBCOMMANDS.items()):
            with self.subTest(prefix=prefix):
                head = " ".join(prefix)
                self.assertEqual("ask", decision(run_gate(bash_call(f"{head} {sorted(live)[0]} x"))))
                self.assertEqual("none", decision(run_gate(bash_call(f"{head} zzz-not-live x"))))
        for exe, reads in sorted(gate.READ_UNLESS.items()):
            with self.subTest(read_unless=exe):
                self.assertEqual("ask", decision(run_gate(bash_call(f"{exe} zzz-live"))))
                self.assertEqual("none", decision(run_gate(bash_call(f"{exe} {sorted(reads)[0]}"))))
        self.assertEqual(set(flag_probe), set(gate.FLAG_LIVE), "every FLAG_LIVE executable needs a probe here")
        for exe, command in sorted(flag_probe.items()):
            with self.subTest(flag=exe):
                self.assertEqual("ask", decision(run_gate(bash_call(command))))

    def test_reason_names_the_matched_rule(self) -> None:
        out = run_gate(bash_call("docker compose -f x.yml up -d web"))
        self.assertIn("matched rule `docker compose up`", reason(out))
        out = run_gate(bash_call("ssh nuc-01 'zfs destroy tank/x'"))
        self.assertIn("matched rule `zfs destroy`", reason(out))
        out = run_gate(bash_call("bash -c 'true'"))
        self.assertIn("cannot bind", reason(out))


if __name__ == "__main__":
    unittest.main()
