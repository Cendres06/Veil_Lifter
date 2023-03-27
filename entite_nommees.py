from venv import create
from semtokenizers import french
import re
from pathlib import Path
from lxml import etree
from scrapping_bs4 import slug_to_nom_fichier,path_extension,ressources_de_travail,chronologie_non_organisee
import pandas as pd
import datetime
import timeline
import glob
import os
import visualisation
import operator
import numpy as np

# Ce document a été créé sous la direction de Yoann Dupont de l'ObTIC le 26/07/2022, puis modifié par mes soins.
#Vise l'utilisation de spacy : https://github.com/YoannDupont/train_spacy

def enlever_tab(texte):
    texte = re.sub('\n\s+',' ',texte)
    texte = re.sub("''",'"',texte)
    #texte = re.sub('█','X',texte)
    return re.sub('”|“','\"',texte)

def to_brat(chemin_entree, chemin_sortie,debug=False):
    """Transforme un fichier .xml en .brat

    Parameters
    ----------
    chemin_entree : str
        Chemin d'entrée du fichier à transformer
    chemin_sortie : str
        Chemin de sortie du fichier transformé
    """

    arbre = etree.parse(chemin_entree)

    noeud_texte = next(arbre.iterfind(".//{*}text"))

    liste_morc_texte = [enlever_tab(noeud_texte.text or '')]

    pos_debut = len(liste_morc_texte[0])

    liste_entites = []
    for rs in list(noeud_texte):
        if debug:
            print(rs.attrib,rs.text)
        etiquette=rs.attrib['type']
        texte = enlever_tab(rs.text)
        texte_apres = enlever_tab(rs.tail or '')
        pos_fin = pos_debut + len(texte)
        liste_entites.append((pos_debut, pos_fin, etiquette))
        liste_morc_texte.append(texte)
        liste_morc_texte.append(texte_apres)
        pos_debut = pos_fin + len(texte_apres)
    
    texte_global = "".join(liste_morc_texte)

    for entite in liste_entites:
        pos_debut,pos_fin,etiquette = entite
        if debug:
            print(entite,'"'+texte_global[pos_debut:pos_fin]+'"')
    
    with open(chemin_sortie+".txt",'w',encoding="utf-8") as file:
        file.write(texte_global)
    
    with open(chemin_sortie+'.ann',"w",encoding="utf-8") as file:
        for index,entite in enumerate(liste_entites):
            pos_debut,pos_fin,etiquette = entite
            texte = texte_global[pos_debut:pos_fin]
            file.write(f'T{index}\t{etiquette} {pos_debut} {pos_fin}\t{texte}\n')

def exemples_to_brat(chemin='..\..\\textes_fr_annotes',debug=False):
    path = Path(chemin)
    for fichier_annote in path.glob('*.xml'):
        to_brat(
            r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\textes_fr_annotes\\'+fichier_annote.stem+r'.xml',
            r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\textes_fr_brat\\'+fichier_annote.stem,
            debug=debug
        )

#exemples_to_brat()

def to_conll(dossier_entree,chemin_sortie,debug=False):
    chemin_dossier = Path(dossier_entree)
    with open(chemin_sortie,'w',encoding='utf-8') as file_conll:
        for fichier_ann in chemin_dossier.glob('*.ann'):
            fichier_texte = chemin_dossier / (fichier_ann.stem + '.txt')
            with open(fichier_texte,'r',encoding="utf-8") as file_txt :
                texte = file_txt.read()
            token_spans = french.word_spans(texte)
            sentence_spans = french.sentence_spans(texte,token_spans)

            with open(fichier_ann,encoding="utf-8") as file_ann :
                liste_entites = []
                for line in file_ann:
                    line = line.strip()
                    if not line:
                        continue
                    annotation = line.split('\t')[1]
                    etiquette,pos_debut,pos_fin = annotation.split()
                    liste_entites.append([etiquette,int(pos_debut),int(pos_fin)])
            
            liste_entites_tokens = []
            for etiquette,pos_debut,pos_fin in liste_entites :
                for num,token in enumerate(token_spans) :
                    if pos_debut == token.start :
                        pos_debut_token = num
                    if pos_fin == token.end :
                        pos_fin_token = num+1
                        liste_entites_tokens.append([etiquette,pos_debut_token,pos_fin_token])
                        break
                else: #On sort de la boucle for sans être passé par le break : pas ajouter l'entité
                    if debug:
                        print('Dans :',file_ann.name)
                        print(etiquette,pos_debut,"(token :",str(pos_debut_token)+")",str(pos_fin))
                        print('"'+texte[pos_debut:pos_fin]+'"')
                        print()
                
            tokens = [texte[token.start:token.end] for token in token_spans]

            bio = ['O' for token in token_spans]
            for etiquette,pos_debut,pos_fin in liste_entites_tokens:
                bio[pos_debut] = f'B-{etiquette}'
                for pos in range(pos_debut+1,pos_fin):
                    bio[pos] = f'I-{etiquette}'
        
        file_conll.write('-DOCSTART- -X- O O\n\n')
        document = list(zip(tokens,bio))
        for sentence in sentence_spans :
            sentence_tokens = document[sentence.start:sentence.end]
            for paire in sentence_tokens:
                file_conll.write('\t'.join(paire)+'\n')
            file_conll.write('\n')

