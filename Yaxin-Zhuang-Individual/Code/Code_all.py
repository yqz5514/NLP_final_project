# %% -------------------------------------- Imports ------------------------------------------------------------------
import os
import torch
import pandas as pd
import regex as re
from sklearn.model_selection import train_test_split
import torch.nn as nn
from transformers import AutoTokenizer, DataCollatorWithPadding
from torch.utils.data import Dataset, DataLoader, TensorDataset
from transformers import AutoModel
from transformers import AdamW
from transformers import get_scheduler
from sklearn.metrics import accuracy_score
import numpy as np
import string
from nltk.corpus import stopwords
#%%
#%%
os.chdir('/home/ubuntu/test/Final-Project-Group/Code')
os.getcwd()
#%%
df = pd.read_csv('Tweets.csv')
#%%
df.head()
#%%
df1 = df[['text','airline_sentiment']].copy()
df1['WORD_COUNT'] = df1['text'].apply(lambda x: len(x.split()))
#%%
df1.describe()
#  WORD_COUNT
# count  14640.000000
# mean      17.653415
# std        6.882259
# min        2.000000
# 25%       12.000000
# 50%       19.000000
# 75%       23.000000
# max       36.000000

# %% -------------------------------------- Global Vars ------------------------------------------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SEED = 42
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)
OUTPUT_DIM = 3
BATCH_SIZE = 64
#MAX_VOCAB_SIZE = 25_000
MAX_LEN = 300
N_EPOCHS = 5
LR = 0.0001
checkpoint = "bert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

# %% -------------------------------------- Helper Functions ------------------------------------------------------------------
def TextCleaning(text):
    '''
    Takes a string of text and performs some basic cleaning.
    1. removes tabs
    2. removes newlines
    3. removes special chars
    4. creates the word "not" from words ending in n't
    '''
    # Step 1
    pattern1 = re.compile(r'\<.*?\>')
    s = re.sub(pattern1, '', text)

    # Step 2
    pattern2 = re.compile(r'\n')
    s = re.sub(pattern2, ' ', s)

    # Step 3
    pattern3 = re.compile(r'[^0-9a-zA-Z!/?]+')
    s = re.sub(pattern3, ' ', s)

    # Step 4
    pattern4 = re.compile(r"n't")
    s = re.sub(pattern4, " not", s)

    return s
def text_process(text):
    """
    Takes in a string of text, then performs the following:
    1. Remove all punctuation
    2. Remove all stopwords
    3. Returns a list of the cleaned text
    """
    STOPWORDS = stopwords.words('english') + ['u', 'ü', 'ur', '4', '2', 'im', 'dont', 'doin', 'ure']
    # Check characters to see if they are in punctuation
    nopunc = [char for char in text if char not in string.punctuation]

    # Join the characters again to form the string.
    nopunc = ''.join(nopunc)

    # Now just remove any stopwords
    return ' '.join([word for word in nopunc.split() if word.lower() not in STOPWORDS])


