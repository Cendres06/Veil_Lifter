import utilities
import pandas as pd
import re

def recup_traducteur(id,chemin="../../bases_de_donnees/en_trad"):
    liste_en_trad = utilities.path_extension("bd_en",False,chemin=chemin,lecture=True)
    line= liste_en_trad.loc[liste_en_trad['id']==id]
    return line['Traducteurice(s)'][0]

def get_all_works(author):
    liste_originaux = utilities.path_extension('bd_fr',lecture=True)
    works = []
    for _,row in liste_originaux.iterrows():
        if utilities.is_in(author,row.loc['Auteurice(s)']):
            works = utilities.insert_in_list_by_date((row.loc['id'],row.loc['Date de création']),works)
    return(works)
