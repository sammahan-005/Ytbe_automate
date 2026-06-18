import os
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

# Scope requis pour téléverser des vidéos sur YouTube
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_youtube_credentials() -> Credentials:
    """
    Gère l'authentification OAuth 2.0 avec mise en cache du jeton (token).
    Si le jeton n'existe pas ou a expiré, demande l'autorisation via navigateur
    en utilisant le fichier client_secrets.json.
    """
    creds = None
    token_path = os.environ.get("YOUTUBE_TOKEN_FILE", "youtube_token.json")
    client_secrets_path = os.environ.get("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

    # 1. Tente de charger les informations d'identification enregistrées
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            print("🔑 Informations d'identification chargées depuis youtube_token.json")
        except Exception as e:
            print(f"⚠️ Erreur lors de la lecture du jeton existant : {e}")

    # 2. Si aucune info d'identification valide n'est disponible, connecte l'utilisateur
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Rafraîchissement du jeton d'accès YouTube...")
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Impossible de rafraîchir le jeton : {e}. Une ré-authentification est requise.")
                creds = None

        if not creds:
            if not os.path.exists(client_secrets_path):
                raise FileNotFoundError(
                    f"\n❌ Le fichier '{client_secrets_path}' est introuvable à la racine du projet.\n"
                    f"Pour activer l'upload automatique, veuillez :\n"
                    f"  1. Créer un projet sur Google Cloud Console.\n"
                    f"  2. Activer l'API 'YouTube Data API v3'.\n"
                    f"  3. Créer des identifiants OAuth 2.0 de type 'Application de bureau'.\n"
                    f"  4. Télécharger le fichier JSON, le renommer '{client_secrets_path}' et le placer à la racine de ce projet.\n"
                )
            
            print("🌐 Ouverture du navigateur pour l'autorisation OAuth YouTube...")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Enregistre les identifiants pour les exécutions futures
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
            print(f"💾 Nouveau jeton enregistré dans {token_path}")

    return creds

def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    privacy_status: str = "private",
    tags: list[str] = None,
    category_id: str = "22"  # 22 correspond à "People & Blogs"
) -> str | None:
    """
    Téléverse une vidéo sur YouTube à l'aide de l'API YouTube Data v3.
    Gère le téléversement résiliable (resumable) avec barre de progression.
    
    Retourne l'ID de la vidéo téléversée en cas de succès, sinon None.
    """
    if not os.path.exists(video_path):
        print(f"❌ Fichier vidéo introuvable : {video_path}")
        return None

    try:
        creds = get_youtube_credentials()
    except Exception as e:
        print(f"❌ Erreur lors de l'authentification YouTube : {e}")
        return None

    # Construction du service d'API YouTube
    youtube = build('youtube', 'v3', credentials=creds)

    body = {
        'snippet': {
            'title': title[:100],  # YouTube limite les titres à 100 caractères
            'description': description,
            'tags': tags or ["Vie de légende", "motivation", "histoire"],
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        },
        'recordingDetails': {
            'locationDescription': 'Paris, France',
            'location': {
                'latitude': 48.856614,
                'longitude': 2.3522219
            }
        }
    }

    print(f"📤 Initialisation de l'upload de la vidéo : {os.path.basename(video_path)}")
    print(f"   Titre : {title[:60]}...")
    print(f"   Visibilité : {privacy_status}")

    # Utilisation d'un chargement par blocs (chunked/resumable) de 1 Mo
    media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)
    request = youtube.videos().insert(
        part='snippet,status,recordingDetails',
        body=body,
        media_body=media
    )

    response = None
    retries = 0
    max_retries = 5

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"⏳ Téléversement : {progress}% effectue...", end="\r", flush=True)
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                retries += 1
                if retries > max_retries:
                    print(f"\n❌ Erreur serveur irrécupérable après {max_retries} tentatives : {e}")
                    return None
                wait_time = 2 ** retries
                print(f"\n⚠️ Erreur serveur {e.resp.status}. Nouvelle tentative dans {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"\n❌ Erreur API YouTube non récupérable : {e}")
                return None
        except Exception as e:
            print(f"\n❌ Une erreur inattendue est survenue pendant l'upload : {e}")
            return None

    print(f"\n✅ Upload terminé avec succès !")
    video_id = response.get("id")
    print(f"🔗 Lien de la vidéo : https://www.youtube.com/watch?v={video_id}")
    
    # Tentative d'application de la miniature personnalisée
    set_video_thumbnail(youtube, video_id, video_path)
    
    return video_id

def set_video_thumbnail(youtube, video_id: str, video_path: str) -> bool:
    """
    Trouve la miniature téléchargée par yt-dlp pour la vidéo originale,
    la convertit en JPEG si nécessaire (car YouTube refuse le WebP),
    et l'associe à la vidéo YouTube téléversée.
    """
    from PIL import Image

    base_path = video_path.rsplit(".", 1)[0]
    # Si le chemin contient le suffixe de modification, on le retire pour trouver la miniature d'origine
    if base_path.endswith("_modified"):
        base_path = base_path[:-9]
    
    # Extensions d'images possibles téléchargées par yt-dlp
    extensions = [".jpg", ".jpeg", ".png", ".webp"]
    thumbnail_path = None
    
    for ext in extensions:
        temp_path = base_path + ext
        if os.path.exists(temp_path):
            thumbnail_path = temp_path
            break
            
    if not thumbnail_path:
        print("ℹ️ Aucune miniature d'origine trouvée à appliquer.")
        return False
        
    print(f"🖼️ Miniature d'origine trouvée : {os.path.basename(thumbnail_path)}")
    
    # Si c'est un fichier webp, on le convertit en JPEG
    if thumbnail_path.lower().endswith(".webp"):
        jpg_path = base_path + "_converted.jpg"
        try:
            print("🔄 Conversion de la miniature de WebP vers JPEG...")
            with Image.open(thumbnail_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(jpg_path, "JPEG", quality=90)
            thumbnail_path = jpg_path
        except Exception as e:
            print(f"⚠️ Erreur lors de la conversion de la miniature : {e}")
            return False
            
    # Téléversement de la miniature
    try:
        print("📤 Application de la miniature personnalisée sur YouTube...")
        media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=media
        )
        request.execute()
        print("✅ Miniature personnalisée appliquée avec succès !")
        
        # Nettoyage du fichier converti temporaire
        if "_converted.jpg" in thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            
        return True
    except Exception as e:
        print(f"⚠️ Impossible d'appliquer la miniature : {e}")
        print("ℹ️ Note : Votre chaîne YouTube doit être validée par téléphone pour autoriser les miniatures personnalisées via l'API.")
        if "_converted.jpg" in thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        return False