contraction_dict = {"ain't": "is not", "aren't": "are not", "can't": "cannot", "'cause": "because",
                    "could've": "could have", "couldn't": "could not", "didn't": "did not", "doesn't": "does not",
                    "don't": "do not", "hadn't": "had not", "hasn't": "has not", "haven't": "have not",
                    "he'd": "he would", "he'll": "he will", "he's": "he is", "how'd": "how did",
                    "how'd'y": "how do you", "how'll": "how will", "how's": "how is", "I'd": "I would",
                    "I'd've": "I would have", "I'll": "I will", "I'll've": "I will have", "I'm": "I am",
                    "I've": "I have", "i'd": "i would", "i'd've": "i would have", "i'll": "i will",
                    "i'll've": "i will have", "i'm": "i am", "i've": "i have", "isn't": "is not", "it'd": "it would",
                    "it'd've": "it would have", "it'll": "it will", "it'll've": "it will have", "it's": "it is",
                    "let's": "let us", "ma'am": "madam", "mayn't": "may not", "might've": "might have",
                    "mightn't": "might not", "mightn't've": "might not have", "must've": "must have",
                    "mustn't": "must not", "mustn't've": "must not have", "needn't": "need not",
                    "needn't've": "need not have", "o'clock": "of the clock", "oughtn't": "ought not",
                    "oughtn't've": "ought not have", "shan't": "shall not", "sha'n't": "shall not",
                    "shan't've": "shall not have", "she'd": "she would", "she'd've": "she would have",
                    "she'll": "she will", "she'll've": "she will have", "she's": "she is", "should've": "should have",
                    "shouldn't": "should not", "shouldn't've": "should not have", "so've": "so have", "so's": "so as",
                    "this's": "this is", "that'd": "that would", "that'd've": "that would have", "that's": "that is",
                    "there'd": "there would", "there'd've": "there would have", "there's": "there is",
                    "here's": "here is", "they'd": "they would", "they'd've": "they would have", "they'll": "they will",
                    "they'll've": "they will have", "they're": "they are", "they've": "they have", "to've": "to have",
                    "wasn't": "was not", "we'd": "we would", "we'd've": "we would have", "we'll": "we will",
                    "we'll've": "we will have", "we're": "we are", "we've": "we have", "weren't": "were not",
                    "what'll": "what will", "what'll've": "what will have", "what're": "what are", "what's": "what is",
                    "what've": "what have", "when's": "when is", "when've": "when have", "where'd": "where did",
                    "where's": "where is", "where've": "where have", "who'll": "who will", "who'll've": "who will have",
                    "who's": "who is", "who've": "who have", "why's": "why is", "why've": "why have",
                    "will've": "will have", "won't": "will not", "won't've": "will not have", "would've": "would have",
                    "wouldn't": "would not", "wouldn't've": "would not have", "y'all": "you all",
                    "y'all'd": "you all would", "y'all'd've": "you all would have", "y'all're": "you all are",
                    "y'all've": "you all have", "you'd": "you would", "you'd've": "you would have",
                    "you'll": "you will", "you'll've": "you will have", "you're": "you are", "you've": "you have"}


def _get_contractions(contraction_dict):
    contraction_re = re.compile('(%s)' % '|'.join(contraction_dict.keys()))
    return contraction_dict, contraction_re


contractions, contractions_re = _get_contractions(contraction_dict)


def replace_contractions(text):
    def replace(match):
        return contractions[match.group(0)]

    return contractions_re.sub(replace, text)

def getLabel(df, label_col, input_col):
    encoded = pd.get_dummies(df, columns=[label_col])
    encoded_val = encoded.iloc[:, 1:].apply(list, axis=1)
    encoded['target'] = encoded_val
    return_df = encoded[[input_col, 'target']]
    return return_df



def create_data_loader(df, tokenizer, max_len=MAX_LEN,batch_size=BATCH_SIZE):
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    ds = TextDataset(
        data_frame = df,
        tokenizer = tokenizer,
        max_len = max_len,
        input_col = input_col)
    return DataLoader(ds, batch_size=BATCH_SIZE, collate_fn=data_collator, drop_last=True)


# %% -------------------------------------- Dataset Class ------------------------------------------------------------------

class TextDataset(Dataset):
    def __init__(self, data_frame, tokenizer, max_len,input_col):
        self.data_frame = data_frame
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data_frame)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        input = self.data_frame.iloc[idx][input_col]
        target = self.data_frame.iloc[idx]['target_list']
        encoding = self.tokenizer(
            input,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            return_attention_mask=True,
            truncation=True,
            padding=True,
            return_tensors='pt', )

        output = {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(target, dtype=torch.long)
        }

        return output



