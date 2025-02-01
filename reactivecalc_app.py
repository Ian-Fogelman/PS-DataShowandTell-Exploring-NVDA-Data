# shiny run --reload reactivecalc_app.py
from shiny import App, ui, reactive, render
import pandas as pd
import duckdb
import yfinance as yf
from functools import reduce
import operator

def get_stock_price_dataframe():
    ticker = "NVDA"
    start_date = "2000-01-01" #IPO Date.
    end_date = "2050-12-31" #Future Date :)
    df = yf.download(ticker, start=start_date, end=end_date)
    df.columns = ['_'.join(col) for col in df.columns]
    df['Date'] = df.index
    df = df.reset_index(drop=True)
    column_names = ['Date','Close','High','Low','Open','Volume']
    rename_map = {'Date': 'Date',   # Mapping of old names to new names
                  'Close_NVDA': 'Close', 
                  'High_NVDA': 'High', 
                  'Low_NVDA': 'Low',
                  'Open_NVDA': 'Open',
                  'Volume_NVDA': 'Volume'
                 }
    df_stock = df.rename(columns=rename_map)[column_names] # Rename and reorder columns
    print('{x} rows of data returned for data between dates {start_date} and {end_date}'.format(x=len(df_stock),start_date=start_date,end_date=end_date))
    return df_stock

def create_split_dataframe():
    ticker = "NVDA"
    stock_splits = yf.Ticker(ticker).splits
    df = pd.DataFrame(stock_splits)
    df['Date'] = df.index
    df = df.reset_index(drop=True)
    df['Date'] = df['Date'].apply(lambda x: x.date())
    df = df.rename(columns={'Stock Splits': 'Multiplier'})
    df = df[['Date', 'Multiplier']]
    return df

def return_stock_splits(begin_date, end_date):
    df = create_split_dataframe()
    query = f"SELECT Multiplier FROM df WHERE Date BETWEEN '{begin_date}' AND '{end_date}' ORDER BY Date ASC"
    result = duckdb.query(query).df()
    return result['Multiplier'].to_list()

def return_stock_price(df_stock, date):
    query = f"SELECT Close FROM df_stock WHERE Date = '{date}'"
    result = duckdb.query(query).df()
    if not result.empty:
        return round(result['Close'][0], 2)
    raise ValueError(f"No stock data available for date: {date}")

def calculate_shares_bought(buyamt, df_stock, begin_date):
    begin_price = return_stock_price(df_stock, begin_date)
    shares = buyamt / begin_price
    return round(shares, 2)

def calculate_cumaltive_multiplier(multipliers):
    return reduce(operator.mul, multipliers, 1)

def calculate(buyamt, begin_date, end_date, df_stock):
    init_shares = calculate_shares_bought(buyamt, df_stock, begin_date)
    init_price = return_stock_price(df_stock, begin_date)
    stock_multipliers = return_stock_splits(begin_date, end_date)
    
    final_shares = init_shares * calculate_cumaltive_multiplier(stock_multipliers)
    end_price = return_stock_price(df_stock, end_date)

    init_value = init_price * init_shares
    adjusted_share_price = end_price / int(calculate_cumaltive_multiplier(stock_multipliers))
    final_value = (adjusted_share_price * final_shares)

    print(f"\nNumber of stock splits: {len(stock_multipliers)}")
    print(stock_multipliers)
    print(f"Initial Value: ${init_value:,.2f}")
    print(f"Final Value: ${final_value:,.2f}")

    print('**' * 20)
    print('Number of stock splits during period: {}'.format(len(stock_multipliers)))
    print('Cumlative stock split multipliers: x{}'.format(int(calculate_cumaltive_multiplier(stock_multipliers))))
    print('**' * 20)
    print('Purchase Date: {}'.format(begin_date))
    print('Stock Price at Purchase: {}'.format(init_price))
    print('Initial Shares: {:,.2f}'.format(round(init_shares,0)))
    print('Initial Value: ${:,.2f}'.format(init_value))

    print('**' * 20)
    print('Sales Date: {}'.format(end_date))
    print('Stock Price at Sale: {} (Adjusted Share Price: {})'.format(end_price, str(round(adjusted_share_price,5))))
    print('Final Shares: {:,.2f}'.format(round(final_shares,0)))
    print('Final Value: ${:,.2f}'.format((final_value)))
    print('**' * 20)
    print('Total Return Over Period: {:,.0f}%'.format(( (final_value - init_value) / init_value ) * 100) )
    return final_value

# UI definition
app_ui = ui.page_fluid(
    ui.card(
        ui.row(
            ui.input_numeric("num1", "Initial Investment:", value=100),
            ui.input_date_range("daterange", "Holding Period:", start="2000-01-03"),
            ui.input_action_button("calculate", "Calculate"),
            ui.output_text("result"),
        )
    )
)

# Global stock data (loaded once)
df_stock = get_stock_price_dataframe()

# Server definition
def server(input, output, session):
    @reactive.event(input.calculate)  # Trigger recalculation when the button is clicked
    def calculate_sum():
        if input.calculate() > 0:
            try:
                buyamt = input.num1()
                begin_date = input.daterange()[0].strftime('%Y-%m-%d')
                end_date = input.daterange()[1].strftime('%Y-%m-%d')
                result = calculate(buyamt, begin_date, end_date, df_stock)
                result = f"${result:,.2f}"
                return f"\n If you bought ${buyamt} of NVDA stock on {begin_date} and sold it on {end_date} it would be worth: {result}"
            except Exception as e:
                output.result.set(f"Error: {str(e)}")

    @output
    @render.text
    def result():
        dt_str_list = [dt.strftime("%Y-%m-%d") for dt in df_stock['Date'].tolist()]
        #Date Input Validation: dates must be active market dates in order to be calculated.
        if (input.daterange()[0].strftime('%Y-%m-%d') not in dt_str_list):
            return f"⚠️ {input.daterange()[0].strftime('%Y-%m-%d')} is not allowed. Dates must be days the US Stock Exchange is Open. Please select a different date. ⚠️"

        if (input.daterange()[1].strftime('%Y-%m-%d') not in dt_str_list):
            return f"⚠️ {input.daterange()[1].strftime('%Y-%m-%d')} is not allowed. Dates must be days the US Stock Exchange is Open. Please select a different date. ⚠️"
        #Date Input Validation: dates must be active market dates in order to be calculated.
        if calculate_sum() is not None:
            buyamt = input.num1()
            begin_date = input.daterange()[0].strftime('%Y-%m-%d')
            end_date = input.daterange()[1].strftime('%m-%d-%Y')
            return f"{calculate_sum()}"
        
        else:
            return ""

app = App(app_ui, server)