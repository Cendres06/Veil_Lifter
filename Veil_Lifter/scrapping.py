from lxml import etree, html
from lxml.html.clean import Cleaner
import requests, re, time, http, time, datetime, unicodedata,os
import pandas as pd

#nettoyage personnalisé
cleaner = Cleaner(page_structure=True, links=False,style=True,inline_style=True,scripts=True,javascript=True,comments=True,meta=True,processing_instructions=True,embedded=True,frames=True,forms=True,remove_tags=["p","em","br","strong","span","table","ul","li","sup","blockquote"])

def patch_http_response_read(func):
    """Cette fonction a été écrite par gushitong et sa version Python3 par Addison Klinke.
    https://stackoverflow.com/questions/44509423/python-requests-chunkedencodingerrore-requests-iter-lines
    Elle sert en effet à éviter les pertes de connexion lors de la construction des bases de donnée."""
    def inner(*args):
        try:
            return func(*args)
        except http.client.IncompleteRead as e:
            return e.partial
    return inner

http.client.HTTPResponse.read = patch_http_response_read(http.client.HTTPResponse.read)

def creer_nouveau_folder(nom,dans=os.getcwd()):
    """Vérifie si un fichier existe dans un chemin et, si non, le crée.
    Ne retourne rien.
    
    nom -> str
    dans -> str"""
    chemin = dans+"/"+nom
    if not os.path.exists(chemin):
        os.makedirs(chemin)

def recup_page(lien):
    """Récupère le corps de la page recherchée.
    Retourne une str.

    lien -> str, format url"""
    #Pistes d'amélioration 
    # -> vérifier le format url, renvoyer une erreur sinon.
    # -> je n'ai pas réussi à utiliser lxml à son plein potentiel en naviguant dans les noeuds.
    ma_page = requests.get(lien)
    tree = html.fromstring(ma_page.text)
    body= tree.find("./body")[0]
    body_texte=etree.tostring(body,pretty_print = True, encoding ="utf-8").decode()
    return(body_texte)

def verif_onglets(ma_page):
    """Vérifie si une page listant plusieurs url dispose d'onglets à explorer pour rendre un compte exhaustif des liens.
    Retourne un int qui désigne le nombre d'onglets.

    ma_page -> str"""

    #on repère l'emplacement du code où se trouve le nombre d'onglets, si il existe
    presence_onglets = re.search("class=\"pager\"",ma_page)
    if presence_onglets:
        nb_onglets = int(re.search("(?<=\"pager-no\">page 1 de )\w{0,3}(?=<)",ma_page)[0])
    else:
        nb_onglets = 0
    return nb_onglets

def recup_page_avec_tag(tag, recherche_onglets = True):
    """Récupère la liste des ids de page qui présentent l'étiquette spécifique.
    Retourne une list[str].
    
    tag -> str, format étiquette (sans espace)
    recherche_onglets -> booleen
    
    15/06/22 : La nouvelle forme adoptée par le site me pousse à transformer cette fonction en une fonction récursive
    afin de pouvoir accéder à toutes les pages de la liste et d'ajouter leur contenu.
    Il faut compter le cas où il n'y a qu'une page unique (absence d'élément pager)"""
    #Pistes d'amélioration 
    # -> vérifier le format étiquette, renvoyer une erreur sinon.
    
    liste_id_pages = []
    lien="http://fondationscp.wikidot.com/system:page-tags/tag/"+tag
    ma_page = recup_page(lien)
    #Si la recherche d'onglet est set sur active
    # (on examine pas un onglet spécifique, on ne sait pas si la page a plusieurs onglets ou non),
    # on prend le tag dans son entièreté
    if recherche_onglets:
        #On cherche si la page a plusieurs onglets
        nb_onglets = verif_onglets(ma_page)
        if nb_onglets!=0:
            #si oui, on regarde toutes les pages en recherche classique, en ajoutant à tag l'onglet spécifique
            for i in range(0,nb_onglets):
                liste_id_pages += recup_page_avec_tag(tag+"/p/"+str(i+1), recherche_onglets=False)
                #Compter le nombre d'id_pages récupéré pour les onglets pleins, tous sauf le dernier ?
                # C'est un chiffre qui ne varie pas normalement
        else:
            #si non, recherche classique sans rien
            liste_id_pages = recup_page_avec_tag(tag, recherche_onglets = False)

    #Si la recherche d'onglet est set sur inactive, on ne cherche pas les onglets = recherche classique
    else:
        #On cherche la zone de la page où se trouve la liste des pages.
        #Mes expressions régulières pourraient être plus efficientes mais je n'arrive pas à les faire fonctionner avec re.
        #Donc je privilégie le résultat.
        recherche = re.search("<\/h4>",ma_page)
        recherche = ma_page[recherche.end():]
        recherche = re.search("(?<=list-pages-box\">)(.|\s)*?(?=<\/p>)",recherche)
        liste_id_pages = [element for element in re.findall('(?<=href=").*?(?=">)', recherche[0]) if not re.match("/deleted:",element)]
        #on ne prend pas les éléments archivés car supprimés des listes officielles
    return liste_id_pages