# %% -------------------------------------- Model Class ------------------------------------------------------------------
class BERT_PLUS_RNN(nn.Module):

    def __init__(self, bert, no_layers, hidden_dim, output_dim, batch_size):
        super(BERT_PLUS_RNN, self).__init__()
        self.bert = bert
        self.output_dim = output_dim
        self.hidden_dim = hidden_dim
        self.batch_size = batch_size
        #self.batch_size = 1
        self.embedding_dim = bert.config.to_dict()['hidden_size']
        self.no_layers = no_layers
        self.lstm = nn.LSTM(input_size=self.embedding_dim, hidden_size=self.hidden_dim, num_layers=no_layers,
                            batch_first=True)
        self.dropout = nn.Dropout(0.5)
        self.fc = nn.Linear(self.hidden_dim, self.output_dim)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x, hidden, attention_mask):
        batch_size = x.size(0)
        embedded = self.bert(input_ids=x,attention_mask=attention_mask)[0]
        input = embedded.permute(1, 0, 2)
        #lstm_out, hidden = self.lstm(input, hidden)
        lstm_out, hidden = self.lstm(embedded, hidden)
        lstm_out = lstm_out.contiguous().view(-1, self.hidden_dim)
        out = self.dropout(lstm_out)
        out = self.fc(out)
        #out = self.fc(lstm_out)
        out = self.softmax(out)
        out = out.view(batch_size, -1, self.output_dim)
        out = out[:, -1]
        return out, hidden

    def init_hidden(self, batch_size):
        h0 = torch.zeros((self.no_layers, batch_size, self.hidden_dim)).to(device)
        c0 = torch.zeros((self.no_layers, batch_size, self.hidden_dim)).to(device)
        hidden = (h0, c0)
        return hidden


# %% -------------------------------------- Data Prep ------------------------------------------------------------------
# step 1: load data from .csv
# PATH = os.getcwd()
# os.chdir(PATH + '/archive(4)/')
#%%
os.chdir('/home/ubuntu/test/Final-Project-Group/Code')
#%%
os.getcwd()
#%%
df = pd.read_csv("Tweets.csv")

# get data with only text and labels
df_copy = df.copy()
input_col = 'text'
label_col = 'airline_sentiment'
df_copy = df_copy[[input_col, label_col]]
df_copy = getLabel(df_copy, label_col, input_col)

# clean X data
df_copy[input_col] = df_copy[input_col].apply(lambda x: x.lower())
#df_copy[input_col] = df_copy[input_col].apply(replace_contractions)
df_copy[input_col] = df_copy[input_col].apply(text_process)
df_copy[input_col] = df_copy[input_col].apply(TextCleaning)
#%%
#%%
df2 = df[['text','airline_sentiment']]
#%%
df2['text'] = df2['text'].apply(text_process)
#%%
input_col = 'text'
label_col = 'airline_sentiment'
# split data
train, test = train_test_split(df2, train_size=0.8, random_state=SEED, stratify=df2['airline_sentiment'])
train, val = train_test_split(train, train_size=0.8, random_state=SEED, stratify=train['airline_sentiment'])

print(f'shape of train data is {train.shape}')
print(f'shape of validation data is {val.shape}')
print(f'shape of test data is {test.shape}')

train_loader = create_data_loader(train, tokenizer=tokenizer, max_len=MAX_LEN, batch_size=BATCH_SIZE)
valid_loader = create_data_loader(val, tokenizer=tokenizer, max_len=MAX_LEN, batch_size=BATCH_SIZE)
test_loader = create_data_loader(test, tokenizer=tokenizer, max_len=MAX_LEN, batch_size=BATCH_SIZE)

# %% -------------------------------------- Model ------------------------------------------------------------------
bert = AutoModel.from_pretrained(checkpoint)
#freeze the pretrained layers
for param in bert.parameters():
    param.requires_grad = False
no_layers = 3
hidden_dim = 256
clip = 5
model = BERT_PLUS_RNN(bert, no_layers, hidden_dim, OUTPUT_DIM, BATCH_SIZE)
model.to(device)

