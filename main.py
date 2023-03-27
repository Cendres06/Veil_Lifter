import scrapping_bs4 as veil_lifter
import trad_network as tn
import time

#liste_textes_ok_fr = veil_lifter.liste_textes_fr(debug=True)
#liste_textes_ok_en = veil_lifter.liste_textes_en_trad(debug=True)
#veil_lifter.bd_credits_fr(chemin="../../",debug=True)
#veil_lifter.bd_credits_en_trad(chemin="../../",debug=True)
#veil_lifter.liste_fragments(nom_bd="annexes",chemin='../../bases_de_donnees/en_trad/',liste_paramètres=[['en'],[],['annexe'],[],[]],debug=True)
#veil_lifter.liste_fragments(nom_bd="fragments",chemin='../../bases_de_donnees/en_trad/',liste_paramètres=[['en'],[],['fragment'],[],[]],debug=True)
#veil_lifter.creation_bd_textes_en(debug=True)
#print(tn.recup_traducteur('/scp-2994'))
DrDharma=tn.get_all_works('Dr Dharma')
print(DrDharma)
