from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error, r2_score
import math
import statistics
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import mean_squared_error
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
vader = SentimentIntensityAnalyzer()

app = Flask(__name__)

vader = SentimentIntensityAnalyzer()


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/know.html')
def know():
    return render_template('know.html')

@app.route('/results', methods=['POST'])
def results():

    def get_historical_from_csv(file_path):
        #print("hello")
        # Try reading the data from the CSV file
        df = pd.read_csv(file_path)
        #print(df)

        # Ensure that the DataFrame has the required columns
        required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        if not set(required_columns).issubset(df.columns):
            print("CSV file is missing required columns.")
            return None

        # Derive 'Adj Close' by doing a backward shift of 7 days from 'Close'
        df['Adj Close'] = df['Close'].shift(-7)

        # Drop rows where 'Adj Close' is NaN (resulting from backward shift)
        df = df.dropna(subset=['Adj Close'])

        print("Data Retrieval Successful (from CSV).")
        return df

    def ARIMA_ALGO(df):
        if 'Date' in df.columns:
            df = df.set_index('Date')
        def arima_model(train, test):
            history = [x for x in train]
            predictions = list()
            forecast_set = list()
            for t in range(len(test)):
                model = ARIMA(history, order=(6,1 ,0))
                model_fit = model.fit()
                output = model_fit.forecast()
                yhat = output[0]
                predictions.append(yhat)
                obs = test[t]
                history.append(obs)

            for t in range(7):
                model = ARIMA(history, order=(6, 1, 0))
                model_fit = model.fit()
                output = model_fit.forecast()
                yhat = output[0]
                forecast_set.append(yhat)
                history.append(output)
            return predictions, forecast_set

        Quantity_date = df[['Close']]
        Quantity_date = Quantity_date.fillna(Quantity_date.bfill())
        fig = plt.figure(figsize=(7.2,4.8),dpi=65)
        plt.plot(df.index, df['Close'])
        plt.savefig('static.png')
        plt.show(fig)
        quantity = Quantity_date.values
        size = int(len(quantity) * 0.80)
        train, test = quantity[0:size], quantity[size:len(quantity)]

        predictions, forecast_set = arima_model(train, test)

        #fig = plt.figure(figsize=(7.2,4.8),dpi=65)
        #plt.plot(test,label='Actual Price')
        #plt.plot(predictions,label='Predicted Price')
        #plt.legend(loc=4)
        #plt.savefig('static1.png')
        #plt.show()
        #plt.close(fig)
        arima_pred=round(forecast_set[0],2)
        error_arima = round(math.sqrt(mean_squared_error(test, predictions)),2)
        accuracy_arima = round((r2_score(test, predictions)*100),2)
        mean = statistics.mean(forecast_set)

        print("ARIMA Model Retrieval Successful..")
        return arima_pred, error_arima, accuracy_arima, forecast_set, mean

    def LSTM_ALGO(df):
        dataset_train = df.iloc[0:int(0.8 * len(df)), :]
        dataset_test = df.iloc[int(0.8 * len(df)):, :]
        training_set = df.iloc[:, 3:4].values  # Taking Adj Close values for all rows

        sc = MinMaxScaler(feature_range=(0, 1))
        training_set_scaled = sc.fit_transform(training_set)  # First fit to data and then transform for training data

        X_train = []
        y_train = []

        for i in range(7, len(training_set_scaled)):
            X_train.append(training_set_scaled[i - 7:i, 0])
            y_train.append(training_set_scaled[i, 0])

        X_train = np.array(X_train)
        y_train = np.array(y_train)

        X_forecast = np.array(X_train[-1, 1:])
        X_forecast = np.append(X_forecast, y_train[-1])
        X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))  # .shape 0=row,1=col
        X_forecast = np.reshape(X_forecast, (1, X_forecast.shape[0], 1))

        regressor = Sequential()

        regressor.add(LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], 1)))
        regressor.add(Dropout(0.1))

        # Add 2nd LSTM layer
        regressor.add(LSTM(units=50, return_sequences=True))
        regressor.add(Dropout(0.1))

        # Add 3rd LSTM layer
        regressor.add(LSTM(units=50, return_sequences=True))
        regressor.add(Dropout(0.1))

        # Add 4th LSTM layer
        regressor.add(LSTM(units=50))
        regressor.add(Dropout(0.1))

        # Add o/p layer
        regressor.add(Dense(units=1))

        # Compile
        regressor.compile(optimizer='adam', loss='mean_squared_error')

        # Training
        regressor.fit(X_train, y_train, epochs=10, batch_size=32)

        # For lstm, batch_size=power of 2
        # Testing
        real_stock_price = dataset_test.iloc[:, 3:4].values
        dataset_total = df.iloc[:, 3:4]
        testing_set = dataset_total[len(dataset_total) - len(dataset_test) - 7:].values
        testing_set = testing_set.reshape(-1, 1)
        testing_set = sc.transform(testing_set)

        X_test = []
        y_test = []
        for i in range(7, len(testing_set)):
            X_test.append(testing_set[i - 7:i, 0])
            y_test.append(testing_set[i, 0])

        X_test = np.array(X_test)
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
        predicted_stock_price = regressor.predict(X_test)

        predicted_stock_price = sc.inverse_transform(predicted_stock_price)
        fig = plt.figure(figsize=(7.2, 4.8), dpi=65)
        plt.plot(real_stock_price, label='Actual Price')
        plt.plot(predicted_stock_price, label='Predicted Price')

        plt.legend(loc=4)
        plt.savefig('LSTM.png')
        plt.show()

        error_lstm = round(math.sqrt(mean_squared_error(real_stock_price, predicted_stock_price)), 2)

        forecasted_stock_price = regressor.predict(X_forecast)
        forecasted_stock_price = sc.inverse_transform(forecasted_stock_price)
        lstm_pred = round(forecasted_stock_price[0, 0], 2)
        accuracy_lstm = round(r2_score(real_stock_price, predicted_stock_price) * 100, 2)

        print("LSTM Model Retrieval Successful..")
        return lstm_pred, error_lstm, accuracy_lstm

    def LIN_REG_ALGO(df):

        # Rest of the function...

        forecast_out = int(7)
        df['Close after n days'] = df['Close'].shift(-forecast_out)
        df_new = df[['Close', 'Close after n days']]

        y = np.array(df_new.iloc[:-forecast_out, -1])
        y = np.reshape(y, (-1, 1))
        X = np.array(df_new.iloc[:-forecast_out, 0:-1])

        # Unknown, X to be forecasted
        X_to_be_forecasted = np.array(df_new.iloc[-forecast_out:, 0:-1])

        # Training, testing to plot graphs, check accuracy
        X_train = X[0:int(0.8 * len(df)), :]
        X_test = X[int(0.8 * len(df)):, :]
        y_train = y[0:int(0.8 * len(df)), :]
        y_test = y[int(0.8 * len(df)):, :]

        # Feature Scaling===Normalization
        sc = StandardScaler()
        X_train = sc.fit_transform(X_train)
        X_test = sc.transform(X_test)
        X_to_be_forecasted = sc.transform(X_to_be_forecasted)

        # Training
        clf = LinearRegression(n_jobs=-1)
        clf.fit(X_train, y_train)

        # Testing
        y_test_pred = clf.predict(X_test)

        fig = plt.figure(figsize=(7.2, 4.8), dpi=65)
        plt.plot(y_test, label='Actual Price')
        plt.plot(y_test_pred, label='Predicted Price')

        plt.legend(loc=4)
        plt.savefig('LR.png')
        plt.show()

        error_lr = round(math.sqrt(mean_squared_error(y_test, y_test_pred)), 2)

        # Forecasting
        forecast_set = clf.predict(X_to_be_forecasted)
        mean = forecast_set.mean()
        lr_pred = round(forecast_set[0, 0], 2)
        accuracy_lr = round(r2_score(y_test, y_test_pred) * 100, 2)

        print("LR Model Retrieval Successful..")
        return lr_pred, error_lr, accuracy_lr

    def RF_ALGO(df):
    # Shift the data by 7 days
        forecast_out = int(7)
        df['Close after n days'] = df['Close'].shift(-forecast_out)
        df_new = df[['Close', 'Close after n days']]

    # Prepare features and target variable
        X = np.array(df_new.iloc[:-forecast_out, :-1])
        y = np.array(df_new.iloc[:-forecast_out, -1])

    # Unknown, X to be forecasted
        X_to_be_forecasted = np.array(df_new.iloc[-forecast_out:, :-1])

    # Training, testing to plot graphs, check accuracy
        X_train = X[0:int(0.8 * len(df)), :]
        X_test = X[int(0.8 * len(df)):, :]
        y_train = y[0:int(0.8 * len(df))]
        y_test = y[int(0.8 * len(df)):]

    # Hyperparameter tuning using GridSearchCV
        param_grid = {
        'n_estimators': [50, 100, 150, 200],
        'max_depth': [None, 10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
        }

        rf_model = RandomForestRegressor(random_state=42)
        grid_search = GridSearchCV(rf_model, param_grid, cv=5, scoring='r2', n_jobs=-1)
        grid_search.fit(X_train, y_train)

        best_rf_model = grid_search.best_estimator_

    # Testing
        y_test_pred = best_rf_model.predict(X_test)

    # Calculate error and accuracy
        error_rf = np.sqrt(mean_squared_error(y_test, y_test_pred))
        accuracy_rf = best_rf_model.score(X_test, y_test) * 100  # R-squared score in percentage

    # Plotting
        plt.figure(figsize=(7.2, 4.8), dpi=65)
        plt.plot(y_test, label='Actual Price')
        plt.plot(y_test_pred, label='Predicted Price')
        plt.legend(loc=4)
        plt.show()

    # Forecasting
        forecast_set = best_rf_model.predict(X_to_be_forecasted)
        mean = forecast_set.mean()

        print("Random Forest Model Retrieval Successful..")
        return forecast_set[0], error_rf, accuracy_rf

    def recommendation(pos, neg, neut, quote_data, mean):
        today_stock = quote_data.iloc[-1:]
        if today_stock.iloc[-1]['Close'] < mean:
            if neg>pos and neg>neut:
                idea="FALL"
                decision="SELL"
            else:
                idea="RISE"
                decision="BUY"
        else:
            idea= "FALL"
            decision= "SELL"

        print("Recommendation Retrieval Successful..")
        return idea, decision

    def get_financial_news(api_key, stock_symbol):
        base_url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": api_key,
            "q": f"{stock_symbol} stock news",
            "sortBy": "publishedAt",
            "pageSize": 20
        }
        news_list = []
        pos = 0
        neg = 0
        neut = 0
        global_polarity = 0.0
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            news_data = response.json()

            if news_data["status"] == "ok":
                articles = news_data["articles"]
                for article in articles:
                    title=article['title']
                    print(f"Title: {title}")
                # print(f"Source: {article['source']['name']}")
                # print(f"URL: {article['url']}")
                    news_list.append(title)
                    compound = vader.polarity_scores(title)["compound"]
                    global_polarity = global_polarity + compound
                    print(title)
                    if (compound > 0):
                        pos = pos + 1
                    elif (compound < 0):
                        neg = neg + 1
                    else:
                        neut = neut + 1
                    print("-" * 30)
            else:
                print("Error in API response")

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
        if global_polarity >= 0:
            news_pol = "OVERALL POSITIVE"
        else:
            news_pol = "OVERALL NEGATIVE"

        print("Sentiment Analysis Retrieval Successful..")
        return global_polarity, news_list, pos, neg, neut, news_pol

