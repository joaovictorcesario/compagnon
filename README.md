# Compagnon virtuel intelligent pour enfants autistes — prototype S7

Projet de groupe Polytech Lille (S7, sujet 7). Personnage animé 2D sur l'écran de
l'ordinateur qui propose une activité (reconnaître les couleurs), adapte son aide et réagit
quand l'enfant semble surchargé. Outil **éducatif** : ni diagnostic, ni thérapie.

* **100 % hors ligne** : aucune donnée envoyée ; l'IA tourne sur `127.0.0.1` (toute autre
  adresse est refusée par le code).
* **0 €** : Python, pygame-ce, Piper (voix), Ollama (IA locale), tous gratuits.
* **Interface en français simple**, réponses uniquement par boutons/images.

| Jalon | Contenu | État |
|---|---|---|
| J4 — Démonstrateur V1 | question → réponse par bouton → le personnage parle | `python -m compagnon` |
| J5 — Démonstrateur V2 | l'IA locale reformule et donne des indices, avec filtre | `python -m compagnon --ia ollama` |

---

## 1. Installation sous Windows

Prérequis : **Python 3.12** (python.org, cocher « Add to PATH ») et Git.

```powershell
git clone <url-du-depot-du-groupe> compagnon
cd compagnon
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[voix,dev]"
```

### Voix française (Piper, ~60 Mo, une seule fois)

Le dossier de données est `%APPDATA%\compagnon` (il est créé au premier lancement).

```powershell
python -m piper.download_voices fr_FR-siwis-medium --data-dir "$env:APPDATA\compagnon\voix"
```

Sans voix installée, le compagnon fonctionne quand même (texte + image) et l'indique dans
le terminal. Option `--sans-voix` pour couper la voix volontairement.

### Lancer le démonstrateur V1

```powershell
python -m compagnon --profil enfant1
```

* `--profil` : **pseudonyme** de l'enfant (jamais son vrai nom).
* `--plein-ecran` pour les tests ; `--graine 3` pour rejouer exactement la même suite de
  questions pendant une démonstration.

### Mode accompagnant (adulte)

**Appui long (3 s) sur le petit point discret en haut à droite**, puis code à 4 chiffres.
Code par défaut **1234** : le changer dans *Données → Changer le code* (stocké haché).
3 codes faux → blocage 30 s.

* **Réglages** (FP4) : volume, voix lente/normale, sons, 3 palettes douces, animations,
  taille du texte, activités et ordre, niveau de départ, seuils réussites/erreurs, délai
  avant de répéter la consigne, pause proposée/automatique, intervalle de pause,
  durée d'activité, récompense (étoile, son, image). Pour l'image préférée, déposer des
  `.png`/`.jpg` dans `%APPDATA%\compagnon\recompenses`.
* **Questions** (FP6) : après un moment difficile, « Était-ce une crise ? » et « Cette aide
  a-t-elle marché ? ». Posées **uniquement à l'adulte**.
* **Données** : mettre l'apprentissage en pause, nouvelle séance, changer le code,
  réinitialisation d'usine (efface tout ce qui a été appris, **garde les journaux**),
  supprimer les journaux (bouton séparé), quitter.

---

## 2. Démonstrateur V2 : IA locale

1. Installer **Ollama** pour Windows depuis ollama.com (gratuit). Il écoute sur
   `127.0.0.1:11434`.
2. Télécharger le modèle (une fois, ~1 Go) :
   ```powershell
   ollama pull qwen2.5:1.5b
   ollama pull qwen2.5:0.5b     # plus petit, pour un PC plus lent / le Raspberry Pi
   ```
3. **Benchmark sur VOTRE PC** (latence, taux de timeout, de rejet et de réserve) :
   ```powershell
   python -m compagnon.tools.benchmark_llm --modele qwen2.5:1.5b qwen2.5:0.5b --prompt normal court -n 50 --sortie bench.json
   ```
   Règle du groupe : si le **taux de réserve dépasse ~20 %**, raccourcir le prompt
   (`--prompt court`) ou passer à `qwen2.5:0.5b`. En démonstration, l'IA doit vraiment
   apparaître.
4. Lancer avec la combinaison retenue :
   ```powershell
   python -m compagnon --ia ollama --modele qwen2.5:1.5b --prompt normal
   ```
