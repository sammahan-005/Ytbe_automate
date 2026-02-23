from Tools import *

URL=input("Entrer l'URL de la vidéo YouTube: ")
mon_contenu=down_vid_sub(URL)
texte=reform_transcription(mon_contenu)
speech_create(texte)
video_modification()
# nettoyage()
