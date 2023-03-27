import math
import pandas as pd
import os
import re
import time

def path_extension(fichier,bd=True,chemin="../../",lecture=False,extension="csv"):
    if chemin:
        if chemin[-1] != "/":
            if bd:
                path=chemin + r'/bases_de_donnees/'+fichier+r'.'+extension
            else:
                path=chemin + r"/" + fichier+r'.'+extension
        else:
            if bd:
                path = chemin + r'bases_de_donnees/'+fichier+r'.'+extension
            else:
                path = chemin + r"/" + fichier+r'.'+extension
    else:
        if bd:
            path = r'/bases_de_donnees/'+fichier+r'.'+extension
        else:
            path = fichier+r'.'+extension
    if lecture and extension=="csv":
        dataframe = pd.read_csv(path,encoding="utf-8-sig")
        return dataframe
    elif lecture:
        print("La lecture n'a pas été faite car l'extension n'est pas en csv.")
    else:
        return path

def round_100_per_cent_sum(liste_pourcentages):
    somme_base = sum(liste_pourcentages)
    if somme_base>100:
        raise Exception('La somme de base dépasse 100%, erreur dans les chiffres.')
    else:
        if 100-somme_base<0.5:
            return liste_pourcentages
        else:
            somme = math.floor(somme_base)
            while somme != 100:
                liste_diff = [math.ceil(pourcentage)-pourcentage for pourcentage in liste_pourcentages]
                min_diff = min(liste_diff)

def is_in(pattern,string):
    if re.search(pattern,string):
        return True
    else:
        return False

def insert_in_list_by_date(title_and_date:tuple,liste:list):
    title,date=title_and_date
    date_time = time.strptime(date.split()[0],'%Y-%m-%d')
    if len(liste)==0:
        liste.append((title,date_time))
        return liste
    i=0
    for _,date_temp in liste:
        if date_temp>date_time:
            break
        else:
            i+=1
    if i==0:
        return [(title,date_time)]+liste
    elif i==len(liste):
        return liste + [(title,date_time)]
    else:
        return liste[:i-1] + [(title,date_time)] + liste[i:]
