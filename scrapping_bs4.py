from bs4 import BeautifulSoup
import requests, re, time, http, time, datetime, unicodedata,os,json
import pandas as pd

#On s'assure d'être dans le bon répertoire
repertoire = os.path.dirname(__file__)
os.chdir(repertoire)

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


#!!! Toutes les fonctions, classes et méthodes qui suivent ont été créées par Corentin POUPRY pour le projet Sherlock.
#Le projet est sous la licence MIT (https://opensource.org/licenses/mit-license.php)
#J'ai obtenu l'autorisation gracieuse de l'auteur pour utiliser ses fonctions et les modifier selon mes besoins.
#Le github du projet : https://github.com/foundation-int-tech-team/sherlock se trouve
#                       dans les githubs du groupe collaboratif de l'équipe technique de la branche internationale de la Fondation SCP

#J'importe ici les librairies qui sont utilisées dans le projet mais pas dans mes fonctions personnelles
import string,random,scrapy
from itemloaders.processors import TakeFirst, MapCompose, Identity
from scrapy.loader import ItemLoader
from scrapy.crawler import CrawlerProcess
from posixpath import join
from nltk import data,tokenize
from typing import List
from dataclasses import dataclass, field
from twisted.internet.defer import inlineCallbacks
from unicodedata import normalize
from w3lib.html import remove_tags, remove_tags_with_content


#regex.py : https://github.com/foundation-int-tech-team/sherlock/blob/master/sherlock/utils/regex.py

regex = {
    'page_id': re.compile(r".pageId = (?P<page>\d+);"),
    'user_id': re.compile(r".userInfo\((?P<user>\d+)\);"),
    'branch_id': re.compile(r".siteId = (?P<branch>\d+);"),
    'page_slug': re.compile(r".requestPageName = \"(?P<page>.+)\";"),
    'timestamp': re.compile(r"time_(?P<time>\d+) "),
    'user_slug': re.compile(r"user:info\/(?P<username>\S+)"),
    'scp_subtitle': re.compile(r"SCP-.+?-(?P<subtitle>.+)")
}

#config.py : https://github.com/foundation-int-tech-team/sherlock/blob/master/sherlock/utils/config.py

class Config:
    """Branches configuration module"""

    is_loaded = False
    content: dict = None
    path = 'data.json'
    wiki = []

    @classmethod
    def load(self):
        """load config file"""

        with open(self.path) as file:
            self.content = json.load(file)
            self.wiki = self.content.keys()

        self.is_loaded = True

    @classmethod
    def get(self, section: str, name: str):
        """get specific section & attribute of the configuration"""

        Config.check(section)

        # pylint: disable=unsubscriptable-object
        return self.content[section][name]

    @classmethod
    def check(self, wiki: str):
        """"check if the current wiki is supported by the configuration"""

        if not self.is_loaded:
            self.load()

        if wiki is None:
            raise AssertionError("You must provide a `site` to crawl")

        if wiki in self.wiki:
            return

        raise NotImplementedError(
            f'"{wiki}" is not in the config file ({self.path})')

    @classmethod
    def get_config(self, section: str):
        Config.check(section)

        # pylint: disable=unsubscriptable-object
        section = self.content[section]

        return {"branch_id": section['id'], "language": section['language']}

#wikidot.py : https://github.com/foundation-int-tech-team/sherlock/blob/master/sherlock/utils/wikidot.py

data.path.append('./data/nltk_data')

def path(site="fondationscp", component=None):
    """Build Wikidot URL for a specific wiki"""

    url = f'http://{site}.wikidot.com/'

    if component:
        url = join(url, component)

    return url

def request(module: str, **kwargs):
    """Format cookies and data to make a request to the Wikidot API"""

    token = ''.join(
        random.choices(string.ascii_lowercase + string.digits, k=6)
    )
    cookies = {'wikidot_token7': token}
    data = {
        'callbackIndex': '1',
        'wikidot_token7': token,
        'moduleName': module,
        **dict([a, str(x)] for a, x in kwargs.items())
    }

    return data, cookies


def time_to_iso(timestamp):
    """Timestamp date to ISO format"""

    return datetime.datetime.utcfromtimestamp(int(timestamp)).isoformat()

def get_preview(response, language: str):
    """extract a preview if possible"""

    # try to find a block with 'preview' as class
    preview = response.css(".preview p::text").get()

    if preview:
        return preview

    # else fallback to the description field
    description = response.xpath(
        "//strong[contains(text(), 'Description')]/ancestor::p").get()

    if not description:
        return None

    description = normalize('NFKD', remove_tags(remove_tags_with_content(
        description, which_ones=("sup",))))

    sentences = []

    try:
        # if the language is supported by nltk, we split the frst 450 chars of the description in correct sentences
        sentences = tokenize.sent_tokenize(description[:450], language)
    except LookupError:
        # fallback to the first 149 + '…' chars of the description
        return description[:149] + '…'

    # if the description contains only one sentence and less
    # than 15 chars, we will consider that there is no preview.
    if len(sentences) == 1:
        return None if len(sentences[0]) <= 15 else sentences[0]

    # last sentence is eliminated because it is probably incomplete...
    return ' '.join(sentences[:-1])

#loaders.py : https://github.com/foundation-int-tech-team/sherlock/blob/master/sherlock/loaders.py

class PageLoader(ItemLoader):
    default_output_processor = TakeFirst()

    title_in = MapCompose(str.strip)
    preview_in = MapCompose(str.strip)
    tags_out = Identity()
    created_at_in = MapCompose(time_to_iso)
    updated_at_in = MapCompose(time_to_iso)

# items.py : https://github.com/foundation-int-tech-team/sherlock/blob/master/sherlock/items.py

