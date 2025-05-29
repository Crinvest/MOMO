import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.title("Estrategia Momentum Mensual - Top 6 con Filtro SMA9")

# Lista de tickers predeterminada
default_tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'ADBE', 'PEP', 'AVGO', 'COST', 'LLY', 'V', 'MA', 'QCOM']
tickers = st.multiselect("Selecciona los tickers para el universo de inversión:", default_tickers, default=default_tickers)

if tickers:
    with st.spinner("Descargando datos mensuales desde Yahoo Finance..."):
        data = yf.download(tickers + ['SPY', 'QQQ'], start='2010-01-01', interval='1mo')['Adj Close']
        price_df = data[tickers].dropna(how='all')
        benchmark_df = data[['SPY', 'QQQ']].dropna(how='all')

    st.subheader("Precios mensuales descargados")
    st.dataframe(price_df.tail())

    # Cálculo de Momentum y SMA
    momentum = price_df.pct_change(5)
    sma_9 = price_df.rolling(9).mean()

    latest_date = price_df.dropna(how='all').index[-1]
    five_months_ago = latest_date - pd.DateOffset(months=5)

    # Filtro de acciones: Precio > SMA(9)
    valid = price_df.loc[latest_date] > sma_9.loc[latest_date]
    momentum_latest = momentum.loc[latest_date][valid]
    top6 = momentum_latest.sort_values(ascending=False).head(6)

    st.subheader(f"Top 6 acciones seleccionadas al {latest_date.strftime('%Y-%m-%d')}")
    st.table(top6)

    # Descargar resultado
    result_df = pd.DataFrame({
        'Ticker': top6.index,
        'Momentum_5M': top6.values,
        'Precio Actual': price_df.loc[latest_date, top6.index],
        'SMA_9M': sma_9.loc[latest_date, top6.index]
    })

    csv = result_df.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar posiciones en CSV", csv, "Posiciones_Actuales.csv", "text/csv")

    # Visualización opcional
    st.line_chart(price_df[top6.index].dropna())

    # Backtest de estrategia
    st.subheader("Backtest desde 2010")
    portfolio_returns = []
    portfolio_dates = []

    for i in range(9, len(price_df)):
        date = price_df.index[i]
        valid_stocks = price_df.iloc[i] > sma_9.iloc[i]
        filtered_momentum = momentum.iloc[i][valid_stocks]
        top = filtered_momentum.sort_values(ascending=False).head(6).index
        if i + 1 < len(price_df):
            next_date = price_df.index[i + 1]
            ret = price_df.loc[next_date, top] / price_df.loc[date, top] - 1
            portfolio_returns.append(ret.mean())
            portfolio_dates.append(next_date)

    portfolio_series = pd.Series(portfolio_returns, index=portfolio_dates)
    portfolio_cum = (1 + portfolio_series).cumprod()

    # Benchmarks
    spy_series = benchmark_df['SPY'].pct_change().reindex(portfolio_cum.index).fillna(0)
    qqq_series = benchmark_df['QQQ'].pct_change().reindex(portfolio_cum.index).fillna(0)
    spy_cum = (1 + spy_series).cumprod()
    qqq_cum = (1 + qqq_series).cumprod()

    st.line_chart(pd.DataFrame({"Momentum Top 6": portfolio_cum, "SPY": spy_cum, "QQQ": qqq_cum}))

    # Métricas de desempeño
    st.subheader("Métricas de desempeño")
    def calculate_metrics(series):
        cagr = (series.iloc[-1])**(1 / (len(series)/12)) - 1
        rolling_max = series.cummax()
        drawdown = series / rolling_max - 1
        max_dd = drawdown.min()
        return cagr, max_dd

    cagr_mom, dd_mom = calculate_metrics(portfolio_cum)
    cagr_spy, dd_spy = calculate_metrics(spy_cum)
    cagr_qqq, dd_qqq = calculate_metrics(qqq_cum)

    metrics_df = pd.DataFrame({
        'CAGR': [cagr_mom, cagr_spy, cagr_qqq],
        'Max Drawdown': [dd_mom, dd_spy, dd_qqq]
    }, index=['Momentum Top 6', 'SPY', 'QQQ'])

    st.table(metrics_df.style.format({"CAGR": "{:.2%}", "Max Drawdown": "{:.2%}"}))
