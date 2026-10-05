TICKER_HTML = """
<div class="tickerbar">
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
  {
    "symbols": [
      {"proName": "OANDA:XAUUSD", "title": "Gold"},
      {"proName": "OANDA:XAGUSD", "title": "Silver"},
      {"proName": "FX:EURUSD", "title": "EUR/USD"},
      {"proName": "FX:USDJPY", "title": "USD/JPY"},
      {"proName": "BITSTAMP:BTCUSD", "title": "Bitcoin"},
      {"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"}
    ],
    "showSymbolLogo": false,
    "colorTheme": "dark",
    "isTransparent": true,
    "displayMode": "compact",
    "locale": "en"
  }
  </script>
</div>
</div>
"""