@dataclass
class PageItem:
    page_id: str = field(default=None)
    branch_id: str = field(default=None)
    title: str = field(default=None)
    preview: str = field(default=None)
    slug: str = field(default=None)
    tags: List[str] = field(default_factory=list)
    created_by: str = field(default=None)
    created_at: str = field(default=None)
    updated_at: str = field(default=None)

#pages.py : https://github.com/foundation-int-tech-team/sherlock/blob/master/sherlock/spiders/pages.py

class PagesSpider(scrapy.Spider):
    name = 'pages'
    liste_textes_ok_fr = path_extension("liste_id_pages",lecture=True)
    start_urls=["http://fondationscp.wikidot.com"+element[0] for element in liste_textes_ok_fr.values]

    def __init__(self, site="fondationscp", *args, **kwargs):
        super(PagesSpider, self).__init__(*args, **kwargs)

        self.info = Config.get_config(site)
        self.api = path(site, 'ajax-module-connector.php')

    def request(self, *args, **kwargs):
        request = scrapy.FormRequest(*args, **kwargs)
        return self.crawler.engine.download(request, self)

    @inlineCallbacks
    def parse(self, response):
        item = PageLoader(PageItem(), response)

        item.add_value('branch_id', self.info['branch_id'])
        item.add_css('title', 'div#page-title::text')
        item.add_css('tags', 'div.page-tags a::text')

        item.add_value('preview', get_preview(
            response, language=self.info['language']))

        script = response.xpath(
            '/html/head/script[contains(., "URL")]/text()').get()

        item.add_value('page_id', script, re=regex['page_id'])
        item.add_value('branch_id', script, re=regex['branch_id'])
        item.add_value('slug', script, re=regex['page_slug'])

        item = item.load_item()

        # Some information is loaded on-demand via an XHR request that we need to simulate here
        data, cookie = request(
            'history/PageRevisionListModule',
            page_id=item.page_id,
            perpage=99999
        )

        response = yield self.request(self.api,
                                      cookies=cookie,
                                      formdata=data,
                                      )

        item = PageLoader(item, response)
        item.add_xpath('created_by', '//table/tr[last()]/td/span/a[1]/@onclick',
                       re=regex['user_id'])
        item.add_xpath('created_at', '//table/tr[last()]/td[6]/span/@class',
                       re=regex['timestamp'])
        item.add_xpath('updated_at', '//table/tr[2]/td[6]/span/@class',
                       re=regex['timestamp'])

        return item.load_item()

#!!! Fin des fonctions du projet Sherlock.

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

def nettoyage_html(field):
    """Utilise la fonction de récupération des données de fond de BeautifulSoup4 comme d'un nettoyeur HTML.
    Retourne une str.
    
    field -> bs4.element.Tag"""
    return field.get_text()

def setup_lien(id_page,domaine="http://fondationscp.wikidot.com"):
    """Permet d'établir un lien efficace à partir d'un simple id de page. Si domaine == 'tag' retourne spécifiquement la page listant les textes avec le tag sur fr.
    Retourne une str.
    
    id_page -> str
    domaine -> str"""
    if re.match("tag",domaine):
        if len(domaine) == 3:
            lien = "http://fondationscp.wikidot.com/system:page-tags/tag/"+id_page+"#pages"
        #Comme on a match une chaîne de taille 3 avec domaine, len(domaine)>=3 et on ne traite pas le cas "len(domaine) < 3", impossible
        else:
            lien = "http://fondationscp.wikidot.com/system:page-tags/tag/"+id_page+"/p/"+domaine[-len(domaine)+3:]
    else:
        if id_page[0]=="/":
            lien = domaine+id_page+"/noredirect/true"
        elif re.match("http://",id_page):
            if re.match(domaine,id_page):
                lien = id_page
                if not re.search("/noredirect/true",lien):
                    lien+="/noredirect/true"
            else:
                raise Exception('Le nom du domaine ne correspond pas. Il aurait dû être : {} .'.format(domaine),"Au lieu de celà, le lien est : {}.".format(id_page))
        elif re.match(re.compile('[a-z]'),id_page):
            lien = domaine+"/"+id_page+"/noredirect/true"
        else:
            raise Exception("L'argument passé en paramètre n'est pas un id valide pour une page web de la Fondation SCP : {}.".format(id_page))

    return lien

def creer_nouveau_folder(nom,dans=os.getcwd()):
    """Vérifie si un fichier existe dans un chemin et, si non, le crée.
    Ne retourne rien.
    
    nom -> str
    dans -> str"""
    chemin = dans+"/"+nom
    if not os.path.exists(chemin):
        os.makedirs(chemin)

def recup_page(id_page,domaine="http://fondationscp.wikidot.com",debug=False,full=False):
    lien = setup_lien(id_page,domaine)
    if debug:
        print(lien)

    ma_page = requests.get(lien)
    ma_page_soup = BeautifulSoup(ma_page.text,'html.parser')

    if ma_page_soup.find(class_="bloc-404") and not ma_page_soup.find(class_="page-tags"):
        raise Exception("La page n'existe pas encore sur le site.")

    if full:
        return ma_page_soup
    else:
        return ma_page_soup.find(id="main-content")


def recup_toutes_pages_avec_tag(tag,verif_onglet=True):
    liste_id_page = []
    if type(verif_onglet)==int:
        page_tags = recup_page(tag,domaine="tag"+str(verif_onglet))
        liste_liens_recup = page_tags.find_all(class_="list-pages-box")[1].find_all("a")
        for lien in liste_liens_recup:
            liste_id_page.append(lien.get('href'))
    elif type(verif_onglet)!=bool:
        raise Exception("Le paramètre verif_onglet a une valeur non-usuelle : {}",format(verif_onglet))
    elif verif_onglet:
        page_tags = recup_page(tag,domaine="tag")
        presence_onglet = page_tags.find(class_="pager")
        if presence_onglet:
            nb_onglets = presence_onglet.find(class_="pager-no").get_text()[-1]
            for i in range(int(nb_onglets)):
                liste_id_page += recup_toutes_pages_avec_tag(tag,verif_onglet=i)
        else:
            liste_liens_recup = page_tags.find_all(class_="list-pages-box")[1].find_all("a")
            for lien in liste_liens_recup:
                liste_id_page.append(lien.get('href'))
    
    return liste_id_page

