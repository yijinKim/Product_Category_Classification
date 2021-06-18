# -*- coding: utf-8 -*-
"""model_training.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1TUAQ4_AH0tnCor2sBtPV5Guzt-brUDIb
"""

import os
import pandas as pd
import numpy as np
import pickle
import random
import time
import datetime

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB 
from sklearn.metrics import accuracy_score

from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, TensorDataset, DataLoader

import warnings
warnings.filterwarnings("ignore") # ignore warning messages


def set_root_dir(location):
    if location == 'colab':
      root_dir = '/content/drive/MyDrive/journal'
      os.chdir(root_dir)
    else: ##location == 'local'
      root_dir = os.getcwd()
    data_dir = os.path.join(root_dir, "data")
    
    print('YOUR WORKING DIR: ', root_dir)
    print('YOUR DATA DIR: ', data_dir)
    return root_dir, data_dir
          

def read_csv(filename):
    return pd.read_csv(os.path.join(data_dir, filename), encoding='utf-8')


def save_csv(df, filename):
    return df.to_csv(os.path.join(data_dir, filename), index=False)

def load_le(filename):
    with open(os.path.join(data_dir, filename), 'rb') as f:
        le = pickle.load(f)
    return le


class NaiveBayes:
    def __init__(self, filename,column_list):
        self.data = read_csv(filename)
        self.column_list = column_list


    def nb(self):
        self.operate_column()
        self.naivebayes()
        print('=====Navie Bayes Completed=====\n')
        return self.data


    def operate_column(self):
        if len(self.column_list) == 1:
            self.data[self.column_list[0]] = self.data[self.column_list[0]].map(str)
        else: ## len = 2 or 3
            self.data['combo'] = ''
            for col in self.column_list:
                self.data['combo'] = self.data['combo'] + ' ' + self.data[col].map(str)
                self.data['combo'] = self.data['combo'].apply(lambda x: x.strip())
                self.column_list = ['combo']
        self.column_list.extend(['cate_two','label'])
        self.data = self.data[self.column_list]
        return self.data


    def naivebayes(self):
        X_train, X_test, y_train, y_test = train_test_split(self.data[self.column_list[0]], self.data['cate_two'], random_state = 0)#데이터 나누기
        count_vect = CountVectorizer()
        tfidf_transformer = TfidfTransformer()
        X_train_counts = count_vect.fit_transform(X_train)
        X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)
        X_test_counts = count_vect.transform(X_test)
        X_test_tfidf = tfidf_transformer.transform(X_test_counts)
        baseline = MultinomialNB()
        baseline.fit(X_train_tfidf, y_train)
        y_test_pred_tnt = baseline.predict(X_test_tfidf)
        print("accuracy : {:.4f}".format(accuracy_score(y_test, y_test_pred_tnt)))

class BeforeTraining:
    def __init__(self, filename,column_list):
        self.data = read_csv(filename)
        self.column_list = column_list
        self.batch_size = 64
        self.max_features = 10000


    def beforetrain(self):
        train, test, train_y, test_y = self.preparing()
        train_sequence_list,test_sequence_list,word_index_list = self.tokenizing(train, test)
        train_loader, test_loader = self.make_tensords(train_sequence_list,test_sequence_list,train_y, test_y)
        print('=====Before Training Completed=====\n')
        return word_index_list, train_loader, test_loader
        

    def preparing(self):
        for col in self.column_list:
            self.data[col] = self.data[col].apply(lambda x: str(x))
        train,test = self.train_test()
        train_y = np.array(train['label'].tolist())
        test_y = np.array(test['label'].tolist())
        return train, test, train_y, test_y


    def train_test(self):
        test = self.data.sample(frac=0.1,random_state = 2020) #10
        train = self.data.drop(test.index)  #90
        for col in self.column_list:
            train[col] = train[col].astype(str)
            test[col] = test[col].astype(str)
        del self.data
        return train, test


    def make_sequence(self, tokenizer, dataframe, column):
        maxlen_list = [61, 92, 200]
        sequence = tokenizer.texts_to_sequences(dataframe[column].tolist())
        sequence = pad_sequences(sequence, maxlen = maxlen_list[column_dict[column]])
        return sequence


    def tokenizing(self, train, test):
        train_sequence_list = []
        test_sequence_list = []
        word_index_list = []
        

        tokenizer = Tokenizer(num_words = self.max_features)  ## max_features = 10000 #토큰화에 사용할 단어수
        for col in self.column_list:
            tokenizer.fit_on_texts(train[col].tolist())
            train_sequence = self.make_sequence(tokenizer, train, col)            
            test_sequence = self.make_sequence(tokenizer, test, col)            
            word_index = tokenizer.word_index

            train_sequence_list.append(train_sequence)
            test_sequence_list.append(test_sequence)
            word_index_list.append(word_index)
        # del train, test
        return train_sequence_list,test_sequence_list, word_index_list
        

    def load_glove(self, word_index):
        EMBEDDING_FILE = os.path.join(data_dir, 'glove.840B.300d.txt')
        def get_coefs(word,*arr): return word, np.asarray(arr, dtype='float32')[:200]
        embeddings_index = dict(get_coefs(*o.split(" ")) for o in open(EMBEDDING_FILE,encoding='utf-8'))
        
        all_embs = np.stack(embeddings_index.values())
        emb_mean,emb_std = -0.005838499,0.48782197
        embed_size = all_embs.shape[1]

        nb_words = min(self.max_features, len(word_index)+1)
        embedding_matrix = np.random.normal(emb_mean, emb_std, (nb_words, embed_size))
        for word, i in word_index.items():
            if i >= self.max_features: continue
            embedding_vector = embeddings_index.get(word)
            if embedding_vector is not None: 
                embedding_matrix[i] = embedding_vector
            else:
                embedding_vector = embeddings_index.get(word.capitalize())
                if embedding_vector is not None: 
                    embedding_matrix[i] = embedding_vector
        return embedding_matrix


    def embed_mat(self, word_index_list):
        debug = 0
        if debug:
            embedding_mat = np.random.randn(120000,200)
        else:
            embedding_mat = self.load_glove(word_index_list)
        return embedding_mat


    def load_tensor(self, ds):
        return torch.tensor(ds, dtype=torch.long).cuda()


    def make_tensords(self, train_sequence_list, test_sequence_list,train_y, test_y):
        x_train = torch.cat([self.load_tensor(train_sequence_list[idx]) for idx in range(len(self.column_list))],dim=1)
        x_test = torch.cat([self.load_tensor(test_sequence_list[idx]) for idx in range(len(self.column_list))],dim=1)
        y_train = self.load_tensor(train_y)
        y_test =self.load_tensor(test_y)

        train_tensords = torch.utils.data.TensorDataset(x_train, y_train)
        test_tensords = torch.utils.data.TensorDataset(x_test, y_test)

        train_loader = torch.utils.data.DataLoader(train_tensords, batch_size=self.batch_size, shuffle=True)
        test_loader = torch.utils.data.DataLoader(test_tensords, batch_size=self.batch_size, shuffle=False)

        return train_loader, test_loader

