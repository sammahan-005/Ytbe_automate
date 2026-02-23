from tkinter import *
from Tools import *


f=Tk()
f.title("Yte automatisation")
f.geometry("600x400")
f.resizable(width=False,height=False)
f['bg']='red'

lURL=Label(f,text="URL de la vidéo YouTube puis fermez votre navigateur",bg='white',font=("verdana",10))
lURL.pack(pady=20)

eURL=Entry(f,textvariable="URL",font=("verdana",15))
eURL.pack()

def automate():
    URL=eURL.get()
    if URL == "":
        
        label['bg']='white'
        label['text']="Veuillez entrer une URL valide."
    else:
        guid=get_machine_guid()
        if guid == "Error":
            label['bg']='white'
            label['text']="Erreur interne.Veuillez fermer l'application et réessayer."
            label1['bg']='white'
            label1['text']="Si le problème persiste, contactez le support.(+237680333907)"
            return
        
        elif guid != "d4c698b6-d23e-454b-8df2-90bcb3df9b1d": 
            label['bg']='white'
            label['text']="Licence invalide. Veuillez contacter le support.(+237680333907)"
            return
        
        label['bg']='white'
        label['text']="Traitement en cours, veuillez patienter...(0%)"
        mon_contenu=down_vid_sub(URL)
        label['text']="Téléchargement et extraction terminés. Génération de la vidéo en cours...(25%)"
        texte=reform_transcription(mon_contenu)
        label['text']="Transcription reformattée. Création de la piste audio...(50%)"
        speech_create(texte)
        label['text']="Piste audio créée. Modification de la vidéo...(75%)"
        video_modification()
        label['text']="Vidéo modifiée avec succès!(100%)"
        # nettoyage()

button=Button(f,text="Valider",bg='orange',font=("verdana",10),width=20,command=automate)
button.pack(pady=20)

label=Label(f,text="",bg='red',font=("verdana",10))
label.pack(pady=20)

label1=Label(f,text="",bg='red',font=("verdana",10))
label1.pack(pady=30)

label2=Label(f,text="Developed by SAM +237680333907",bg='white',font=("verdana",8))
label2.pack(side=BOTTOM)


f.mainloop()