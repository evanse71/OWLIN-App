import os, pathlib
from openai import OpenAI

AGENT_ID = os.getenv("OWLIN_AGENT_ID")  # set this to agt_... when available
ASK = "Generate Owlin SDK for Cursor"
OUT_PATH = pathlib.Path("sdk/owlin_agent_sdk.py")

def extract_first_code_block(text: str) -> str:
    i = text.find("```")
    if i == -1:
        return text
    nl = text.find("\n", i + 3)
    j = text.find("```", nl + 1)
    return text[nl + 1:j] if j != -1 else text

def main():
    if not AGENT_ID:
        raise SystemExit("Set OWLIN_AGENT_ID=agt_... in your env to use this script.")
    client = OpenAI()
    res = client.agents.invoke(AGENT_ID, input=ASK)
    code = extract_first_code_block(res.output_text or "")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(code, encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(code)} bytes)")

if __name__ == "__main__":
    main()

# ---- optional smoke test (requires FastAPI on :8000) ----
if False:  # set to True to run smoke test
    import importlib.util, sys
    p = "sdk/owlin_agent_sdk.py"
    spec = importlib.util.spec_from_file_location("owlin_sdk", p)
    mod = importlib.util.module_from_spec(spec); sys.modules["owlin_sdk"] = mod
    spec.loader.exec_module(mod)
    sdk = mod.OwlinAgentSDK("http://127.0.0.1:8000")
    print("health:", sdk.health())
    print("invoices:", sdk.list_invoices()[:2])
