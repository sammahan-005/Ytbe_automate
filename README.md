# 🤖 YouTube Content Recreator Bot

Ce projet est un pipeline automatisé en Python permettant de transformer et de republier du contenu vidéo. Le bot télécharge une vidéo, utilise l'IA pour réécrire le script, génère une nouvelle voix off via synthèse vocale (TTS), remonte la vidéo de manière aléatoire ou structurée, puis la publie sur YouTube.



## 🌟 Fonctionnalités

- **Extraction** : Téléchargement de vidéos depuis YouTube avec `yt-dlp`.
- **Intelligence Artificielle** : Réécriture créative du script via l'API **Google Gemini**.
- **Synthèse Vocale** : Génération d'une voix off locale avec `pyttsx3`.
- **Montage Dynamique** : Manipulation vidéo, découpage et effets avec `MoviePy`.
- **Automatisation** : Publication directe sur YouTube via l'API Data v3.
