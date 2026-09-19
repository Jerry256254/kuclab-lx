"""Agentni smycka: model -> nastroje -> model.

Potvrzeni rizikovych nastroju resi callback `confirm(tool, args) -> bool`,
ktery dodava UI (chat). Daemon posila pozadavek o potvrzeni klientovi.
"""
import llm as llm_mod
import policy as policy_mod
import tools

MAX_ROUNDS = 8

SYSTEM = (
    "Jsi KucLab Agent, cesky (nebo jazykem uzivatele) mluvici asistent v Linuxu KucLab LX. "
    "Odpovidej strucne a jednoduse. Kdyz muzes ukol splnit nastrojem, pouzij ho. "
    "Nebezpecne prikazy (mazani, formatovani, systemove zmeny) vzdy nejprve vysvetli "
    "a pokracuj jen na jasny souhlas. Nikdy neuvadej, ze jsi AI jazykovy model od nejake firmy."
)


class Agent:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.client = llm_mod.LLMClient(cfg)
        custom = (cfg.get("system_prompt") or "").strip()
        self.system = f"{SYSTEM}\n{custom}" if custom else SYSTEM

    def ask(self, history: list, on_token=None, confirm=None) -> dict:
        """Jedno kolo: historie [{role, content}] -> {"text", "actions"}.

        confirm(tool, args) -> True/False; None znamena bez UI (daemon rezim
        potvrzeni resi sam pres klienta).
        """
        pol = policy_mod.load(tools.tool_names())
        messages = [{"role": "system", "content": self.system}] + history
        actions: list[dict] = []
        text = ""
        for _ in range(MAX_ROUNDS):
            result = self.client.chat(messages, tools.tool_schemas(), on_token)
            text = result["text"]
            calls = result["tool_calls"]
            if not calls:
                break
            messages.append({"role": "assistant", "content": text or "", "tool_calls": calls})
            for call in calls:
                name = call["name"]
                args = call["arguments"] or {}
                verdict = policy_mod.check(pol, name)
                if verdict == policy_mod.DENY:
                    output = "Zakazano uzivatelem (policy deny)."
                    allowed = False
                elif verdict == policy_mod.ALLOW:
                    output = tools.run(name, args)
                    allowed = True
                else:
                    ok = confirm(name, args) if confirm else False
                    output = tools.run(name, args) if ok else "Uzivatel nepotvrdil."
                    allowed = bool(ok)
                actions.append({"tool": name, "args": args, "allowed": allowed, "output": output[:2000]})
                messages.append({"role": "tool", "content": output[:4000]})
            on_token = None  # streamujeme jen prvni odpoved
        else:
            text += "\n\n(Pozn.: dosazen limit kroku.)"
        return {"text": text, "actions": actions}
