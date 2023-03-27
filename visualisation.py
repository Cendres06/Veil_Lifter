import pandas as pd
from utilities import path_extension
import re
import timeline
import matplotlib.pyplot as plt
from sklearn import metrics

def csv_camembert_normal(donnees,nom='random-test',chemin='..\..\csv_for_visualisation',point=True):
    #checker les points
    values = list(donnees.values())
    legende = list(donnees.keys())
    if point:
        values = [re.sub(re.compile('\.'),',',str(data)) for data in values]
    df = pd.DataFrame(values,legende)
    print(df)
    path = path_extension(nom,bd=False,chemin=chemin)
    df.to_csv(path,header=None,encoding='utf-8-sig')

def confusion_matrice(predicted,actual):
    confusion_matrice = metrics.confusion_matrix(actual, predicted)
    cm_display = metrics.ConfusionMatrixDisplay(confusion_matrix = confusion_matrice, display_labels = [False, True])

    cm_display.plot()
    plt.show()