#to_conll(r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\spacy_eval\évaluation_des_résultats_26-08-22\évaluation des résultats\corpus_test_verif',    r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\spacy_eval\évaluation_des_résultats_26-08-22\évaluation des résultats\corpus_test_verif.conll',debug=True)
#to_conll(r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\spacy_eval\évaluation_des_résultats_26-08-22\évaluation des résultats\corpus_entrainement',r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\spacy_eval\évaluation_des_résultats_26-08-22\évaluation des résultats\corpus_entrainement.conll',debug=True)

#to_conll(r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\sem_textes_fr_brat', r'C:\Users\Perrine\Documents\Document\Scolaire\Master_Humanités_Numériques\M1\Codes_mémoire\sem_texte_fr_conll\sem_textes_fr_conll.txt',debug=True)

def remplace_accent(word):
    word = re.subn(re.compile('ê|è|é|ë'),'e',word)[0]
    word = re.subn(re.compile('Ê|È|É|Ë'),'E',word)[0]

    word = re.subn(re.compile('ï|î'),'i',word)[0]
    word = re.subn(re.compile('Ï|Î'),'I',word)[0]

    word = re.subn(re.compile('û|ù|ü'),'u',word)[0]
    word = re.subn(re.compile('Û|Ù|Ü'),'U',word)[0]

    word = re.subn(re.compile('ô|ö'),'o',word)[0]
    word = re.subn(re.compile('Ô|Ö'),'O',word)[0]

    word = re.subn(re.compile('â|à|ä'),'a',word)[0]
    word = re.subn(re.compile('Â|À|Ä'),'A',word)[0]

    return(word)

def leven(x, y,diff_accent=False,diff_maj=False):
    """Fonction créée par Khaleel O.
    https://devrescue.com/levenshtein-distance-in-python/ """
    if not diff_accent:
        x = remplace_accent(x)
        y = remplace_accent(y)
    if not diff_maj:
        x = x.lower()
        y = y.lower()
    n = len(x)
    m = len(y)

    A = [[i + j for j in range(m + 1)] for i in range(n + 1)]

    for i in range(n):
        for j in range(m):
            A[i + 1][j + 1] = min(A[i][j + 1] + 1,              # insert
                                  A[i + 1][j] + 1,              # delete
                                  A[i][j] + int(x[i] != y[j]))  # replace

    return A[n][m]


def pourcentage_difference(chaine1,chaine2):
    distance = leven(chaine1,chaine2)
    diff = abs(len(chaine1)-len(chaine2))
    calcul = (distance + diff)/(max(len(chaine1),len(chaine2)))*100
    return calcul

def dico_entite(nom,chemin='..\..\\bases_de_donnees\echantillon\\',debug=False):
    dico = {}
    if chemin[-1]!='\\':
        chemin += '\\'
    if re.match(re.compile('EN_'),nom):
        path = chemin+nom
    else:
        path=chemin+'EN_'+nom
    if not re.match(re.compile('.txt'),path[-1:-5]):
        path+='.txt'
    if debug:
        print('Chemin :',path,'\n')
    with open(path,'r',encoding='utf-8') as file:
        for line in file:
            line = re.sub('\n','',line)
            if debug:
                print('On examine la ligne :')
                print(line)
            line = line.split('\t')
            if debug:
                print('On divise :')
                print(line)
            declinaisons = line[1].split('|')
            if debug:
                print('Les déclinaisons de l\'EN sont :')
                print(declinaisons)
            types = line[2].split('|')
            if debug:
                print('Les différents types de l\'EN sont :')
                print(types)
            dico[line[0]]=(declinaisons,types)
            if debug:
                print('On rajoute au dictionnaire l\'entrée suivante :')
                print('dico[',line[0],'] = ('+declinaisons+',',types+')','\n')
    return dico

#print('Faire dico SAPHIR')
dico_SAPHIR = dico_entite('SAPHIR')
print('Fait dico SAPHIR')

def string_list_to_list(string):
    string = string[1:-1]
    string = re.sub('\'',"",string)
    liste = string.split(', ')
    return liste

def dico_to_requetes(dico,debug=False):
    #re.compile -> flags, ignore case ?
    # re.compile('A',flags=re.I)
    if debug:
        print('Dico :','\n',dico,'\n')
    dico_regex = {}
    for clef_entite in dico.keys():
        if debug:
            print('\n','On étudie la clef d\'entité :',clef_entite,'\n')
        derivations = dico[clef_entite][0]
        requetes=[]
        types = dico[clef_entite][1]
        for derivation in derivations:
            if debug:
                print('On étudie sa dérivation :',derivation,'\n')
            requete=''
            for char in derivation:
                if char in ['.','\\','/','+','?','(',')','[',']','*','^','$','"']:
                    requete+='\\'+char
                elif re.match(re.compile('[A-Za-zéàïëüöèêâîäôûù]'),char):
                    if re.search(re.compile('[a-zéàïëüöèêâîäôûù]'),derivation):
                        requete+='['+char.lower()+char.upper()+']'
                    else:
                        requete+=char
                else:
                    requete+=char
            if debug:
                print('Requête pour la dérivation :',requete,'\n')
            requetes.append(re.compile(requete))
        dico_regex[clef_entite]=(requetes,types)

    return dico_regex

