import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import io
from datetime import datetime

def fetch_data(stock_symbol, start_date, end_date):
    data = yf.download(stock_symbol, start=start_date, end=end_date)
    return data

def calculate_ema(data, span):
    return data['Close'].ewm(span=span, adjust=False).mean()

def calculate_volatility(data, window):
    return data['Close'].rolling(window=window).std()

def calculate_bollinger_bands(data, window):
    sma = data['Close'].rolling(window=window).mean()
    rolling_std = data['Close'].rolling(window=window).std()
    data['upper_band'] = sma + (rolling_std * 2)
    data['lower_band'] = sma - (rolling_std * 2)

def calculate_atr(data, window):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=window).mean()

def plot_stock_data(data, strategy):
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot stock price
    ax.plot(data['Close'], label='Close Price', color='#0A0AFF', linewidth=2)

    if strategy == "8 and 21 EMA crossover":
        ax.plot(data['ema_8'], label='8 EMA', color='#FF9800', linewidth=2, alpha=0.8)
        ax.plot(data['ema_21'], label='21 EMA', color='#4CAF50', linewidth=2, alpha=0.8)
        ax.plot(data[data['position'] == 1].index, data['ema_8'][data['position'] == 1], '^', markersize=12, color='g', lw=0, label='Buy Signal')
        ax.plot(data[data['position'] == -1].index, data['ema_8'][data['position'] == -1], 'v', markersize=12, color='r', lw=0, label='Sell Signal')

    elif strategy == "Bollinger Bands":
        ax.plot(data['upper_band'], label='Upper Bollinger Band', color='#FF9800', linewidth=2, alpha=0.8)
        ax.plot(data['lower_band'], label='Lower Bollinger Band', color='#4CAF50', linewidth=2, alpha=0.8)
        ax.plot(data[data['buy_signal']].index, data['lower_band'][data['buy_signal']], '^', markersize=12, color='g', lw=0, label='Buy Signal')

    elif strategy == "ATR Breakouts":
        ax.plot(data['atr'], label='Average True Range', color='#FF9800', linewidth=2, alpha=0.8)
        ax.plot(data[data['buy_signal']].index, data['Close'][data['buy_signal']], '^', markersize=12, color='g', lw=0, label='Buy Signal')

    elif strategy == "Momentum Trading with Volatility":
        ax.plot(data['momentum'], label='Momentum', color='#FF9800', linewidth=2, alpha=0.8)
        ax.plot(data['volatility'], label='Volatility', color='#4CAF50', linewidth=2, alpha=0.8)
        ax.plot(data[data['buy_signal']].index, data['Close'][data['buy_signal']], '^', markersize=12, color='g', lw=0, label='Buy Signal')

    elif strategy == "Volatility Squeeze":
        ax.plot(data['squeezing'], label='Volatility Squeeze', color='#FF9800', linewidth=2, alpha=0.8)
        ax.plot(data[data['buy_signal']].index, data['Close'][data['buy_signal']], '^', markersize=12, color='g', lw=0, label='Buy Signal')

    # Add legend
    ax.legend()

    # Customize chart layout (add axis labels, title, and gridlines)
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.set_title('Stock Analysis')
    ax.grid(True)

    # Display the plot in Streamlit app
    st.pyplot(fig)

def analyze_stock(stock_symbol, start_date, end_date, strategy):
    try:
        # Fetch stock data
        data = fetch_data(stock_symbol, start_date, end_date)

        # Calculate and average volatility
        data['volatility'] = calculate_volatility(data, 21)

        if strategy == "8 and 21 EMA crossover":
            data['ema_8'] = calculate_ema(data, 8)
            data['ema_21'] = calculate_ema(data, 21)
            data['signal'] = 0
            data.iloc[8:, data.columns.get_loc('signal')] = np.where(data['ema_8'][8:] > data['ema_21'][8:], 1, 0)
            data['position'] = data['signal'].diff()

        elif strategy == "Bollinger Bands":
            calculate_bollinger_bands(data, 20)
            data['buy_signal'] = data['Close'] > data['lower_band']

        elif strategy == "ATR Breakouts":
            data['atr'] = calculate_atr(data, 14)
            data['buy_signal'] = data['Close'].diff() > data['atr']

        elif strategy == "Momentum Trading with Volatility":
            data['momentum'] = data['Close'] - data['Close'].shift(10)
            data['buy_signal'] = (data['momentum'] > 0) & (data['volatility'] > data['volatility'].mean())

        elif strategy == "Volatility Squeeze":
            calculate_bollinger_bands(data, 20)
            data['sma_20'] = data['Close'].rolling(window=20).mean()
            data['squeezing'] = (data['upper_band'] - data['lower_band']) / data['sma_20']
            data['buy_signal'] = data['squeezing'].diff() > 0

        # Plot the stock data
        plot_stock_data(data, strategy)

        # Save the plot as an Excel file
        df_plot = pd.DataFrame(data={'Date': data.index, 'Close': data['Close']})
        file_name = f"{stock_symbol}_{strategy}_plot.xlsx"

        # Create a BytesIO object to save the Excel file data in memory
        excel_file = io.BytesIO()
        with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
            df_plot.to_excel(writer, index=False, sheet_name='Sheet1')
        excel_file.seek(0)

        # Create a download button for the Excel file
        st.download_button(
            label="Download the plot data as an Excel file",
            data=excel_file,
            file_name=file_name,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        st.error(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    st.title("Stock Analysis")

    stock_symbol = st.text_input("Enter the stock symbol (e.g. AAPL): ")
    start_date = st.date_input("Enter the start date:", value=datetime.today())
    end_date = st.date_input("Enter the end date:", value=datetime.today())

    strategies = [
        "8 and 21 EMA crossover",
        "Bollinger Bands",
        "ATR Breakouts",
        "Momentum Trading with Volatility",
        "Volatility Squeeze"
    ]

    selected_strategy = st.selectbox("Select a strategy:", strategies)

    if st.button("Analyze"):
        with st.spinner("Analyzing stock data..."):
            st.write(f"Analyzing stock {stock_symbol} with {selected_strategy} strategy...")
            analyze_stock(stock_symbol, start_date, end_date, selected_strategy)