def recup_tags(id_page):
    """Récupère la liste des étiquettes d'une page précise.
    Retourne une list[str].
    
    id_page -> str, format id de page (/..../....)"""
    lien = "http://fondationscp.wikidot.com"+id_page+"/noredirect/true"
    ma_page = recup_page(lien)
    #On cherche la zone où sont indiquées les étiquettes
    recherche = re.search("(?<=class=\"page-tags\">)(.|\s)*?(?=<\/span>)",ma_page)
    #On divise cette zone selon les tags
    liste_tags = re.findall("(?<=>)[\w-]+(?=<)",recherche[0])
    return liste_tags

def verif_tags_format(liste_tags,liste_tags_format):
    """Vérifie si la liste des tags présente au moins un élément de la liste_tags_formats.
    Retourne un booléen.

    liste_tags -> list[str]
    liste_tags_format -> list[str]"""

    if liste_tags_format==[]:
        return True
    for element in liste_tags:
        #dès qu'on trouve un élément de format, on valide
        if element in liste_tags_format:
            return True
    return False

def verif_tags_necessaire(liste_tags,liste_tags_necessaire):
    """Vérifie si la liste des tags présente tous les éléments de la liste_tags_necessaire.
    Retourne un booléen.
    
    liste_tags -> list[str]
    liste_tags_necessaire -> list[str]"""

    if liste_tags_necessaire==[]:
        return True
    for element in liste_tags_necessaire:
        #dès qu'on trouve un élément absent, on annule
        if element not in liste_tags:
            return False
    return True

def verif_combi_interdites(liste_tags,liste_combinaisons_interdites):
    """Vérifie si la liste des tags présente une combinaison de liste_combinaisons_interdites.
    Retourne un booléen.
    
    liste_tags -> list[str]
    liste_combinaisons_interdites -> list[str]"""

    if liste_combinaisons_interdites==[]:
        return True
    for tag_a,tag_b in liste_combinaisons_interdites:
        #dès qu'on trouve une combinaison interdite, on annule
        if tag_a in liste_tags and tag_b in liste_tags:
            return False
    return True

def verif_interdit(liste_tags,liste_tags_interdits):
    """Vérifie si la liste des tags présente un élément de la liste_tags_interdits.
    Retourne un booléen.
    
    liste_tags -> list[str]
    liste_tags_interdits -> list[str]"""

    if liste_tags_interdits==[]:
        return True
    for element in liste_tags:
        #dès qu'on trouve un élément interdit, on annule
        if element in liste_tags_interdits:
            return False
    else:
        return True