dico_regex = dico_to_requetes(dico_SAPHIR)
#print(dico_regex)

#ICI modifier les prochaines fonctions utilisant dico_regex qui sont cassées à cause du rajout de types

def cherche_regex_dans_textes(bd,dico_requetes):
    donnees = path_extension(bd,lecture=True)
    donnees = donnees[['id','nom_fichier']]
    nom_fichiers = donnees['nom_fichier'].values

    dico_trouve = {}

    for nom_fichier in nom_fichiers:
        chemin = path_extension(nom_fichier,False,'../../textes_fr',extension='txt')
        ligne = donnees.loc[donnees['nom_fichier']==nom_fichier]
        id = ligne['id'].values[0]

        dico_trouve[id]=[]
        with open(chemin,'r',encoding='utf-8') as file:
            texte = file.read()
            for clef_entite in dico_requetes.keys():
                for requete in dico_requetes[clef_entite]:
                    if re.search(requete,texte):
                        dico_trouve[id].append(clef_entite)
                        break
    
    dico_trouve['total']=dico_requetes.keys()

    return dico_trouve

res_regex=cherche_regex_dans_textes('bd_ENs_SAPHIR',dico_regex)
#print(res_regex)

#def cherche_regex_dans_texte(a,dico_requetes):

def regex_vs_sem(bd,dico_regex_trouve,debug=False):
    donnees_sem = path_extension(bd,lecture=True)[['id','entitées nommées']]
    #sem en référence

    total = list(dico_regex_trouve[list(dico_regex_trouve.keys())[-1]])
    if debug:
        print(total)
        print(type(total))

    predicted = []
    actual = []

    vp = 0
    fp = 0
    fn = 0
    vn = 0

    for id_page in list(dico_regex_trouve.keys())[:-1]:
        ligne = donnees_sem.loc[donnees_sem['id'] == id_page]
        toutes_en_str = ligne['entitées nommées'].values[0]
        toutes_en = string_list_to_list(toutes_en_str)
        en_regex = dico_regex_trouve[id_page]
        if debug:
            print(en_regex)
            print(toutes_en,'\n')
        for entite in total:
            if entite in toutes_en:
                actual.append(True)
                if entite in en_regex:
                    predicted.append(True)
                    if debug:
                        print(entite,'dans les deux pred. VP')
                    vp+=1
                else:
                    predicted.append(False)
                    if debug:
                        print(entite,'dans la pred sem seulement. FN')
                    fn+=1
            else:
                actual.append(False)
                if entite in en_regex:
                    predicted.append(True)
                    if debug:
                        print(entite,'dans la pred regex seulement. FP')
                    fp+=1
                else:
                    predicted.append(False)
                    if debug:
                        print(entite,'dans aucune pred. VN')
                    vn+=1

    if debug:
        print(len(predicted))
        print(len(actual))

    return predicted,actual,vp,fp,fn,vn,vp+fp+fn+vn,len(dico_regex_trouve[list(dico_regex_trouve.keys())[-1]])*len(list(dico_regex_trouve.keys())[:-1])

compare_sem_regex=regex_vs_sem('bd_ENs_SAPHIR',res_regex)
predicted = compare_sem_regex[0]
actual = compare_sem_regex[1]

visualisation.confusion_matrice(predicted,actual)

def test_rajouter_ou_enlever_caractere(chaine1,chaine2,diff_accent=False,diff_maj=False):
    if len(chaine1)==len(chaine2):
        return False
    elif len(chaine1)<len(chaine2):
        chaine_plus_courte=chaine1
        chaine_plus_longue=chaine2
    else:
        chaine_plus_courte=chaine2
        chaine_plus_longue=chaine1
    
    if not diff_accent:
        chaine_plus_courte = remplace_accent(chaine_plus_courte)
        chaine_plus_longue = remplace_accent(chaine_plus_longue)
    if not diff_maj:
        chaine_plus_longue = chaine_plus_longue.lower()
        chaine_plus_courte = chaine_plus_courte.lower()

    ordre_cara = [*chaine_plus_courte]

    for char in ordre_cara:
        if not char in chaine_plus_longue:
            return False
        else:
            pos_char = chaine_plus_longue.rfind(char)
            if pos_char == len(chaine_plus_longue)-1:
                chaine_plus_longue=''
            else:
                chaine_plus_longue = chaine_plus_longue[pos_char:]
    
    return True

def recup_EN_BRAT(nom,chemin='..\..\sem_textes_fr_brat'):
    if chemin[-1]!='\\':
        chemin += '\\'
    path = chemin+nom
    if not re.match(re.compile('\.ann'),path[-4:]):
        path+='.ann'

    if not Path(path).is_file():
        return None

    pattern_nom_en = re.compile('T[0-9]+\t(\w+) [0-9]+ [0-9]+\t(.+)')

    with open(path,'r',encoding='utf-8') as file:
        ann_complet = file.read()
    
    toutes_EN = list(set(re.findall(pattern_nom_en,ann_complet)))

    return (toutes_EN)

