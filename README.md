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

> **Membres du groupe (non-programmeurs)** : pas besoin de lire ce qui suit. Télécharger
> le ZIP (bouton vert **Code → Download ZIP**), l'extraire, puis double-cliquer sur
> **`Lancer le compagnon.bat`** (installe tout la première fois, puis lance le jeu).
> Pour modifier le jeu et envoyer ses modifications au groupe, suivre le guide
> **[Pour faire les mods](Pour%20faire%20les%20mods.md)** ; avant chaque envoi,
> double-cliquer sur **`Verifier mes modifications.bat`**.

## 1. Installation sous Windows

Prérequis : **Python 3.12** (python.org, cocher « Add to PATH ») et Git.

```powershell
git clone https://github.com/joaovictorcesario/compagnon.git compagnon
cd compagnon
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[voix,dev]"
```

### Voix française (Piper)

Les deux voix (`fr_FR-siwis-medium`, `fr_FR-upmc-medium`, ~140 Mo) sont **livrées dans
`voix\`** avec le dépôt : rien à télécharger. Pour les retélécharger si besoin :

```powershell
python -m piper.download_voices fr_FR-siwis-medium fr_FR-upmc-medium --data-dir voix
```

Les modèles sont cherchés dans cet ordre : `$env:COMPAGNON_VOIX`,
`%APPDATA%\compagnon\voix`, `<projet>\voix`, `.\voix`. Pour vérifier (affiche où il a
cherché, puis dit une phrase) :

```powershell
python outils\verifier_voix.py
```

> Si la voix a été téléchargée par une application empaquetée (Microsoft Store, certains
> assistants), Windows peut rediriger `%APPDATA%` vers un dossier privé de cette
> application : utiliser alors le dossier `voix\` du projet.

Voix par défaut : **jessica** (calme et naturelle, choisie par le groupe). L'adulte peut en
changer dans le mode accompagnant (*Réglages → Voix*, appliqué à la fermeture), ou pour un
lancement avec `--voix`. Piper n'a pas de voix d'enfant en français : les variantes
« douce »/« enfant » montent la hauteur (sans accélérer le débit).

| Préréglage | Voix | Hauteur |
|---|---|---|
| `jessica` (**défaut**) | fr_FR-upmc-medium (locutrice jessica) | normale |
| `jessica-douce`, `jessica-enfant` | fr_FR-upmc-medium (jessica) | +3 / +5 demi-tons |
| `siwis`, `siwis-douce`, `siwis-enfant` | fr_FR-siwis-medium | 0 / +3 / +5 demi-tons |

Le terminal affiche la voix chargée (`[voix] piper:fr_FR-upmc-medium:jessica:+0`). Sans voix
installée, le compagnon fonctionne quand même (texte + image) et l'indique. Option
`--sans-voix` pour couper la voix volontairement.

### Personnage personnalisé

Le personnage dessiné (« Pipo », formes simples, original) est remplaçable sans toucher au
code : déposer une image par expression dans `%APPDATA%\compagnon\personnage\` (ou
`--personnage <dossier>`) : `neutre.png` (obligatoire), `content.png`, `encourage.png`,
`calme.png`, `ecoute.png` (attend la réponse), et en option `parle.png` (bouche ouverte,
alternée pendant que la voix parle). PNG carré à fond transparent, n'importe quelle taille ;
une expression manquante utilise `neutre.png`. Pas de clignotement : seule une
« respiration » lente et la bouche qui bouge pendant la parole, les deux coupées si les
animations sont désactivées. Code : `compagnon/dessin.py` (partie 4) (interface
`Character`).

### Écrans et design

Accueil (le personnage dit « Bonjour ! » + cartes de jeux) → toucher une carte → le
personnage annonce le jeu et montre l'**emploi du temps visuel** (« D'abord : le jeu »
→ « Ensuite : une récompense » → « Fin », l'étape en cours reste visible en haut à droite
pendant la partie) → jeu → écran de fin (« C'est fini pour aujourd'hui. Bravo ! », étoiles
gagnées, bouton *Menu*). Le petit haut-parleur d'une carte fait dire au personnage à quoi
sert le jeu. Bouton *Maison* discret en haut à gauche du jeu, avec confirmation par
pictogrammes (pas de sortie par erreur).

* **Calme** (FC2) : tous les choix visuels sont des *tokens* dans
  `compagnon/apparence.py` (fond, surface, texte, contour, 3 couleurs d'accent,
  rayons, ombres). Les 3 palettes du mode accompagnant en sont dérivées. Contraste du texte
  ≥ 4,5:1 vérifié par `tests/test_theme.py`. Rien ne clignote ; fondu ≤ 250 ms entre les
  écrans, supprimé quand les animations sont désactivées.
* **Police** : Andika (SIL Open Font License, conçue pour l'apprentissage de la lecture),
  incluse dans `compagnon/polices/` : fonctionne hors ligne.
* **Fenêtre** redimensionnable, tout est mis à l'échelle (canevas logique 1280×720) ;
  **F11** ou `--plein-ecran` pour le plein écran.
* **Ajouter un jeu** : écrire l'activité, puis une entrée dans
  `compagnon/jeux.py` (partie 3) (titre, phrase de description, illustration,
  couleur de carte parmi les accents). La carte apparaît seule, après les cartes existantes.
* **Captures automatiques** de tous les écrans (1280×720 et 1920×1080) :
  ```powershell
  python outils\captures.py
  ```
  Résultat dans `docs/captures/`. Le menu à 4 cartes y utilise des jeux fictifs, jamais
  présents dans l'application.

### Lancer l'application

```powershell
python -m compagnon --profil enfant1
```

* `--profil` : **pseudonyme** de l'enfant (jamais son vrai nom).
* `--plein-ecran` pour les tests ; `--graine 3` pour rejouer exactement la même suite de
  questions pendant une démonstration.

### Mode accompagnant (adulte)

**Appui long (3 s) sur le petit point discret en haut à droite** (sur tous les écrans,
accueil compris), puis code à 4 chiffres.
Code par défaut **1234** : le changer dans *Données → Changer le code* (stocké haché).
3 codes faux → blocage 30 s.

* **Réglages** (FP4) : volume, voix (timbre), débit lent/normal, son de réussite
  (oui/non), 3 palettes douces, animations, taille du texte, niveau de départ, seuils réussites/erreurs, délai avant de répéter la consigne, pause
  proposée/automatique, intervalle de pause, durée d'activité, récompense visuelle (étoile,
  image, aucune). Pour l'image préférée, déposer des `.png`/`.jpg` dans
  `%APPDATA%\compagnon\recompenses`.
* **Bonne réponse** : pas de phrase répétée, mais toujours le même **son doux** (trois notes
  sol-do-mi, timbre de marimba, 1,2 s, volume bas, attaque et fin progressives ; généré
  par `voice/sounds.py`) + la récompense visuelle. Désactivable (*Son de réussite*).
* **Jeux** (FP4) : quels jeux apparaissent sur l'écran d'accueil de l'enfant et dans quel
  ordre (*Affiché/Caché*, *Monter/Descendre*). 4 cartes au maximum, au moins une. Les
  cartes gardent leur place d'une séance à l'autre (FC1).
* **Questions** (FP6) : après un moment difficile, « Était-ce une crise ? » et « Cette aide
  a-t-elle marché ? ». Posées **uniquement à l'adulte**.
* **Données** : mettre l'apprentissage en pause, nouvelle séance (retour à l'accueil), changer le code,
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
   python outils\benchmark_llm.py --modele qwen2.5:1.5b qwen2.5:0.5b --prompt normal court -n 50 --sortie bench.json
   ```
   Règle du groupe : si le **taux de réserve dépasse ~20 %**, raccourcir le prompt
   (`--prompt court`) ou passer à `qwen2.5:0.5b`. En démonstration, l'IA doit vraiment
   apparaître.

   Mesure de référence (portable RTX 2050 4 Go, 100 requêtes, timeout 1,3 s,
   détail dans `docs/benchmark_rtx2050.json`) :

   | Modèle | Prompt | Latence p50 / p95 | IA | Réserve |
   |---|---|---|---|---|
   | **qwen2.5:1.5b** | **normal** | 0,23 s / 0,34 s | **92 %** | **8 %** ✅ |
   | qwen2.5:1.5b | court | 0,22 s / 0,40 s | 67 % | 33 % |
   | qwen2.5:0.5b | normal | 0,25 s / 0,36 s | 41 % | 59 % |
   | qwen2.5:0.5b | court | 0,17 s / 0,30 s | 73 % | 27 % |

   Combinaison retenue : **1.5b + normal**. Exemples de phrases acceptées :
   « Touche l'orange. », « C'est la couleur de l'aubergine. », « Le chocolat est marron. »
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
Chaque phrase passe par le filtre (`compagnon/ia.py`, partie 1) :

