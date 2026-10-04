TICKER_HTML = """
<div class="tickerbar">
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
  {
    "symbols": [
      {"proName": "OANDA:XAUUSD", "title": "Gold"},
      {"proName": "TVC:DXY", "title": "USD Index"},
      {"proName": "TVC:US10Y", "title": "US 10Y"},
      {"proName": "OANDA:XAGUSD", "title": "Silver"},
      {"proName": "TVC:USOIL", "title": "Oil"},
      {"proName": "FX:EURUSD", "title": "EUR/USD"}
    ],
    "showSymbolLogo": true,
    "colorTheme": "dark",
    "isTransparent": true,
    "displayMode": "adaptive",
    "locale": "en"
  }
  </script>
</div>
</div>
"""

CALENDAR_HTML = """
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
  {
    "colorTheme": "dark",
    "isTransparent": true,
    "width": "100%",
    "height": "650",
    "locale": "en",
    "importanceFilter": "0,1",
    "countryFilter": "us,eu,gb,jp,cn"
  }
  </script>
</div>
"""