# Replace 'YOUR_API_KEY' with your actual News API key
    csv_file_path = '/Users/sanvisharma/Desktop/project/data/tcsn.csv'
    df = pd.read_csv(csv_file_path)
    quote_data=df.dropna()

    historical_data = get_historical_from_csv(csv_file_path)

    if historical_data is not None and not historical_data.empty:
        # Process the historical data as needed
        today_stock = historical_data.iloc[-1:]
        today_stock = today_stock.round(2)
        historical_data = historical_data.dropna()
    
    arima_pred, error_arima, accuracy_arima, forecast_set, mean = ARIMA_ALGO(historical_data)
    print(accuracy_arima)

    lstm_pred, error_lstm, accuracy_lstm = LSTM_ALGO(historical_data)
    print(accuracy_lstm)

    lr_pred, error_lr, accuracy_lr = LIN_REG_ALGO(historical_data)
    print(accuracy_lr)

    rf_pred, error_rf, accuracy_rf = RF_ALGO(historical_data)
    print(accuracy_rf)

    maximum_accuracy=max(accuracy_arima, accuracy_lstm, accuracy_rf, accuracy_lr)
    print("Max Accuracy of model is", maximum_accuracy, "%")

# Replace 'YOUR_API_KEY' with your actual News API key
    news_api_key = 'efe1f77897c44a75a2ea2dee7476648b'
    stock_symbol = 'TCS'  # Replace with the desired stock symbol

    global_polarity, news_list, pos, neg, neut, news_pol = get_financial_news(news_api_key, stock_symbol)
    print('positive= ',pos)
    print('negative= ',neg)
    print('neutral= ',neut)
    print(news_pol)

#print(mean)
    idea, decision = recommendation(pos, neg, neut, quote_data, mean)
    print(decision)

    return redirect(url_for('result_page'))

    @app.route('/')
    def index():
        return render_template('finalres.html', arima_accuracy=accuracy_arima, lstm_accuracy=accuracy_lstm,
                               lr_accuracy=accuracy_lr, rf_accuracy=accuracy_rf, max_accuracy=maximum_accuracy,
                               sentiment=news_pol, decision=decision)


    return render_template('results.html', arima_accuracy=accuracy_arima, lstm_accuracy=accuracy_lstm,
                               lr_accuracy=accuracy_lr, rf_accuracy=accuracy_rf, max_accuracy=maximum_accuracy,
                               sentiment=news_pol, decision=decision)



@app.route('/result.html', methods=['GET'])
def result_page():
    return render_template('result.html')

if __name__ == '__main__':
    app.run(debug=True)