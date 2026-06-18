
import yt_dlp
import os
import asyncio
import re
import edge_tts
import requests
from moviepy import *
from moviepy.video import fx as vfx
from random import shuffle, randint
import imageio_ffmpeg


# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

VOIX_TTS = "fr-FR-HenriNeural"          # Voix masculine naturelle
VOLUME_MUSIQUE = 0.12                    # Volume de la musique de fond (12 % du volume original)
CLIP_MIN_SEC = 5                         # Durée minimale d'un clip (secondes)
CLIP_MAX_SEC = 10                        # Durée maximale d'un clip (secondes)
BACKGROUND_MUSIC_FILE = "background_music.mp3"  # Fichier optionnel à la racine du projet


# ─────────────────────────────────────────────
#  1. TÉLÉCHARGEMENT & EXTRACTION
# ─────────────────────────────────────────────

def _detecter_navigateur() -> str | None:
    """Détecte le premier navigateur disponible avec des cookies valides."""
    for browser in ("firefox", "chrome", "chromium", "brave", "opera", "edge"):
        try:
            with yt_dlp.YoutubeDL({"cookiesfrombrowser": (browser,), "quiet": True}) as ydl:
                ydl.cookiejar
            return browser
        except Exception:
            continue
    return None


def _essayer_download(url: str, ydl_opts: dict):
    """Tente un téléchargement avec les options données. Retourne info ou None."""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info
    except Exception as e:
        print(f"⚠️ Erreur lors du téléchargement : {e}")
        return None


def down_vid_sub(url: str) -> tuple[str | None, str | None, str | None]:
    """
    Télécharge une vidéo YouTube et extrait les sous-titres en français.
    Stratégie en 2 passes :
      - Passe 1 : clients iOS/android_vr (sans cookies → contourne le n-challenge YouTube)
      - Passe 2 : client web + cookies navigateur (si passe 1 échoue)

    Retourne:
        (transcription, video_path, base_path) si succès
        (None, None, None) en cas d'échec
    """
    base_folder = "downloads"

    base_opts = {
        "outtmpl": f"{base_folder}/%(title)s/%(title)s.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["fr"],
        "quiet": False,
        "sleep_interval": 3,
        "max_sleep_interval": 8,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
    }

    # ── Passe 1 : clients tv/ios/android_vr — pas de cookies, contournent le n-challenge ──
    print("🔄 Passe 1 : tentative via clients alternatifs (tv, ios, android_vr)...")
    opts_passe1 = {
        **base_opts,
        "extractor_args": {"youtube": {"player_client": ["tv", "ios", "android_vr"]}},
    }
    info = _essayer_download(url, opts_passe1)

    # Récupération et vérification du chemin pour la Passe 1
    if info is not None:
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            video_path = ydl.prepare_filename(info)
        if not os.path.exists(video_path):
            print("⚠️ Fichier vidéo manquant en Passe 1 (possible erreur 403). Déclenchement de la Passe 2...")
            info = None

    # ── Passe 2 : client web avec cookies navigateur ──
    if info is None:
        print("⚠️ Passe 1 échouée ou incomplète. Passage au client web avec cookies navigateur...")
        browser = _detecter_navigateur()
        opts_passe2 = {
            **base_opts,
            "extractor_args": {"youtube": {"player_client": ["web"]}},
        }
        if browser:
            print(f"✅ Cookies détectés depuis : {browser}")
            opts_passe2["cookiesfrombrowser"] = (browser,)
        else:
            print("⚠️ Aucun navigateur compatible. Tentative sans cookies...")
        info = _essayer_download(url, opts_passe2)

    if info is None:
        print("❌ Impossible d'extraire les informations de la vidéo après deux tentatives.")
        return None, None, None

    # Récupération finale du chemin et validation
    with yt_dlp.YoutubeDL(base_opts) as ydl:
        video_path = ydl.prepare_filename(info)

    if not os.path.exists(video_path):
        print(f"❌ Erreur : le fichier vidéo attendu n'a pas été généré : {video_path}")
        return None, None, None

    base_path = video_path.rsplit(".", 1)[0]
    srt_filename = f"{base_path}.fr.srt"
    vtt_filename = f"{base_path}.fr.vtt"

    if os.path.exists(vtt_filename):
        with open(vtt_filename, "r", encoding="utf-8") as f:
            transcription = f.read()
    elif os.path.exists(srt_filename):
        with open(srt_filename, "r", encoding="utf-8") as f:
            transcription = f.read()
    else:
        print("❌ Aucun sous-titre français (.vtt ou .srt) trouvé.")
        return None, None, None

    return transcription, video_path, base_path


# ─────────────────────────────────────────────
#  2. REFORMULATION IA (DeepSeek)
# ─────────────────────────────────────────────