def flat_accuracy(preds, labels):
    pred_flat = np.argmax(preds, axis=1).flatten()
    labels_flat = labels.flatten()
    return np.sum(pred_flat == labels_flat) / len(labels_flat)

def format_time(elapsed):
    elapsed_rounded = int(round((elapsed)))
    return str(datetime.timedelta(seconds=elapsed_rounded))


def load_model_cuda(column_list, model_name):
    if model_name == 'cnn':
        model = CNN_Label().to(device)
    elif model_name =='bilstm':
        model = BiLSTM_Label().to(device)

    loss_fn = nn.CrossEntropyLoss(reduction='sum')
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=0.001)
    model.cuda()
    return model, loss_fn, optimizer

class CNN_Label(nn.Module):
  def __init__(self):
    super(CNN_Label, self).__init__()
    # self.embeds = nn.ModuleList([nn.Embedding(len(word_index_list[column_dict[C]]) +1,embed_size) for C in column_list]) 
    self.embeds = nn.ModuleList([nn.Embedding(len(word_index_list[i])+1, embed_size) for i in range(len(column_list))])
    self.embeds.weight = nn.Parameter(torch.tensor(embedding_matrix, dtype=torch.float32))
    self.embeds.weight.requires_grad = False
    self.dropout = nn.Dropout(0.3) 
    self.convs1 = nn.ModuleList([nn.Conv2d(1, num_filters, (K, embed_size)) for K in filter_sizes])
    self.maxpool1d = nn.MaxPool1d(2)
    self.relu = nn.ReLU()  
    self.fc1 = nn.Linear(len(filter_sizes)*num_filters, 512)
    self.fc2 = nn.Linear(512, 256)
    self.fc3 = nn.Linear(256, 64)
    self.fc4 = nn.Linear(64, 120)

  def forward(self, x):
    x = [embed(x).squeeze(2) for embed in self.embeds] ##
    x = torch.cat(x, 1) ##
    x = x.unsqueeze(1)
    x = self.dropout(x)
    x = [F.relu(conv(x)).squeeze(3) for conv in self.convs1]
    x = [F.max_pool1d(i, i.size(2)).squeeze(2) for i in x] 
    x = torch.cat(x, 1)
    x = F.relu(self.fc1(x))
    x = F.relu(self.fc2(x))
    x = F.relu(self.fc3(x))
    x = F.log_softmax(self.fc4(x), dim=1)
    
    return x