5. Test d'acceptation V2 (100 reformulations réelles, aucune phrase inadaptée) :
   ```powershell
   $env:COMPAGNON_MODELE="qwen2.5:1.5b"; python -m pytest -m llm -s
   ```

**Fonctionnement** : le modèle ne fait que *formuler* (la couleur cible et les associations
« rouge → fraise, tomate… » viennent du fichier de contenu, l'IA n'invente pas de faits).
Chaque phrase passe par le filtre (`src/compagnon/ai/filter.py`) :

* une seule phrase, **10 mots maximum**, lettres et ponctuation simple ;
* chaque mot appartient au **vocabulaire simple** (`ai/lexique_simple.txt`) + mots de
  l'activité ; élisions (`l'`, `c'est`, `qu'`, `jusqu'à`) et traits d'union
  (`celui-ci`, `touche-le`) découpés avant vérification ;
* accents : normalisation Unicode, apostrophes typographiques ; un mot écrit sans accent
  (`tres`) est accepté **et corrigé** (`très`) seulement s'il correspond à un seul mot du
  lexique ;
* aucun mot interdit (échec, médical, inadapté), même sans accent ; aucune autre couleur
  que la cible ; la reformulation garde la couleur ; l'indice utilise une association prévue.

Si le modèle répond après **1,3 s**, se trompe ou est rejeté → **phrase préparée**
immédiatement (réaction < 2 s garantie). Chaque phrase est journalisée avec sa source
(`llm` ou `reserve`), la latence et la raison du rejet.

---

## 3. Tests et validation

```powershell
python -m pytest            # 72 tests, < 10 s, temps simulé
python -m ruff check src tests
```

Les tests utilisent une **horloge simulée** (`FakeClock`) : « 15 s sans réponse » se teste
sans attendre. Les scénarios du cahier des charges (`tests/test_scenarios.py`) servent
aussi de **script de démonstration** :

| Comportement joué | Ce que le compagnon perçoit | Réaction attendue | Test |
|---|---|---|---|
| L'enfant ne répond pas | rien pendant 15 s | répète la consigne plus simple | `test_s1_…` |
| Activité trop difficile | 3 erreurs de suite | donne un indice, puis facilite | `test_s2_…` |
| L'enfant progresse | 3 réussites sans aide | rend un peu plus difficile | `test_s3_…` |
| Demande de répéter | icône haut-parleur | répète exactement pareil | `test_s4_…` |
| Agitation | > 5 clics en 3 s | propose une pause, coupe les sons, calme l'écran | `test_s5_…` |
| Demande une pause | bouton « Pause » | tout s'arrête, écran calme, reprend au même point | `test_s6_…` |
| Ne veut pas continuer | « J'ai fini » ou rien pendant 60 s | termine calmement, sans message d'échec | `test_s7_…`, `test_s7b_…` |
| L'adulte répond « oui » à « Était-ce une crise ? » | retour en mode accompagnant | la séance suivante propose la pause plus tôt | `test_s8_…` |

**Observateur en direct** pendant un jeu de rôle (dans un 2e terminal) :

```powershell
python -m compagnon.tools.tail_log
```

Affiche chaque événement avec son temps : question, réponse, aide, `IA`/`RES` (source de
la phrase), surcharge, pause… Les journaux sont dans `%APPDATA%\compagnon\journaux\*.jsonl`.

---

## 4. Architecture