def recup_tags(id_page):
    liste_tags = []
    ma_page = recup_page(setup_lien(id_page))
    tags = ma_page.find(class_="page-tags").find_all("a")
    for etiquette_brut in tags:
        etiquette=etiquette_brut.get_text()
        if etiquette[0]!="_":
            liste_tags.append(etiquette)
    return(liste_tags)

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

def comptage_liste_tag(tag):
    #print("Tag examiné :",tag)
    ma_page = recup_page(tag,domaine="tag",debug=True)
    #print(type(ma_page))
    pages = ma_page.find(class_="pager-no")
    if pages:
        pages = nettoyage_html(pages)
        num = int(pages[-1])
    else:
        num = 1
    return(num)

liste_exceptions_intégrales_fr = ["/incidents-provoques-par-le-personnel-2"]

def ressources_de_travail(liste_tags_language=['fr'], liste_tags_format = [], liste_tags_necessaire = [], liste_tags_interdits = [], liste_combinaisons_interdites = [],liste_exceptions_intégrales = liste_exceptions_intégrales_fr,debug=False):
    
    if debug:
        start = time.time()
        print("Début du travail")
    liste_finale = []
    #Sans condition à part le langage (et si langage est vide, renvoie une liste vide)
    if(liste_tags_format==[] and liste_tags_necessaire==[] and liste_tags_interdits == [] and liste_combinaisons_interdites == []):
        if debug:
            print("On a pas de condition")
        for element in liste_tags_language:
            for id_page in recup_toutes_pages_avec_tag(element):
                if debug:
                    print("Etape de la ressource examinée :",id_page)
                    if debug=="SEVERE":
                        input('Appuyez sur votre clavier pour continuer le débugage :')
                if id_page not in liste_exceptions_intégrales and not re.match("/system:",id_page) and not re.match("/deleted:",id_page):
                    liste_finale.append(id_page)
    #On a des conditions
    else:
        if debug:
            print("On a des conditions.")
        liste_tag_all_lang = ["fr","en","cn","zh","cz","de","es","it","jp","ko","pl","pt","ru","th","ua","int"]
        liste_tags_interdits += [tag for tag in liste_tag_all_lang if not tag in liste_tags_language]
        #à des fins d'efficacité, on se concentre sur les tags nécessaires afin de réduire notre champ de recherche
        #s'il y en a plusieurs, on fait un examen pour trouver le tag ayant la plus petite liste de textes associés

        if len(liste_tags_necessaire) > 1:
            if debug:
                print("Plusieurs tags sont nécessaires.")
            #Rappel : cas où il y a plusieurs tags nécessaires

            #par défaut, on dit que le premier élément est notre première trouvaille
            plus_petit_tag = liste_tags_necessaire[0]
            if debug:
                print("On examine le tag nécessaire",plus_petit_tag)
            #on conserve aussi la longueur de la liste pour la comparer
            len_actuel = comptage_liste_tag(plus_petit_tag)
            #Pour chaque autre tag nécessaire, on examine sa taille :
            for element_necessaire in liste_tags_necessaire[1:]:
                if debug:
                    print("On examine le tag nécessaire",element_necessaire)
                #On compare le nombre d'onglets :
                len_examinee = comptage_liste_tag(element_necessaire)
                if len_examinee < len_actuel:
                #si la taille est inférieure à la tag de notre dernière trouvaille, on change nos valeurs
                    if debug:
                        print("Nouveau tag nécessaire plus petit !")
                    plus_petit_tag = element_necessaire
                    len_actuel = len_examinee
                elif len_examinee==len_actuel:
                    len_examinee = len(recup_toutes_pages_avec_tag(element_necessaire,len_examinee))
                    len_actuel_temp = len(recup_toutes_pages_avec_tag(element_necessaire,len_actuel))
                    if len_examinee<len_actuel_temp:
                        if debug:
                            print("Nouveau tag nécessaire plus petit !")
                    plus_petit_tag = element_necessaire
                    len_actuel = len_examinee
            if debug:
                print("Plus petit tag nécessaire :",plus_petit_tag)
            #une fois cet examen fini, on dit que la liste_finale est notre dernière trouvaille.
            liste_finale_brut = recup_toutes_pages_avec_tag(plus_petit_tag)
            if debug:
                print("Liste finale à élaguer :")
                print(liste_finale_brut)
                if debug=="SEVERE":
                    input('Appuyez sur votre clavier pour continuer le débugage :')
            # On fonctionne ensuite par ajout des éléments qui conviennent à une autre liste
            
            #pour commencer, on exclut notre trouvaille des tags nécessaire examinés pour éviter un cas idiot où on compare un objet à lui-même
            liste_tags_necessaire_modif = [tag for tag in liste_tags_necessaire if tag != plus_petit_tag]
            liste_finale = []
            for i in range(len(liste_finale_brut)):
                id_page = liste_finale_brut[i]
                if debug:
                    print("Etape de la ressource examinée :",id_page)
                if (not re.match("/system:",id_page)) and not re.match("/deleted:",id_page):
                    liste_tags = recup_tags(id_page)
                    if debug:
                        print("Liste des tags de la page :",liste_tags)
                        input('Appuyez sur votre clavier pour continuer le débugage :')
                    #On vérifie : les combinaisons interdites, les tags interdits, les formats demandés,
                    # et une alternative aux formats qui vérifient la langue sur le même principe
                    # (càd au moins un élément doit être présent dans la liste des tags de la page)
                    if (verif_combi_interdites(liste_tags,liste_combinaisons_interdites) and verif_interdit(liste_tags,liste_tags_interdits) and verif_tags_format(liste_tags,liste_tags_format) and verif_tags_necessaire(liste_tags,liste_tags_necessaire_modif) and verif_tags_format(liste_tags,liste_tags_language) and id_page not in liste_exceptions_intégrales):
                        #si une seule des conditions est fausse, on supprime la page de la liste finale
                        liste_finale.append(id_page)
        #s'il n'y a qu'un seul tag nécessaire, la procédure est simplifiée :
        elif len(liste_tags_necessaire) == 1:
            if debug:
                print("Un seul tag est nécessaire")
            #Rappel : cas où il y a un seul tag nécessaire
            for id_page in recup_toutes_pages_avec_tag(liste_tags_necessaire[0]):
                if debug:
                    print("Etape de la ressource examinée :",id_page)
                if (not re.match("/system:",id_page)) and not re.match("/deleted:",id_page):
                    liste_tags = recup_tags(id_page)
                    if debug:
                        print("Liste des tags de la page :",liste_tags)
                        if debug=="SEVERE":
                            input('Appuyez sur votre clavier pour continuer le débugage :')
                    #On fait nos vérifications usuelles spécifiées dans les paramètres
                    if verif_combi_interdites(liste_tags,liste_combinaisons_interdites) and verif_interdit(liste_tags,liste_tags_interdits) and verif_tags_format(liste_tags,liste_tags_format) and verif_tags_necessaire(liste_tags,liste_tags_necessaire) and id_page not in liste_exceptions_intégrales:
                        liste_finale.append(id_page)
        #s'il n'y a aucun tag nécessaire, on prend les tags de langue comme base. La procédure est plus longue.
        else:
            if debug:
                print("Aucun tag nécessaire")
            for element in liste_tags_language:
                if debug:
                    print("On étudie le langage :",element)
                for id_page in recup_toutes_pages_avec_tag(element):
                    if debug:
                        print("Etape de la ressource examinée (pas de tag nécessaire) :",id_page)
                        if debug=="SEVERE":
                            input('Appuyez sur votre clavier pour continuer le débugage :')
                    if (not re.match("/system:",id_page)) and not re.match("/deleted:",id_page):
                        liste_tags = recup_tags(id_page)
                        #On fait nos vérifications usuelles spécifiées dans les paramètres
                        if verif_combi_interdites(liste_tags,liste_combinaisons_interdites) and verif_interdit(liste_tags,liste_tags_interdits) and verif_tags_format(liste_tags,liste_tags_format) and id_page not in liste_exceptions_intégrales:
                            liste_finale.append(id_page)   
        if debug:
            end = time.time()
            print("Temps de travail pour récupérer les id_pages =",end-start) 
        return(liste_finale)

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

