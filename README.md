# 🤖 YouTube Content Recreator Bot

Ce projet est un pipeline automatisé en Python permettant de télécharger, reformuler, éditer et republier automatiquement du contenu vidéo sur YouTube. Le robot prend une URL de vidéo YouTube en entrée et réalise toutes les étapes du processus jusqu'à la publication finale sur votre chaîne.

---

## 🌟 Fonctionnalités majeures

### 1. 📥 Téléchargement & Extraction des sous-titres (`yt-dlp`)
- **Stratégie de téléchargement en 2 passes** :
  - **Passe 1** : Utilise des clients alternatifs (`tv`, `ios`, `android_vr`) sans cookies pour contourner le *n-challenge* et les blocages récents de YouTube.
  - **Passe 2** : Si la première passe échoue, tente un téléchargement classique via le client `web` en extrayant automatiquement les cookies de vos navigateurs locaux (`firefox`, `chrome`, `brave`, `opera`, etc.).
- Extraction automatique des sous-titres en français (formats `.srt` ou `.vtt`).

### 2. 🤖 Reformulation IA & Métadonnées (`DeepSeek API`)
- **Nettoyage de la transcription** : Suppression automatique des métadonnées temporelles, balises HTML/XML de positionnement et doublons de lignes.
- **Réécriture de script** : Reformulation intelligente de l'histoire pour la chaîne cible **"Vie de légende"** en conservant la longueur d'origine, tout en éliminant les caractères spéciaux et les formats markdown gênants pour la synthèse vocale.
- **Métadonnées optimisées** : Génération d'un titre court et percutant (moins de 100 caractères) et d'une description optimisée avec des hashtags pertinents (comme `#viedelegende`) et un appel à l'action pour les abonnements.

### 3. 🎙️ Synthèse Vocale Premium (`edge-tts`)
- Utilisation de la voix neuronale Azure **`fr-FR-HenriNeural`** (voix masculine française extrêmement naturelle).
- Génération asynchrone ultra-rapide du fichier audio de la voix off.

### 4. 🎬 Montage Vidéo Dynamique (`MoviePy 2.x`)
- Désactivation du son original de la vidéo.
- **Découpage & Mélange aléatoire** : Découpage automatique de la vidéo en clips de durée variable (entre 5 et 10 secondes), puis mélange de ces clips pour créer un nouveau montage dynamique (le premier clip d'origine est déplacé pour éviter les correspondances directes).
- **Ajustement automatique de la durée** : Si la voix off est plus courte que la vidéo, celle-ci est découpée. Si la voix off est plus longue, la vidéo est mise en boucle pour couvrir toute la piste sonore.
- **Musique de fond optionnelle** : Si le fichier `background_music.mp3` est présent à la racine, il est automatiquement ajouté sous la voix off avec un volume atténué (12% par défaut) et bouclé ou coupé selon la longueur finale.

### 5. 📤 Publication automatique sur YouTube (`YouTube Data API v3`)
- **Authentification OAuth 2.0 sécurisée** : Connexion via le protocole Google avec mise en cache locale du jeton d'accès dans `youtube_token.json`.
- **Upload résiliable (Resumable Upload)** : Envoi par blocs de 1 Mo pour supporter les interruptions réseau avec affichage de la progression en temps réel.
- **Visibilité configurable** : Statut de publication modifiable via le fichier de configuration `.env` (`public`, `private`, `unlisted`).
- **Gestion intelligente des miniatures** : 
  - Détection automatique de la miniature d'origine téléchargée par `yt-dlp`.
  - Conversion automatique des miniatures au format `WebP` vers `JPEG` (requis par l'API YouTube).
  - Téléversement et application automatique de la miniature sur la nouvelle vidéo.

---

## 📁 Structure du projet

```bash
.
├── Action.py                 # Point d'entrée principal (CLI interactive)
├── Tools.py                  # Module contenant les utilitaires (Téléchargement, IA, TTS, Montage)
├── YoutubeUploader.py        # Gestion de l'authentification Google OAuth et de l'upload YouTube
├── requirements.txt          # Liste des dépendances Python requises
├── .env                      # Configuration des variables d'environnement (clés API, confidentialité)
├── client_secrets.json       # Vos identifiants OAuth Google (à obtenir sur Google Cloud Console)
├── youtube_token.json        # Jeton d'accès YouTube généré automatiquement après la 1ère connexion
└── background_music.mp3      # Musique de fond optionnelle pour accompagner la voix off
```

---

## 🚀 Installation & Configuration

### 1. Prérequis système
- **Python 3.10** ou version ultérieure.
- **FFmpeg** installé sur le système (utilisé par `MoviePy` et `yt-dlp` pour fusionner et encoder les vidéos).
  - *Sur Ubuntu/Debian :* `sudo apt install ffmpeg`

### 2. Cloner le projet et installer les dépendances
1. Activez ou créez votre environnement virtuel :
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Installez les packages requis :
   ```bash
   pip install -r requirements.txt
   ```

### 3. Configurer les variables d'environnement (`.env`)
Créez ou modifiez le fichier `.env` à la racine du projet :
```env
# Clé API DeepSeek pour la reformulation du script et des métadonnées
DEEPSEEK_API_KEY=votre_cle_api_deepseek_ici

# Visibilité des vidéos sur YouTube (public, private ou unlisted)
YOUTUBE_PRIVACY_STATUS=public
```

### 4. Configurer les identifiants YouTube API
Pour autoriser l'upload automatique :
1. Allez sur la [Google Cloud Console](https://console.cloud.google.com/).
2. Créez un projet et activez l'API **YouTube Data API v3**.
3. Accédez à la section **Identifiants** (Credentials), créez des identifiants de type **ID client OAuth** pour une **Application de bureau** (Desktop Application).
4. Téléchargez le fichier JSON des identifiants, renommez-le `client_secrets.json` et placez-le à la racine du projet.

*(Note : Lors de la première exécution, une fenêtre de navigateur s'ouvrira pour vous authentifier auprès de votre compte Google/YouTube. Un fichier `youtube_token.json` sera généré pour mémoriser la session.)*

---

## 💻 Utilisation

Pour lancer le pipeline complet, exécutez simplement la commande suivante :

```bash
python Action.py
```

### Étapes du script :
1. **Entrez l'URL** de la vidéo d'origine à cloner.
2. Le robot **télécharge** la vidéo et extrait les sous-titres.
3. Le texte est **reformulé** via l'API DeepSeek.
4. Le fichier audio de la **voix off** est généré avec `edge-tts`.
5. Le robot réalise le **montage vidéo** (mutes, coupes, mélanges, voix off, musique).
6. Le script propose ensuite les **métadonnées** (Titre et Description) générées par IA.
7. Vous pouvez accepter ou modifier le titre proposé, puis valider pour lancer **l'upload direct** sur YouTube.