optimizer = AdamW(model.parameters(), lr=LR)
criterion = torch.nn.BCELoss()
#%%
#%%
df2 = df1[['text','airline_sentiment']]
df2['text'] = df2['text'].apply()
#%%---------------------------------------Lime_n------------------------
import torch
import torch.nn.functional as F
from lime.lime_text import LimeTextExplainer
#print(test)

class_names = ['positive', 'neutral', 'negative']

def predictor(texts):
    outputs = model(input_ids=batch['input_ids'].to(device), attention_mask=batch['attention_mask'].to(device))
    tensor_logits = outputs[0].cpu()
    probas = F.softmax(tensor_logits).detach().numpy()


    return probas

c=predictor(test_doc[0])
print(c.shape)
text="hello my bame is"
print(c)
explainer = LimeTextExplainer(class_names=class_names)
exp = explainer.explain_instance(test_doc[0], predictor, num_features=20, num_samples=2000)



# Store our loss and accuracy for plotting
#%%
from lime.lime_text import LimeTextExplainer

explainer = LimeTextExplainer(class_names=['neutral', 'positive', 'negative'])


def predict_probab(STR):
    z = tokenizer.encode_plus(
        STR,
        add_special_tokens=True,
        max_length=200,
        return_attention_mask=True,
        is_split_into_words=True,
        truncation=True,
        padding='max_length',
        return_tensors='pt', )
    # z = tokenizer.encode_plus(STR, add_special_tokens=True, max_length=512, truncation=True, padding='max_length',
    #                           return_token_type_ids=True, return_attention_mask=True, return_tensors='np')
    #inputs = [z['input_ids'], z['attention_mask']]
    inputs, attention_mask = z['input_ids'].to(device),z['attention_mask'].to(device)
    h = model.init_hidden(1)
    h = tuple([each.data for each in h])
    output, h = model(inputs, h, attention_mask)
    preds = output.detach().cpu().numpy().reshape(1, -1)

    # for batch in test_loader:
    #     outputs = model(input_ids=batch[input_ids].to(device), attention_mask=batch['attention_mask'].to(device))
    #     preds = outputs.detach().cpu().numpy()
    #     return preds
    # inputs = [z['input_ids'], z['attention_mask']]
    # k = []
    # k.append(float(output.reshape(-1, 1)))
    # #k.append(float(1 - output.reshape(-1, 1)))
    # k = np.array(k).reshape(1, -1)

    return preds

#input_ids = '13789'
STR = str(test.text[13789])
exp = explainer.explain_instance(STR, predict_probab, num_features=10, num_samples=1)
#%%
# mport numpy as np
# import lime
# import torch
import torch.nn.functional as F
from lime.lime_text import LimeTextExplainer
#%%
# from transformers import AutoTokenizer, AutoModelForSequenceClassification

# tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
# model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
class_names=['neutral', 'positive', 'negative']

def predictor(STR):
    z = tokenizer.encode_plus(
        STR,
        add_special_tokens=True,
        max_length=200,
        return_attention_mask=True,
        is_split_into_words=True,
        truncation=True,
        padding='max_length',
        return_tensors='pt', )
# outputs = model(**tokenizer(texts, return_tensors="pt", padding=True))

    inputs, attention_mask = z['input_ids'].to(device), z['attention_mask'].to(device)
    h = model.init_hidden(1)
    h = tuple([each.data for each in h])
    output, h = model(inputs, h, attention_mask)
    #token_logits = model(inputs, h, attention_mask).logits
    #outputs = output.view(-1, OUTPUT_DIM)
    #preds = output.detach().cpu().numpy()
    result = []
    logits = output[0]
    logits = F.softmax(logits).cpu().numpy()
    result.append(logits.detach().cpu().numpy()[0])
    results_array = np.array(result)
    return results_array
#         results = []
#         for example in examples:
#
#             with torch.no_grad():
#                 outputs = self.model(example[0], example[1], example[2])
#             logits = outputs[0]
#             logits = F.softmax(logits, dim = 1)
#             results.append(logits.cpu().detach().numpy()[0])
#
#         results_array = np.array(results)
#
#         return results_array
#
explainer = LimeTextExplainer(class_names=class_names)