def compar_BRAT_dico(nom,dico,chemin='..\..\sem_textes_fr_brat',debug=False):
    #évacuer les mots vides comme déterminant
    #supprimer les comparaisons pour les éléments extrêmement précis comme 'SCP-XXX-FR', ou extrêmement vides comme les barres de censure avec ou sans espace, avec ou sans tiret.
    #faire une liste des éléments les plus proches et seulement si on a trouvé aucune correspondance exacte on parcourt le reste. Avec les brak de for.
    "Si taille du mot > certaine_taille ET qu'il est entièrement contenu tel quel dedans"

    toutes_EN = recup_EN_BRAT(nom,chemin)
    if not toutes_EN:
        return None

    if debug:
        print('EN du fichier .ann :',toutes_EN,'\n')

    dico_ENs_cherchees_trouvees = {}

    if type(dico) == str:
        dico = dico_entite(dico)
    clefs = [*dico.keys()]
    if debug:
        print('Dictionnaire de travail :',clefs,'\n')

    for type_en,entite in toutes_EN:
        if debug:
            print('On étudie l\'entité',entite,'de type',type_en+'.\n')
        for clef_entite in clefs:
            if debug:
                print('On compare l\'entité',entite,'à l\'entrée du dictionnaire',clef_entite+'.\n')
            for derivation in dico[clef_entite][0]:
                if debug:
                    print('On regarde la dérivation',derivation+'.\n')
                if derivation==entite:
                    if debug:
                        print('La dérivation convient !')
                    if type_en in dico[clef_entite][1]:
                        if debug:
                            print('Le type convient !')
                        if clef_entite not in dico_ENs_cherchees_trouvees.keys():
                            dico_ENs_cherchees_trouvees[clef_entite]=1
                        else:
                            dico_ENs_cherchees_trouvees[clef_entite]+=1
                        print('\n')
                        break
                    else:
                        print('L\'entité nommée étudiée correspond bien à une entitée nommée du dictionnaire, mais elle n\'a pas le même type.')
                        print('Entité nommée :',entite,'de type',type_en)
                        print('Types possibles :',dico[clef_entite][1],'pour l\'entité de clef :',clef_entite)
                        ask = input('Voulez-vous assimiler cette entité nommée à l\'entité clef ? (y/n) : ')
                        while ask not in ['y','n']:
                            ask = input('Voulez-vous assimiler cette entité nommée à l\'entité clef ? (y/n) : ')
                        print('\n')
                        if ask=='y':
                            dico[clef_entite][1].append(type_en)
                            if clef_entite not in dico_ENs_cherchees_trouvees.keys():
                                dico_ENs_cherchees_trouvees[clef_entite]=1
                            else:
                                dico_ENs_cherchees_trouvees[clef_entite]+=1
                            break
                elif pourcentage_difference(derivation,entite)<=30.0 or (test_rajouter_ou_enlever_caractere(derivation,entite) and pourcentage_difference(derivation,entite)<=40.0):
                    if debug:
                        print('Pourcentage :',pourcentage_difference(derivation,entite),' ; rajout de caractères :',test_rajouter_ou_enlever_caractere(derivation,entite))
                    print('Entité nommée étudiée:',entite)
                    print('Dérivation :',derivation)
                    print('L\'entité de clef :',clef_entite)
                    ask = input('Confirmez-vous une parenté ? (y/n) : ')
                    while ask not in ['y','n']:
                        ask = input('Confirmez-vous une parenté ? (y/n) : ')
                    print('\n')
                    if ask=='y':
                        if clef_entite not in dico_ENs_cherchees_trouvees.keys():
                            dico_ENs_cherchees_trouvees[clef_entite]=1
                        else:
                            dico_ENs_cherchees_trouvees[clef_entite]+=1
                        break
            else:
                continue
            break
    
    return dico_ENs_cherchees_trouvees

def recherche_EN_ensemble_textes(ressources,nom_bd,dico,chemin='..\..\sem_textes_fr_brat',freq=False):
    bd_textes_fr = pd.DataFrame(columns=['id','nom_fichier','entitées nommées'])

    for slug in ressources:
        nom_fichier = slug_to_nom_fichier(slug,extension=False)

        entites_nommees = compar_BRAT_dico(nom_fichier,dico,chemin)
        if not entites_nommees:
            continue

        donnees = {'id':slug,'nom_fichier':nom_fichier,'entitées nommées':list(entites_nommees.keys())}
        bd_textes_fr.loc[slug] = pd.Series(donnees)
    
    path = path_extension('bd_'+nom_bd)
    bd_textes_fr.to_csv(path, index=False,encoding="utf-8-sig")


#textes_saphir = ressources_de_travail(liste_tags_format=['conte','scp'],liste_tags_necessaire=['saphir'],liste_tags_interdits=['expliqué','centre','annexe','fanart','aile-fr','aile-en','fragment','gazette-aleph','dans-les-coulisses'],liste_combinaisons_interdites=[('humour','scp')])
#recherche_EN_ensemble_textes(textes_saphir,'ENs_SAPHIR',dico_SAPHIR)

