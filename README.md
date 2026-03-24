# Exchange Rates Dashboard

A small Flask web app that shows:

- The latest `USD -> MXN` exchange rate
- The latest `USD -> CAD` exchange rate
- A refresh button to pull the newest rates
- Two charts that show exchange-rate history over time
- Two tables with the same historical data

The app uses [Frankfurter](https://www.frankfurter.dev/) for exchange-rate data and stores a local history in SQLite.

## Run it

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the server:

   ```bash
   flask --app app run --debug
   ```

4. Open the local URL shown by Flask in your browser.

## Tests

```bash
pytest
```