def ressources_de_travail(liste_tags_language, liste_tags_format = [], liste_tags_necessaire = [], liste_tags_interdits = [], liste_combinaisons_interdites = [],liste_pages_exclues = [],debug = False):
    """Récupère la liste des id de page qui répondent aux conditions spécifiées.
    Retourne une list[str].
    
    Tous les paramètres sont des list[str] sauf debug qui est bool."""
    
    start = time.time()
    #print("Début de la fonction de recup des ressources de travail")

    #On crée le récipient final
    liste_finale = []
    #si on veut créer la base de données d'un ou de plusieurs langages, aucune condition n'est nécessaire et on va au plus simple
    if(liste_tags_format==[] and liste_tags_necessaire==[] and liste_tags_interdits == [] and liste_combinaisons_interdites == []):
        for element in liste_tags_language:
            for id_page in recup_page_avec_tag(element):
                if debug:
                    print("Etape de la ressource examinée :",id_page)
                liste_finale.append(id_page)

        end = time.time()
        #print("Temps de travail =",end-start)
        return(liste_finale)
    #Si des conditions sont posées en paramètres :
    else:
        liste_tag_all_lang = ["fr","en","cn","zh","cz","de","es","it","jp","ko","pl","pt","ru","th","ua","int"]
        
        liste_tags_interdits += [tag for tag in liste_tag_all_lang if not tag in liste_tags_language]
        #à des fins d'efficacité, on se concentre sur les tags nécessaires afin de réduire notre champ de recherche
        #s'il y en a plusieurs, on fait un examen pour trouver le tag ayant la plus petite liste de textes associés
        if len(liste_tags_necessaire) > 1:
            #Rappel : cas où il y a plusieurs tags nécessaires

            #par défaut, on dit que le premier élément est notre première trouvaille
            plus_petit_tag = liste_tags_necessaire[0]
            #le marqueur place sert à se souvenir de l'emplacement exact de notre liste de liens la plus petite
            marqueur_place = 0
            #on sauvegarde chaque liste de tags nécessaire dans une sur-liste, afin de pouvoir les réutiliser sans devoir refaire
            #des appels de fonctions coûteux
            sauvegarde_listes_elements_necessaire = [recup_page_avec_tag(plus_petit_tag)]
            #on conserve aussi la longueur de la liste pour la comparer
            len_actuel = len(sauvegarde_listes_elements_necessaire[0])
            #Pour chaque autre tag nécessaire, on examine sa taille :
            for element_necessaire in liste_tags_necessaire[1:]:
                sauvegarde_listes_elements_necessaire.append(recup_page_avec_tag(element_necessaire))
                len_examinee = len(sauvegarde_listes_elements_necessaire[len(sauvegarde_listes_elements_necessaire)-1])
                #si la taille est inférieure à la tag de notre dernière trouvaille, on change nos valeurs
                if len_actuel > len_examinee:
                    plus_petit_tag = element_necessaire
                    len_actuel = len_examinee
                    marqueur_place = len(sauvegarde_listes_elements_necessaire)-1
            
            #une fois cet examen fini, on dit que la liste_finale est notre dernière trouvaille.
            liste_finale = sauvegarde_listes_elements_necessaire[marqueur_place]
            # On fonctionne ensuite par suppression des éléments qui ne conviennent pas
            
            #pour commencer, on exclut notre trouvaille des tags nécessaire examinés pour éviter un cas idiot où on compare un objet à lui-même
            if marqueur_place == len(liste_tags_necessaire)-1:
                liste_tags_necessaire_modif = liste_tags_necessaire[:len(liste_tags_necessaire)-1]
            else:
                liste_tags_necessaire_modif = liste_tags_necessaire[:marqueur_place]+liste_tags_necessaire[marqueur_place+1:]
            for id_page in liste_finale:
                if id_page not in liste_pages_exclues:
                    print("Etape de la ressource examinée :",id_page)
                    liste_tags = recup_tags(id_page)
                    #On vérifie : les combinaisons interdites, les tags interdits, les formats demandés,
                    # et une alternative aux formats qui vérifient la langue sur le même principe
                    # (càd au moins un élément doit être présent dans la liste des tags de la page)
                    if not (verif_combi_interdites(liste_tags,liste_combinaisons_interdites) and verif_interdit(liste_tags,liste_tags_interdits) and verif_tags_format(liste_tags,liste_tags_format) and verif_tags_necessaire(liste_tags,liste_tags_necessaire_modif) and verif_tags_format(liste_tags,liste_tags_language)):
                        #si une seule des conditions est fausse, on supprime la page de la liste finale
                        liste_finale.remove(id_page)
            #une fois que c'est fait, on retourne le résultat
            end = time.time()
            print("Temps de travail =",end-start)
            return(liste_finale)
        #s'il n'y a qu'un seul tag nécessaire, la procédure est simplifiée :
        elif len(liste_tags_necessaire) == 1:
            #Rappel : cas où il y a un seul tag nécessaire

            for id_page in recup_page_avec_tag(liste_tags_necessaire[0]):
                print("Etape de la ressource examinée :",id_page)
                if id_page not in liste_pages_exclues:
                    liste_tags = recup_tags(id_page)
                    #On fait nos vérifications usuelles spécifiées dans les paramètres
                    if verif_combi_interdites(liste_tags,liste_combinaisons_interdites) and verif_interdit(liste_tags,liste_tags_interdits) and verif_tags_format(liste_tags,liste_tags_format):
                        liste_finale.append(id_page)
            end = time.time()
            print("Temps de travail =",end-start)
            return liste_finale
        #s'il n'y a aucun tag nécessaire, on prend les tags de langue comme base. La procédure est plus longue.
        else:
            for element in liste_tags_language:
                for id_page in recup_page_avec_tag(element):
                    print("Etape de la ressource examinée (pas de tag nécessaire) :",id_page)
                    if id_page not in liste_pages_exclues:
                        liste_tags = recup_tags(id_page)
                        if(id_page=="scp-061-fr"):
                            print("Cas à problème :",id_page)
                            print(liste_tags)
                        #On fait nos vérifications usuelles spécifiées dans les paramètres
                        if verif_combi_interdites(liste_tags,liste_combinaisons_interdites) and verif_interdit(liste_tags,liste_tags_interdits) and verif_tags_format(liste_tags,liste_tags_format):
                            liste_finale.append(id_page)   
            end = time.time()
            print("Temps de travail pour récupérer les id_pages =",end-start) 
            return(liste_finale)

