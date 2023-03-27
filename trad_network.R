library(readr)
library(sets)
library(stringr)
library("tm")
source("functions.R")
library(cluster)

recup_traducteur=function(id,chemin="../../bases_de_donnees/en_trad"){
  liste_en_trad = read.csv(paste(chemin,'bd_en.csv',sep='/'),encoding = 'UTF-8')
  line = liste_en_trad[liste_en_trad[,1]==id,]
  return(line[,4])
}

#a = recup_traducteur('/scp-2994')

recup_date=function(id,chemin="../../bases_de_donnees/en_trad"){
  liste_en_trad = read.csv(paste(chemin,'bd_en.csv',sep='/'),encoding = 'UTF-8')
  line = liste_en_trad[liste_en_trad[,1]==id,]
  return(str_split(line[,5],' ')[[1]][1])
}

#recup_date('/085-romance-adult')
#recup_date('/jonathan-ball-s-proposal')

get_all_works=function(author,chemin="../../bases_de_donnees"){
  liste_originaux = read.csv(paste(chemin,'bd_fr.csv',sep='/'),encoding = 'UTF-8')
  works = data.frame(matrix(ncol = 2, nrow = 0))
  for (i in 1:nrow(liste_originaux)){
    line = liste_originaux[i,]
    temp_author = line[,3]
    if (grepl(author,temp_author)){
      temp_id = line[,1]
      temp_date = str_split(line[,4],' ')[[1]][1]
      works = rbind(works,c(temp_id,temp_date))
    }
  }
  colnames(works) <- c('ID', 'DATE')
  return(works)
}

#b = get_all_works('Dr Dharma')

IsDate <- function(mydate, date.format = "%Y-%m-%d") {
  #Source: https://gist.github.com/micstr/69a64fbd0f5635094a53
  # Check if field is a date using as.Date that looks for unambiguous dates
  #   Assumes date format so NA returned not Character error. 
  #   Why? with no date format, R tries two defaults then gives error. 
  #   BUT With a dateformat R returns NA
  # Args
  #   Suspected date and optional date format string
  # Returns
  #   TRUE if thinks it is a date
  tryCatch(!is.na(as.Date(mydate, date.format)),  
           error = function(err) {FALSE})  
}

create_corpus_trad=function(id,chemin="../../bases_de_donnees/en_trad"){
  traducteur = recup_traducteur(id,chemin)
  date_ref = recup_date(id,chemin)
  works_traducteur = get_all_works(traducteur)
  file.copy(paste('../../textes_en',id,'.txt',sep=''),"../../bases_de_donnees/lieu_corpus/corpus")
  file.rename(from=paste('../../bases_de_donnees/lieu_corpus/corpus',id,'.txt',sep=''), to='../../bases_de_donnees/lieu_corpus/corpus/TRAD.txt')
  if (nrow(works_traducteur)>0){
    for (i in 1:nrow(works_traducteur)){
      line = works_traducteur[i,]
      work_date = line[[2]][1]
      if(IsDate(date_ref) && IsDate(work_date)){
        work_date = as.Date(work_date)
        if (date_ref<work_date){
          work_id = line[,1]
          if(file.exists(paste('../../textes_fr',work_id,'.txt',sep=''))){
            file.copy(paste('../../textes_fr',work_id,'.txt',sep=''),"../../bases_de_donnees/lieu_corpus/corpus")
          }
        }
      }else{
        print('Erreur date csv')
        print(paste('Trad :',date_ref))
        print(paste('Objet :',work_date))
        work_id = line[,1]
        if(file.exists(paste('../../textes_fr',work_id,'.txt',sep=''))){
          file.copy(paste('../../textes_fr',work_id,'.txt',sep=''),"../../bases_de_donnees/lieu_corpus/corpus")
        }
      }
      
    }
  }
}
create_corpus_trad('/085-romance-adult')
#create_corpus_trad('/jonathan-ball-s-proposal')
#create_corpus_trad('/scp-2994')

delete_corpus=function(chemin='../../bases_de_donnees/lieu_corpus/corpus'){
  list_file = list.files(chemin, full.names = TRUE)
  list_file = list_file[list_file!=paste(chemin,'/temoin.txt',sep='')]
  file.remove(list_file)
}

delete_corpus()

delete_scp=function(texte){
  return(gsub('[sS][cC][Pp](-[0-9A-Za-z]*)*','',texte))
}

