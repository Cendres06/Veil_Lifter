import spacy

# Ce document a été créé sous la direction de Yoann Dupont de l'ObTIC le 26/07/2022.
# https://github.com/YoannDupont/train_spacy

nom_fichier=r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\textes_fr\scp-101-fr.txt'

dossier_modele=r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\spacyModel\model-best'

nlp = spacy.load(dossier_modele)

with open(nom_fichier,'r',encoding='utf-8') as file:
    text = file.read()

for entity in nlp(text).ents:
    print(entity.start, entity.end, '-', entity.label_, '-',entity)