def trouver_module_credit(body_texte):
    """Récupère le module de crédit brut d'une page.
    Retourne où une str, où une list[str].
    
    body_texte -> str"""
    #Il faut que je repense la récupération des crédits :
# 1. Tant qu'on ne toruve pas un ":" marqueur, on ajoute à a valeur les lignes
#   -> comment faire s'il y a un ":" dans la valeur du champ ?
# 2. Garder les <> de lien dans les images (option à rajouter dans nettoyage_html) 

    module_credit_sale = re.search('(?<=<div class=\"credit\")(.|\s)*?(?<=</div>)',body_texte)
    if module_credit_sale:
        module_credit_sale = re.findall('(?<=>).*(?=<)',module_credit_sale[0])
    else:
        module_credit_sale="Module_crédit_absent"
        return("Module_crédit_absent")
    #On normalise en réunissant les champs éventuels qui n'ont pas été correctement séparés
    i=0
    while i < len(module_credit_sale)-1:
        if module_credit_sale[i] != "" and not ":" in module_credit_sale[i]:
            j=i+1
            while(module_credit_sale[j]=="" and j<len(module_credit_sale)-1):
                j+=1
            if j<len(module_credit_sale)-1:
                module_credit_sale[i] = module_credit_sale[i] + ":" + module_credit_sale[j]
                module_credit_sale.remove(module_credit_sale[j])
        i+=1
        
    return(module_credit_sale)

def espace_en_trop(chaine):
    """Nettoie les espaces en bordure de chaine.
    Retourne une str.
    
    chaine -> str"""
    if(chaine==""):
        return ""
    elif chaine[0]==" ":
        return espace_en_trop(chaine[1:])
    elif chaine[len(chaine)-1]==" ":
        return espace_en_trop(chaine[:len(chaine)-1])
    else:
        return chaine

def nettoyage_module_credit(module_credit_sale):
    """Nettoie le module en enlevant l'HTML et en uniformisant. Prend en compte le cas où le module de crédit est absent.
    Retourne ou une str, ou un dictionnaire{str:str}.
    
    module_credit_sale -> str ou list[str]"""
    if type(module_credit_sale)!=list:
        return "Module_crédit_absent"
    module_credit_propre = {}
    ind_orphelin = 0
    for element in module_credit_sale:
        #On effectue un nettoyage personnalisé
        nettoyage = cleaner.clean_html(element)
        if(nettoyage!=0):
            champs = nettoyage.split(':')
            #On peut avoir effectué une séparation abusive
            if len(champs)==1:
                nom_champ = "orphelin"+str(ind_orphelin)
                ind_orphelin+=1
                module_credit_propre[nom_champ] = espace_en_trop(champs[0])
            else:
                module_credit_propre[espace_en_trop(champs[0])]=espace_en_trop(champs[1])
    return module_credit_propre