def normalisation_date(date):
    """Transforme la date en une timestamp selon la forme.
    Retourne un datetime.
    
    date -> str"""

    date = unicodedata.normalize('NFKD',date)
    #Si c'est une phrase, comme "le 12 Juin" ou "Publié le 12"
    if not re.match(re.compile("[0-9]"),date):
        debut_date = re.search(re.compile("[0-9]"),date)
        date = date[debut_date.start():]
    if re.match(re.compile("[0-9]{4}"),date):
        if len(date)>4:
            if re.search("-",date):
                sep = "-"
            else:
                sep = "/"
            element = datetime.datetime.strptime(date,"%Y"+sep+"%m"+sep+"%d")
        else:
            #Si seule l'année est connue :
            element = datetime.datetime.strptime(date,"%Y")
    elif re.match(re.compile("[0-9]{1,2}[\/-][0-9]{1,2}[\/-][0-9]{2,4}"),date):
        if not re.match(re.compile("[0-9]{2}[\/-][0-9]{2}[\/-][0-9]{4}"),date):
            if re.search("-",date):
                sep = "-"
            else:
                sep = "/"
            sep_date = date.split(sep=sep)
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
        #jour
        if re.match(re.compile("[0-9]{2}"),date[0]):
            new_date = date[0][:2] + "/"
        elif re.match(re.compile("[0-9]{1}"),date[0]):
            new_date = "0"+ date[0][0] + "/"
        else:
            #même si c'est faux, on set au jour milieu du mois pour éviter tout problème (cas où le jour est écrit en lettres qui sera peut-être à traiter, cas par cas)
            new_date = "15/"
        #mois
        if re.match(re.compile("[Jj][aA]"),date[1]):
            new_date += "01/"
        elif re.match(re.compile("[Ff]"),date[1]):
            new_date += "02/"
        elif re.match(re.compile("[Mm][aA][rR]"),date[1]):
            new_date += "03/"
        elif re.match(re.compile("[Aa][vV]"),date[1]):
            new_date += "04/"
        elif re.match(re.compile("[Mm][Aa][Ii]"),date[1]):
            new_date += "05/"
        elif re.match(re.compile("[Jj][uU][Ii][Nn]"),date[1]):
            new_date += "06/"
        elif re.match(re.compile("[Jj][Uu][iI][Ll]"),date[1]):
            new_date += "07/"
        elif re.match(re.compile("[Aa][oO]"),date[1]):
            new_date += "08/"
        elif re.match(re.compile("[Ss]"),date[1]):
            new_date += "09/"
        elif re.match(re.compile("[Oo]"),date[1]):
            new_date += "10/"
        elif re.match(re.compile("[Nn]"),date[1]):
            new_date += "11/"
        else:
            new_date += "12/"
        #année
        if re.match(re.compile("[0-9]{4}"),date[2]):
            new_date += date[2][0:4]
        else:
            new_date += "20"+date[2][0:2]
        #En raison d'un évènement local dit le "35 Décembre" pour Noël, je normalise certaines dates.
        if new_date[0:2]=="35" and new_date[3:5]=="12":
            new_date="04/02/" + new_date[6:]
        element = datetime.datetime.strptime(new_date,"%d/%m/%Y")
    return(element)