def _nettoyer_vtt(contenu_brut: str) -> str:
    """Nettoie le contenu d'un fichier VTT pour ne garder que le texte parlé."""
    # Supprime les balises de timing, les balises <c> et les lignes d'en-tête
    texte = re.sub(r"WEBVTT.*?\n", "", contenu_brut)
    texte = re.sub(r"Kind:.*?\n", "", texte)
    texte = re.sub(r"Language:.*?\n", "", texte)
    texte = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> .*?\n", "", texte)
    texte = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", texte)
    texte = re.sub(r"<c>|</c>", "", texte)
    texte = re.sub(r"align:.*?%", "", texte)
    texte = re.sub(r"\n{2,}", "\n", texte).strip()
    # Supprime les doublons de lignes consécutives
    lignes = texte.splitlines()
    vues = set()
    lignes_uniques = []
    for ligne in lignes:
        ligne = ligne.strip()
        if ligne and ligne not in vues:
            vues.add(ligne)
            lignes_uniques.append(ligne)
    return " ".join(lignes_uniques)


def reform_transcription(contenu_brut: str) -> str | None:
    """
    Reformule la transcription brute (VTT/SRT) avec l'API DeepSeek Chat.

    Retourne le texte reformulé, ou None en cas d'échec.
    """
    # Nettoyage du texte brut avant envoi à l'IA
    contenu_propre = _nettoyer_vtt(contenu_brut)
    nbre_mot = len(contenu_propre.split())

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY introuvable dans l'environnement.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt = (
        f"Je t'envoie le script d'une vidéo YouTube. "
        f"Reformule son contenu en un paragraphe d'environ {nbre_mot} mots. "
        f"Ce texte sera utilisé dans ma propre chaîne YouTube nommée 'Vie de légende'. "
        f"Parle comme si tu racontais une histoire captivante. "
        f"Tu peux utiliser tes propres expressions tout en restant dans l'esprit de la vidéo. "
        f"Eviter les asterics et caracteres speciaux"
        f"Renvoie directement le texte sans markdown, sans les guillemets"
        f"Voici le script :\n\n{contenu_propre}"
    )

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    try:
        print("🤖 Reformulation du script via DeepSeek...")
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=data,
            timeout=90,
        )
        response.raise_for_status()
        result = response.json()
        texte = result["choices"][0]["message"]["content"]
        print(f"\n📝 Script reformulé ({len(texte.split())} mots) :\n{texte[:200]}...\n")
        return texte
    except requests.exceptions.Timeout:
        print("❌ Délai d'attente dépassé lors de l'appel à DeepSeek.")
        return None
    except Exception as e:
        print(f"❌ Erreur lors de l'appel à DeepSeek : {e}")
        return None