def normalisation_date(date):
    """Transforme la date en une timestamp selon la forme.
    Retourne un datetime.
    
    date -> str"""

    date = unicodedata.normalize('NFKD',date)
    #Si c'est une phrase, comme "le 12 Juin" ou "Publié le 12"
    if not re.match("[0-9]",date):
        debut_date = re.search("[0-9]",date)
        date = date[debut_date.start():]
    if re.match("[0-9]{4}",date):
        #Si seule l'année est connue :
        element = datetime.datetime.strptime(date,"%Y")
    elif re.match("[0-9]{1,2}\/[0-9]{1,2}\/[0-9]{2,4}",date):
        if not re.match("[0-9]{2}\/[0-9]{2}\/[0-9]{4}",date):
            sep_date = date.split(sep="/")
            #jour
            if len(sep_date[0])==1:
                date = "0"+sep_date[0]+"/"
            else:
                date=sep_date[0]+"/"
            #mois
            if len(sep_date[1])==1:
                date += "0"+sep_date[1]+"/"
            else:
                date += sep_date[1]+"/"
            #année
            if len(sep_date[2])==2:
                date += "20"+sep_date[2]
            else:
                date += sep_date[2]
        element = datetime.datetime.strptime(date,"%d/%m/%Y")
    else:
        date = date.split(sep=" ")
        #print(date)
        #jour
        if re.match("[0-9]{2}",date[0]):
            new_date = date[0][:2] + "/"
        elif re.match("[0-9]{1}",date[0]):
            new_date = "0"+ date[0][0] + "/"
        else:
            #même si c'est faux, on set au jour milieu du mois pour éviter tout problème (cas où le jour est écrit en lettres qui sera peut-être à traiter, cas par cas)
            new_date = "15/"
        #mois Janvier Février Mars Avril Mai Juin Juillet Août Septembre Octobre Novembre Décembre
        if re.match("[Jj][aA]",date[1]):
            new_date += "01/"
        elif re.match("[Ff]",date[1]):
            new_date += "02/"
        elif re.match("[Mm][aA][rR]",date[1]):
            new_date += "03/"
        elif re.match("[Aa][vV]",date[1]):
            new_date += "04/"
        elif re.match("[Mm][Aa][Ii]",date[1]):
            new_date += "05/"
        elif re.match("[Jj][uU][Ii][Nn]",date[1]):
            new_date += "06/"
        elif re.match("[Jj][Uu][iI][Ll]",date[1]):
            new_date += "07/"
        elif re.match("[Aa][oO]",date[1]):
            new_date += "08/"
        elif re.match("[Ss]",date[1]):
            new_date += "09/"
        elif re.match("[Oo]",date[1]):
            new_date += "10/"
        elif re.match("[Nn]",date[1]):
            new_date += "11/"
        else:
            new_date += "12/"
        #année
        if re.match("[0-9]{4}",date[2]):
            new_date += date[2][0:4]
        else:
            new_date += "20"+date[2][0:2]
        #En raison d'un évènement local dit le "35 Décembre" pour Noël, je normalise certaines dates.
        if new_date[0:2]=="35" and new_date[3:5]=="12":
            new_date="04/02/" + new_date[6:]
        element = datetime.datetime.strptime(new_date,"%d/%m/%Y")
    return(element)