STR = str(test.text[13789])
exp = explainer.explain_instance(STR, predictor, num_features=20, num_samples=2000)
exp.show_in_notebook(text=STR)
#%%
df2 = df[['text','airline_sentiment']]
#%%
df2['text'] = df2['text'].apply(text_process)
#%%
# s_mapping = {
#            'neutral': 1,
#            'positive': 2,
#             'negative': 3}
# df2['airline_sentiment'] = df2['airline_sentiment'].map(s_mapping)

#%%----------------------------------------lime

class_names = ['positive','negative', 'neutral']

results = []
def predictor(STR):
    z = tokenizer.encode_plus(
            STR,
            add_special_tokens=True,
            max_length=300,
            return_attention_mask=True,
            is_split_into_words=True,
            truncation=True,
            padding=True,
            return_tensors='pt',
            )
        #output = model(**tokenizer(STR, return_tensors="pt", padding=True))

    inputs, attention_mask = z['input_ids'].to(device), z['attention_mask'].to(device)
    # for batch in test_loader:
    #     output = model(input_ids=batch['input_ids'].to(device), attention_mask=batch['attention_mask'].to(device))

    h = model.init_hidden(1)
    h = tuple([each.data for each in h])
    output,h = model(inputs, h, attention_mask)
    #probas = F.softmax(model(inputs, h, attention_mask).logits).detach().numpy()
    with torch.no_grad():
        #output = model(inputs, h, attention_mask)
           logits = output[0]

           logits = F.softmax(logits,dim=0)
           results.append(logits.cpu().detach().numpy()[0])
           results_array = np.array(results)

    return results_array

    #probas = F.softmax(h, dim = 1).cpu().detach().numpy()

    # results.append(h.detach()[0])
    #
    # ress = [res for res in results]
    # results_array = np.array(ress)
    # return results_array



# results.append(raw_outputs[0])
#
# ress = [res for res in results]
# results_array = np.array(ress)
# return results_array
#
# outputs = model(**tokenizer(texts, return_tensors="pt", padding=True))
# probas = F.softmax(outputs.logits).detach().numpy()
        #return probas
#%%
#predictor(str(test.text[13789]))
#%%
explainer = LimeTextExplainer(class_names=class_names)

STR = str(test.text[2998])
exp = explainer.explain_instance(STR, predictor, num_features=20, num_samples=2000)
exp.show_in_notebook(text=STR)

#%%
for batch in test_loader:
    print(batch[13789])
