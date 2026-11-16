"""Prompts for the local model. Two styles: "normal" and "court" (shorter, for slow CPUs).

The model only PHRASES things: the target colour and the associations ("une fraise",
"le ciel"...) come from the activity content, so a hint is never an invented fact.
Small models follow complete example sentences much better than rules, so each prompt
shows examples built with the SAME colour (another colour would leak into the answer)
and asks for one association drawn at random (variety).

Benchmark on RTX 2050 (2026-11-16): with rule-only prompts the 1.5b model wrote
"Bleu comme mer." / "Comme lavande." -> replaced by these few-shot prompts.
"""

from __future__ import annotations

import random

SYSTEM = {
    "normal": ("Tu aides un enfant de 6 ans à reconnaître les couleurs. Tu écris UNE phrase "
               "courte et correcte, en français très simple, avec les petits mots "
               "(le, la, un, une). Pas de guillemets, pas d'emoji."),
    "court": "Une phrase courte et correcte, français très simple, avec le, la, un, une.",
}


def _le(cible: str) -> str:
    return "l'" if cible[0] in "aeiouyéè" else "le "


def build_prompt(style: str, kind: str, ctx: dict, rng: random.Random) -> tuple[str, str]:
    """Returns (system, prompt)."""
    style = style if style in SYSTEM else "normal"
    cible = ctx["cible"]
    Cible = cible.capitalize()
    le = _le(cible)
    assoc = list(ctx.get("associations", [])) or [cible]
    if kind == "simplifier":
        # The full instruction is NOT shown: the 1.5b model then copied it without the
        # colour ("Touche le ballon.") in 1 answer out of 5.
        if style == "court":
            prompt = (f"Exemple : Touche {le}{cible}.\n"
                      f"Autre phrase pour toucher le {cible}, avec le mot « {cible} » :")
        else:
            # The model sometimes answers with the infinitive ("Toucher le rouge."):
            # clean_llm_output turns it into "Touche le rouge.". A wording without
            # "toucher" was tried and gave twice as many rejects (echoed the prompt).
            prompt = (
                f"Dis à l'enfant de toucher la couleur {cible}, en 3 à 6 mots. "
                f"Le mot « {cible} » doit être dans la phrase.\n"
                "Exemples :\n"
                f"Touche {le}{cible}.\n"
                f"Où est le ballon {cible} ?\n"
                f"Montre-moi {le}{cible}.\n"
                f"Ta phrase avec « {cible} » :"
            )
    elif kind == "indice":
        mot = rng.choice(assoc)
        others = [a for a in assoc if a != mot] or assoc
        ex1, ex2 = others[0], others[-1]
        if style == "court":
            prompt = (f"Exemple : {Cible} comme {ex1}.\n"
                      f"Même chose avec « {mot} » :")
        else:
            prompt = (
                f"Écris un petit indice pour trouver la couleur {cible}, avec « {mot} ».\n"
                "Exemples :\n"
                f"{Cible} comme {ex1}.\n"
                f"C'est la couleur de {ex2}.\n"
                f"Avec « {mot} » :"
            )
    else:
        raise ValueError(f"type inconnu : {kind}")
    return SYSTEM[style], prompt
