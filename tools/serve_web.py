#!/usr/bin/env python3
"""Serve the web export locally.

    tools/serve_web.py            # http://127.0.0.1:8060
    tools/serve_web.py 9000

`python -m http.server` cannot serve this build. The Web Demo preset sets
`variant/thread_support=true`, so the engine uses SharedArrayBuffer, and every
browser gates that behind **cross-origin isolation** — the page must be served
with both COOP and COEP or it fails at startup with a bare
"SharedArrayBuffer is not defined". Those two headers are the whole reason this
file exists; everything else here is the stdlib doing its job.

Bound to 127.0.0.1 deliberately, not 0.0.0.0. Cross-origin isolation needs a
secure context, and browsers grant that to `localhost` and `127.0.0.1` but not
to a LAN address — so binding wider would not make phone testing work, it would
only publish the build.

Build first, from the repo root:

    tools/export.sh web
"""

from __future__ import annotations

import functools
import http.server
import pathlib
import sys
from typing import ClassVar

ROOT = pathlib.Path(__file__).resolve().parent.parent / "build" / "web"
DEFAULT_PORT = 8060


class Handler(http.server.SimpleHTTPRequestHandler):
    # `.wasm` is the one that matters: `WebAssembly.instantiateStreaming`
    # rejects any other content type, and `mimetypes` consults /etc/mime.types
    # and the Windows registry, so it is not dependable across machines.
    extensions_map: ClassVar[dict[str, str]] = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",
    }

    def end_headers(self) -> None:
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        # `no-cache`, not `no-store`: the goal is that a rebuilt .pck can never
        # be served beside a cached .wasm, and mandatory revalidation achieves
        # that — `send_head` already answers If-Modified-Since with a 304.
        # `no-store` would also forbid revalidation, re-transferring all 89 MB
        # on every reload to buy nothing.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("  %s\n" % (fmt % args))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not (ROOT / "index.html").exists():
        print(f"No build at {ROOT}. Run: tools/export.sh web", file=sys.stderr)
        return 1

    try:
        port = int(args[0]) if args else DEFAULT_PORT
    except ValueError:
        print(f"port must be a number, got {args[0]!r}", file=sys.stderr)
        return 2

    handler = functools.partial(Handler, directory=str(ROOT))
    try:
        # Threading is not an optimisation here. A single-threaded server
        # serves one connection to completion before accepting the next, and
        # Chrome opens speculative sockets that send nothing — one of those
        # stalls the whole page until it times out. The engine also fetches
        # `index.js` once per pthread worker, nine times in parallel.
        with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
            print(f"serving {ROOT} at http://127.0.0.1:{port}  (ctrl-c to stop)")
            server.serve_forever()
    except OSError as error:
        print(f"cannot serve on port {port}: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
