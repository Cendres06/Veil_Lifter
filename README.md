# Veil_Lifter
Module python servant à récupérer les textes de la branche francophone et à effectuer plusieurs opérations statistiques.

Ce README.md n'est PAS à jour!!!!

## **scrapping.py :** principales fonctions

Pour chercher une liste de textes sur la base de leurs tags, en privilégiant la recherche par langage :

__ressources_de_travail__ :

Prend plusieurs paramètres de recherche :
* languages recherchés (sert de base)
* formats recherchés (les textes doivent avoir au moins un tag parmi ceux précisés)
* étiquettes nécessaires (les textes doivent avoir tous les tags précisés)
* étiquettes interdites (les textes ne doivent avoir aucun des tags précisés)
* combinaisons interdites (les textes ne doivent pas présenter ces combinaisons de tags, mais peuvent présenter les tags individuels composant ces combinaisons interdites.)

Le dernier paramètre sert principalement à exclure les SCP-J si besoin, lesquels n'ont pas d'étiquette propre mais diposent en revanche des étiquettes 'humour' et 'scp'.

Par défaut, ressources_de_travail() retourne la liste des textes francophones originels.

*Exemples* :

* ressources_de_travail(liste_tags_language=['fr'], liste_tags_format=['conte','scp'],liste_tags_interdits=['expliqué','centre','annexe','fanart','aile-fr','aile-en','fragment','gazette-aleph'],liste_combinaisons_interdites=[('humour','scp')])

-> Récupère la liste des contes et scp principaux francophones

__process_pour_credits_fr__ :

Récupère les informations contenues dans le module de crédit pour une page précise, ordonnées automatiquement dans des champs spécifiques selon leur nature.

*Exemples* :

* process_pour_credits_fr('/scp-173-fr')

-> Récupère les informations du module de crédit de SCP-173-FR

__liste_fr__ :

Récupère la liste des contes et scp francophones originels.

__creation_bd_fr__ :

Crée une base de données csv des informations des modules de crédits des contes et scp francophones originels.

__ecriture_fichier__ :

Importe le texte d'une page dans un fichier .txt

*Exemples* :

* ecriture_fichier('/scp-173-fr')

-> Récupère le texte de SCP-173-FR

__creation_bd_textes_fr__ :

Crée un répertoire de tous les fichiers .txt correspondant aux contes et scp francophones originels.
