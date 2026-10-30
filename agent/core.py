"""The ReAct loop: Thought -> Action -> Observation -> Decision. Returns answer + trace."""
import json
import re

import config
from agent.prompt_builder import build_system_prompt


def parse_json(text):
    """Pull the first JSON object out of a model reply (handles ```json fences and chatter)."""
    text = re.sub(r"```(?:json)?", "", str(text))
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            depth += text[i] == "{"
            depth -= text[i] == "}"
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break
        start = text.find("{", start + 1)
    return None


class AgentExecutor:
    def __init__(self, llm, tools, role=None, max_iterations=None):
        self.llm, self.tools = llm, tools
        self.max_iterations = max_iterations or config.MAX_ITERATIONS
        self.system = build_system_prompt(tools, **({"role": role} if role else {}))

    def run(self, query, verbose=False):
        messages = [{"role": "user", "content": query}]
        trace, seen, nudged, draft = [], {}, False, None
        for step in range(self.max_iterations):
            force_final = any(n > config.MAX_SAME_TOOL_CALLS for n in seen.values())
            if force_final:
                messages.append({"role": "user", "content": "You repeated a tool. Give your final_answer now."})
            reply = self.llm.generate(self.system, messages)
            data = parse_json(reply)
            if data is None or not (data.get("action") or "final_answer" in data):
                messages += [{"role": "assistant", "content": reply or "(empty)"},
                             {"role": "user", "content": "Invalid format. Reply with ONE JSON object with an \"action\" or a \"final_answer\"."}]
                continue
            thought = str(data.get("thought", ""))
            is_agri = bool(re.search(r'soil|crop|moisture|water|irrigat|fertiliz|npk|nitrogen|phosphor|potassium|urea|dap|ph|weather|rain|tomato|rice|paddy|maize|cotton|banana|groundnut|dose|acre|hectare|field|yield|spray', query, re.I))
            if "final_answer" in data and not trace and not nudged and is_agri:
                nudged = True
                messages += [{"role": "assistant", "content": json.dumps(data)},
                             {"role": "user", "content": "Do not answer from memory. Call get_soil_readings first."}]
                continue
            if "final_answer" in data:
                answer = draft or str(data["final_answer"])
                if verbose:
                    print(f"[Thought] {thought}\n[Final] {answer}")
                return answer, trace
            name, args = data.get("action"), data.get("args") or {}
            key = (name, json.dumps(args, sort_keys=True, default=str))
            seen[key] = seen.get(key, 0) + 1
            observation = self._call_tool(name, args)
            draft = self._dosage_answer(name, observation) or draft
            trace.append({"thought": thought, "tool": name, "args": args, "observation": observation[:2000]})
            if verbose:
                print(f"[Thought] {thought}\n[Action] {name}({args})\n[Observation] {observation[:300]}")
            messages += [{"role": "assistant", "content": json.dumps(data)},
                         {"role": "user", "content": f"OBSERVATION: {observation}"}]
        return draft or self._wrap_up(messages), trace

    @staticmethod
    def _dosage_answer(name, observation):
        """The deterministic pipeline's answer from a calculate_dosage call, if it produced one.
        Returned verbatim as the final answer so the LLM cannot alter doses or mistype the Tamil."""
        if name != "calculate_dosage":
            return None
        try:
            return json.loads(observation).get("answer_draft")
        except (ValueError, AttributeError):
            return None

    def _call_tool(self, name, args):
        tool = self.tools.get(name)
        if tool is None:
            return f"ERROR: unknown tool '{name}'. Available: {', '.join(self.tools)}"
        try:
            return str(tool.execute(**args))
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"

    def _wrap_up(self, messages):
        """Out of steps: ask once for a final answer from what we have."""
        messages.append({"role": "user", "content": "Step limit reached. Reply with a final_answer JSON now."})
        data = parse_json(self.llm.generate(self.system, messages)) or {}
        return str(data.get("final_answer") or "I could not finish within the step limit.")
