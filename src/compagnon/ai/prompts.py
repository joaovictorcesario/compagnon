"""Prompts for the local model. Two styles: "normal" and "court" (shorter, faster).

The model only PHRASES things: the target colour and the associations come from the
activity content, so a hint is never an invented fact.
"""

from __future__ import annotations

import random

SYSTEM = {
    "normal": ("Tu parles à un enfant de 6 ans, en français très simple. "
               "Tu réponds par une seule phrase courte, sans guillemets, sans emoji."),
    "court": "Réponds en français très simple, une seule phrase courte.",
}


def build_prompt(style: str, kind: str, ctx: dict, rng: random.Random) -> tuple[str, str]:
    """Returns (system, prompt)."""
    style = style if style in SYSTEM else "normal"
    cible = ctx["cible"]
    assoc = list(ctx.get("associations", []))
    if kind == "simplifier":
        if style == "court":
            prompt = f"Consigne plus simple avec le mot « {cible} », 6 mots maximum :"
        else:
            prompt = (
                f"Dis cette consigne plus simplement : « {ctx['consigne']} »\n"
                f"Garde le mot « {cible} ». 8 mots maximum. Pas d'autre couleur.\n"
                f"Exemple : Touche le {cible}.\n"
                "Phrase :"
            )
    elif kind == "indice":
        if style == "court":
            mot = rng.choice(assoc) if assoc else cible
            prompt = (f"Petit indice pour la couleur {cible}, avec le mot « {mot} », "
                      "6 mots maximum :")
        else:
            exemple = assoc[-1] if assoc else cible
            prompt = (
                f"Donne un petit indice pour trouver la couleur {cible}.\n"
                f"Utilise un de ces mots : {', '.join(assoc)}.\n"
                "Ne dis aucune autre couleur. 8 mots maximum.\n"
                f"Exemple : {cible.capitalize()} comme {exemple}.\n"
                "Indice :"
            )
    else:
        raise ValueError(f"type inconnu : {kind}")
    return SYSTEM[style], prompt
