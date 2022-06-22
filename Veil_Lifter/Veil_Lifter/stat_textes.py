import os

def taille_du_corpus(corpus='textes_fr'):
    """Effectue le calcul de la taille du corpus.
    Retourne le nombre de textes, la taille du corpus en signes, la moyenne signes/texte, la variance du set de données et
    l'écart-type du set de données.
    
    corpus -> str, position du répertoire du corpus"""
    liste_textes = os.listdir(corpus)
    nb_textes = len(liste_textes)
    somme= 0
    val_pour_var = []
    for nom_file in liste_textes:
        file = open(corpus+"/"+nom_file,'r',encoding="utf-8")
        val_pour_var.append(len(file.read()))
        somme += val_pour_var[len(val_pour_var)-1]
    moyenne = somme / nb_textes
    total_signe = sum(val_pour_var)
    val_pour_var = [(val - moyenne)**2 for val in val_pour_var]
    variance = sum(val_pour_var)/(nb_textes-1)
    ecart_type = variance**0.5
    return nb_textes,total_signe,round(moyenne,3),round(variance,3),round(ecart_type,3)