#%%--------------------------------------lime_method_2----------------------------------------------------------
import lime
from lime import lime_text
class Prediction:

    def __init__(self, bert_model_class, model_path, lower_case, seq_length):

        self.model, self.tokenizer, self.model_config = \
                    self.load_model(bert_model_class, model_path, lower_case)
        self.max_seq_length = seq_length
        self.device = "cpu"
        self.model.to("cpu")

    def load_model(self, bert_model_class, model_path, lower_case):

        config_class, model_class, tokenizer_class = MODEL_CLASSES[bert_model_class]
        config = config_class.from_pretrained(model_path)
        tokenizer = tokenizer_class.from_pretrained(model_path, do_lower_case=lower_case)
        model = model_class.from_pretrained(model_path, config=config)

        return model, tokenizer, config

    def predict_label(self, text_a, text_b):

        self.model.to(self.device)

        input_ids, input_mask, segment_ids = self.convert_text_to_features(text_a, text_b)
        with torch.no_grad():
            outputs = self.model(input_ids, segment_ids, input_mask)

        logits = outputs[0]
        logits = F.softmax(logits, dim=1)
        # print(logits)
        logits_label = torch.argmax(logits, dim=1)
        label = logits_label.detach().cpu().numpy()

        # print("logits label ", logits_label)
        logits_confidence = logits[0][logits_label]
        label_confidence_ = logits_confidence.detach().cpu().numpy()
        # print("logits confidence ", label_confidence_)

        return label, label_confidence_


    def _truncate_seq_pair(self, tokens_a, max_length):
        """Truncates a sequence pair in place to the maximum length."""

        # This is a simple heuristic which will always truncate the longer sequence
        # one token at a time. This makes more sense than truncating an equal percent
        # of tokens from each, since if one sequence is very short then each token
        # that's truncated likely contains more information than a longer sequence.
        while True:
            total_length = len(tokens_a)
            if total_length <= max_length:
                break
            if len(tokens_a) > max_length:
                tokens_a.pop()

    def convert_text_to_features(self, text_a, text_b=None):

        features = []
        cls_token = self.tokenizer.cls_token
        sep_token = self.tokenizer.sep_token
        cls_token_at_end = False
        sequence_a_segment_id = 0
        sequence_b_segment_id = 1
        cls_token_segment_id = 1
        pad_token_segment_id = 0
        mask_padding_with_zero = True
        pad_token = 0
        tokens_a = self.tokenizer.tokenize(text_a)
        tokens_b = None

        self._truncate_seq_pair(tokens_a, self.max_seq_length - 2)

        tokens = tokens_a + [sep_token]
        segment_ids = [sequence_a_segment_id] * len(tokens)

        if tokens_b:
            tokens += tokens_b + [sep_token]
            segment_ids += [sequence_b_segment_id] * (len(tokens_b) + 1)


        tokens = [cls_token] + tokens
        segment_ids = [cls_token_segment_id] + segment_ids

        input_ids = self.tokenizer.convert_tokens_to_ids(tokens)

        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        input_mask = [1 if mask_padding_with_zero else 0] * len(input_ids)
        #
        # # Zero-pad up to the sequence length.
        padding_length = self.max_seq_length - len(input_ids)


        input_ids = input_ids + ([pad_token] * padding_length)
        input_mask = input_mask + ([0 if mask_padding_with_zero else 1] * padding_length)
        segment_ids = segment_ids + ([pad_token_segment_id] * padding_length)

        assert len(input_ids) == self.max_seq_length
        assert len(input_mask) == self.max_seq_length
        assert len(segment_ids) == self.max_seq_length

        input_ids = torch.tensor([input_ids], dtype=torch.long).to(self.device)
        input_mask = torch.tensor([input_mask], dtype=torch.long).to(self.device)
        segment_ids = torch.tensor([segment_ids], dtype=torch.long).to(self.device)

        return input_ids, input_mask, segment_ids

    def predictor(self, text):

        examples = []
        print(text)
        for example in text:
            examples.append(self.convert_text_to_features(example))

        results = []
        for example in examples:

            with torch.no_grad():
                outputs = self.model(example[0], example[1], example[2])
            logits = outputs[0]
            logits = F.softmax(logits, dim = 1)
            results.append(logits.cpu().detach().numpy()[0])

        results_array = np.array(results)

        return results_array



if __name__ == '__main__':

    model_path = "models/mrpc"
    bert_model_class = "bert"
    prediction = Prediction(bert_model_class, model_path,
                                lower_case = True, seq_length = 512)
    label_names = [0, 1]
    explainer = LimeTextExplainer(class_names=label_names)
    train_df = pd.read_csv("data/train.tsv", sep = '\t')

    train_ls = train_df["string"].tolist()

    for example in train_ls:

        exp = explainer.explain_instance(example, prediction.predictor)
        words = exp.as_list()
#%%_----------------------------------------------------------
import numpy as np
import lime
import torch
import torch.nn.functional as F
from lime.lime_text import LimeTextExplainer

from transformers import AutoTokenizer, AutoModelForSequenceClassification

tokenizer = AutoTokenizer.from_pretrained(checkpoint)
model = AutoModelForSequenceClassification.from_pretrained(checkpoint)
class_names = ['positive','negative', 'neutral']

def predictor(texts):
    outputs = model(**tokenizer(texts, return_tensors="pt", padding=True))
    probas = F.softmax(outputs.logits).detach().numpy()
    return probas

