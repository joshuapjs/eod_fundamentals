import os
import requests
import pandas as pd
from eod import EodHistoricalData

# Ticker symbols of companies in the US need to be followed by .US : "AAPL" -> "AAPL.US"

key = os.environ["API_EOD"]  # gathering the API-Key for EODhistoricaldata, stored in an environment variable
client = EodHistoricalData(key)  # setting up the client for downloading the fundamental data


def get_group(symbol, name=None):
    """
    Access all relevant stocks within a certain industry, determined by the symbol given
    :param symbol: requires one single ticker symbol as a string
    :type symbol: str
    :param name: filter the competitors list by the company's name to avoid redundancies  in case of multiple listing
    :type name: str, optional
    :return: list of all stock symbols within the same industry of the most relevant exchanges
    """
    group_symbols = []
    tickers = []
    relevant_exchanges = ['Xetra', 'US', 'LSE', 'HK', 'SHG']  # List of what I found to be the most relevant exchanges

    if ".US" in symbol:
        symbol = symbol.replace(".US", "")

    # Searching the stock symbol on the most relevant exchanges
    for exchange in relevant_exchanges:

        initial_resp = requests.get(f'https://eodhistoricaldata.com/api/screener?api_token={key}&filters=['
                                    f'["code","=","{symbol}"],'
                                    f'["exchange","=","{exchange}"]'
                                    f']&limit=500&offset=0')

        if len(initial_resp.json()["data"]) > 0:
            tickers.append(initial_resp.json()["data"][0])

    # Check if the stock is listed on several Exchanges with the same symbol
    if len(tickers) > 1:
        print("DANGER: Stock is listed on different exchanges... ")
    stock_industry = tickers[0]["industry"]
    tickers.clear()

    # Searching for all the stocks within the same industry on all different exchanges
    for exchange in relevant_exchanges:

        market_resp = requests.get(f'https://eodhistoricaldata.com/api/screener?api_token={key}&filters=['
                                   f'["industry","=","{stock_industry}"],'
                                   f'["exchange","=","{exchange}"]'
                                   f']&limit=500&offset=0')

        if len(market_resp.json()["data"]) > 0:
            if len(market_resp.json()["data"]) > 1:
                for element in market_resp.json()["data"]:
                    tickers.append((element["code"], element["name"]))
                tickers.append((market_resp.json()["data"][0]["code"], market_resp.json()["data"][0]["name"]))

    # Check to avoid redundancy of the competitors
    for i in tickers:
        if i[0] in group_symbols:
            pass
        elif name is not None and name in i[1]:
            pass
        else:
            group_symbols.append(i[0])

    return group_symbols


def get_statement(element, statement_type="Balance_Sheet"):
    """
    :param element: ticker symbol or multiple symbol of the company
    :type element: str or list
    :param statement_type: "Balance_Sheet" or "Income_Statement" or "Cash_Flow"
    :type statement_type: str, optional
    :return: DataFrame of all recorded historical statements depending on the statement type and the ticker symbol
    """
    resp = []

    # downloading multiple datasets if a list of symbols is given or one dataset if only one symbol is given
    if isinstance(element, list):
        for i in element:
            series = client.get_fundamental_equity(i)
            resp.append(series)
    else:
        series = client.get_fundamental_equity(element)
        resp.append(series)

    # filtering the dataset
    data = pd.DataFrame(
        pd.DataFrame(resp)["Financials"]
        .iloc[0][statement_type]["quarterly"]
    )

    return data


def get_highlights(element):
    """
    Access to the highlights predefined and given by EODhistoricaldata

    :param element: ticker symbol or multiple symbol of the company
    :type element: str or list
    :return: DataFrame of the fundamental "Highlights" via EODhistoricaldata as a DataFrame for every stock given
    """
    resp = []

    if isinstance(element, list):
        for i in element:
            series = client.get_fundamental_equity(i)
            resp.append(series)
    else:
        series = client.get_fundamental_equity(element)
        resp.append(series)

    data = pd.DataFrame(
        pd.DataFrame(resp)["Highlights"].iloc[0],
        index=[0]
    ).transpose()

    return data


def group_overview(elements):
    """
    The highlights can be adjusted for a list of the highlights visit:
    https://eodhistoricaldata.com/financial-apis/stock-etfs-fundamental-data-feeds/#Equities_Fundamentals_Data_API

    :param elements: ticker symbol or multiple symbol of the company
    :type elements: str, list
    :return: DataFrame providing an overview about different KPIs for all stock tickers given as "elements"
    """
    kpis = {}

    if isinstance(elements, list):
        formatted_elements = elements
        pass
    else:
        formatted_elements = list(elements)

    for element in formatted_elements:
        highlights = get_highlights(element)
        kpis[str(element)] = [
            highlights["EarningsShare"].iloc[0],
            highlights["EPSEstimateCurrentYear"].iloc[0],
            highlights["ProfitMargin"].iloc[0],
            highlights["OperatingMarginTTM"].iloc[0],
            highlights["ReturnOnAssetsTTM"].iloc[0],
            highlights["QuarterlyRevenueGrowthYOY"].iloc[0],
            highlights["QuarterlyEarningsGrowthYOY"].iloc[0]]
    df = pd.DataFrame(kpis, index=["EPS",
                                   "EPS (current year)",
                                   "Profit margin",
                                   "Operating margin (trailing 12-month)",
                                   "ROA (trailing 12-month)",
                                   "Quarterly revenue growth (YoY)",
                                   "Quarterly earnings growth (YoY)"])

    return df


def compare(equity, group):  # Builds on the group_overview function
    """
    Example::

        df = group_overview(["BCOR.US", "BSIG.US", "RILY.US", "VRTS.US", "WETF.US"])  # DataFrame of a group
        df1 = compare("BCOR.US",df)  # Comparing KPIs of the stock with the averages of its group

    :param equity: Ticker symbol of the stock that ought to be compared
    :type equity: str
    :param group: DataFrame created by the
    group_overview function with symbols of the competitors you want to derive an avarage of - Including the symbol
    of the stock you want to compare to its market
    :type group: pd.DataFrame

    :return: DataFrame containing different KPIs of one stock and the average of its group given as a separate list
    """
    index = group.index
    data = {}
    averages = []
    for row in index:
        average = group.loc[row].mean()
        averages.append(average)
    data[str(equity)] = group[equity]
    data["Market"] = averages
    df = pd.DataFrame(data, index=["EPS",
                                   "EPS (current year)",
                                   "Profit margin",
                                   "Operating margin (Trailing 12-month)",
                                   "ROA (Trailing 12-month)",
                                   "Quarterly revenue growth (YoY)",
                                   "Quarterly earnings growth (YoY)"])

    return df