def entites_nommees_plus_frequentes(ressources,dico,chemin='..\..\sem_textes_fr_brat',freq=20,bypass=False):
    #si freq float, c'est qu'on cherche une fréquence minimale ? un peu bête
    frequences = {}

    if not bypass:
        for slug in ressources:
            nom_fichier = slug_to_nom_fichier(slug,extension=False)
            entites_nommees = compar_BRAT_dico(nom_fichier,dico,chemin)

            if not entites_nommees:
                continue

            for clef_entite in entites_nommees.keys():
                if clef_entite not in frequences.keys():
                    frequences[clef_entite]=entites_nommees[clef_entite]
                else:
                    frequences[clef_entite]+=entites_nommees[clef_entite]

            print(frequences)
            a=input(' : ')

        path = path_extension('sauvegarde_dico_freq',chemin='..\..\\')
        df = pd.DataFrame(frequences,index=frequences.keys())
        df.to_csv(path,encoding='utf-8-sig')        
    else:
        df = pd.read_csv(path_extension('sauvegarde_dico_freq',chemin='..\..\\'),encoding='utf-8-sig').iloc[0]
        for i in range(len(df.index)):
            frequences[df.index[i]]=df.loc[df.index[i]]

    frequences.pop('Unnamed: 0')
    print(frequences)

    liste_res = sorted(frequences.items(), key=operator.itemgetter(1),reverse=True)
    print(liste_res)

    if len(frequences.keys())<=freq:
        return liste_res
    else:
        return liste_res[:freq]


#print(entites_nommees_plus_frequentes(textes_saphir,dico_SAPHIR,bypass=True))

def pourcentages_EN_type(chemin='..\..\sem_textes_fr_brat'):

    wd = os.getcwd()
    path = chemin + '\\'
    os.chdir(path)
    files_names = glob.glob('*.ann')
    os.chdir(wd)

    etre = 0
    objet = 0
    lieu = 0
    groupe = 0
    administratif = 0
    oeuvre = 0
    evenement = 0
    phenomene = 0
    total_EN = 0

    for file_name in files_names:
        toutes_EN = recup_EN_BRAT(file_name)
        total_EN+=len(toutes_EN)
        for type,_ in toutes_EN:
            if type=='être':
                etre+=1
            elif type=='objet':
                objet+=1
            elif type=='lieu':
                lieu+=1
            elif type=='groupe':
                groupe+=1
            elif type=='administratif':
                administratif+=1
            elif type=='oeuvre':
                oeuvre += 1
            elif type=='événement':
                evenement+=1
            elif type=='phénomène':
                phenomene+=1
            else:
                print('Type non reconnu :',type)
    
    dico = {}
    dico['être'] = round(etre*100/total_EN,2)
    dico['objet'] = round(objet*100/total_EN,2)
    dico['lieu'] = round(lieu*100/total_EN,2)
    dico['groupe'] = round(groupe*100/total_EN,2)
    dico['administratif'] = round(administratif*100/total_EN,2)
    dico['oeuvre'] = round(oeuvre*100/total_EN,2)
    dico['événement'] = round(evenement*100/total_EN,2)
    dico['phénomène'] = round(phenomene*100/total_EN,2)
    dico['total'] = total_EN

    return dico

#donnees = pourcentages_EN_type()
#visualisation.csv_camembert_normal(donnees,'pourcentages_EN_BRAT_V1')


def point_depart_entite(clef_entite,bd_affilie,bd_complet='bd_fr',debug=False):

    bd_affilie = path_extension(bd_affilie,lecture=True)
    if debug:
        print('La BDD affiliée à l\'entité a été chargée :\n',bd_affilie)

    donnees = path_extension(bd_complet,lecture=True)
    donnees = donnees[['id','Auteurice(s)','Date de création']]

    if debug:
        print('\nLa BDD complète a été chargée :\n',donnees)

    best_date = datetime.datetime.now()
    auteur = ['']
    texte_origine = ''

    for i in range(bd_affilie.shape[0]):
        ligne = bd_affilie.iloc[i]
        if debug:
            print('\n On vérifie si la ligne n°'+str(i),'contient la clef')
        entites = string_list_to_list(ligne['entitées nommées'])
        if debug:
            print('\n ENs :',entites)
        if clef_entite in entites:
            
            id_page = bd_affilie['id'].loc[i]
            if debug:
                print('\nClef trouvée dans le texte :',id_page)
            ligne_bd = donnees.loc[donnees['id'] == id_page]
            if debug:
                print('\nOn va chercher dans les données complètes :',ligne_bd)
            #Problème avec "/trouver-l-absolution"
            if not ligne_bd.empty:
                if debug:
                    print('\nOn a trouvé.')
                date_candidate = ligne_bd['Date de création'].values[0]
                if debug:
                    print('\nDate :',date_candidate)
                    print('On compare avec la date :',best_date)
                    print('Why')
                    print('Statut :',datetime.datetime.strptime(date_candidate[:10],"%Y-%m-%d") < best_date)
                if datetime.datetime.strptime(date_candidate[:10],"%Y-%m-%d") < best_date:
                    if debug:
                        print('\nMeilleure date que :',best_date)
                    best_date = datetime.datetime.strptime(date_candidate[:10],"%Y-%m-%d")
                    auteur = ligne_bd['Auteurice(s)'].values[0]
                    texte_origine = id_page
                    if debug:
                        print('\n Nouvelle solution :',best_date,auteur,texte_origine)
    
    if auteur == ['']:
        return None
    else:
        if debug:
            print('On retourne la solution.')
        return best_date,auteur,texte_origine