def orga_credits_fr(module_credit_propre,id_page):
    """Attribue les différentes valeurs en module de crédit selon leur nature.  Prend en compte le cas où le module de crédit est absent.
    Retourne un dictionnaire.
    
    module_credit_propre -> dict{str:str}"""

    liste_champs = ["Titre","Auteurice(s)","Date de création","Image & Licence","Remerciements","Commentaires","Autres"]
    dict_orga = {"id":id_page}

    #Cas module de crédit absent
    if type(module_credit_propre) == str:
        for champ in liste_champs:
            dict_orga[champ]="Module_crédit_absent"
        return dict_orga

    #Sinon
    for element in liste_champs:
        dict_orga[element] = ""
    #Pour chaque champ du module de crédit, on fait une recherche large en expression régulière, afin de détecter automatiquement le
    # type d'informations renseignées.
    for champ in module_credit_propre:
        valeur = module_credit_propre[champ]
        if re.search("[Tt]itre",champ):
            dict_orga["Titre"] = unicodedata.normalize('NFKD',valeur)
        elif re.search("([Aa]utr{0,1}(eur){0,1}(ice){0,1}s{0,1})|([EéeÉ]crit par)",champ):
            dict_orga["Auteurice(s)"] = unicodedata.normalize('NFKD',valeur)
        elif re.search("[Dd]ate",champ):
            dict_orga["Date de création"] = normalisation_date(unicodedata.normalize('NFKD',valeur))
        elif re.search("([I|i]mage)|([Cc]rédit)|([Ll]icence)|([Ll]égal)|([Aa]ttribution)|([Cc]ode)",champ):
            #Comme plusieurs champs différents peuvent se qualifier, on s'assure qu'ils seront ajoutés les uns à la suite des autres.
            if dict_orga["Image & Licence"]!="":
                dict_orga["Image & Licence"] += "\n" + unicodedata.normalize('NFKD',valeur)
            else:
                dict_orga["Image & Licence"] = unicodedata.normalize('NFKD',valeur)
        elif re.search("[Rr]emerciement",champ):
            if dict_orga["Remerciements"]!="":
                dict_orga["Remerciements"] += "\n" + unicodedata.normalize('NFKD',valeur)
            else:
                dict_orga["Remerciements"] = unicodedata.normalize('NFKD',valeur)
            dict_orga["Remerciements"] = unicodedata.normalize('NFKD',valeur)
        elif re.search("([Nn]ote)|([Cc]ommentaire)|([Rr]emarque)",champ):
            if dict_orga["Commentaires"]!="":
                dict_orga["Commentaires"] += "\n" + unicodedata.normalize('NFKD',valeur)
            else:
                dict_orga["Commentaires"] = unicodedata.normalize('NFKD',valeur)
        else:
            if dict_orga["Autres"]!="":
                dict_orga["Autres"] += "\n" + unicodedata.normalize('NFKD',valeur)
            else:
                dict_orga["Autres"] = unicodedata.normalize('NFKD',valeur)

    #Tout champ laissé vide est marqué comme tel
    for champ in liste_champs:
        if dict_orga[champ]=="":
            dict_orga[champ]="Non-assigné"

    return dict_orga

def process_pour_credits_fr(id_page):
    """On effectue toutes les opérations nécessaires pour obtenir les crédits d'une page précise.
    Retourne un dictionnaire{str:str}.
    
    id_page -> str, format id_page"""
    lien = "http://fondationscp.wikidot.com"+id_page
    body_texte = recup_page(lien)
    module_credit_sale = trouver_module_credit(body_texte)
    module_credit_propre = nettoyage_module_credit(module_credit_sale)
    credit_orga = orga_credits_fr(module_credit_propre,id_page)
    return credit_orga

def liste_textes_fr():
    """Fait la liste des contes et rapports francophones.
    Retourne une list[str(format id_page)]"""
    liste_textes_ok_fr = ressources_de_travail(liste_tags_language=['fr'], liste_tags_format=['conte','scp'],liste_tags_interdits=['expliqué','centre','annexe','fanart','aile-fr','aile-en','fragment','gazette-aleph'],liste_combinaisons_interdites=[('humour','scp')])
    liste_textes_ok_fr = pd.DataFrame(liste_textes_ok_fr,columns=["Id_page"])
    creer_nouveau_folder("bases_de_donnees")
    liste_textes_ok_fr.to_csv('bases_de_donnees/liste_id_pages.csv',index=False,encoding="utf-8-sig")
    
    return(liste_textes_ok_fr)

def creation_bd_fr(màj_liste = False,debug = False):
    """Crée une base de données répertoriant les différents crédits manuellement ajoutés des contes et scp francophones.
    Ne retourne rien.

    màj_list -> bool
    debug -> bool

    A ce jour, ne rend pas un résultat exact."""
    
    start = time.time()
    #print("Début de la fonction de creation de la BD FR")
    creer_nouveau_folder("bases_de_donnees")
    #On récupère la liste
    if màj_liste:
        liste_textes_ok_fr=liste_textes_fr()
    else:
        liste_textes_ok_fr = pd.read_csv('bases_de_donnees/liste_id_pages.csv', encoding="utf-8-sig")
    #print("La liste des textes à travailler est faite.")
    bd_textes_fr = pd.DataFrame(columns=["id","Titre","Auteurice(s)","Date de création","Image & Licence","Remerciements","Commentaires","Autres"])
    for i in range(0,len(liste_textes_ok_fr.index)):
        id_page = liste_textes_ok_fr.loc[i,:][0]
        if debug:
            print("Etape de la mise en forme :",id_page)
        credit_orga = process_pour_credits_fr(id_page)
        bd_textes_fr.loc[id_page] = pd.Series(credit_orga)
    bd_textes_fr.to_csv('bases_de_donnees/bd_fr.csv', index=False,encoding="utf-8-sig")
    end = time.time()
    #print("Temps de travail pour créer la base de données =",end-start)