* une seule phrase, **10 mots maximum**, lettres et ponctuation simple ;
* chaque mot appartient au **vocabulaire simple** (`ai/lexique_simple.txt`) + mots de
  l'activité ; élisions (`l'`, `c'est`, `qu'`, `jusqu'à`) et traits d'union
  (`celui-ci`, `touche-le`) découpés avant vérification ;
* accents : normalisation Unicode, apostrophes typographiques ; un mot écrit sans accent
  (`tres`) est accepté **et corrigé** (`très`) seulement s'il correspond à un seul mot du
  lexique ;
* aucun mot interdit (échec, médical, inadapté), même sans accent ; aucune autre couleur
  que la cible ; la reformulation garde la couleur ; l'indice utilise une association prévue ;
* qualité (ajoutée après le premier benchmark) : au moins 3 mots, article après « comme »
  (« comme le ciel », pas « comme mer »), élision obligatoire (« l'herbe », pas « la herbe »),
  reformulation différente de la consigne ; un infinitif en tête (« Toucher le rouge. »)
  est mis à l'impératif (« Touche le rouge. »).

Si le modèle répond après **1,3 s**, se trompe ou est rejeté → **phrase préparée**
immédiatement (réaction < 2 s garantie). Chaque phrase est journalisée avec sa source
(`llm` ou `reserve`), la latence et la raison du rejet.

---

## 3. Tests et validation

```powershell
python -m pytest            # 78 tests, < 10 s, temps simulé
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
python outils\tail_log.py
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
│                       SessionController (compagnon/seance.py)                        │
│         handle(événement) / tick()  — pur, synchrone, testable sans écran            │
├──────────────┬──────────────┬───────────────┬──────────────────┬─────────────────────┤
│ jeux.py      │ seance.py    │ enfant.py     │ ia.py            │ adulte.py           │
│ couleurs     │ 5 niveaux    │ silence, clics│ Rephraser (stub, │ code, réglages,     │
│ (JSON)       │ d'aide +     │ erreurs, pause│ Ollama) → filtre │ questions à l'adulte│
│              │ difficulté   │ sensibilité   │ → phrases préparées                    │
├──────────────┴──────────────┴───────────────┴──────────────────┴─────────────────────┤
│ enfant.py profil (niveau, aides efficaces, préférences, sensibilité, pause, reset)   │
│ seance.py journal JSONL  reglages.py (RealClock / FakeClock)   enfant.py (FP7)       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Le code est **à plat** : un fichier par grande partie, chacun commence par un sommaire
(« PARTIE 1, 2… »). Tout le contenu modifiable sans programmer est dans `contenu/`.

| Fichier | Rôle | Exigences |
|---|---|---|
| `compagnon/seance.py` | orchestration de la séance (`SessionController`), niveaux d'aide 1–5 et difficulté 2/3/4/6 choix, journal JSONL, interface `Display` | toutes, FP2 |
| `compagnon/jeux.py` + `contenu/couleurs.json` | contrat `Activity`, activité « couleurs », catalogue des cartes d'accueil | FP1, FC1, FC4 |
| `compagnon/enfant.py` | profil (mémoire entre séances, questions à l'adulte, reset), seuils de surcharge, point d'extension émotion FP7 (désactivé) | FP5, FP6, FP7 |
| `compagnon/ia.py` + `contenu/lexique_simple.txt` | génération locale + filtre + réserve + timeout | FP3 |
| `compagnon/phrases.py` + `contenu/phrases.txt` | phrases fixes du personnage | FP3, FP5 |
| `compagnon/adulte.py` | code, logique et écran du mode accompagnant | FP4 |
| `compagnon/ecran.py`, `dessin.py`, `apparence.py` | écrans pygame, outils de dessin et personnage, jetons de design | FC1–FC3, FC7 |
| `compagnon/voix.py` | interface `Voice` + Piper/pygame, son de réussite | FC2, FC4 |
| `compagnon/reglages.py` | réglages, dossiers de données, horloge, événements | — |
| `outils/` | captures d'écran, benchmark du modèle, suivi du journal, test de la voix | V2, validation |

### Choix de réglage par défaut (à valider par le groupe)

* Surcharge par **erreurs** : 5 erreurs de suite → pause proposée (3 erreurs déclenchent
  déjà l'indice). Chaque « oui » à « crise » enlève un cran : clics 5→4→3 (min 3),
  erreurs 5→4 (min 4), pause planifiée 3 min → 2 min 30 → … (min 1 min 30).
  Uniquement si l'apprentissage est actif ; le reset d'usine annule tout.
* Pause planifiée proposée toutes les 3 min ; activité de 4 min ou 10 questions.
* « Son de réussite » = le son doux de bonne réponse ; la voix suit le volume.
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
  classe dans `compagnon/ia.py`, partie 3) qui lit des reformulations **générées et filtrées à
  l'avance sur le PC**, toujours hors ligne.
* **Robot (FC7)** : écrire `RobotDisplay` qui implémente `compagnon/seance.py::Display`
  (visage sur un petit écran, moteur de tête via `gpiozero`, boutons physiques ou écran
  tactile → mêmes `InputEvent`). Le reste du code ne change pas.

---

## 6. Données et confidentialité

* Tout reste dans le dossier de données local (profils, réglages, code haché, journaux,
  cache de voix) ; rien de cela n'est dans git (`.gitignore`). Seuls les modèles de voix
  (publics) sont livrés dans `voix\`.
* Les journaux identifient l'enfant par pseudonyme uniquement.
* Pas de caméra ni de micro en S7. Le point d'extension FP7 exige un traitement en mémoire,
  sans enregistrement.
* Internet n'est utilisé qu'à l'**installation** (pip, voix, modèle).