def origine_all_dico(dico,bd_affilie,bd_complet='bd_fr',filtre=False):
    clefs = dico.keys()
    dico_origine = {}
    for clef_entite in clefs:
        if filtre:
            if clef_entite in filtre:
                dico_origine[clef_entite]=point_depart_entite(clef_entite,bd_affilie,bd_complet)
        else:
            dico_origine[clef_entite]=point_depart_entite(clef_entite,bd_affilie,bd_complet)

    return dico_origine

sauvegarde_SAPH_20plusfreq = [('SAPHIR', 50), ('SAPHIR_Dieu', 31), ('SCP-393-FR', 10), ('FIMOmega-5', 7), ('SAPHIR_anomalie', 7), ('SCP-496-FR', 7), ('SAPHIR_devise', 5), ('SAPHIR_Pierre_Alain', 5), ('SCP-227-FR', 5), ('SAPHIR_RUBIS', 4), ('SAPHIR_Pierre_Hsing', 4), ('SAPHIR_GRENAT', 4), ('SAPHIR_Laurence_Melklior', 4), ('SAPHIR_Solomon_D██████', 4), ('SAPHIR_Pietro_Bozonni', 3), ('SCP-164-FR', 3), ('SAPHIR_EMERAUDE', 3), ('SAPHIR_James_X', 3), ('Syndrome_Fibulson', 3), ('SCP-482-FR', 3)]
filtre = [clef for clef,_ in sauvegarde_SAPH_20plusfreq]

dico_SAPHIR_origine = origine_all_dico(dico_SAPHIR,'bd_ENs_SAPHIR','bd_fr',filtre=filtre)

def create_timeline_origine(dico_origine):
    names = dico_origine.keys()
    valeurs = [tuple for tuple in dico_origine.values() if tuple != None]
    dates = [date for date,_,_ in valeurs]

    timeline.plot_timeline(names,dates)

#create_timeline_origine(dico_SAPHIR_origine)

#textes_saphir = ressources_de_travail(liste_tags_format=['conte','scp'],liste_tags_necessaire=['saphir'],liste_tags_interdits=['expliqué','centre','annexe','fanart','aile-fr','aile-en','fragment','gazette-aleph','dans-les-coulisses'],liste_combinaisons_interdites=[('humour','scp')],debug=True)

def create_timeline_textes(ressources,titre):
    dates = chronologie_non_organisee(ressources)

    timeline.plot_timeline(ressources,dates,titre)

#create_timeline_textes(textes_saphir,'Chronologie des textes de SAPHIR')

def create_timeline_auteurs(ressources,titre,nom_bd='bd_fr',debug=False):
    if debug:
        print(ressources)
        print(len(ressources))

    donnees = path_extension(nom_bd,lecture=True)
    valeurs = []
    textes_exclure = []
    ind = 0
    for id_page in ressources:
        if debug:
            print(id_page)
        ligne_bd = donnees.loc[donnees['id'] == id_page]
        auteurices = ligne_bd['Auteurice(s)'].values
        if debug:
            print(auteurices)
        if not np.any(auteurices):
            if debug:
                print('On supprime',id_page)
            textes_exclure.append(id_page)
        else:
            str_auteurices = ''
            if len(auteurices)>1:
                for i in range(len(auteurices)):
                    auteurice_temp = auteurices[i]
                    if i == len(auteurices)-1:
                        str_auteurices+="& "+auteurice_temp
                    elif i == len(auteurices)-2:
                        str_auteurices+=auteurice_temp+" "
                    else:
                        str_auteurices+=auteurice_temp+", "
                valeurs.append(str_auteurices)
            else:
                valeurs.append(auteurices[0])
            ind +=1

    print(len(valeurs))

    pages_correctes = [id_page for id_page in ressources if id_page not in textes_exclure]

    if debug:
        print(pages_correctes)
        print(len(pages_correctes))

    dates = chronologie_non_organisee(pages_correctes)

    if debug:
        print(dates)
        print(len(dates))

    if debug:
        print(dates)
        print(valeurs)
        print(len(dates),len(valeurs))

    #timeline.plot_timeline(valeurs,dates,titre)
    timeline.plot_timeline(valeurs,dates,titre,valeurs[dates.index(min(dates))])

#create_timeline_auteurs(textes_saphir,titre='Auteur·ice·s des textes liés à SAPHIR')