def trouver_module_credit(id_page,debug=False):
    if debug:
        print("debut travail")
    ma_page = recup_page(id_page)
    module_brut = ma_page.find(class_="credit")
    if not module_brut:
        return False
    module_text = module_brut.get_text()
    if debug:
        print("Module récupéré :")
        print(module_text,'\n')
    sep_ligne = [ligne for ligne in module_text.split('\n') if ligne !='']
    if debug:
        print("Division en lignes :")
        print(sep_ligne,"\n")
    pattern_credits = re.compile("(.*?):(.*)(?=\n|$)")
    champs_valeurs = re.findall(pattern_credits,module_text)

    if debug:
        print("Champs & valeurs bruts :")
        print(champs_valeurs,"\n")

    pattern_ligne_indep = re.compile("(?<=\n)([^:]*)(?=\n)")
    ligne_indep = [ligne for ligne in re.findall(pattern_ligne_indep,module_text) if ligne != '']

    if len(ligne_indep)==0:
        if debug:
            print("Travail terminé prématurément\n")
        return champs_valeurs
    else:
        if debug:
            print("On essaye d'ordonner nos lignes indépendantes.")
        ligne_indep_ok = []
        for ligne in ligne_indep:
            ligne=ligne.split('\n')
            ligne_indep_ok += [ligne_ok for ligne_ok in ligne if ligne_ok !='']
    ligne_indep = ligne_indep_ok
    if debug:
        print("On a des lignes indépendantes :")
        print(ligne_indep,"\n")

    liste_ind_maj = []
    for ligne in sep_ligne:
        if re.match(re.compile("(.*?):"),ligne):
            liste_ind_maj.append(sep_ligne.index(ligne))

    if debug:
        print("Les positions de nos lignes maj sont :")
        print(liste_ind_maj,"\n")

    for ligne in ligne_indep:
        ind = sep_ligne.index(ligne)
        for i in range(len(liste_ind_maj)):
            if(debug):
                print("On examine si",i,"est plus grand que",liste_ind_maj[i])
            if liste_ind_maj[i] > ind:
                pos = i-1
                break
            if i == len(liste_ind_maj)-1:
                pos = i
        if debug:
            print("La ligne indépendante n°{}".format(ind),"est située après la ligne majeure n°{}".format(pos))
            #print("Champ incomplet :")
            #print(champs_valeurs[pos][1]+"\n")
        champ,valeur_incomplet = champs_valeurs[pos]
        champs_valeurs[pos]=(champ,valeur_incomplet+" "+ligne)
        if debug:
            print("Nouvelle valeur :")
            print(champs_valeurs[pos][1]+ligne,"\n")

    return champs_valeurs

liste_exceptions_manuelles_fr = ["/proposition-des-drs-gemini-et-tesla"]

def ordonnance_credit(id_page,debug = False,liste_exceptions_manuelles=liste_exceptions_manuelles_fr):
    liste_champs = ["Titre","Auteurice(s)","Date de création","Image & Licence","Remerciements","Commentaires","Autres"]
    dict_orga = {"id":id_page}
    for element in liste_champs:
        dict_orga[element] = ""

    if id_page in liste_exceptions_manuelles:
        if debug:
            print("On a une exception manuelle !")
        if id_page=="/proposition-des-drs-gemini-et-tesla":
            dict_orga["Titre"]='SAI-001 - Proposition des Drs Gémini et Tesla dite "La Campagne de Nouvelle-Hollande"'
            dict_orga["Auteurice(s)"]="Messieurs DrGemini et DrTesla"
            dict_orga["Date de création"]=normalisation_date(unicodedata.normalize('NFKD',"29 Novembre 2017"))
            if debug:
                print("Dico pour la page /proposition-des-drs-gemini-et-tesla :")
                print(dict_orga,"\n")
    else:
        module_credit_propre = trouver_module_credit(id_page,debug)

        #Cas module de crédit absent
        if not module_credit_propre:
            for champ in liste_champs:
                dict_orga[champ]="Module de crédit absent"
            return dict_orga
        #Pour chaque champ du module de crédit, on fait une recherche large en expression régulière, afin de détecter automatiquement le
        # type d'informations renseignées.
        for champ,valeur in module_credit_propre:
            valeur=espace_en_trop(valeur)
            if re.search("[Tt]itre",champ):
                dict_orga["Titre"] = unicodedata.normalize('NFKD',espace_en_trop(valeur))
            elif re.search("([Aa]utr{0,1}(eur){0,1}(ice){0,1}s{0,1})|([EéeÉ]crit par)",champ):
                dict_orga["Auteurice(s)"] = unicodedata.normalize('NFKD',espace_en_trop(valeur))
            elif re.search("[Dd]ate",champ):
                dict_orga["Date de création"] = normalisation_date(unicodedata.normalize('NFKD',espace_en_trop(valeur)))
            elif re.search("([I|i]mage)|([Cc]rédit)|([Ll]icence)|([Ll]égal)|([Aa]ttribution)|([Cc]ode)",champ):
                #Comme plusieurs champs différents peuvent se qualifier, on s'assure qu'ils seront ajoutés les uns à la suite des autres.
                if dict_orga["Image & Licence"]!="":
                    dict_orga["Image & Licence"] += " " + unicodedata.normalize('NFKD',espace_en_trop(valeur))
                else:
                    dict_orga["Image & Licence"] = unicodedata.normalize('NFKD',espace_en_trop(valeur))
            elif re.search("[Rr]emerciement",champ):
                if dict_orga["Remerciements"]!="":
                    dict_orga["Remerciements"] += " " + unicodedata.normalize('NFKD',espace_en_trop(valeur))
                else:
                    dict_orga["Remerciements"] = unicodedata.normalize('NFKD',espace_en_trop(valeur))
                dict_orga["Remerciements"] = unicodedata.normalize('NFKD',espace_en_trop(valeur))
            elif re.search("([Nn]ote)|([Cc]ommentaire)|([Rr]emarque)",espace_en_trop(valeur)):
                if dict_orga["Commentaires"]!="":
                    dict_orga["Commentaires"] += " " + unicodedata.normalize('NFKD',espace_en_trop(valeur))
                else:
                    dict_orga["Commentaires"] = unicodedata.normalize('NFKD',espace_en_trop(valeur))
            else:
                if dict_orga["Autres"]!="":
                    dict_orga["Autres"] += " " + unicodedata.normalize('NFKD',espace_en_trop(valeur))
                else:
                    dict_orga["Autres"] = unicodedata.normalize('NFKD',espace_en_trop(valeur))

    #Tout champ laissé vide est marqué comme tel
    for champ in liste_champs:
        if dict_orga[champ]=="":
            dict_orga[champ]="Non-assigné"

    return dict_orga