stylo_compare=function(chemin='../../bases_de_donnees/lieu_corpus/',plot=FALSE,id='Dendogramm'){
  original_dir = getwd()
  setwd(chemin)
  corpus = VCorpus(DirSource("corpus", encoding = "UTF-8"), readerControl = list(language = "fr"))
  corpus = tm_map(corpus, content_transformer(tolower))
  corpus = tm_map(corpus, stripWhitespace)
  corpus = tm_map(corpus,content_transformer(delete_scp))
  myDTM = as.matrix(DocumentTermMatrix(corpus, control=list(removePunctuation=FALSE, 
                                                            wordLengths=c(1, Inf), 
                                                            stopwords = FALSE,
                                                            stemming = FALSE
  )))
  data = countAffixes(t(myDTM))
  cluster_maCAH = agnes(t(data), metric = "manhattan", method="ward")
  if(plot){
    plot(cluster_maCAH, which.plots = 2,main=id) 
  }
  setwd(original_dir)
  return(cluster_maCAH)
}

result = stylo_compare(plot=TRUE)
c=result$diss
ac = result$ac
#create_corpus_trad('/escape-from-terminus')

diss_to_df=function(diss_matrix){
  all_textes = list.files(paste(getwd(),'/../../bases_de_donnees/lieu_corpus/corpus',sep=''),recursive = TRUE)
  df <- data.frame(matrix(ncol = length(all_textes)-1, nrow = length(all_textes)-1))
  colnames(df)=all_textes[1:length(all_textes)-1]
  rownames(df)=all_textes[2:length(all_textes)]
  taille = length(all_textes)-1
  last = 1
  for (i in 1:taille){
    #print(paste('i :',i))
    text = all_textes[i]
    end = last+length(all_textes)-1-i
    values = diss_matrix[last:end]
    if (length(values)<length(all_textes)-1){
      while(length(values)<length(all_textes)-1){
        values = c(NA,values)
      }
    }
    df[text] = values
    last = end+1
    #print(paste('Last_indice :',last))
  }
  return(df)
}

df = diss_to_df(c)

find_closest_to_trad=function(diss_matrix){
  if (class(diss_matrix)[1]=="dissimilarity"){
    df = diss_to_df(diss_matrix)
  }else{
    df = diss_matrix
  }
  min=100000000000000
  min_text = NA
  if("TRAD.txt" %in% colnames(df)){
    values = df['TRAD.txt']
    for(i in 1:length(values)){
      value = values[i]
      if(typeof(value)=="list"){
        value = value[[1]][i]
      }
      if(!is.na(value) && value<min){
        min = value
        min_text = rownames(df)[i]
      }
    }
  }
  if("TRAD.txt" %in% rownames(df)){
    values = df['TRAD.txt',]
    for(i in 1:length(values)){
      value = values[[i]]
      if(typeof(value)=="list"){
        value = value[[1]][i]
      }
      if(!is.na(value) && value<min){
        min = value
        min_text = colnames(df)[i]
      }
    }
  }
  return(min_text)
}

find_closest_to_trad(df)

find_farthest_to_trad=function(diss_matrix){
  if (class(diss_matrix)[1]=="dissimilarity"){
    df = diss_to_df(diss_matrix)
  }else{
    df = diss_matrix
  }
  max=0
  max_text = NA
  if("TRAD.txt" %in% colnames(df)){
    values = df['TRAD.txt']
    for(i in 1:length(values)){
      value = values[i]
      if(typeof(value)=="list"){
        value = value[[1]][i]
      }
      if(!is.na(value) && value>max){
        max = value
        max_text = rownames(df)[i]
      }
    }
  }
  if("TRAD.txt" %in% rownames(df)){
    values = df['TRAD.txt',]
    for(i in 1:length(values)){
      value = values[[i]]
      if(typeof(value)=="list"){
        value = value[[1]][i]
      }
      if(!is.na(value) && value>max){
        max = value
        max_text = colnames(df)[i]
      }
    }
  }
  return(max_text)
}

find_farthest_to_trad(df)