class BiLSTM_Label(nn.Module):    
    def __init__(self):
        super(BiLSTM_Label, self).__init__()
        self.hidden_size = 64
        n_classes = len(le.classes_)
        # self.embeds = nn.ModuleList([nn.Embedding(len(word_index_list[column_dict[C]]) +1,embed_size) for C in column_list]) 
        self.embeds = nn.ModuleList([nn.Embedding(len(word_index_list[i])+1, embed_size) for i in range(len(column_list))])
        self.embeds.weight = nn.Parameter(torch.tensor(embedding_matrix, dtype=torch.float32))
        self.embeds.weight.requires_grad = False ###
        # self.embedding = nn.Embedding(len(word_index_list[2]) +1, embed_size)
        self.lstm = nn.LSTM(embed_size, self.hidden_size, bidirectional=True, batch_first=True)
        self.linear = nn.Linear(self.hidden_size*4 , 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.out = nn.Linear(64, n_classes)

    def forward(self, x):
        x = [embed(x).squeeze(2) for embed in self.embeds]
        h_embedding = torch.cat(x, 1)
        # h_embedding = self.embedding(x)
        #_embedding = torch.squeeze(torch.unsqueeze(h_embedding, 0))
        h_lstm, _ = self.lstm(h_embedding)
        avg_pool = torch.mean(h_lstm, 1)
        max_pool, _ = torch.max(h_lstm, 1)
        conc = torch.cat(( avg_pool, max_pool), 1)
        conc = self.relu(self.linear(conc))
        conc = self.dropout(conc)
        out = self.out(conc)
        return out

class Training:
    def __init__(self,  model, loss_fn, optimizer,  train_loader, test_loader):
        self.model = model
        self.loss_fn = loss_fn
        self.optimizer = optimizer
        self.train_loader = train_loader
        self.test_loader = test_loader
        self.seed_val = 42

    def training(self):
        training_stats = self.train_model(model, train_loader, test_loader)
        df_stats = self.print_stats(training_stats)
        return df_stats
        

    def train_model(self, model, train_loader, test_loader):
        random.seed(self.seed_val)
        np.random.seed(self.seed_val)
        torch.manual_seed(self.seed_val)
        torch.cuda.manual_seed_all(self.seed_val)

        training_stats = []

        # Measure the total training time for the whole run.
        start_time = time.time()
        epoch_i = 0

        while True:
            t0 = time.time()
            total_train_loss = 0
            self.model.train()

            for step,  (x_batch, y_batch) in enumerate(self.train_loader):
                self.model.zero_grad()        
                y_pred = self.model(x_batch)
                loss  = loss_fn(y_pred, y_batch)
                optimizer.zero_grad()
                total_train_loss += loss.item()
                loss.backward()
                optimizer.step()
            avg_train_loss = total_train_loss / len(self.train_loader)            
            training_time = format_time(time.time() - t0)
            t0 = time.time()
            self.model.eval()

            total_eval_accuracy = 0
            total_eval_loss = 0
            nb_eval_steps = 0

            for i, (x_batch, y_batch) in enumerate(self.test_loader):
                with torch.no_grad():        
                    y_pred = self.model(x_batch).detach()
                total_eval_loss += loss_fn(y_pred,y_batch).item()
                y_pred = y_pred.detach().cpu().numpy()
                label_ids = y_batch.to('cpu').numpy()
                total_eval_accuracy += flat_accuracy(y_pred, label_ids)

            avg_test_accuracy = total_eval_accuracy / len(self.test_loader)   
            avg_test_loss = total_eval_loss / len(self.test_loader)
            if epoch_i == 0:
                min_test_loss = avg_test_loss
            else:
                if min_test_loss >= avg_test_loss:
                    min_test_loss = avg_test_loss
                else:
                    break
            test_time = format_time(time.time() - t0)
            training_stats.append(
                {
                    'epoch': epoch_i + 1,
                    'Train. Loss': avg_train_loss,
                    'Test. Loss': avg_test_loss,
                    'Test. Acc.': avg_test_accuracy
                }
            )
            epoch_i = epoch_i + 1
        print("")
        print("Training complete!")
        print("Total Training time {:} (h:mm:ss)".format(format_time(time.time()-start_time)))
        return training_stats


    def print_stats(self, stats):
        pd.set_option('precision', 4)
        df_stats = pd.DataFrame(data = stats)
        df_stats = df_stats.set_index('epoch')
        return df_stats

if __name__ == "__main__":
    column_dict = {'name': 0, 'keyword': 1, 'description': 2}
    
    #check your working directory
    rootdir, data_dir = set_root_dir('colab')
    #input label encoder file
    le = load_le('label_encoder.pkl')

    #select your data columns
    column_list = ['name','description']
    # column_list = ['keyword']

    #filename
    filename = 'step5/step5_unit.csv'

    #Naive Bayes
    naive = NaiveBayes(filename, column_list)
    data = naive.nb()

    #ML
    before_train = BeforeTraining(filename, column_list)
    word_index_list, train_loader, test_loader = before_train.beforetrain()
    embedding_matrix = before_train.embed_mat(word_index_list[0])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    embed_size = 200
    num_filters = 128
    n_classes = len(le.classes_)
    filter_sizes = {'name':[2, 3], 'keyword':[2, 3], 'description':[3, 4, 5]}[column_list[0]]

    model, loss_fn, optimizer = load_model_cuda(column_list, 'cnn')

    after_train = Training(model, loss_fn, optimizer,  train_loader, test_loader)
    # training(model, train_loader, test_loader)
    # print_stats(training_stats)
    df_stats = after_train.training()
    df_stats

df_stats

