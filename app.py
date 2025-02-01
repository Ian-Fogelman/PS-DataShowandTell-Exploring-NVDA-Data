#shiny run --reload app.py
from shiny import App, render, ui
import pandas as pd
import shiny
import yfinance as yf
import finnhub
from datetime import datetime, timedelta
import shinyswatch
import matplotlib.pyplot as plt

API_KEY = "XXXXXXXX"  # TODO: Replace with your Finnhub API key https://finnhub.io/register
finnhub_client = finnhub.Client(api_key=API_KEY)

def get_current_date_last_seven():
    current_date = datetime.now()
    date_7_days_ago = current_date - timedelta(days=7)
    cd = current_date.strftime('%Y-%m-%d')
    lsd = date_7_days_ago.strftime('%Y-%m-%d')
    print("Current date:", cd)
    print("Date 7 days ago:", lsd)
    return (cd,lsd)

def ts_to_date_str(timestamp):
    dt_object = datetime.fromtimestamp(timestamp)
    formatted_date = dt_object.strftime('%m-%d-%Y')
    return str(formatted_date)

def get_news():
    symbol = 'NVDA'
    d = get_current_date_last_seven()
    begin = d[1]
    end = d[0]
    news = finnhub_client.company_news(symbol, _from=begin, to=end)
    print('Number of news stories returned: ' + str(len(news)))
    return news

news = get_news() #Retreive News with Finnhub API, news comes in as a list of dictionaries, i.e: [{},{}].

app_ui = ui.page_fluid(
    ui.row(
        ui.h1("Data Show and Tell: Exploring NVIDIA Finance Data with Python Shiny", style="text-align: center; margin-top: 20px;")
    ),
    ui.row(
        ui.h3("NVDA Data Historical Prices", style="text-align: center; margin-top: 20px;"),
        ui.card(ui.output_data_frame("my_table"),ui.download_button("download", "Download CSV"), height="400px"),
        ui.h3("NVDA Stock Close Prices Over Time", style="text-align: center; margin-top: 20px;"),
        ui.output_plot("my_plot"),
        ui.h3("NVDA Data Historical Stock Splits", style="text-align: center; margin-top: 20px;", class_="col-md-12"),
        ui.card(ui.output_data_frame("stock_splits")),
    ),
    ui.div(
        ui.tags.style("""
            .center-text {
                text-align: center;
            }
        """),
        ui.h3("NVDA News Feed (Last 7 days)"),
        ui.div(
            # Scrollable container
            ui.div(
                # Dynamically generated cards
                *[
                    ui.div(
                        ui.card(
                            ui.card_header(card["headline"]),
                            ui.card_body('Date: ' + ts_to_date_str(card["datetime"])),
                            ui.card_body('Source: ' + card["source"]),
                            ui.tags.a("Read More", href=card["url"], target='_blank'),
                            class_="col-md-12"  
                        ),
                        class_="card-container",
                    )
                    for card in news  # For each dict in the `news` list, a card will be produced.
                ],
                class_="scrollable-container",
            ),
            class_="outer-container",
        ),
        class_="center-text"
    ),
    ui.tags.style(
            """
            .outer-container {
                max-height: 400px;
                width: 100%;
                overflow: hidden;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .scrollable-container {
                max-height: 400px;
                width: 100%;
                overflow-y: auto;
                display: grid;
                grid-template-columns: repeat(3, 1fr); /* 3 cards per row */
                gap: 16px;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 16px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                background-color: #fff;
            }
            .card-container {
                width:100%;
            }
            """
        ),

        # OPTIONAL - Change Theme with shinyswatch# For more details see: https://bootswatch.com/
        # Uncomment any "theme=shinyswatch.theme" line to see the theme applied to the application.
        #theme=shinyswatch.theme.lux,
        theme=shinyswatch.theme.darkly,
        #theme=shinyswatch.theme.cerulean,
        #theme=shinyswatch.theme.cyborg,
        #theme=shinyswatch.theme.lumen,
        #theme=shinyswatch.theme.cosmo,
        #theme=shinyswatch.theme.flatly,
        #theme=shinyswatch.theme.journal,
        #theme=shinyswatch.theme.litera,
        #theme=shinyswatch.theme.materia,
        #theme=shinyswatch.theme.minty,
        #theme=shinyswatch.theme.morph,
        # OPTIONAL - Change Theme with shinyswatch#
)

def get_dataframe():
    ticker = "NVDA"
    start_date = "2000-01-01" #IPO Date.
    end_date = "2050-12-31" #Future Date :)
    df = yf.download(ticker, start=start_date, end=end_date)
    df.columns = ['_'.join(col) for col in df.columns]
    df['Date'] = df.index
    df = df.reset_index(drop=True)
    column_names = ['Date','Close','High','Low','Open','Volume']
    rename_map = {'Date': 'Date', # Map old column names to new names
                  'Close_NVDA': 'Close', 
                  'High_NVDA': 'High', 
                  'Low_NVDA': 'Low',
                  'Open_NVDA': 'Open',
                  'Volume_NVDA': 'Volume'
                 }  
    df = df.rename(columns=rename_map)[column_names] # Rename and reorder columns
    columns_to_round = {"Close": 3, "High": 3, 'Low': 3, 'Open':3}
    df = df.round(columns_to_round)
    df['Volume'] = df['Volume'].apply(lambda x: f"{x:,}")
    df = df.sort_values(by='Date', ascending=False)
    df['Date'] = df['Date'].dt.date
    print('{x} rows of data returned for data between dates {start_date} and {end_date}'.format(x=len(df),start_date=start_date,end_date=end_date))
    return df

df = get_dataframe()

def server(input, output, session):
    @output
    @render.data_frame
    def my_table():
        return df

    @output
    @render.data_frame
    def stock_splits():
        ticker = "NVDA"
        stock_splits = yf.Ticker(ticker).splits
        df = pd.DataFrame(stock_splits)
        df['Date'] = df.index
        df = df.reset_index(drop=True)
        df['Date'] = df['Date'].apply(lambda x: x.date())
        df = df.rename(columns={'Stock Splits': 'Multiplier'})
        df = df[['Date', 'Multiplier']]
        return df

    @session.download(filename="NVDA_Stock_Data.csv")
    def download():
        yield df.to_csv()
    
    @shiny.render.plot
    def my_plot():
        # Create a Matplotlib figure and axes
        fig, ax = plt.subplots()
        # Plot the data
        ax.plot(df['Date'], df['Close'], label="Close Price", color="blue", linewidth=2)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Close Price (USD)", fontsize=12)
        ax.grid(True, linestyle="--", alpha=0.7)
        ax.legend(loc="upper left")
        fig.tight_layout()
        return fig

app = shiny.App(app_ui, server)