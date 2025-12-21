
from urllib import response
import yt_dlp
import os
import time
import pyttsx3
from google import genai
from moviepy import *
from random import shuffle
from moviepy.video import fx as vfx 




def down_vid_sub(URL):
    """
    Purpose:
    Télécharger une vidéo depuis une URL donnée en utilisant yt-dlp,
    extraire les sous-titres en français, et sauvegarder la transcription 
    """
    
    url = URL
    global base_path
    global folder_path
    global video_path
    # Chemin de base
    base_folder = 'downloads'

    ydl_opts = {
        # STRUCTURE DE DOSSIER : downloads/Titre_Video/Titre_Video.extension
        'outtmpl': f'{base_folder}/%(title)s/%(title)s.%(ext)s',
        
        'format': 'bestvideo/best',
        'writethumbnail': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['fr'],
        'quiet': False, # Affiche la progression dans la console
        
        # AJOUTS POUR ÉVITER L'ERREUR 429
        'cookiesfrombrowser': ('chrome',),
        'sleep_interval': 5,          # Attend 5 secondes entre les étapes
        'max_sleep_interval': 10,     # Jusqu'à 10 secondes (aléatoire)
        'nocheckcertificate': True,
        'ignoreerrors': True,         # Continue même si un sous-titre échoue
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(URL, download=True)
        
        if info is None:
            print("Impossible d'extraire les informations.")
            return # On quitte la fonction proprement

        # Récupération du chemin exact
        video_path = ydl.prepare_filename(info)
        
        folder_path = os.path.dirname(video_path)
        
        # Chemins des fichiers (On utilise la base sans extension)
        base_path = video_path.rsplit('.', 1)[0]
        srt_filename = f"{base_path}.fr.srt"
        vtt_filename = f"{base_path}.fr.vtt"
       

        
        with open(vtt_filename, "r", encoding="utf-8") as fichier:
                mon_contenu = fichier.read()

        
        return mon_contenu
    # end def

def reform_transcription(mon_contenu):
        """
        Purpose: 
        Reformuler le texte avec l'API Gemini 2.5 Flash de Google GenAI.
        """
        nbre_mot=str(len(mon_contenu.split()))

        client = genai.Client(api_key="Your_GenAI_API_Key_Here")
        response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents="Je t'envois le script du video ytube. J'aimerais que tu reformules son contenu en un paragraphe de " + nbre_mot + " mots.Ce texte sera utilise dans ma propre chaine youtube ayant pour nom:Vie de legende. Parle comme si tu racontais une histoire. Tu as le droit d'utiliser tes propres expressions tout en restant dans l'esprit de la video. Voici le script : " + mon_contenu
        )
        print(response.text)
        return response.text
# end def    
    
def speech_create(texte):
    """
    Purpose: Convertir un texte en fichier audio MP3 en utilisant pyttsx3.
    """
    global output_path
    engine = pyttsx3.init()

    # 1. On définit le texte et le nom du fichier de sortie
    # Note : Utilisez l'extension .mp3 ou .wav
    output_path = f"{base_path}_audio.mp3"
    engine.save_to_file(texte, output_path)

    # 2. IMPORTANT : Il faut lancer runAndWait() pour que l'écriture se termine
    engine.runAndWait()
    print(f"Fichier audio généré et sauvegardé sous : {output_path}")

    
    

   
# end def    


def video_modification():
    """
    Purpose: Modifier la vidéo téléchargée avec moviepy (Couper, reassembler et ajouter l'audio genere).
    """
    
    video=VideoFileClip(video_path)
    audio=AudioFileClip(output_path)
    video=video.without_audio()  # On mute la vidéo originale
    duree=int(video.duration)
    # Couper la vidéo en parties de 30 secondes
    clips = []
    for start in range(0, duree, 30):
        end = min(start + 30, duree) # Compare le saut de 30 secondes avec la fin de la vidéo
        clip = video.subclipped(start, end)
        clips.append(clip)
        
    # Reassembler aleatoirement les clips en s'assurant que le premier ne soit pas a la meme position
    first_clip = clips[0]
    remaining_clips = clips[1:]
    shuffle(remaining_clips)
    shuffled_clips = remaining_clips + [first_clip]

    # Reassembler les clips mélangés
    final_video = concatenate_videoclips(shuffled_clips)
    
    # Ajouter la nouvelle piste audio
    dureeaudio = audio.duration

    if dureeaudio < final_video.duration:
        final_video = final_video.subclipped(0, dureeaudio)
        final_video = final_video.set_audio(audio)
    else:
        final_video = final_video.with_effects([vfx.Loop(duration=dureeaudio)])
        final_video = final_video.with_audio(audio)
    
    # Sauvegarder la vidéo modifiée
    
    final_video.write_videofile(video_path.rsplit('.', 1)[0] + '_modified.mp4', codec='libx264', audio_codec='aac')

    