explainer = LimeTextExplainer(class_names=class_names)

str_to_predict = "surprising increase in revenue in spite of decrease in market share"
exp = explainer.explain_instance(str_to_predict, predictor, num_features=20, num_samples=2000)
exp.show_in_notebook(text=str_to_predict)
#%%
# this is joe method
# https://towardsdatascience.com/how-to-save-and-load-a-model-in-pytorch-with-a-complete-example-c2920e617dee
def train_model(start_epochs, n_epochs, valid_loss_min_input,
                training_loader, validation_loader, model,
                optimizer, checkpoint_path, best_model_path):
    # initialize tracker for minimum validation loss
    valid_loss_min = valid_loss_min_input

    for epoch in range(start_epochs, n_epochs + 1):
        train_loss = 0
        valid_loss = 0

        model.train()
        print('############# Epoch {}: Training Start   #############'.format(epoch))
        for batch_idx, data in enumerate(training_loader):
            # print('yyy epoch', batch_idx)
            ids = data['ids'].to(device, dtype=torch.long)
            mask = data['mask'].to(device, dtype=torch.long)
            token_type_ids = data['token_type_ids'].to(device, dtype=torch.long)
            targets = data['targets'].to(device, dtype=torch.float)

            outputs = model(ids, mask, token_type_ids)

            optimizer.zero_grad()
            loss = loss_fn(outputs, targets)
            # if batch_idx%5000==0:
            #   print(f'Epoch: {epoch}, Training Loss:  {loss.item()}')

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            # print('before loss data in training', loss.item(), train_loss)
            train_loss = train_loss + ((1 / (batch_idx + 1)) * (loss.item() - train_loss))
            # print('after loss data in training', loss.item(), train_loss)

        print('############# Epoch {}: Training End     #############'.format(epoch))

        print('############# Epoch {}: Validation Start   #############'.format(epoch))
        ######################
        # validate the model #
        ######################

        model.eval()

        with torch.no_grad():
            for batch_idx, data in enumerate(validation_loader, 0):
                ids = data['ids'].to(device, dtype=torch.long)
                mask = data['mask'].to(device, dtype=torch.long)
                token_type_ids = data['token_type_ids'].to(device, dtype=torch.long)
                targets = data['targets'].to(device, dtype=torch.float)
                outputs = model(ids, mask, token_type_ids)

                loss = loss_fn(outputs, targets)
                valid_loss = valid_loss + ((1 / (batch_idx + 1)) * (loss.item() - valid_loss))
                val_targets.extend(targets.cpu().detach().numpy().tolist())
                val_outputs.extend(torch.sigmoid(outputs).cpu().detach().numpy().tolist())

            print('############# Epoch {}: Validation End     #############'.format(epoch))
            # calculate average losses
            # print('before cal avg train loss', train_loss)
            train_loss = train_loss / len(training_loader)
            valid_loss = valid_loss / len(validation_loader)
            # print training/validation statistics
            print('Epoch: {} \tAvgerage Training Loss: {:.6f} \tAverage Validation Loss: {:.6f}'.format(
                epoch,
                train_loss,
                valid_loss
            ))

            # create checkpoint variable and add important data
            checkpoint = {
                'epoch': epoch + 1,
                'valid_loss_min': valid_loss,
                'state_dict': model.state_dict(),
                'optimizer': optimizer.state_dict()
            }

            # save checkpoint
            save_ckp(checkpoint, False, checkpoint_path, best_model_path)

            ## TODO: save the model if validation loss has decreased
            if valid_loss <= valid_loss_min:
                print('Validation loss decreased ({:.6f} --> {:.6f}).  Saving model ...'.format(valid_loss_min,
                                                                                                valid_loss))
                # save checkpoint as best model
                save_ckp(checkpoint, True, checkpoint_path, best_model_path)
                valid_loss_min = valid_loss

        print('############# Epoch {}  Done   #############\n'.format(epoch))

    return model
