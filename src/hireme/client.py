"""Thin wrapper around the `claude` CLI in headless mode.

We shell out to the local `claude` binary instead of using the Anthropic SDK
directly. This lets us reuse whatever authentication the Claude Code CLI is
already configured with (OAuth, proxy, etc.) — the user does not need a raw
ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ClaudeCLIError(RuntimeError):
    pass


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int

    @classmethod
    def from_envelope(cls, env: dict[str, Any]) -> "Usage":
        u = env.get("usage") or {}
        return cls(
            input_tokens=u.get("input_tokens", 0) or 0,
            output_tokens=u.get("output_tokens", 0) or 0,
            cache_creation_input_tokens=u.get("cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=u.get("cache_read_input_tokens", 0) or 0,
        )

    def summary(self) -> str:
        return (
            f"in={self.input_tokens} out={self.output_tokens} "
            f"cache_write={self.cache_creation_input_tokens} "
            f"cache_read={self.cache_read_input_tokens}"
        )


@dataclass
class Response:
    text: str
    structured: dict[str, Any] | None
    usage: Usage
    raw: dict[str, Any]


class HiremeClient:
    """Invoke the local `claude` CLI in --print mode."""

    def __init__(
        self,
        model: str | None = None,
        claude_bin: str = "claude",
        verbose: bool = False,
    ):
        resolved = shutil.which(claude_bin)
        if not resolved:
            raise ClaudeCLIError(
                f"`{claude_bin}` binary not found on PATH. Install Claude Code first."
            )
        self.claude_bin = resolved
        self.model = model
        self.verbose = verbose

    def call(
        self,
        *,
        system: str,
        prompt: str,
        json_schema: dict[str, Any] | None = None,
        add_dirs: list[Path] | None = None,
        allowed_tools: list[str] | None = None,
        timeout_seconds: int = 300,
    ) -> Response:
        output_format = "stream-json" if self.verbose else "json"
        cmd: list[str] = [
            self.claude_bin,
            "--print",
            "--bare",
            "--output-format", output_format,
            "--permission-mode", "bypassPermissions",
        ]
        if self.verbose:
            cmd.append("--verbose")
        if self.model:
            cmd += ["--model", self.model]
        if json_schema is not None:
            cmd += ["--json-schema", json.dumps(json_schema)]
        if allowed_tools is not None:
            cmd += ["--tools", ",".join(allowed_tools) if allowed_tools else ""]
        if add_dirs:
            cmd += ["--add-dir", *[str(p) for p in add_dirs]]
        cmd += ["--system-prompt", system]
        cmd += ["--", prompt]

        if self.verbose:
            return self._call_streaming(cmd, timeout_seconds)
        return self._call_batched(cmd, timeout_seconds)

    def _call_batched(self, cmd: list[str], timeout_seconds: int) -> Response:
        try:
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise ClaudeCLIError(f"`claude` timed out after {timeout_seconds}s") from e

        if proc.returncode != 0:
            raise ClaudeCLIError(
                f"`claude` exited {proc.returncode}\nstderr:\n{proc.stderr.strip()}"
            )

        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise ClaudeCLIError(
                f"could not parse `claude` JSON output: {e}\nstdout:\n{proc.stdout[:500]}"
            ) from e

        return _envelope_to_response(envelope)

    def _call_streaming(self, cmd: list[str], timeout_seconds: int) -> Response:
        """Run claude with --output-format=stream-json, tee progress to stderr,
        and return the final result event as a Response."""
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge; verbose progress goes here too
            text=True,
        )

        result_event: dict[str, Any] | None = None
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip("\n")
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    # Non-JSON progress noise from bare/verbose — echo to stderr.
                    print(f"    claude: {line}", file=sys.stderr, flush=True)
                    continue
                _echo_stream_event(ev)
                if ev.get("type") == "result":
                    result_event = ev
            proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as e:
            proc.kill()
            raise ClaudeCLIError(f"`claude` timed out after {timeout_seconds}s") from e

        if proc.returncode != 0:
            raise ClaudeCLIError(f"`claude` exited {proc.returncode}")
        if result_event is None:
            raise ClaudeCLIError("`claude` streamed no final result event")

        return _envelope_to_response(result_event)


def _envelope_to_response(envelope: dict[str, Any]) -> Response:
    if envelope.get("is_error"):
        raise ClaudeCLIError(
            f"`claude` reported error: {envelope.get('result') or envelope}"
        )
    return Response(
        text=envelope.get("result") or "",
        structured=envelope.get("structured_output"),
        usage=Usage.from_envelope(envelope),
        raw=envelope,
    )


def _echo_stream_event(ev: dict[str, Any]) -> None:
    """Print a one-line summary of a stream-json event to stderr for progress visibility."""
    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init":
        tools = ",".join(ev.get("tools") or []) or "-"
        print(f"    claude: session start (tools={tools})", file=sys.stderr, flush=True)
    elif t == "assistant":
        msg = ev.get("message") or {}
        for block in msg.get("content") or []:
            btype = block.get("type")
            if btype == "text":
                snippet = (block.get("text") or "").strip().replace("\n", " ")[:80]
                if snippet:
                    print(f"    claude> {snippet}", file=sys.stderr, flush=True)
            elif btype == "tool_use":
                name = block.get("name", "?")
                inp = block.get("input") or {}
                arg = inp.get("file_path") or inp.get("command") or ""
                print(
                    f"    claude> tool_use: {name}({str(arg)[:80]})",
                    file=sys.stderr,
                    flush=True,
                )
    elif t == "user":
        # tool results — usually noisy, keep short
        msg = ev.get("message") or {}
        for block in msg.get("content") or []:
            if block.get("type") == "tool_result":
                content = block.get("content")
                if isinstance(content, list):
                    for sub in content:
                        if isinstance(sub, dict) and sub.get("type") == "text":
                            snippet = (sub.get("text") or "").strip().replace("\n", " ")[:60]
                            print(
                                f"    claude< tool_result: {snippet}",
                                file=sys.stderr,
                                flush=True,
                            )
                            break
    elif t == "result":
        pass  # handled by caller
