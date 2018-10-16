import torch
import torch.nn as nn
import torch.nn.functional as F


class HybridModule(nn.Module):

    def __init__(self, query_max_size, core_term_size, core_term_embedding_size,
                 lstm_hidden_size=64, lstm_num_layers=2, fc_hidden_size=28, margin=0.25):
        super(HybridModule, self).__init__()
        self.core_term_size = core_term_size
        self.core_term_embedding = nn.Embedding(core_term_size, core_term_embedding_size)
        self.margin = margin
        self.rnn = nn.LSTM(
            input_size=query_max_size + core_term_embedding_size,
            hidden_size=lstm_hidden_size,
            num_layers=lstm_num_layers,
            batch_first=True,
            bidirectional=True)

        self.fc_1 = nn.Linear(lstm_hidden_size * 2, fc_hidden_size)
        self.fc_2 = nn.Linear(fc_hidden_size, 1)

    def encode(self, matrix, core_terms):
        core_term_vec = self.core_term_embedding(core_terms)
        x = torch.cat([matrix, core_term_vec], dim=2)
        batch_size, seq_len, emb_size = x.size()
        rnn_out, _ = self.rnn(x, None) # batch_sz x seq_len x hidden_sz*2
        #rnn_out = F.maxpool1d(rnn_out.transpose(1, 2), seq_len).sequeeze(2) # batch_sz x hidden_sz*2
        rnn_out = rnn_out[:, -1, :] # use the last output state, batch_sz x hidden_sz*2
        x = F.dropout(rnn_out, 0.25, self.training)
        x = F.relu(self.fc_1(x))
        output = torch.tanh(self.fc_2(x))
        return output

    def forward(self, pos_matrix, pos_core_terms, neg_matrix, neg_core_terms):
        pos_score = self.encode(pos_matrix, pos_core_terms)
        neg_score = self.encode(neg_matrix, neg_core_terms)
        loss = (self.margin-pos_score+neg_score).clamp(min=1e-6).mean()
        return loss