def recup_page_parent(id_page):
    """Récupère la page_parent d'une page ayant un fil d'ariane. Si la structure du fil d'Arianne est complexe (>2 éléments), on remonte au plus haut.
    Retourne une str, format id_page.

    id_page -> str, format id_page"""


    lien= "http://fondationscp.wikidot.com"+id_page
    body_texte = recup_page(lien)
    miette_de_pains = re.search("(?<=<div id=\"breadcrumbs\">)(.|\s)*(?=<\/div>)",body_texte)
    #On récupère le fil d'Ariane
    id_page_parent = re.search("(?<=href=\").+?(?=\">)",miette_de_pains[0])
    return(id_page_parent[0])

def liste_fragments(liste_textes_ok,liste_pages_exclues = ['/fragment:scp-5764-1','/fragment:version-2','/fragment:version-3','/fragment:version-4','/fragment:version-5','/fragment:version-6'],nom_bd = 'fragments', liste_paramètres=[['fr'],[],['fragment'],[],[]],debug=False):
    """Cette fonction sert à récupérer les fragments d'une page, c'est-à-dire ses différents composants stockés à une autre url, et à créer des bases de données.
    Peut servir à récupérer les fragments comme les annexes.
    Retourne la liste des fragments (list[str]) et la liste de leurs parents (list[str]).

    liste_textes_ok et liste_pages_exclues sont des list[str]
    nom_bd -> str
    liste_paramètre -> list[list[str]], désigne les paramètres recherchés
    debug -> bool

    Les pages exclues sont celles qui posent problème à mon programme, lequel n'est donc pas efficace à 100%.
    
    Récupérer fragments francophones :
    #liste_fragments(liste_id_pages)
    Récupérer annexes francophones :
    #liste_fragments(liste_id_pages,[],'annexes',[['fr'],[],['annexe'],[],[]])"""
    
    #On récupère la liste des fragments francophones pouvant se qualifier en candidats (respectant les paramètres de recherche)
    liste_fragments_fr = ressources_de_travail(liste_paramètres[0], liste_tags_format=liste_paramètres[1], liste_tags_necessaire=liste_paramètres[2], liste_tags_interdits=liste_paramètres[3], liste_combinaisons_interdites=liste_paramètres[4],liste_pages_exclues=liste_pages_exclues,debug=debug)
    
    liste_parents_ok = []
    liste_fragments_ok = []
    #On vérifie ensuite qu'il y a bien une correspondance entre nos textes étudiés et les fragments candidats
    for id_page in liste_fragments_fr:
        if debug:
            print("On cherche la page_parent de :",id_page)
        id_parent = recup_page_parent(id_page+'/noredirect/true')
        #Si le parent figure dans les textes étudiés, on ajoute le fragment dans notre base de donnée
        if id_parent in liste_textes_ok.values:
            liste_fragments_ok.append([id_page,id_parent])
            if not id_parent in liste_parents_ok:
                liste_parents_ok.append(id_parent)
    
    creer_nouveau_folder("bases_de_donnees")

    #Création des bases de données
    liste_fragments_ok = pd.DataFrame(data=liste_fragments_ok,columns=["Id_page","Id_parent"])
    liste_fragments_ok.to_csv("bases_de_donnees/"+nom_bd+'_a_retenir.csv',encoding="utf-8-sig")

    liste_parents_fr = pd.DataFrame(data=liste_parents_ok,columns=["Id_page"])
    liste_parents_fr.to_csv("bases_de_donnees/"+'parents_de_'+nom_bd+'_a_retenir.csv',encoding="utf-8-sig")
    return(liste_fragments_ok,liste_parents_fr)

