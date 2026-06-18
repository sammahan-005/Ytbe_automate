import os
from dotenv import load_dotenv
load_dotenv()

from Tools import down_vid_sub, reform_transcription, speech_create, video_modification, generate_metadata
from YoutubeUploader import upload_video_to_youtube


def main():
    url = input("Entrer l'URL de la vidéo YouTube : ").strip()
    if not url:
        print("❌ URL vide. Arrêt.")
        return

    # ── Étape 1 : Téléchargement et extraction des sous-titres ──
    transcription, video_path, base_path = down_vid_sub(url)
    if not transcription or not video_path:
        print("❌ Le téléchargement ou l'extraction des sous-titres a échoué. Arrêt du programme.")
        return

    # ── Étape 2 : Reformulation du script via DeepSeek ──
    nouveau_texte = reform_transcription(transcription)
    if not nouveau_texte:
        print("❌ La reformulation du script a échoué. Arrêt du programme.")
        return

    # ── Étape 3 : Génération de la voix off (edge-tts) ──
    audio_path = speech_create(nouveau_texte, base_path)
    if not audio_path:
        print("❌ La génération audio a échoué. Arrêt du programme.")
        return

    # ── Étape 4 : Montage vidéo ──
    final_video_path = video_modification(video_path, audio_path)
    if not final_video_path:
        print("❌ La modification de la vidéo a échoué. Arrêt du programme.")
        return

    # ── Étape 5 : Génération des métadonnées et upload YouTube ──
    print("\n🔍 Génération du titre et de la description pour YouTube...")
    titre, description = generate_metadata(nouveau_texte)

    print("\n📝 Métadonnées proposées :")
    print(f"📌 Titre : {titre}")
    print(f"📌 Description :\n{description}\n")

    choix = input("Souhaitez-vous uploader cette vidéo sur YouTube ? (O/n) : ").strip().lower()
    if choix in ("", "o", "oui", "y", "yes"):
        custom_titre = input(f"Titre de remplacement (laisser vide pour garder '{titre}') : ").strip()
        if custom_titre:
            titre = custom_titre
        
        privacy_status = os.environ.get("YOUTUBE_PRIVACY_STATUS", "private")
        print(f"\n🚀 Lancement de l'upload sur YouTube (Visibilité : {privacy_status})...")
        video_id = upload_video_to_youtube(
            video_path=final_video_path,
            title=titre,
            description=description,
            privacy_status=privacy_status
        )
        if video_id:
            print(f"\n🎉 Succès ! Vidéo mise en ligne avec l'ID : {video_id}")
        else:
            print("\n❌ L'upload a échoué.")
    else:
        print("\nℹ️ Upload annulé par l'utilisateur.")


if __name__ == "__main__":
    main()