def liste_textes_fr(chemin="../../",debug=False):
    """Fait la liste des contes et rapports francophones.
    Retourne une list[str(format id_page)]"""
    liste_textes_ok_fr = ressources_de_travail(liste_tags_language=['fr'], liste_tags_format=['conte','scp'],liste_tags_interdits=['expliqué','centre','annexe','fanart','aile-fr','aile-en','fragment','gazette-aleph','dans-les-coulisses'],liste_combinaisons_interdites=[('humour','scp')],debug=debug)
    liste_textes_ok_fr = pd.DataFrame(liste_textes_ok_fr,columns=["Id_page"])
    creer_nouveau_folder("bases_de_donnees")
    path = path_extension("liste_id_pages",chemin)
    liste_textes_ok_fr.to_csv(path,index=False,encoding="utf-8-sig")
    
    return(liste_textes_ok_fr)

def bd_credits_fr(màj_liste = False, chemin="../../", debug=False):
    if màj_liste:
        liste_textes_ok_fr = liste_textes_fr(chemin=chemin,debug=debug)
    else:
        liste_textes_ok_fr = path_extension("liste_id_pages",chemin,lecture=True)
    
    bd_textes_fr = pd.DataFrame(columns=["id","Titre","Auteurice(s)","Date de création","Image & Licence","Remerciements","Commentaires","Autres"])
    for i in range(0,len(liste_textes_ok_fr.index)):
        id_page = liste_textes_ok_fr.loc[i,:][0]
        if debug:
            print("Etape de la mise en forme :",id_page)
        credit_orga = ordonnance_credit(id_page,liste_exceptions_manuelles=liste_exceptions_manuelles_fr)
        bd_textes_fr.loc[id_page] = pd.Series(credit_orga)
    path = path_extension('bd_fr',chemin)
    bd_textes_fr.to_csv(path, index=False,encoding="utf-8-sig")

#bd_credits_fr(màj_liste=True,chemin="../../")

def liste_text_ok_fr_TO_json(màj_liste = False,fichier="data",chemin=None,debug=False):
    if màj_liste:
        if debug:
            print("Liste en cours de màj...\n")
        liste_textes_ok_fr = liste_textes_fr(chemin=chemin,debug=False)
        if debug:
            print("Liste mise à jour.\n")
    else:
        liste_textes_ok_fr = path_extension("liste_id_pages",chemin="../../",lecture=True)
        if debug:
            print("liste_textes_ok_fr récupérée\n")

    donnees = {
        "fondationscp" : {
            "id" : 464696,
            "index" : [],
            "language": "french"
        }
    }

    for element in liste_textes_ok_fr.values:
        id_page = element[0]
        donnees["fondationscp"]["index"].append(id_page[1:])
    if debug:
        print("Dico json :")
        print(donnees,"\n")

    path = path_extension(fichier,bd=False,chemin=None,extension="json")
    if debug:
        print("Chemin choisi pour le fichier json :")
        print(path)
        print("Dans le répertoire :")
        print(os.getcwd(),"\n")
    with open(path,mode="w",encoding="utf-8") as file:
        json.dump(donnees,file,indent=6)

#liste_text_ok_fr_TO_json()

def recup_donnees_ajax():
    
    process = CrawlerProcess(settings={
        "FEEDS": {
            "items.json": {"format": "json"},
        },
    })

    process.crawl(PagesSpider)
    process.start()
    #res = spider.parse(response)
    #return res

#recup_donnees_ajax(")