def generate_metadata(nouveau_texte: str) -> tuple[str, str]:
    """
    Génère un titre accrocheur et une description optimisée pour YouTube
    en se basant sur le script reformulé, en utilisant l'API DeepSeek.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY introuvable dans l'environnement pour générer les métadonnées.")
        return "Vie de légende - Histoire inspirante", "Vidéo générée automatiquement par Vie de légende."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt = (
        f"Voici le script d'une vidéo de ma chaîne YouTube 'Vie de légende' :\n\n"
        f"{nouveau_texte}\n\n"
        f"Génère un titre court et extrêmement accrocheur pour cette vidéo (moins de 100 caractères, sans guillemets, sans emoji, adapté à YouTube).\n"
        f"Génère également une description engageante résumant brièvement l'histoire racontée, avec quelques hashtags pertinents (dont #viedelegende) et un appel à l'action pour s'abonner.\n"
        f"Renvoie le résultat STRICTEMENT sous le format suivant, sans autre texte ni introduction :\n"
        f"TITRE: <titre de la vidéo>\n"
        f"DESCRIPTION: <description de la vidéo>"
    )

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    try:
        print("🤖 Génération du titre et de la description via DeepSeek...")
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=data,
            timeout=45,
        )
        response.raise_for_status()
        result = response.json()
        raw_text = result["choices"][0]["message"]["content"].strip()
        
        # Parsing du titre et de la description
        title = "Vie de légende"
        description = "Vidéo générée automatiquement par Vie de légende."
        
        match_title = re.search(r"TITRE:\s*(.*)", raw_text, re.IGNORECASE)
        match_desc = re.search(r"DESCRIPTION:\s*([\s\S]*)", raw_text, re.IGNORECASE)
        
        if match_title:
            title = match_title.group(1).strip().strip('"').strip("'")
        if match_desc:
            description = match_desc.group(1).strip()
            # Supprime la partie TITRE si elle est capturée par erreur dans la description
            description = re.sub(r"TITRE:.*", "", description, flags=re.IGNORECASE).strip()
            
        return title, description
    except Exception as e:
        print(f"⚠️ Erreur lors de la génération des métadonnées DeepSeek : {e}")
        return "Vie de légende - Histoire inspirante", f"Découvrez cette histoire inspirante sur la chaîne Vie de légende.\n\nScript :\n{nouveau_texte[:200]}..."


# ─────────────────────────────────────────────
#  3. SYNTHÈSE VOCALE (edge-tts)
# ─────────────────────────────────────────────

async def _generer_audio_async(texte: str, output_path: str) -> None:
    """Génère le fichier audio avec edge-tts de manière asynchrone."""
    communicate = edge_tts.Communicate(texte, VOIX_TTS)
    await communicate.save(output_path)


def speech_create(texte: str, base_path: str) -> str | None:
    """
    Convertit un texte en fichier audio MP3 en utilisant edge-tts (voix Azure naturelle).

    Retourne:
        Le chemin du fichier audio généré, ou None en cas d'erreur.
    """
    output_path = f"{base_path}_audio.mp3"
    try:
        print(f"🎙️ Génération de la voix off avec edge-tts (voix : {VOIX_TTS})...")
        asyncio.run(_generer_audio_async(texte, output_path))
        print(f"✅ Audio généré : {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Erreur lors de la génération audio : {e}")
        return None


# ─────────────────────────────────────────────
#  4. MONTAGE VIDÉO (MoviePy)
# ─────────────────────────────────────────────

def _decouper_clips_aleatoires(video: VideoFileClip) -> list:
    """Découpe la vidéo en clips de durée aléatoire (CLIP_MIN_SEC à CLIP_MAX_SEC secondes)."""
    clips = []
    position = 0
    duree_totale = int(video.duration)

    while position < duree_totale:
        duree_clip = randint(CLIP_MIN_SEC, CLIP_MAX_SEC)
        fin = min(position + duree_clip, duree_totale)
        clips.append(video.subclipped(position, fin))
        position = fin

    return clips


def video_modification(video_path: str, audio_path: str) -> str | None:
    """
    Modifie la vidéo téléchargée :
    - Mute la vidéo originale
    - Découpe en clips courts (5 à 10 s) et les mélange
    - Ajuste la durée à la voix off
    - Ajoute la voix off (+ musique de fond si disponible)
    - Exporte la vidéo finale

    Args:
        video_path: Chemin vers la vidéo originale téléchargée.
        audio_path: Chemin vers le fichier audio de la voix off.
    """
    video = None
    audio_voix = None
    audio_musique = None
    final_video = None

    try:
        print("🎬 Chargement des fichiers médias...")
        video = VideoFileClip(video_path).without_audio()
        audio_voix = AudioFileClip(audio_path)
        duree_audio = audio_voix.duration

        # 1. Découpage en clips courts et mélange aléatoire
        print(f"✂️ Découpage en clips de {CLIP_MIN_SEC} à {CLIP_MAX_SEC} secondes...")
        clips = _decouper_clips_aleatoires(video)

        # On s'assure que le premier clip n'est pas en première position après le shuffle
        premier_clip = clips[0]
        reste = clips[1:]
        shuffle(reste)
        clips_melanges = reste + [premier_clip]

        # 2. Assemblage des clips
        print("🔗 Assemblage des clips...")
        montage = concatenate_videoclips(clips_melanges)

        # 3. Ajuster la durée à la voix off (couper ou boucler)
        if duree_audio < montage.duration:
            final_video = montage.subclipped(0, duree_audio)
        else:
            final_video = montage.with_effects([vfx.Loop(duration=duree_audio)])

        # 4. Préparer la piste audio (voix off + musique de fond optionnelle)
        if os.path.exists(BACKGROUND_MUSIC_FILE):
            print(f"🎵 Musique de fond détectée : {BACKGROUND_MUSIC_FILE}")
            audio_musique = AudioFileClip(BACKGROUND_MUSIC_FILE)

            # Boucler ou couper la musique à la durée de la voix off
            if audio_musique.duration < duree_audio:
                audio_musique = audio_musique.with_effects([afx.AudioLoop(duration=duree_audio)])
            else:
                audio_musique = audio_musique.subclipped(0, duree_audio)

            audio_musique = audio_musique.with_effects([afx.MultiplyVolume(VOLUME_MUSIQUE)])
            piste_finale = CompositeAudioClip([audio_voix, audio_musique])
            final_video = final_video.with_audio(piste_finale)
        else:
            print("ℹ️ Pas de musique de fond détectée (fichier 'background_music.mp3' absent). Voix seule.")
            final_video = final_video.with_audio(audio_voix)

        # 5. Export de la vidéo finale
        output_video_path = video_path.rsplit(".", 1)[0] + "_modified.mp4"
        print(f"💾 Export de la vidéo finale : {output_video_path}")
        final_video.write_videofile(output_video_path, codec="libx264", audio_codec="aac")
        print(f"\n✅ Terminé ! Vidéo sauvegardée sous : {output_video_path}")
        return output_video_path

    except Exception as e:
        print(f"❌ Erreur lors du montage vidéo : {e}")
        raise
    finally:
        # Libération propre des ressources pour éviter les fuites mémoire
        for clip in [final_video, audio_musique, audio_voix, video]:
            if clip is not None:
                try:
                    clip.close()
                except Exception:
                    pass
