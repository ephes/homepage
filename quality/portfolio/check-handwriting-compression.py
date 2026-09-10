"""Exercise the production storage/WhiteNoise contract in an isolated temporary root.

Run with the deployment interpreter; --require-brotli fails if its optional encoder
is missing. No project settings, credentials, database, or deployed hosting required.
"""

import argparse
import gzip
import json
from pathlib import Path
import shutil
import tempfile
from wsgiref.util import setup_testing_defaults

from django.conf import settings
from whitenoise import WhiteNoise
from whitenoise.compress import brotli_installed
from whitenoise.storage import CompressedManifestStaticFilesStorage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-brotli", action="store_true")
    args = parser.parse_args()
    prototype = Path(__file__).resolve().parents[2] / "docs/superpowers/prototypes"
    report = {"brotli_encoder_installed": brotli_installed, "assets": {}}
    with tempfile.TemporaryDirectory(
        prefix="portfolio-handwriting-static-"
    ) as directory:
        settings.configure(STATIC_URL="/static/", STATIC_ROOT=directory)
        storage = CompressedManifestStaticFilesStorage(location=directory)
        filenames = ("handwriting-glyphs.js", "handwriting-contact.js")
        for filename in filenames:
            shutil.copyfile(prototype / filename, Path(directory) / filename)
        for _, _, result in storage.post_process(
            {name: (storage, name) for name in filenames}
        ):
            if isinstance(result, Exception):
                raise result

        def fallback(environ, start_response):
            start_response("404 Not Found", [])
            return [b""]

        application = WhiteNoise(fallback, root=directory, prefix="static/")
        for filename in filenames:
            hashed = storage.hashed_files[filename]
            original = (Path(directory) / hashed).read_bytes()
            asset = {"hashed_name": hashed, "raw": len(original), "responses": {}}
            for accept, expected in (
                ("identity", None),
                ("gzip", "gzip"),
                ("br, gzip", "br" if brotli_installed else "gzip"),
            ):
                environ = {}
                setup_testing_defaults(environ)
                environ.update(
                    PATH_INFO=f"/static/{hashed}", HTTP_ACCEPT_ENCODING=accept
                )
                response = {}

                def start_response(status, headers):
                    response.update(status=status, headers=dict(headers))

                body = application(environ, start_response)
                try:
                    payload = b"".join(body)
                finally:
                    if hasattr(body, "close"):
                        body.close()
                headers = response["headers"]
                assert response["status"].startswith("200"), response
                assert headers.get("Content-Encoding") == expected, response
                assert "Accept-Encoding" in headers.get("Vary", ""), response
                assert int(headers["Content-Length"]) == len(payload), response
                if expected == "gzip":
                    decoded = gzip.decompress(payload)
                elif expected == "br":
                    import brotli

                    decoded = brotli.decompress(payload)
                else:
                    decoded = payload
                assert decoded == original, "Content encoding must preserve every byte"
                asset["responses"][accept] = {
                    "encoding": expected,
                    "bytes": len(payload),
                    "vary": headers["Vary"],
                }
            report["assets"][filename] = asset
    print(json.dumps(report, indent=2))
    if args.require_brotli and not brotli_installed:
        parser.exit(
            1,
            "Brotli generation unavailable: install the WhiteNoise brotli extra in the deployment build environment.\n",
        )


if __name__ == "__main__":
    main()
