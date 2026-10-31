"""Closed-book LLM-as-judge baseline on the same 974 clean triples (R2-W7). gemma3 via local Ollama, temperature 0.
Resumable: appends to out/llm_judge_gemma3.csv. Run: python3 -I llm_judge.py"""
import csv, json, pathlib, sys, urllib.request
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
D = HERE.parent / "Datasets" / "intermediate"
OUT = HERE / "out" / "llm_judge_gemma3.csv"; OUT.parent.mkdir(exist_ok=True)
TPL = {"treats": "{s} is used to treat {o}.", "causes": "{s} can cause {o}.", "interacts_with": "{s} interacts with {o}."}
PROMPT = ("You are a careful biomedical fact checker. Using only your own pharmacological knowledge, decide whether "
          "the statement is a true, established fact.\nStatement: {st}\nAnswer with exactly one word: TRUE or FALSE.")


def ask(st):
    body = json.dumps({"model": "gemma3:latest", "prompt": PROMPT.format(st=st), "stream": False,
                       "options": {"temperature": 0, "num_predict": 4}}).encode()
    r = urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"}), timeout=120)
    return json.load(r)["response"].strip()


facts = pd.read_csv(D / "verification_results.csv")[["subject", "predicate", "object", "ground_truth", "category"]]
done = set(pd.read_csv(OUT)["i"]) if OUT.exists() else set()
new = not OUT.exists()
with open(OUT, "a", newline="") as fh:
    w = csv.writer(fh)
    if new: w.writerow(["i", "subject", "predicate", "object", "ground_truth", "category", "raw", "judge_decision"])
    for i, r in facts.iterrows():
        if i in done: continue
        raw = ask(TPL[r.predicate].format(s=r.subject, o=r.object))
        dec = "VERIFIED" if raw.upper().startswith("TRUE") else "HALLUCINATION"
        w.writerow([i, r.subject, r.predicate, r.object, r.ground_truth, r.category, raw, dec]); fh.flush()
        if i % 50 == 0: print(i, raw, flush=True)