def recup_texte_propre(id_page):
    """Récupère le texte nettoyé de tout html (à l'exception des liens pour étude intertextuelle).
    Retourne un list[str].
    
    id_page -> str, format id_page"""
    lien= "http://fondationscp.wikidot.com"+id_page+"/noredirect/true"
    body_texte = recup_page(lien)
    #On cherche la partie corps du texte.
    texte = re.search("(?<=id=\"page-content\">)(.|\s)*",body_texte)[0]
    #On se déplace sous le module de crédit si il existe
    place_mod_credit = re.search('(?<=<div class=\"credit\")(.|\s)*?(?<=<div style)',texte)
    if place_mod_credit:
        texte = "<"+texte[place_mod_credit.end():]
    #On délimite le texte
    texte = re.search("(.|\s)+?(?=<!-- wikidot_bottom_300x250 -->)",texte)[0]
    #nettoyage personnalisé
    texte = cleaner.clean_html(texte)

    #On divise en lignes et on exclut les lignes qui sont vides ou qui sont du bruit.
    texte = texte.split('\n')
    texte = [paragraphe for paragraphe in texte if (re.search("\w",paragraphe) and not re.match("(\s)*<\/{0,1}div>\Z",paragraphe) and not re.match("(\s)*<\/{0,1}div.*>",paragraphe))]

    return(texte)

def ecriture_fichier(id_page,folder='/textes_fr/'):
    """Crée ou écrase un fichier.txt avec le texte d'une page précise.
    Ne retourne rien.
    
    id_page -> str, format id_page
    folder -> str
    
    Ne fonctionne QUE si les bases de données des annexes et fragments ont déjà été créées !!!!"""

    nom_fichier = ""
    #Certains caractères URL étant impossibles à insérer dans un nom de fichier ou de document, on les supprime
    for char in id_page[1:]:
        if char not in ["/","\\","\"","<",">",":","|","*","?"]:
            nom_fichier += char
    nom_fichier += ".txt"
    chemin = os.getcwd()+folder+nom_fichier
    #On vérifie si le folder existe, sinon on le crée
    creer_nouveau_folder(folder)
    texte= recup_texte_propre(id_page)
    #On récupère les fragments et les annexes
    bd_fragments_fr = pd.read_csv('bases_de_donnees/fragments_a_retenir.csv',index_col=0)
    bd_parents_fr = pd.read_csv('bases_de_donnees/parents_a_retenir.csv',index_col=0)
    bd_annexes_fr = pd.read_csv('bases_de_donnees/annexes_a_retenir.csv',index_col=0)
    bd_parents_annexes_fr = pd.read_csv('bases_de_donnees/parents_de_annexes_a_retenir.csv',index_col=0)

    #on vérifie si la page a des fragments
    if id_page in bd_parents_fr.values:
        #print("La page a des fragments")
        mask = (bd_fragments_fr['Id_parent'] == id_page)
        liste_fragments = []
        for i in range(len(mask.values)):
            if mask.loc[i]:
                liste_fragments.append(bd_fragments_fr.loc[i,"Id_page"])
        for fragment in liste_fragments:
            #print("On examine le fragment :",fragment)
            texte += recup_texte_propre(fragment+'/noredirect/true')
            #print(texte)
    #On vérifie si la page a des annexes
    if id_page in bd_parents_annexes_fr.values:
        #print("La page a des annexes")
        mask = (bd_annexes_fr['Id_parent'] == id_page)
        liste_annexes = []
        for i in range(len(mask.values)):
            if mask.loc[i]:
                liste_annexes.append(bd_annexes_fr.loc[i,"Id_page"])
        for annexe in liste_annexes:
            #print("On examine l'annexe' :",annexe)
            texte += recup_texte_propre(annexe)

    file = open(chemin,'w',encoding="utf-8")
    #print("On ouvre le fichier.")
    for ligne in texte[1:]:
        file.write(ligne+"\n")
    file.close()
    #print("On ferme le fichier.")

def creation_bd_textes_fr(màj_liste = False):
    """Importe tous les rapports et contes francophones sur lesquels travailler dans un répertoire approprié.
    Ne retourne rien.
    
    màj_liste -> bool"""

    start = time.time()
    print("Début de la fonction de creation de la BD FR")

    if màj_liste:
        liste_textes_ok_fr=liste_textes_fr()
    else:
        liste_textes_ok_fr = pd.read_csv('bases_de_donnees/liste_id_pages.csv', encoding="utf-8-sig")
    print("La liste des textes à travailler est faite.")
    textes_problematiques = ["/apres-aleph-team-11"]
    for i in range(0,len(liste_textes_ok_fr.index)):
        id_page = liste_textes_ok_fr.loc[i,:][0]
        if id_page not in textes_problematiques:
            print("Création du fichier pour :",id_page)
            ecriture_fichier(id_page)

#Pistes d'améliorations :
# Créer des généralités pour travailler sur les BDDs