"""Fixed phrases said by the character. All of them pass the sentence filter (tested).

Never a failure message (FP5): a wrong answer only gets a neutral "Essaie encore."
"""

WRONG = "Essaie encore."
VISUAL_HINT = "Regarde bien celui-ci."
MODEL = "Regarde, c'est celui-là."
PAUSE_OFFER = "Tu veux faire une pause ?"
SCHEDULED_PAUSE_OFFER = "On peut faire une petite pause."
PAUSE = "C'est la pause."
END_CHILD = "D'accord, on s'arrête, merci et à bientôt !"
END_SILENCE = "On s'arrête là pour aujourd'hui."
END_ADULT = "On s'arrête là pour aujourd'hui."

ALL_FIXED = (WRONG, VISUAL_HINT, MODEL, PAUSE_OFFER, SCHEDULED_PAUSE_OFFER, PAUSE,
             END_CHILD, END_SILENCE)

HELP_LABELS = {
    0: "aucune",
    1: "répéter",
    2: "reformuler",
    3: "indice",
    4: "indice visuel",
    5: "modèle",
}
