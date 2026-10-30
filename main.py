import argparse
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from agent.core import AgriAgent

# Direct all logs strictly to STDERR so STDOUT contains only pure JSON
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# Silence third-party HTTP request logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("groq").setLevel(logging.WARNING)

class AgentHTTPHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/agent":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            query = body.get("query", "Evaluate Trichy Plot #4")
            agent = AgriAgent()
            result = agent.run(query)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    parser = argparse.ArgumentParser(description="AgentX Autonomous Crop Telemetry Agent")
    parser.add_argument("--json", type=str, help="Run single query and print contract JSON to stdout")
    parser.add_argument("--serve", action="store_true", help="Start local HTTP bridge on port 8000 for React UI")
    args = parser.parse_args()

    if args.serve:
        server = HTTPServer(("0.0.0.0", 8000), AgentHTTPHandler)
        sys.stderr.write("[SERVER] AgentX Python Backend listening on http://localhost:8000/api/agent\n")
        server.serve_forever()
        return

    query = args.json if args.json is not None else "Evaluate Trichy Plot #4 (Tomato)"
    try:
        agent = AgriAgent()
        result = agent.run(query)
        payload = {
            "answer": result.get("answer", ""),
            "trace": result.get("trace", [])
        }
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"[FATAL] Graceful fallback triggered: {e}\n")
        fallback = {
            "answer": f"Telemetry diagnostic fallback: unable to complete full cycle ({str(e)}). Check sensor CSV formatting.",
            "trace": [
                {
                    "thought": "Unhandled exception occurred during execution; returning graceful diagnostic.",
                    "tool": "analyze_soil_telemetry",
                    "args": {"query": query},
                    "observation": str(e)
                }
            ]
        }
        sys.stdout.write(json.dumps(fallback) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()