```
          ┌──────────── Couche d'affichage (seule partie qui change en S8) ───────────┐
          │ PygameDisplay (S7)        RobotDisplay (S8, à écrire)        FakeDisplay   │
          │ PygameVoice (Piper)       RecordingVoice (tests / --sans-voix)  (tests)    │
          └──────▲ commandes : announce_activity, show_scene, show_reward, │ événements│
                 │ propose_pause, show_pause, set_calm, show_end…          ▼ (Kind.*)  │
┌────────────────┴─────────────────────────────────────────────────────────────────────┐
│                       SessionController (core/controller.py)                         │
│         handle(événement) / tick()  — pur, synchrone, testable sans écran            │
├──────────────┬──────────────┬───────────────┬──────────────────┬─────────────────────┤
│ activities/  │ adaptation/  │ overload/     │ ai/              │ companion/          │
│ couleurs     │ 5 niveaux    │ silence, clics│ Rephraser (stub, │ code, réglages,     │
│ (JSON)       │ d'aide +     │ erreurs, pause│ Ollama) → filtre │ questions à l'adulte│
│              │ difficulté   │ sensibilité   │ → phrases préparées                    │
├──────────────┴──────────────┴───────────────┴──────────────────┴─────────────────────┤
│ child/ profil (niveau, aides efficaces, préférences, sensibilité, pause, reset)      │
│ logs/ journal JSONL     core/clock (RealClock / FakeClock)     perception/ (FP7)     │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

| Module | Rôle | Exigences |
|---|---|---|
| `core/controller.py` | orchestration de la séance | toutes |
| `activities/` + `content/couleurs.json` | activité « couleurs », consignes, associations, phrases préparées | FP1, FC1, FC4 |
| `adaptation/` | niveaux d'aide 1–5 (répéter, reformuler, indice, indice visuel, modèle à 2 choix) ; difficulté = nombre de choix 2/3/4/6 | FP2 |
| `overload/` | seuils de surcharge et leur évolution avec la sensibilité | FP5, FP6 |
| `ai/` | génération locale + filtre + réserve + timeout | FP3 |
| `child/` | mémoire entre séances, questions à l'adulte, pause de l'apprentissage, reset | FP6 |
| `companion/` | logique du mode accompagnant (sans écran) | FP4 |
| `display/` | interface `Display` + version pygame + version de test | FC1–FC3, FC7 |
| `voice/` | interface `Voice` + Piper/pygame | FC2, FC4 |
| `perception/` | point d'extension FP7 (désactivé, rien n'est enregistré) | FP7, FC5 |
| `tools/` | benchmark du modèle, suivi du journal en direct | V2, validation |

### Choix de réglage par défaut (à valider par le groupe)

* Surcharge par **erreurs** : 5 erreurs de suite → pause proposée (3 erreurs déclenchent
  déjà l'indice). Chaque « oui » à « crise » enlève un cran : clics 5→4→3 (min 3),
  erreurs 5→4 (min 4), pause planifiée 3 min → 2 min 30 → … (min 1 min 30).
  Uniquement si l'apprentissage est actif ; le reset d'usine annule tout.
* Pause planifiée proposée toutes les 3 min ; activité de 4 min ou 10 questions.
* « Sons » = effets sonores (récompense) ; la voix suit le volume.
* Le compteur de 60 s pour « termine calmement » part de la dernière action de l'enfant.
* Mauvaise réponse → « Essaie encore. », jamais de message d'échec.

---

## 5. Linux et Raspberry Pi (S8)

Le même code tourne sous Linux. Données dans `~/.local/share/compagnon`.

```bash
sudo apt install python3-venv libsdl2-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[voix,dev]"
python -m piper.download_voices fr_FR-siwis-low --data-dir ~/.local/share/compagnon/voix
python -m compagnon --voix fr_FR-siwis-low --plein-ecran
```

* **Raspberry Pi 4/5 (Raspberry Pi OS 64 bits)** : pygame peut afficher sans bureau
  (`SDL_VIDEODRIVER=kmsdrm`). Voix Piper `low` ou `medium` plus rapides que le temps réel.
* **IA sur le Pi** : `qwen2.5:0.5b` via Ollama (ARM64) ; mesurer avec le benchmark. Si
  le taux de réserve est trop élevé, solution prévue : un générateur « cache » (nouvelle
  classe dans `ai/rephraser.py`) qui lit des reformulations **générées et filtrées à
  l'avance sur le PC**, toujours hors ligne.
* **Robot (FC7)** : écrire `RobotDisplay` qui implémente `display/base.py::Display`
  (visage sur un petit écran, moteur de tête via `gpiozero`, boutons physiques ou écran
  tactile → mêmes `InputEvent`). Le reste du code ne change pas.

---

## 6. Données et confidentialité

* Tout reste dans le dossier de données local (profils, réglages, code haché, journaux,
  cache de voix) ; rien n'est dans git (`.gitignore`).
* Les journaux identifient l'enfant par pseudonyme uniquement.
* Pas de caméra ni de micro en S7. Le point d'extension FP7 exige un traitement en mémoire,
  sans enregistrement.
* Internet n'est utilisé qu'à l'**installation** (pip, voix, modèle).