def ordonnance_metadonnees(id_page,debug=False):
    ma_page = recup_page(id_page)
    champs = ["Titre","Auteurice","Date de création","Score de vote"]
    dico = {"id":id_page}
    for champ in champs:
        dico[champ]=""

    #Titre
    titre_brut = ma_page.find(id="page-title").get_text()
    pattern_titre = re.compile(r'(?<= )(\w+)')
    titre_brut = re.findall(pattern_titre,titre_brut)
    titre = ""
    for mot in titre_brut:
        titre += mot+" "

    dico["Titre"]=titre[:-1]
    if debug:
        print("Etat actuel du dico :\n",dico,'\n')
    
    #Auteurice

    #Date de création

    #Score
    if debug:
        print("On cherche le score :\n")
    score = ma_page.find(class_="rate-points")
    if not score:
        if debug:
            print("Exception : score en indice 0 à 5")
        score = float(ma_page.find(class_="page-rate-widget-start").get("data-rating"))
        if not score:
            raise Exception("La page suivante n'a pas de module de crédit à repérer : {}".format(id_page))
        if debug:
            print("Notation brute : \"",score,"\"\n")
    else:
        score = score.get_text()
        if debug:
            print("Notation brute : \"",score,"\"\n")
        pattern_score = re.compile(r'(?<=notation:)(.|\+|\-)+')
        score = re.search(pattern_score,score)[0][1:]
        if debug:
            print("Notation précise :\"",score,"\"\n")
        if score[0]=="+":
            if debug:
                print("Score positif\n")
            score = int(score[1:])
        elif score[0] == "-":
            if debug:
                print("Score négatif\n")
            score = -int(score[1:])
        else:
            if debug:
                print("Score nul\n")
            score = 0
    
    dico["Score de vote"]=score
    
    return dico

#print(ordonnance_metadonnees("/proposition-des-drs-gemini-et-tesla"))
#print(ordonnance_metadonnees("/xks2018:au-dela-de-xibalba"))
#print(ordonnance_metadonnees("/confessions-d-un-vieil-homme"))

def bd_metadonnees_fr(màj_liste = False, chemin="../../", debug=False):
    if debug:
        print("Début du travail")
    if màj_liste:
        if debug:
            print("Mise à jour de la liste...")
        liste_textes_ok_fr = liste_textes_fr(chemin=chemin,debug=debug)
        if debug:
            print("Liste mise à jour")
    else:
        liste_textes_ok_fr = path_extension("liste_id_pages",chemin,lecture=True)
        if debug:
            print("Liste des textes récupérée")
    
    bd_textes_fr = pd.DataFrame(columns=["id","Titre","Auteurice","Date de création","Score de vote"])
    for i in range(0,len(liste_textes_ok_fr.index)):
        id_page = liste_textes_ok_fr.loc[i,:][0]
        if debug:
            print("Etape de la mise en forme :",id_page)
        metadonnees_orga = ordonnance_metadonnees(id_page)
        bd_textes_fr.loc[id_page] = pd.Series(metadonnees_orga)
    path = path_extension('bd_meta_fr',chemin)
    bd_textes_fr.to_csv(path, index=False,encoding="utf-8-sig")

#bd_metadonnees_fr(debug=True)

def triple_vote(triple):
    id_page,signe,vote = triple
    if vote=="0":
        return 0
    elif signe=="+":
        return id_page,int(vote)
    else:
        return id_page,-int(vote) 

def extreme_date(echantillon,besoin,textes_dates_credit = pd.DataFrame()):
    if textes_dates_credit.empty:
        textes_dates_credit = path_extension('bd_fr',lecture=True)[["id","Date de création"]]

    dates_echantillon = []
    for id_page in echantillon:
        dates_echantillon.append(int(normalisation_date(textes_dates_credit.loc[textes_dates_credit["id"]==id_page]["Date de création"].values[0][:10]).year))
    
    if besoin=="+" or besoin=="True" or besoin=="max" or besoin==">" or re.match(re.compile("sup"),besoin):
        dates_echantillon.sort()
        besoin="+"
    elif besoin=="-" or besoin=="False" or besoin=="min" or besoin=="<" or re.match(re.compile("inf"),besoin):
        dates_echantillon.sort(reverse=True)
        besoin="-"
    else:
        raise Exception("La fonction n'a pas compris si vous vouliez trouver l'extrême supérieur ou inférieur. Quatre symboles sont compatibles avec la fonction : {+ ou -}, {True ou False},{> ou <},{sup ou inf}.")
    

    return dates_echantillon[0],besoin

def moyenne_date(ids_pages,textes_dates_credit = pd.DataFrame()):
    datetimeList = []
    if textes_dates_credit.empty:
        textes_dates_credit = path_extension('bd_fr',lecture=True)[["id","Date de création"]]
    for id_page in ids_pages:
        date = normalisation_date(textes_dates_credit.loc[textes_dates_credit["id"]==id_page]["Date de création"].values[0][:10])
        datetimeList.append(date)
    moyenne=int(datetime.datetime.strftime(datetime.datetime.fromtimestamp(sum(map(datetime.datetime.timestamp,datetimeList))/len(datetimeList)),"%Y"))
    moyenne = int(datetime.datetime.now().year) - moyenne
    return moyenne

