import datetime
import json
import sqlite3

import requests
from django.shortcuts import render

# Create your views here.
from nsetools import Nse
import pandas as pd

from stock_data.settings import DATABASES


def get_stock_data(request):
    nse = Nse()
    if request.method == "POST":
        symbol = request.POST.get('symbol', 'BANKNIFTY')

        try:
            i = True
            j = 1
            while(i):
                page = get_option_data(symbol)
                if page.status_code == 200:
                    i = False
                else:

                    i = True
                    print(f"Trying to connect - {j}")
                    j += 1
            dajs = json.loads(page.text)

        except Exception as e:
            print(e)
            return render(request, 'stockData.html')

        expiry_dt = dajs['records']['expiryDates'][0]

        ce_values = [data['CE'] for data in dajs['records']['data'] if "CE" in data and data['expiryDate'] == expiry_dt]

        pe_values = [data['PE'] for data in dajs['records']['data'] if "PE" in data and data['expiryDate'] == expiry_dt]


        ce_df = pd.DataFrame(ce_values, columns=['changeinOpenInterest', 'strikePrice'])
        pe_df = pd.DataFrame(pe_values, columns=['changeinOpenInterest', 'strikePrice'])
        engine = sqlite3.connect(DATABASES['default']['NAME'])





        if symbol == "BANKNIFTY":
            nse_symbol = "nifty bank"
        elif symbol == "NIFTY":
            nse_symbol = "nifty 50"
        index_quote =  nse.get_index_quote(nse_symbol)
        ce_df['strikePrice'] = ce_df['strikePrice'].astype(int)
        index_quote_lastPrice = int(index_quote['lastPrice'])
        ce_df_sort = ce_df.iloc[(ce_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
        pe_df_sort = pe_df.iloc[(pe_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
        cr1 = ce_df_sort[0]-7
        cr2 = ce_df_sort[0]+8
        pr1 = pe_df_sort[0] - 7
        pr2 = pe_df_sort[0] + 8
        ce_dt = ce_df[cr1:cr2]
        pe_dt = pe_df[pr1:pr2]
        print(cr1,cr2,pr1,pr2)
        print(ce_values)
        print(pe_values)
        # ce_dt['openInterest'] = ce_dt['openInterest'].astype(int)
        # pe_dt['openInterest'] = pe_dt['openInterest'].astype(int)
        ce_dt['changeinOpenInterest'] = ce_dt['changeinOpenInterest'].astype(int) * 25
        pe_dt['changeinOpenInterest'] = pe_dt['changeinOpenInterest'].astype(int) * 25
        ce_dt['strikePrice'] = ce_dt['strikePrice'].astype(int)
        pe_dt['strikePrice'] = pe_dt['strikePrice'].astype(int)
        ce_changeInOpenInterest_sum = ce_dt['changeinOpenInterest'].sum()
        pe_changeInOpenInterest_sum = pe_dt['changeinOpenInterest'].sum()
        diff_changeinOpenInterest = pe_changeInOpenInterest_sum - ce_changeInOpenInterest_sum
        # ce_dt['totalTradedVolume'] = ce_dt['totalTradedVolume'].astype(int)
        # pe_dt['totalTradedVolume'] = pe_dt['totalTradedVolume'].astype(int)
        # ce_totalTradedVolume_sum = ce_dt['totalTradedVolume'].sum()
        # pe_totalTradedVolume_sum = pe_dt['totalTradedVolume'].sum()
        # diff_totalTradedVolume = pe_totalTradedVolume_sum - ce_totalTradedVolume_sum
        if diff_changeinOpenInterest > 1000000:
            call = "Buy Call Option"
        elif diff_changeinOpenInterest < -1000000:
            call = "Buy Put Option"
        else:
            call = "Neutral"

        print(dajs['records']['timestamp'])
        date_time_obj = datetime.datetime.strptime(dajs['records']['timestamp'], '%d-%b-%Y %H:%M:%S')
        ce_dt['timestamp'] = date_time_obj
        pe_dt['timestamp'] = date_time_obj

        # ce_dt.to_sql(name='ce_stock_data', con=engine, index=False, if_exists='append')
        # pe_dt.to_sql(name='pe_stock_data', con=engine, index=False, if_exists='append' )
        context = {"symbol":symbol,"call":call, "ce_data":ce_dt.to_html(classes='table table-striped'), "pe_data":pe_dt.to_html(classes='table table-striped'), "diff_changeinOpenInterest":diff_changeinOpenInterest, "ce_sum":ce_changeInOpenInterest_sum, "pe_sum":pe_changeInOpenInterest_sum}
        return render(request, 'stockData.html', context=context)
    else:
        return render(request, 'stockData.html')

def get_option_data(symbol):
    new_url = f'https://www.nseindia.com/api/option-chain-indices?symbol={symbol}'
    referer = f"https://www.nseindia.com/get-quotes/derivatives?symbol={symbol}"
    cookie_dict = {
        "bm_sv": "F140DF14529DCBD46F41C0CA2BF24EE7~kbGVwkURJC0sZAK/dfkMMNdp+I5+fHncaM2faFXjIOis8SUGWPA/GL7or2MbB6YbioUNsFqm3nrGbRNslXEU7WSilb4gIqms3So5NhURNXUP9myu2XvCRZ3tTZ+zWzH5ID/z7AVtakwD4BwJlLTxGmikyK3IYlREFTfHDs+N42c="}
    headers = {"Referer": referer,
               'User-Agent': "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0",
               "Accept - Language": "en - US, en;q = 0.9", "Accept-Encoding": "gzip, deflate, br"
               }
    s = requests.session()
    for cookie in cookie_dict:
        s.cookies.set(cookie, cookie_dict[cookie])

    page = s.get(new_url, headers=headers)

    return page