def UNUSED_compar_BRAT_dico(nom,dico,nom_dico,chemin='..\..\sem_texte_fr_brat',maj_dico=True,debug=False):
    """Non fonctionnel (tourne infiniment,erreurs nettes d'identification positive d'une parenté)"""
    toutes_EN = recup_EN_BRAT(nom,chemin)
    if debug:
        print('EN du fichier .ann :',toutes_EN,'\n')

    liste_ENs_cherchees_trouvees = []

    if type(dico) == str:
        dico = dico_entite(dico)
    clefs = [*dico.keys()]
    if debug:
        print('Dictionnaire de travail :',clefs,'\n')

    for type_en,entite in toutes_EN:
        if debug:
            print('On étudie l\'entité',entite,'de type',type_en+'.\n')
        for clef_entite in clefs:
            if debug:
                print('On compare l\'entité',entite,'à l\'entrée du dictionnaire',clef_entite+'.\n')
            for derivation in dico[clef_entite][0]:
                if debug:
                    print('On regarde la dérivation',derivation+'.\n')
                if derivation==entite:
                    if debug:
                        print('La dérivation convient !')
                    if type_en in dico[clef_entite][1]:
                        if debug:
                            print('Le type convient !')
                        if clef_entite not in liste_ENs_cherchees_trouvees:
                            liste_ENs_cherchees_trouvees.append(clef_entite)
                        break
                    else:
                        print('L\'entité nommée étudiée correspond bien à une entitée nommée du dictionnaire, mais elle n\'a pas le même type.')
                        print('Entité nommée :',entite,'de type',type_en)
                        print('Types possibles :',dico[clef_entite][1],'pour l\'entité de clef :',clef_entite)
                        print('Voulez-vous rajouter à l\'entrée du dictionnaire déjà existente (r), créer une nouvelle entrée pour l\'entitée nommée étudiée (c) ou ne rien faire et passer à la comparaison suivante (n) ?')
                        ask = input('Rajouter (r) / Créer nouvelle (c) / Ne rien faire (n) : ')
                        while ask not in ['r','c','n']:
                            ask = input('Rajouter (r) / Créer nouvelle (c) / Ne rien faire (n) : ')
                        if ask=='r':
                            dico[clef_entite][1].append(type_en)
                            if clef_entite not in liste_ENs_cherchees_trouvees:
                                liste_ENs_cherchees_trouvees.append(clef_entite)
                            break
                        elif ask=='c':
                            new_clef=''
                            while new_clef=='':
                                new_clef = input('Veuillez entrer le nouveau nom de l\'entite : ')
                                if ' ' in new_clef:
                                    print('Erreur : espace dans le nom de la clef. Veuillez réessayer.')
                                    new_clef=''
                                elif new_clef=='':
                                    print('Erreur : le nom de la clef ne peut être vide. Veuillez réessayer.')
                                else:
                                    ask = input('Le nouveau nom de l\'entité serait :',new_clef+'. Confirmez-vous ? (y/n) : ')
                                    while ask not in ['y','n']:
                                        ask = input('Confirmez-vous ? (y/n) : ')
                                    if ask == 'n':
                                        new_clef=''
                                    else:
                                        if not re.match(re.compile(nom_dico),new_clef):
                                            print('En ajoutant le nom du dictionnaire avant celui de l\'entité, cela donne le nom :',nom_dico+'_'+new_clef)
                                            ajout_nom_dico = input('Voulez-vous ajouter le nom du dictionnaire avant ? (y/n) : ')
                                            while ajout_nom_dico not in ['y','n']:
                                                ajout_nom_dico = input('Confirmez-vous ? (y/n) : ')
                                            if ajout_nom_dico=='y':
                                                new_clef = nom_dico+'_'+new_clef
                            dico[new_clef]=([entite],[type_en])
                            break
                elif test_rajouter_ou_enlever_caractere(derivation,entite):
                    print('L\'entité nommée étudiée peut correspondre à une entitée nommée du dictionnaire : elle est contenue dans une dérivation ou la dérivation contient l\'entité étudiée.')
                    print('Entité nommée étudiée:',entite)
                    print('Dérivation :',derivation)
                    print('L\'entité de clef :',clef_entite)
                    ask = input('Confirmez-vous une parenté ? (y/n) : ')
                    while ask not in ['y','n']:
                        ask = input('Confirmez-vous une parenté ? (y/n) : ')
                    if ask=='y':
                        if type_en in dico[clef_entite][1]:
                            if debug:
                                print('Le type convient !')
                            dico[clef_entite][0].append(entite)
                            if clef_entite not in liste_ENs_cherchees_trouvees:
                                liste_ENs_cherchees_trouvees.append(clef_entite)
                            break
                        else:
                            print('L\'entité nommée étudiée correspond bien à une entitée nommée du dictionnaire, mais elle n\'a pas le même type.')
                            print('Entité nommée :',entite,'de type',type_en)
                            print('Types possibles :',dico[clef_entite][1],'pour l\'entité de clef :',clef_entite)
                            print('Voulez-vous rajouter à l\'entrée du dictionnaire déjà existente (r), créer une nouvelle entrée pour l\'entitée nommée étudiée (c) ou ne rien faire et passer à la comparaison suivante (n) ?')
                            ask = input('Rajouter (r) / Créer nouvelle (c) / Ne rien faire (n) : ')
                            while ask not in ['r','c','n']:
                                ask = input('Rajouter (r) / Créer nouvelle (c) / Ne rien faire (n) : ')
                            if ask=='r':
                                dico[clef_entite][0].append(entite)
                                dico[clef_entite][1].append(type_en)
                                if clef_entite not in liste_ENs_cherchees_trouvees:
                                    liste_ENs_cherchees_trouvees.append(clef_entite)
                                break
                            elif ask=='c':
                                new_clef=''
                                while new_clef=='':
                                    new_clef = input('Veuillez entrer le nouveau nom de l\'entite : ')
                                    if ' ' in new_clef:
                                        print('Erreur : espace dans le nom de la clef. Veuillez réessayer.')
                                        new_clef=''
                                    elif new_clef=='':
                                        print('Erreur : le nom de la clef ne peut être vide. Veuillez réessayer.')
                                    else:
                                        ask = input('Le nouveau nom de l\'entité serait :',new_clef+'. Confirmez-vous ? (y/n) : ')
                                        while ask not in ['y','n']:
                                            ask = input('Confirmez-vous ? (y/n) : ')
                                        if ask == 'n':
                                            new_clef=''
                                        else:
                                            if not re.match(re.compile(nom_dico),new_clef):
                                                print('En ajoutant le nom du dictionnaire avant celui de l\'entité, cela donne le nom :',nom_dico+'_'+new_clef)
                                                ajout_nom_dico = input('Voulez-vous ajouter le nom du dictionnaire avant ? (y/n) : ')
                                                while ajout_nom_dico not in ['y','n']:
                                                    ajout_nom_dico = input('Confirmez-vous ? (y/n) : ')
                                                if ajout_nom_dico=='y':
                                                    new_clef = nom_dico+'_'+new_clef
                                dico[new_clef]=([entite],[type_en])
                                break
                elif pourcentage_difference(derivation,entite)<=0.3:
                    print('Il y a une grande similarité entre l\'entité nommée étudiée et une entité du dictionnaire.')
                    print('Entité nommée étudiée:',entite)
                    print('Dérivation :',derivation)
                    print('L\'entité de clef :',clef_entite)
                    ask = input('Confirmez-vous une parenté ? (y/n) : ')
                    while ask not in ['y','n']:
                        ask = input('Confirmez-vous une parenté ? (y/n) : ')
                    if ask=='y':
                        if type_en in dico[clef_entite][1]:
                            if debug:
                                print('Le type convient !')
                            dico[clef_entite][0].append(entite)
                            if clef_entite not in liste_ENs_cherchees_trouvees:
                                liste_ENs_cherchees_trouvees.append(clef_entite)
                            break
                        else:
                            print('L\'entité nommée étudiée correspond bien à une entitée nommée du dictionnaire, mais elle n\'a pas le même type.')
                            print('Entité nommée :',entite,'de type',type_en)
                            print('Types possibles :',dico[clef_entite][1],'pour l\'entité de clef :',clef_entite)
                            print('Voulez-vous rajouter à l\'entrée du dictionnaire déjà existente (r), créer une nouvelle entrée pour l\'entitée nommée étudiée (c) ou ne rien faire et passer à la comparaison suivante (n) ?')
                            ask = input('Rajouter (r) / Créer nouvelle (c) / Ne rien faire (n) : ')
                            while ask not in ['r','c','n']:
                                ask = input('Rajouter (r) / Créer nouvelle (c) / Ne rien faire (n) : ')
                            if ask=='r':
                                dico[clef_entite][0].append(entite)
                                dico[clef_entite][1].append(type_en)
                                if clef_entite not in liste_ENs_cherchees_trouvees:
                                    liste_ENs_cherchees_trouvees.append(clef_entite)
                                break
                            elif ask=='c':
                                new_clef=''
                                while new_clef=='':
                                    new_clef = input('Veuillez entrer le nouveau nom de l\'entite : ')
                                    if ' ' in new_clef:
                                        print('Erreur : espace dans le nom de la clef. Veuillez réessayer.')
                                        new_clef=''
                                    elif new_clef=='':
                                        print('Erreur : le nom de la clef ne peut être vide. Veuillez réessayer.')
                                    else:
                                        ask = input('Le nouveau nom de l\'entité serait :',new_clef+'. Confirmez-vous ? (y/n) : ')
                                        while ask not in ['y','n']:
                                            ask = input('Confirmez-vous ? (y/n) : ')
                                        if ask == 'n':
                                            new_clef=''
                                        else:
                                            if not re.match(re.compile(nom_dico),new_clef):
                                                print('En ajoutant le nom du dictionnaire avant celui de l\'entité, cela donne le nom :',nom_dico+'_'+new_clef)
                                                ajout_nom_dico = input('Voulez-vous ajouter le nom du dictionnaire avant ? (y/n) : ')
                                                while ajout_nom_dico not in ['y','n']:
                                                    ajout_nom_dico = input('Confirmez-vous ? (y/n) : ')
                                                if ajout_nom_dico=='y':
                                                    new_clef = nom_dico+'_'+new_clef
                                dico[new_clef]=([entite],[type_en])
                                break
            else:
                continue
            break
    
    if maj_dico:
        a=0
    
    return liste_ENs_cherchees_trouvees,dico