def echantillon_textes_representatifs_fr(k=10,moy_spec=5,epsilon=1,debug=False,chemin="../../"):
    if k <= 60:
        page_panels = recup_page("/top-rated-pages")

        panels = page_panels.find_all(class_="feature-block")
        pattern = re.compile("[fF]rancophone")
        panels = [panel for panel in panels if re.search(pattern,panel.find(class_="panel-heading").text)]
        liste_data = []
        if debug:
            print("Voici les sections récupérées :")
        for panel in panels:
            if debug:
                print(panel.find(class_="panel-heading"))
            chaine_à_regex = ""
            loc = panel.find(class_="list-pages-box")
            loc = str(loc.p)
            chaine_à_regex += loc + "\n"
            pattern_id_vote = re.compile("(?<=href=\")(.+?)(?=\">).*<\/a> \(([\+-]){0,1}([0-9]*)(?=\))")
            #Debug
            #chaine_à_regex+='<a href="test">test</a>'
            #fin debug
            liste_data += re.findall(pattern_id_vote,chaine_à_regex)
        if debug:
            print("\nVoici les données brutes récupérés :")
            print(liste_data,"\n")
        if len(liste_data)!=60:
            if debug:
                print("Exception !!!!")
                print("Taille des données :",len(liste_data))
            if len(liste_data)<60:
                raise Exception("Il semblerait que la récupération automatique des pages populaires ait récupéré moins d'éléments que prévu. Cela peut être dû à un problème d'expression régulière ou à un changement de format de la ListPage. Revoir la fonction.")
            else:
                raise Exception("Il semblerait que la récupération automatique des pages populaires ait récupéré plus d'éléments que prévu. Cela peut être dû à un problème d'expression régulière ou à un changement de format de la ListPage. Revoir la fonction.")

        if debug:
            print("On importe les textes ok...")
        liste_textes_ok_fr=path_extension("liste_id_pages",chemin,lecture=True)
        if debug:
            print("Importation réussie.")

        liste_data = [triple_vote((id_page,signe,vote)) for id_page,signe,vote in liste_data if id_page in liste_textes_ok_fr.values]
        textes_dates_credit = None
        if len(liste_data)<k:
            print("Ici, faire la fonction pour chercher sur scpper")
        else:
            if debug:
                print("Voici les données organisées :")
                print(liste_data,"\n")

            liste_data.sort(key=lambda x:x[1],reverse=True)

            if debug:
                print("On ordonne par popularité :")
                print(liste_data,"\n")

            textes_dates_credit=pd.DataFrame()
            echantillon = [id_page for id_page,_ in liste_data[:k]]
            moyenne = moyenne_date(echantillon)

            if debug:
                print("On sélectionne les",k,"premières pages les plus populaires :")
                print(echantillon,"\n")
                print("Cet échantillon a une moyenne d'ancienneté de :",moyenne,"année(s).\n")
            
            if abs(moy_spec-moyenne)<=epsilon:
                return(echantillon)
            else:
                best = (echantillon,moyenne)
                if moyenne <= moy_spec-epsilon:
                    besoin = "+"
                else:
                    besoin = "-"
            for id_page,_ in liste_data[k:]:
                if textes_dates_credit.empty:
                    textes_dates_credit=path_extension('bd_fr',lecture=True)[["id","Date de création"]]
                date = int(normalisation_date(textes_dates_credit.loc[textes_dates_credit["id"]==id_page]["Date de création"].values[0][:10]).year)
                date_extreme,besoin = extreme_date(best[0],besoin,textes_dates_credit)
                if (besoin=="+" and date_extreme<date):
                    for i in range(k):
                        if int(normalisation_date(textes_dates_credit.loc[textes_dates_credit["id"]==best[0][i]]["Date de création"].values[0][:10]).year)<date:
                            if i == 0:
                                new_echantillon = [id_page] + best[0][1:]
                            elif i == len(best[0])-1:
                                new_echantillon = best[0][:k-1] + [id_page]
                            else:
                                new_echantillon = best[0][:i] + [id_page] + best[0][i+1:]
                            new_moyenne = moyenne_date(new_echantillon,textes_dates_credit)
                            #On vérifie si notre nouvel échantillon est valide
                            if abs(moy_spec-new_moyenne)>=epsilon:
                                return(new_echantillon)
                            #On vérifie si notre nouvel échantillon est meilleur que le précédent
                            elif abs(moy_spec-new_moyenne)<abs(moy_spec-best[1]):
                                best = (new_echantillon,new_moyenne)
                                if new_moyenne <= moy_spec-epsilon:
                                    besoin = "+"
                                else:
                                    besoin = "-"
                elif(besoin=="-" and date_extreme>date):
                    for i in range(k):
                        if int(normalisation_date(textes_dates_credit.loc[textes_dates_credit["id"]==best[0][i]]["Date de création"].values[0][:10]).year)<date:
                            if i == 0:
                                new_echantillon = [id_page] + best[0][1:]
                            elif i == len(best[0])-1:
                                new_echantillon = best[0][:k-1] + [id_page]
                            else:
                                new_echantillon = best[0][:i] + [id_page] + best[0][i+1:]
                            new_moyenne = moyenne_date(new_echantillon,textes_dates_credit)
                            #On vérifie si notre nouvel échantillon est valide
                            if abs(moy_spec-new_moyenne)<=epsilon:
                                return(new_echantillon)
                            #On vérifie si notre nouvel échantillon est meilleur que le précédent
                            elif abs(moy_spec-new_moyenne)<abs(moy_spec-best[1]):
                                best = (new_echantillon,new_moyenne)
                                if new_moyenne <= moy_spec-epsilon:
                                    besoin = "+"
                                else:
                                    besoin = "-"
            #On a pas réussi à trouver un échantillon valide avec l'epsilon spécifié, alors on propose le prochain meilleur
            print("Malheureusement les pages les plus populaires ne permettent pas d'obtenir une moyenne d'ancienneté de",str(moy_spec)+",","même avec une marge d'erreur de ",epsilon,"année(s).")
            print("Le meilleur échantillon trouvé a une moyenne d'ancienneté de",best[1],"qui implique de revoir la marge d'erreur à",abs(moy_spec-best[1]),"année(s).")
            print("Le programme peut également aller chercher un ensemble de texte remplissant la condition première sur https://scpper.com/, mais cela prendra plus de temps.")
            print("Voulez-vous utiliser le meilleur échantillon (y), affiner la recherche (c), ou abandonner la tâche (n) ?")
            ask = input("y/c/n :")
            while ask not in ["y","c","n"]:
                ask = input("y/c/n :")
            if ask=="y":
                return best[0]
            elif ask=="n":
                return None
            else:
                print("Ici, faire la fonction pour chercher sur scpper")

    else:
        print("Ici, faire la fonction pour chercher sur scpper")

#echantillon_supposé=echantillon_textes_representatifs_fr(debug=True)
#print("Résultat :")
#print(echantillon_supposé)
#print(moyenne_date(echantillon_supposé))