stat_quantity=function(chemin="../../textes_en"){
  #Le témoin doit être ajouté à la main dans le corpus avant de lancer. Peut-être que je changerai ça plus tard.
  all_trad = list.files(path=chemin)
  all_trad = all_trad[all_trad!='scp-173.txt']
  verif = list.files(path='../../bases_de_donnees/lieu_corpus/corpus')
  if (length(verif)!=1){
    delete_corpus()
  }
  nb_scp = 0
  nbf_scp = 0
  nb_conte = 0
  nbf_conte = 0
  total_scp = 0
  total_conte = 0
  ac_list = c()
  number = c()
  for(id_text in all_trad){
    end=nchar(id_text)-4
    id=paste('/',substring(id_text,1,end),sep='')
    print(id)
    create_corpus_trad(id)
    if(length(list.files('../../bases_de_donnees/lieu_corpus/corpus'))>2){
      cluster=stylo_compare()
      df = diss_to_df(cluster$diss)
      ac_list = c(ac_list,cluster$ac)
      number = c(number,length(cluster$order))
      closest = find_closest_to_trad(df)
      farthest = find_farthest_to_trad(df)
      if(substring(id_text,1,4)=='scp-'){
        if(closest=='temoin.txt'){
          nb_scp=nb_scp+1
        }else if(farthest == 'temoin.txt'){
          nbf_scp = nbf_scp+1
        }
        total_scp=total_scp+1
      }else{
        if(closest=='temoin.txt'){
          nb_conte=nb_conte+1
        }else if(farthest == 'temoin.txt'){
          nbf_conte = nbf_conte+1
        }
        total_conte=total_conte+1
      }
      delete_corpus()
    }
  }
  if(total_scp>0 && total_conte>0){
    print(paste('Le témon est le texte le plus proche de',scales::percent(nb_scp/total_scp),'des rapports.'))
    print(paste('Le témon est le texte le plus proche de',scales::percent(nb_conte/total_conte),'des contes.'))
    print(paste('Le témon est le texte le plus éloigné de',scales::percent(nbf_scp/total_scp),'des rapports.'))
    print(paste('Le témon est le texte le plus éloigné de',scales::percent(nbf_conte/total_conte),'des contes.'))
    print(paste('Le AC moyen des clusters est de',mean(ac_list),'avec une variance de',var(ac_list),'et un écart-type de',sd(ac_list),'.'))
    print(paste("La taille moyenne de l'échantillon est de",mean(number),'avec une variance de',var(number),"avec un écart-type de",sd(number),"."))
    print(paste("Le corpus le plus grand compte",max(number),"textes, le corpus le moins grand compte",min(number),"textes."))
  }
}

stat_quantity()

random_corpus=function(taille_max=27,taille_min=2){
  
  all_trad = list.files(path="../../textes_en")
  ind_trad=sample(1:length(all_trad),1)
  
  taille_corpus = sample(taille_min:taille_max,1)
  
  all_fr = list.files(path="../../textes_fr")
  inds_fr = sample(1:length(all_fr),taille_corpus)
  
  id_trad = all_trad[ind_trad]
  file.copy(paste('../../textes_en/',id_trad,sep=''),"../../bases_de_donnees/lieu_corpus/corpus")
  file.rename(from=paste('../../bases_de_donnees/lieu_corpus/corpus/',id_trad,sep=''), to='../../bases_de_donnees/lieu_corpus/corpus/TRAD.txt')
  
  for(i in 1:length(inds_fr)){
    id = all_fr[inds_fr[i]]
    file.copy(paste('../../textes_fr/',id,sep=''),"../../bases_de_donnees/lieu_corpus/corpus")
  }
  
  return(id_trad)
}

random_stat_quantity=function(nb_corpus=100){
  nb_scp = 0
  nbf_scp = 0
  nb_conte = 0
  nbf_conte = 0
  total_scp = 0
  total_conte = 0
  ac_list = c()
  for(i in 1:nb_corpus){
    id_text = random_corpus()
    cluster=stylo_compare()
    df = diss_to_df(cluster$diss)
    ac_list = c(ac_list,cluster$ac)
    closest = find_closest_to_trad(df)
    farthest = find_farthest_to_trad(df)
    if(substring(id_text,1,4)=='scp-'){
      if(closest=='temoin.txt'){
        nb_scp=nb_scp+1
      }else if(farthest == 'temoin.txt'){
        nbf_scp = nbf_scp+1
      }
      total_scp=total_scp+1
    }else{
      if(closest=='temoin.txt'){
        nb_conte=nb_conte+1
      }else if(farthest == 'temoin.txt'){
        nbf_conte = nbf_conte+1
      }
      total_conte=total_conte+1
    }
    delete_corpus()
  }
  if(total_scp>0 && total_conte>0){
    print(paste('Le témoin est le texte le plus proche de',scales::percent(nb_scp/total_scp),'des rapports.'))
    print(paste('Le témoin est le texte le plus proche de',scales::percent(nb_conte/total_conte),'des contes.'))
    print(paste('Le témoin est le texte le plus éloigné de',scales::percent(nbf_scp/total_scp),'des rapports.'))
    print(paste('Le témoin est le texte le plus éloigné de',scales::percent(nbf_conte/total_conte),'des contes.'))
    print(paste('Le AC moyen des clusters est de',mean(ac_list),'avec une variance de',var(ac_list),'et un écart-type de',sd(ac_list),'.'))
  }
}

random_stat_quantity()
