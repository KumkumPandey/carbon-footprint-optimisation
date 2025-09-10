import torch
import torch.nn as nn
import numpy as np
from flask import Flask, request, jsonify, render_template
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib

# 1. Dummy Time-Series Data
data = {
    'time': pd.to_datetime(pd.date_range(start='2025-01-01', periods=100, freq='h')),
    'traffic_level': np.random.randint(1, 4, 100),
    'weather_condition': np.random.randint(1, 4, 100)
}
df = pd.DataFrame(data).set_index('time')

# 2. Preprocess Data
scaler_traffic = MinMaxScaler()
scaler_weather = MinMaxScaler()
df['traffic_scaled'] = scaler_traffic.fit_transform(df[['traffic_level']])
df['weather_scaled'] = scaler_weather.fit_transform(df[['weather_condition']])

# 3. Create Sequences for LSTM
def create_sequences(input_data, sequence_length):
    sequences = []
    for i in range(len(input_data) - sequence_length):
        seq = input_data[i:i + sequence_length]
        label = input_data[i + sequence_length]
        sequences.append((seq, label))
    return sequences

sequence_length = 12
traffic_sequences = create_sequences(df['traffic_scaled'].values, sequence_length)
weather_sequences = create_sequences(df['weather_scaled'].values, sequence_length)

# 4. Define LSTM Model
class LSTMForecaster(nn.Module):
    def __init__(self, input_size=1, hidden_layer_size=50, output_size=1):
        super().__init__()
        self.hidden_layer_size = hidden_layer_size
        self.lstm = nn.LSTM(input_size, hidden_layer_size)
        self.linear = nn.Linear(hidden_layer_size, output_size)
        self.hidden_cell = (torch.zeros(1,1,self.hidden_layer_size),
                            torch.zeros(1,1,self.hidden_layer_size))

    def forward(self, input_seq):
        lstm_out, self.hidden_cell = self.lstm(input_seq.view(len(input_seq), 1, -1), self.hidden_cell)
        predictions = self.linear(lstm_out.view(len(input_seq), -1))
        return predictions[-1]

# 5. Train the models
def train_model(sequences):
    model = LSTMForecaster()
    loss_function = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    epochs = 50
    for i in range(epochs):
        for seq, labels in sequences:
            optimizer.zero_grad()
            model.hidden_cell = (torch.zeros(1, 1, model.hidden_layer_size),
                                 torch.zeros(1, 1, model.hidden_layer_size))
            y_pred = model(torch.Tensor(seq).view(-1, 1))
            single_loss = loss_function(y_pred, torch.Tensor([labels]))
            single_loss.backward()
            optimizer.step()
    return model

traffic_model = train_model(traffic_sequences)
weather_model = train_model(weather_sequences)

# 6. Save the models and scalers
torch.save(traffic_model.state_dict(), 'traffic_lstm.pth')
torch.save(weather_model.state_dict(), 'weather_lstm.pth')
joblib.dump(scaler_traffic, 'scaler_traffic.pkl')
joblib.dump(scaler_weather, 'scaler_weather.pkl')
print("PyTorch models and scalers saved successfully!")