# Pour faire les mods

Guide pour **les membres du groupe**, écrit pour des personnes qui ne savent pas
programmer. On n'a besoin d'**aucune ligne de commande** : tout se fait avec des
logiciels à fenêtres et des doubles-clics.

> **En bref**
> 1. Pour **jouer** : télécharger le ZIP, double-cliquer sur `Lancer le compagnon.bat`.
> 2. Pour **modifier** : installer GitHub Desktop + VS Code, accepter l'invitation de
>    João sur GitHub, « cloner » le projet une fois.
> 3. À chaque séance de travail : **Pull** → modifier → tester → **Vérifier** →
>    **Commit** → **Push**.
> 4. **Tout ce qu'on peut changer sans programmer est dans le dossier `contenu/`**
>    (phrases, couleurs du jeu, mots, dessins du personnage). Le programme est dans
>    `compagnon/` : un fichier par grande partie du jeu. Voir le
>    [plan du projet](#5-le-plan-du-projet) et les [recettes](#6-recettes--que-modifier-et-où).

---

## Sommaire

1. [Juste jouer (sans rien modifier)](#1-juste-jouer-sans-rien-modifier)
2. [Installer les outils pour modifier (une seule fois)](#2-installer-les-outils-pour-modifier-une-seule-fois)
3. [Récupérer le projet sur son ordinateur (une seule fois)](#3-récupérer-le-projet-sur-son-ordinateur-une-seule-fois)
4. [La routine de travail (à chaque fois)](#4-la-routine-de-travail-à-chaque-fois)
5. [Le plan du projet](#5-le-plan-du-projet)
6. [Recettes : que modifier, et où](#6-recettes--que-modifier-et-où)
7. [Voir tous les écrans sans jouer](#7-voir-tous-les-écrans-sans-jouer)
8. [En cas de problème](#8-en-cas-de-problème)
9. [Petit lexique](#9-petit-lexique)

---

## 1. Juste jouer (sans rien modifier)

1. Ouvrir <https://github.com/joaovictorcesario/compagnon>.
2. Cliquer sur le bouton vert **`<> Code`**, puis **Download ZIP** (environ 140 Mo : la
   voix française est déjà dedans).
3. Dans le dossier *Téléchargements*, faire un clic droit sur `compagnon-main.zip` →
   **Extraire tout…** → **Extraire**.
   ⚠️ Il faut extraire : ça ne marche pas si on lance depuis l'intérieur du ZIP.
4. Dans le dossier extrait, **double-cliquer sur `Lancer le compagnon.bat`**.

**La première fois**, une fenêtre noire s'ouvre et installe tout toute seule
(environ 2 minutes, il faut Internet) :

| Message affiché | Ce qui se passe |
|---|---|
| `[1/3] Preparation de Python pour le projet` | prépare un Python rien que pour le projet |
| `[2/3] Installation des bibliotheques` | télécharge les « briques » du jeu (affichage, voix…) |

La voix, elle, est **déjà incluse** dans le dossier `voix` : rien à télécharger.

Puis le compagnon s'ouvre. **Les fois suivantes**, il s'ouvre tout de suite, et il
fonctionne **sans Internet**.

**Si Python n'est pas installé**, la fenêtre le dit et propose de l'installer
(répondre `O` pour oui). Sinon, une page s'ouvre : télécharger **Python 3.12**, et
pendant l'installation **cocher la case « Add python.exe to PATH »**. Ensuite, relancer
`Lancer le compagnon.bat`.

**Si Windows affiche « Windows a protégé votre ordinateur »** : cliquer sur
**Informations complémentaires** → **Exécuter quand même**. C'est normal pour un fichier
téléchargé depuis Internet.

Pendant le jeu :

* **Mode adulte** : rester appuyé 3 secondes sur le petit point gris en haut à droite,
  code **1234**.
* **Plein écran** : touche **F11**.
* **Ne pas fermer la fenêtre noire** tant que le jeu est ouvert : c'est elle qui le fait
  tourner.

> 💡 **L'IA (version V2)** est facultative. Pour l'avoir : installer Ollama
> (<https://ollama.com>), puis, dans le menu Démarrer, ouvrir « Invite de commandes » et
> taper une seule fois `ollama pull qwen2.5:1.5b`. Ensuite `Lancer le compagnon.bat`
> l'utilise tout seul. Sans Ollama, le jeu marche avec ses phrases préparées.

---

## 2. Installer les outils pour modifier (une seule fois)

Pour modifier le jeu **et envoyer ses modifications à tout le groupe**, on travaille
tous directement sur le dépôt GitHub de João. Il faut trois logiciels gratuits et un
compte.

| Quoi | Où | À quoi ça sert |
|---|---|---|
| **Compte GitHub** | <https://github.com/signup> | pour avoir le droit de modifier le dépôt |
| **GitHub Desktop** | <https://desktop.github.com> | récupérer et envoyer les modifications, avec des boutons |
| **Visual Studio Code** (VS Code) | <https://code.visualstudio.com> | ouvrir et modifier les fichiers |
| **Python 3.12** | <https://www.python.org/downloads/windows/> | faire tourner le jeu (cocher « Add python.exe to PATH ») |

Python n'est pas obligatoire à cette étape : `Lancer le compagnon.bat` propose de
l'installer s'il manque.

### Avoir le droit de modifier le dépôt

1. Chaque membre **envoie son nom d'utilisateur GitHub à João**.
2. João va sur la page du dépôt → **Settings** → **Collaborators** → **Add people** →
   tape le nom → **Add**.
3. Le membre reçoit un **e-mail d'invitation** (ou une notification sur github.com) et
   clique sur **Accept invitation**.

C'est fait : tout le monde peut maintenant modifier le même dépôt.

---

## 3. Récupérer le projet sur son ordinateur (une seule fois)

1. Ouvrir **GitHub Desktop** et se connecter avec son compte GitHub
   (*File → Options → Accounts → Sign in*).
2. **File → Clone repository…** → onglet **GitHub.com** → choisir
   `joaovictorcesario/compagnon`.
3. **Local path** : choisir où mettre le dossier (par exemple `Documents\GitHub`), puis
   **Clone**.
4. Pour ouvrir le dossier : **Repository → Show in Explorer**.
5. Dans ce dossier, double-cliquer sur **`Lancer le compagnon.bat`** une première fois
   (il installe tout, comme dans la partie 1).
6. Pour ouvrir les fichiers dans VS Code : **Repository → Open in Visual Studio Code**.

> ⚠️ Ne pas travailler dans un dossier « ZIP » téléchargé : il n'est pas relié à GitHub,
> et vos modifications ne pourraient pas être envoyées.

---

## 4. La routine de travail (à chaque fois)

C'est **la partie la plus importante**. Si tout le monde suit ces 7 étapes, on ne se
marche jamais dessus.

| # | Étape | Où | Comment |
|---|---|---|---|
| 1 | **Récupérer** le travail des autres | GitHub Desktop | bouton en haut **Fetch origin**, puis **Pull origin** s'il apparaît |
| 2 | **Prévenir** le groupe | message au groupe | « Je modifie les phrases du personnage » (pour ne pas être deux sur le même fichier) |
| 3 | **Modifier** | VS Code | ouvrir le fichier, changer, **Ctrl + S** pour enregistrer |
| 4 | **Essayer** | double-clic | `Lancer le compagnon.bat` : regarder si le changement marche |
| 5 | **Vérifier** | double-clic | `Verifier mes modifications.bat` : il doit afficher **TOUT EST BON** |
| 6 | **Enregistrer dans l'historique** (*commit*) | GitHub Desktop | en bas à gauche, écrire un résumé (ex. « Phrase de pause plus douce »), puis **Commit to main** |
| 7 | **Envoyer** au groupe (*push*) | GitHub Desktop | bouton en haut **Push origin** |

Dans GitHub Desktop, la colonne de gauche (**Changes**) montre **tous les fichiers que
vous avez modifiés**, et à droite, en rouge ce qui a été enlevé, en vert ce qui a été
ajouté. C'est le bon endroit pour relire avant d'envoyer.

**Les règles d'or :**

* ✅ Toujours **Pull avant** de commencer, et **Push juste après** avoir fini.
* ✅ **Petites modifications** : une idée = un commit.
* ✅ **Ne jamais envoyer** si `Verifier mes modifications.bat` dit **ATTENTION**.
* ✅ Un seul membre à la fois sur un même fichier (d'où l'étape 2).
* ❌ Ne pas renommer ni déplacer de fichiers ou de dossiers sans en parler au groupe.

---

## 5. Le plan du projet

Légende : 🟢 facile, à modifier librement · 🟠 possible, avec précaution ·
🔴 ne pas toucher sans en parler (c'est de la programmation).

```
compagnon/  (le dossier du projet)
│
├── Lancer le compagnon.bat          ← double-clic : jouer
├── Verifier mes modifications.bat   ← double-clic : vérifier avant d'envoyer
├── Pour faire les mods.md           ← ce guide
├── README.md                        ← documentation technique (pour le rapport)
│
├── contenu/          🟢 TOUT CE QU'ON PEUT CHANGER SANS PROGRAMMER
│   ├── phrases.txt          les phrases dites par le personnage
│   ├── couleurs.json        le jeu des couleurs : consignes, couleurs, indices
│   ├── lexique_simple.txt   les mots simples autorisés
│   └── personnage/          (à créer) vos dessins du personnage
│
├── compagnon/        le programme : un fichier par grande partie du jeu
│   ├── apparence.py   🟢 couleurs de l'écran, taille du texte
│   ├── ecran.py       🟠 les écrans de l'enfant (« Bonjour ! », boutons…)
│   ├── jeux.py        🟠 les jeux et les cartes de l'écran d'accueil
│   ├── voix.py        🟠 la voix et le son de bonne réponse
│   ├── reglages.py    🟠 les réglages par défaut
│   ├── ia.py          🟠 l'IA et les mots interdits
│   ├── seance.py      🔴 le déroulement d'une séance (le « cerveau »)
│   ├── enfant.py      🔴 le profil de l'enfant, les signes de surcharge
│   ├── adulte.py      🔴 le mode adulte et son écran
│   ├── dessin.py      🔴 les outils de dessin et le personnage dessiné
│   ├── phrases.py     🔴 lit contenu/phrases.txt
│   ├── app.py         🔴 démarre tout
│   └── polices/       la police d'écriture (Andika)
│
├── voix/             la voix française (déjà incluse, ne pas toucher)
├── tests/            🔴 les vérifications automatiques
├── outils/           petits programmes pour l'équipe (captures d'écran…)
└── docs/             images de tous les écrans, résultats des mesures
```

**Pour avoir une vue d'ensemble :** chaque fichier de `compagnon/` commence par un
**sommaire** (« Sommaire : 1. … 2. … »). Chaque partie est marquée dans le fichier par
`PARTIE 1`, `PARTIE 2`… : avec **Ctrl + F** on y va directement.

Le chemin d'une séance, du clic au son :

```
app.py  →  ecran.py   l'accueil : l'enfant touche une carte
        →  seance.py  choisit la question, juge la réponse, décide de l'aide
             ├── jeux.py    les couleurs, lues dans contenu/couleurs.json
             ├── ia.py      reformule la phrase, si l'IA est installée
             ├── voix.py    dit la phrase
             └── enfant.py  retient ce qui aide l'enfant
        →  ecran.py   affiche la question, les ballons, le personnage
```

---

## 6. Recettes : que modifier, et où

Pour trouver un texte n'importe où dans le projet : dans VS Code, **Ctrl + Maj + F**,
puis taper le texte cherché. VS Code montre tous les fichiers où il apparaît.

Quelques règles d'écriture, valables dans les fichiers `.py` et `.json` :

* Les textes sont **entre guillemets droits** `"comme ceci"`. Il ne faut jamais
  effacer les guillemets.
* Les apostrophes **à l'intérieur** du texte ne posent pas de problème :
  `"C'est la pause."` est correct.
* Après une modification : **Ctrl + S** (sinon rien n'est enregistré ; un point blanc
  sur l'onglet du fichier veut dire « pas enregistré »).

### 6.1 🟢 Les phrases du personnage

**Fichier :** `contenu/phrases.txt`

C'est un simple fichier texte. Chaque phrase est sur une ligne, avec une explication
au-dessus (les lignes qui commencent par `#`) :

```
# Après une mauvaise réponse
WRONG = Essaie encore.

# Pendant la pause
PAUSE = C'est la pause.
```

On change **seulement le texte après le signe `=`**, sans guillemets. On ne touche pas au
nom en majuscules à gauche : c'est grâce à lui que le jeu sait quand dire la phrase.

**Exemple :** `PAUSE = C'est la pause.` → `PAUSE = On se repose un peu.`

⚠️ Chaque phrase est vérifiée automatiquement (cahier des charges FP3/FP5) :

* **une seule phrase**, **10 mots maximum** ;
* des **mots simples** : ils doivent se trouver dans `contenu/lexique_simple.txt` (voir 6.3) ;
* **jamais de mot d'échec** (faux, raté, nul, erreur…) ni de mot médical.

Si une règle n'est pas respectée, `Verifier mes modifications.bat` affiche **ATTENTION**.

La voix est générée automatiquement pour la nouvelle phrase. La toute première fois,
elle peut mettre une seconde de plus.

### 6.2 🟢 Le jeu des couleurs

**Fichier :** `contenu/couleurs.json`

Ce fichier décrit tout le jeu. Il contient une partie **niveaux**, puis une partie par
**couleur** :

```json
{
  "id": "rouge", "nom": "rouge", "formes": ["rouge", "rouges"], "rgb": [214, 69, 65],
  "associations": ["une fraise", "une tomate", "une cerise", "une coccinelle", "les pompiers"],
  "consigne": "Touche le ballon rouge.",
  "reserve_simplifier": ["Touche le rouge.", "Montre le ballon rouge."],
  "reserve_indice": ["Rouge comme une fraise.", "C'est la couleur des tomates."]
}
```

| Champ | Ce que c'est | Peut-on le changer ? |
|---|---|---|
| `id` | nom interne de la couleur | 🔴 non (sauf pour une nouvelle couleur) |
| `nom` | le mot dit à l'enfant | 🟠 rarement |
| `formes` | toutes les façons d'écrire la couleur (masculin, féminin, pluriel) | 🟢 compléter si besoin |
| `rgb` | la couleur du ballon, en Rouge-Vert-Bleu (de 0 à 255) | 🟢 oui (voir 6.5 pour trouver les nombres) |
| `associations` | les objets de cette couleur, **avec leur article** (« une fraise ») ; l'IA s'en sert pour les indices | 🟢 oui |
| `consigne` | la phrase de la question | 🟢 oui |
| `reserve_simplifier` | phrases plus simples, utilisées si l'IA ne répond pas | 🟢 oui |
| `reserve_indice` | indices tout prêts, utilisés si l'IA ne répond pas | 🟢 oui |

**Les niveaux** (en haut du fichier) :

```json
"1": {"choix": 2, "couleurs": ["rouge", "bleu", "jaune", "vert"]},
```

* `choix` = **nombre de ballons** affichés à ce niveau ;
* `couleurs` = les couleurs qui peuvent apparaître à ce niveau.

**Ajouter une couleur** (exemple : blanc) :

1. Copier tout un bloc de couleur, de `{` à `}`, et le coller après le dernier bloc.
2. Mettre une **virgule** entre le bloc précédent et le nouveau.
3. Changer `id`, `nom`, `formes`, `rgb`, `associations`, `consigne` et les phrases.
4. Ajouter `"blanc"` dans la liste `couleurs` d'au moins un niveau.

⚠️ **Le format JSON est strict** :

* chaque texte entre **guillemets droits** `"` ;
* une **virgule entre deux éléments**, mais **pas de virgule après le dernier** ;
* chaque `{` a son `}` et chaque `[` a son `]`.

VS Code **souligne en rouge** les erreurs de format : s'il y a du rouge, il y a une faute
juste avant.

### 6.3 🟢 Les mots autorisés pour l'IA

**Fichier :** `contenu/lexique_simple.txt`

C'est la liste des mots simples que l'IA (et les phrases préparées) ont le droit
d'utiliser. Si `Verifier mes modifications.bat` refuse une phrase à cause d'un
`mot_inconnu`, il suffit d'**ajouter le mot** ici :

* les mots sont **séparés par des espaces**, en **minuscules**, **avec les accents** ;
* on peut en mettre plusieurs par ligne ;
* une ligne qui commence par `#` est un commentaire (ignoré).

Les **mots interdits** (échec, médical, grossier) sont dans `compagnon/ia.py`
(partie 1), dans la liste `FORBIDDEN` (🟠 : on peut **ajouter** un mot interdit entre guillemets,
suivi d'une virgule, mais ne jamais en retirer sans en parler).

### 6.4 🟠 Les textes des écrans

**Fichier :** `compagnon/ecran.py`

| Texte à l'écran | Ce qu'il faut chercher (Ctrl + F) |
|---|---|
| « Bonjour ! » (accueil) | `GREETING =` |
| « C'est fini pour aujourd'hui. Bravo ! » | `END_TITLE =` |
| Boutons « Aide », « Pause », « J'ai fini » | `("Aide"` |
| « On retourne au menu ? » | `On retourne` |
| « D'abord » / « le jeu » / « Ensuite » / « une récompense » / « Fin » | `D'abord` |
| « Reprendre », « Continuer », « Menu » | le mot lui-même |

On ne change que le texte entre guillemets. Les phrases **dites** par le personnage
sont dans `contenu/phrases.txt` (6.1), pas ici.

### 6.5 🟢 Les couleurs de l'écran

**Fichier :** `compagnon/apparence.py`, partie `PALETTES`

Il y a trois palettes (`sable`, `ciel`, `menthe`) : l'adulte choisit dans le mode
accompagnant. Chaque couleur est écrite `(Rouge, Vert, Bleu)` avec des nombres de
0 à 255 :

| Nom | Où on le voit |
|---|---|
| `bg` | le fond de l'écran |
| `surface` | les cartes, les bulles |
| `accent1` / `accent2` / `accent3` | bouton Aide (bleu) / Pause (jaune) / J'ai fini (vert), et les cartes de jeux |
| `char`, `char_shade`, `cheek`, `leaf` | le personnage : corps, ombre, joues, feuille |
| `text`, `text_soft` | le texte |

**Pour trouver les nombres d'une couleur :** aller sur
<https://htmlcolorcodes.com/fr/>, choisir la couleur, et recopier les trois nombres
**RGB** : `rgb(205, 225, 244)` s'écrit `(205, 225, 244)`.

⚠️ Pour les enfants autistes, il faut des couleurs **douces** (pastel), jamais vives.
`Verifier mes modifications.bat` contrôle que le **texte reste lisible** (contraste
suffisant) : si vous foncez trop un fond, il affichera ATTENTION.

### 6.6 🟢 La taille du texte

**Fichier :** `compagnon/apparence.py`, partie `FONT_SIZES`

```python
"moyen": (36, 30, 38),   # (consigne, boutons, titres)
```

L'adulte choisit déjà petit / moyen / grand dans le mode accompagnant. On ne change ces
nombres que si les trois tailles sont toutes trop petites ou trop grandes.

### 6.7 🟢 Remplacer le personnage par vos dessins

**Pas besoin de toucher au code.**

1. Dessiner le personnage avec un logiciel gratuit (Krita, GIMP, Canva…).
   ⚠️ Un personnage **original**, pas un personnage connu (dessin animé, jeu…).
2. Exporter une image **PNG carrée, fond transparent**, au moins **512 × 512 pixels**,
   pour chaque expression :

   | Fichier | Quand on la voit |
   |---|---|
   | `neutre.png` (**obligatoire**) | souriant, au calme |
   | `content.png` | bonne réponse, annonce du jeu |
   | `encourage.png` | aide, après une erreur (« Essaie encore ») |
   | `calme.png` | pause (yeux fermés, détendu) |
   | `ecoute.png` | attend la réponse de l'enfant |
   | `parle.png` (facultatif) | bouche ouverte : alternée avec les autres quand la voix parle |

3. Créer un dossier **`personnage`** dans le dossier **`contenu`** (donc
   `contenu/personnage/`) et y mettre les images.
4. Relancer `Lancer le compagnon.bat` : il utilise le dossier `contenu/personnage`
   automatiquement.
5. **Commit + Push** (partie 4) : tout le groupe aura le nouveau personnage.

Une expression manquante est remplacée par `neutre.png`. Pour revenir au personnage
dessiné d'origine, il suffit de renommer le dossier.

### 6.8 🟢 La carte du jeu sur l'écran d'accueil

**Fichier :** `compagnon/jeux.py`, partie 3, tout en bas (`CATALOG = …`)

```python
CatalogEntry(
    id="couleurs", title="Les couleurs",
    description="Touche le ballon de la bonne couleur.",
    icon="ballons", color="accent1", factory=ColorActivity,
),
```

| Champ | Ce que c'est | Peut-on le changer ? |
|---|---|---|
| `title` | le nom sous la carte | 🟢 |
| `description` | la phrase dite quand on touche le petit haut-parleur de la carte | 🟢 (mêmes règles que 6.1) |
| `color` | couleur de la carte : `"accent1"`, `"accent2"` ou `"accent3"` | 🟢 |
| `icon` | `"ballons"` (dessin intégré) ou le chemin d'une image, ex. `"contenu/personnage/carte_couleurs.png"` | 🟢 |
| `id`, `factory` | le lien avec le programme du jeu | 🔴 |

**Quels jeux apparaissent, et dans quel ordre** : ça ne se change pas ici, mais dans le
**mode adulte → onglet « Jeux »**.

### 6.9 🟠 Le son de bonne réponse

**Fichier :** `compagnon/voix.py`, partie 3

```python
NOTES_HZ = (392.00, 523.25, 659.25)  # G4, C5, E5  (sol, do, mi)
LENGTH_S = 1.2                       # durée totale en secondes
PEAK = 0.30                          # volume maximum (0.30 = doux ; ne pas dépasser 0.5)
```

On peut changer les notes (fréquences en Hz, par exemple 440.00 = la), la durée ou le
volume. ⚠️ Rester **doux et court** : pas de son fort ni soudain (cahier des charges FC2).

### 6.10 🟠 Les réglages par défaut

Presque tout se règle **sans code**, dans le **mode adulte → Réglages** : volume, voix,
vitesse de la voix, son, palette, animations, taille du texte, niveau de départ, délais,
pauses, récompense…

Les valeurs **de départ** sont dans `compagnon/reglages.py`, partie 1 (classe `Settings`).
⚠️ Les tests vérifient les scénarios du cahier des charges (15 s de silence, 3 erreurs…).
Changer ces valeurs fera donc échouer la vérification **même si le jeu marche** :
en parler au groupe avant.

### 6.11 🔴 Ajouter un nouveau jeu (formes, animaux, émotions…)

Là, il faut programmer. Le projet est prêt pour ça : un nouveau jeu = un fichier de
programme dans `compagnon/jeux.py` (sur le modèle du jeu des couleurs, partie 2) + une
entrée dans la liste des cartes (6.8). La carte
apparaît alors toute seule sur l'écran d'accueil.

Le plus simple : écrire le **contenu** (les questions, les réponses, les phrases, en
s'inspirant de `contenu/couleurs.json`) et demander à João ou à un assistant de programmation
de faire la partie programme.

---

## 7. Voir tous les écrans sans jouer

Pour regarder tous les écrans d'un coup (pratique pour vérifier un changement de couleur
ou de texte, et pour le rapport) :

1. Dans VS Code : menu **Terminal → New Terminal**.
2. Copier-coller cette ligne, puis **Entrée** :

   ```
   .venv\Scripts\python outils\captures.py
   ```

3. Les images sont créées dans `docs/captures/1280x720/` et `docs/captures/1920x1080/`.

---

## 8. En cas de problème

| Problème | Solution |
|---|---|
| « Python 3.12 n'est pas installé » | Laisser `Lancer le compagnon.bat` l'installer (`O`), ou l'installer depuis python.org en **cochant « Add python.exe to PATH »**, puis relancer. |
| La fenêtre noire se ferme tout de suite | Vérifier que le dossier a bien été **extrait** du ZIP (et pas ouvert directement dedans), puis relancer. |
| « Un probleme est survenu » | Faire une capture d'écran de la fenêtre noire et l'envoyer au groupe. |
| Le jeu s'arrête en parlant de « phrases.txt, ligne … » | Une ligne de `contenu/phrases.txt` n'a plus la forme `NOM = texte` (signe `=` effacé, nom changé…) : la corriger. |
| Le personnage ne parle pas | Vérifier le volume dans le mode adulte, et que le dossier `voix` contient bien les fichiers `.onnx` (sinon, retélécharger le projet). |
| `Verifier mes modifications.bat` dit **ATTENTION** | Lire les lignes `FAILED` et les messages juste au-dessus : ils indiquent le fichier et souvent le mot en cause (`mot_inconnu:`, `mot_interdit:`, `trop_long`…). Corriger, enregistrer, revérifier. |
| Je me suis trompé et je veux tout annuler | GitHub Desktop → colonne **Changes** → clic droit sur le fichier → **Discard changes…** (revient à la dernière version). |
| J'ai déjà envoyé (Push) une erreur | GitHub Desktop → onglet **History** → clic droit sur le commit → **Revert changes in commit**, puis **Push origin**. Rien n'est jamais perdu. |
| GitHub Desktop dit **« conflict »** | Deux personnes ont changé le même endroit. Ne rien forcer : prévenir le groupe et le résoudre ensemble (c'est pour l'éviter qu'il faut prévenir avant de modifier). |
| GitHub Desktop refuse le Push (« newer commits ») | Quelqu'un a envoyé avant vous : cliquer **Pull origin**, puis **Push origin**. |
| Windows a protégé votre ordinateur | **Informations complémentaires** → **Exécuter quand même**. |

---

## 9. Petit lexique

| Mot | Ce que ça veut dire |
|---|---|
| **Dépôt** (*repository*) | le projet complet stocké sur GitHub, avec tout son historique |
| **Cloner** | copier le dépôt sur son ordinateur, en restant relié à GitHub |
| **Commit** | enregistrer une étape de travail dans l'historique, avec un petit résumé |
| **Push** | envoyer ses commits sur GitHub, pour tout le groupe |
| **Pull** | récupérer sur son ordinateur les commits des autres |
| **Conflit** | deux personnes ont modifié la même ligne en même temps |
| **Test** | un petit programme qui vérifie automatiquement que le jeu respecte le cahier des charges |
| **JSON** | un format de fichier texte pour ranger des informations (`couleurs.json`) |
| **Terminal** | fenêtre où l'on tape des commandes (ici, presque jamais nécessaire) |
| **`.venv`** | le Python privé du projet, créé par `Lancer le compagnon.bat` (ne pas y toucher) |
