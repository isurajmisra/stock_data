from __future__ import absolute_import, unicode_literals
import datetime
import json
import time
from django.core.cache import cache
import requests
from django.db.models import Q
from django.shortcuts import render, redirect
from requests.adapters import HTTPAdapter
from django.http import JsonResponse
import pandas as pd
from urllib3 import Retry
from .models import IntradayData
from datetime import timedelta
import socket
from urllib3.connection import HTTPConnection

HTTPConnection.default_socket_options = ( 
            HTTPConnection.default_socket_options + [
            (socket.SOL_SOCKET, socket.SO_SNDBUF, 1000000), #1MB in byte
            (socket.SOL_SOCKET, socket.SO_RCVBUF, 1000000)
        ])

def home(request):
    IntradayData.objects.filter(time__lte=datetime.datetime.now() - datetime.timedelta(days=1)).delete()
    print("data deleted.")
    return render(request, 'stockData.html')

def get_chart(request):
    return render(request, 'optionChart.html')

# Urls for fetching Data
url_oc      = "https://www.nseindia.com/option-chain"
url_bnf     = 'https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY'
url_nf      = 'https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY'
url_indices = "https://www.nseindia.com/api/allIndices"

# Headers Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                         'like Gecko) '
                         'Chrome/12.0.0.0 Safari/537.36',
           'accept-language': 'en;q=0.9, 'accept-encoding': 'gzip, deflate, br'}
sess = requests.Session()

def set_cookie():
    request = sess.get(url_oc, headers=headers, timeout=5)
    cookies = dict(request.cookies)
    return cookies

cookies = set_cookie()

def get_option_data(symbol):
    if symbol=="NIFTY":
        response = sess.get(url_nf, headers=headers, timeout=5, cookies=cookies)
    else:
        response = sess.get(url_bnf, headers=headers, timeout=5, cookies=cookies)
    return response
       
    
    

def api_get_data(request):

    symbol = request.GET.get('symbol') or "BANKNIFTY"
    print(symbol)
    today = datetime.date.today()
    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday' ]
    day_name = datetime.date.today().strftime("%A")
    
    try:
        ti = datetime.datetime.now().strftime("%H:%M")
        if request.META['HTTP_HOST'] != '127.0.0.1:8000':
            request.META['HTTP_HOST'] = '127.0.0.1:8000'
            ti = datetime.datetime.now() + timedelta(hours=5, minutes=30)

        today9_30am = ti.replace(hour=9, minute=15)
        today4_30am = ti.replace(hour=16, minute=30)
        
        if  ti > today9_30am and ti  < today4_30am and day_name in days_list:
            page = get_option_data(symbol)

    except Exception as e:
        print(e)
        context = {}
        # return JsonResponse(context, safe=False)
    try:
        dajs = json.loads(page.text)
        expiry_dt = dajs['records']['expiryDates'][0]

        ce_values = [data['CE'] for data in dajs['records']['data'] if "CE" in data and data['expiryDate'] == expiry_dt]

        pe_values = [data['PE'] for data in dajs['records']['data'] if "PE" in data and data['expiryDate'] == expiry_dt]

        ce_df = pd.DataFrame(ce_values, columns=['changeinOpenInterest', 'strikePrice'])
        pe_df = pd.DataFrame(pe_values, columns=['changeinOpenInterest', 'strikePrice'])


        ce_df['strikePrice'] = ce_df['strikePrice'].astype(int)
        index_quote_lastPrice = int(dajs['records']['underlyingValue'])
        ce_df_sort = ce_df.iloc[(ce_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
        pe_df_sort = pe_df.iloc[(pe_df['strikePrice'] - index_quote_lastPrice).abs().argsort()[:1]].index.tolist()
        cr1 = ce_df_sort[0] - 7
        cr2 = ce_df_sort[0] + 8
        pr1 = pe_df_sort[0] - 7
        pr2 = pe_df_sort[0] + 8
        ce_dt = ce_df[cr1:cr2]
        pe_dt = pe_df[pr1:pr2]
        if symbol == 'BANKNIFTY':
            multiplier = 25
        elif symbol == 'NIFTY':
            multiplier = 50
            
        print(f"CE Option Chain :\n {ce_dt}")
        print("-----------------------------------------------------")
        print(f"PE Option Chain :\n {pe_dt}")
        
        ce_dt['changeinOpenInterest'] = ce_dt['changeinOpenInterest'].astype(int) * multiplier
        pe_dt['changeinOpenInterest'] = pe_dt['changeinOpenInterest'].astype(int) * multiplier
        ce_dt['strikePrice'] = ce_dt['strikePrice'].astype(int)
        pe_dt['strikePrice'] = pe_dt['strikePrice'].astype(int)
        ce_changeInOpenInterest_sum = ce_dt['changeinOpenInterest'].sum()
        pe_changeInOpenInterest_sum = pe_dt['changeinOpenInterest'].sum()
        diff_changeinOpenInterest = pe_changeInOpenInterest_sum - ce_changeInOpenInterest_sum

        if diff_changeinOpenInterest > 1000000:
            call = "Buy Call Option"
        elif diff_changeinOpenInterest < -1000000:
            call = "Buy Put Option"
        else:
            call = "Neutral"

        date_time_obj = datetime.datetime.strptime(dajs['records']['timestamp'], '%d-%b-%Y %H:%M:%S')
        ce_dt['timestamp'] = date_time_obj
        pe_dt['timestamp'] = date_time_obj
        dat_time_date = date_time_obj.date()

        if today == dat_time_date:
            if IntradayData.objects.filter(Q(time=date_time_obj)|Q(call=ce_changeInOpenInterest_sum, put=pe_changeInOpenInterest_sum, diff=diff_changeinOpenInterest)).first() is None:
                intraday_data = IntradayData.objects.create(symbol=symbol, call=ce_changeInOpenInterest_sum,
                                                            put=pe_changeInOpenInterest_sum,
                                                            diff=diff_changeinOpenInterest, time=date_time_obj,
                                                            signal=call)
                intraday_data.save()
    except Exception as e:
        print(e)

    result = []
    intraday_data = IntradayData.objects.filter(symbol=symbol, time__date=today)
    for data in intraday_data:
        result.append({"symbol": data.symbol, "signal": data.signal,
               "diff": str(data.diff),
               "call": str(data.call),
               "put": str(data.put),
               "time": data.time
               })
    # context = {"symbol": symbol, "call": call,
    #            "diff_changeinOpenInterest": str(diff_changeinOpenInterest),
    #            "ce_sum": str(ce_changeInOpenInterest_sum),
    #            "pe_sum": str(pe_changeInOpenInterest_sum),
    #            "time": date_time_obj.time().strftime("%H:%M:%S"),
    #            "ce_data":ce_dt.to_html(classes='table table-striped'),
    #            "pe_data":pe_dt.to_html(classes='table table-striped')
    #            }


    return JsonResponse(result, safe=False)



def get_intraday_data(request):
    symbol = request.GET.get('symbol') or "BANKNIFTY"
    today = datetime.date.today()
    print(today)
    result = []
    intraday_data = IntradayData.objects.filter(symbol=symbol, time__date=today).order_by('-id')[:10][::-1]
    for data in intraday_data:
        result.append({'diff':data.diff,'time':data.time})

    return JsonResponse(result, safe=False)
