#!/usr/bin/python

import dash
from dash.dependencies import Output, Input, State
import dash_core_components as dcc
import dash_html_components as html
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objs as go
import requests
import pandas as pd
import io
import json
import xlrd
import re

EXCHANGE_RATE_EXCEL_URL = 'https://www.boi.org.il/he/Markets/Documents/yazigmizt.xlsx'
EXCHANGE_RATE_SINGLE_DAY_URL = 'https://www.boi.org.il/currency.xml?'
CURRENCY_NUMS = {
    'US DOLLAR': '01',
    'ENGLISH POUND': '02',
    'JAPANESE YEN(100)': '31',
    'SWISS FRANC': '05',
    'SWEDISH KRONA': '03',
    'NORWEGIAN KRONE': '28',
    'DANISH KRONE': '12',
    'CANADIAN DOLLAR': '06',
    'AUSTRALIAN DOLLAR': '18',
    'SOUTH AFR. RAND': '17',
    'EUR': '27',
    'JORDANIAN DINAR': '69',
    'LEBANESE POUND(10)': '70',
    'EGYPTIAN POUND': '79'
}


class CsvEmptyError(Exception):
    pass


class CurrencyChoiceError(Exception):
    pass


class DateChoiceError(Exception):
    pass


now = datetime.today()
start_default = now - relativedelta(months=1)

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.H1("ILS Exchange Rates"),
        html.Img(src="/assets/stock_icon.jpg")
    ], className="banner"),

    html.Br(),

    dcc.Dropdown(
        id='viewer',
        options=[
            {'label': 'Graph View', 'value': 'Graph View'},
            {'label': 'Single Day View', 'value': 'Single Day View'}
        ],
        value='Graph View'
    ),

    html.Br(),

    html.Div([
        html.H2(children="Graph View"),
        html.Div([
            html.Button(id="load-data-button", n_clicks=0, children="load data", style={'display': 'block'}),
            html.Label(id="error-loading-message")
        ]),

        html.Div([
            html.Br(),

            html.Div([
                dcc.DatePickerRange(
                    id="date-picker-range",
                    start_date=start_default,
                    end_date=now,
                    max_date_allowed=now
                ),

                html.Br(),
                html.Br(),

                dcc.Dropdown(
                    id="currency",
                    options=[
                        {'label': 'US DOLLAR', 'value': 'US DOLLAR'},
                        {'label': 'ENGLISH POUND', 'value': 'ENGLISH POUND'},
                        {'label': 'JAPANESE YEN', 'value': 'JAPANESE YEN(100)'},
                        {'label': 'SWISS FRANC', 'value': 'SWISS FRANC'},
                        {'label': 'SWEDISH KRONA', 'value': 'SWEDISH KRONA'},
                        {'label': 'NORWEGIAN KRONE', 'value': 'NORWEGIAN KRONE'},
                        {'label': 'DANISH KRONE', 'value': 'DANISH KRONE'},
                        {'label': 'CANADIAN DOLLAR', 'value': 'CANADIAN DOLLAR'},
                        {'label': 'AUSTRALIAN DOLLAR', 'value': 'AUSTRALIAN DOLLAR'},
                        {'label': 'SOUTH AFR. RAND', 'value': 'SOUTH AFR. RAND'},
                        {'label': 'EUR', 'value': 'EUR'},
                        {'label': 'JORDANIAN DINAR', 'value': 'JORDANIAN DINAR'},
                        {'label': 'LEBANESE POUND', 'value': 'LEBANESE POUND(10)'},
                        {'label': 'EGYPTIAN POUND', 'value': 'EGYPTIAN POUND'}
                    ],
                    value='',
                    placeholder='choose a currency'
                ),

                html.Br(),
                html.Br(),

                html.Button(id="submit-button", n_clicks=0, children="submit")
            ]),
            html.Br(),
            html.Label(id='currency-choice-error'),
            html.Br(),
            html.Br(),

            html.Div(
                dcc.Graph(id="currency_rate_graph")
            )
        ], style={'display': 'none'}, id='graph-container'),

        html.Div(id='intermediate-value', style={'display': 'none'})
    ], style={'display': 'none'}, id='graph-div'),

    html.Div([
        html.H2(children="Single Day View"),

        dcc.Dropdown(
            id="single-day-currency",
            options=[
                {'label': 'US DOLLAR', 'value': 'US DOLLAR'},
                {'label': 'ENGLISH POUND', 'value': 'ENGLISH POUND'},
                {'label': 'JAPANESE YEN', 'value': 'JAPANESE YEN(100)'},
                {'label': 'SWISS FRANC', 'value': 'SWISS FRANC'},
                {'label': 'SWEDISH KRONA', 'value': 'SWEDISH KRONA'},
                {'label': 'NORWEGIAN KRONE', 'value': 'NORWEGIAN KRONE'},
                {'label': 'DANISH KRONE', 'value': 'DANISH KRONE'},
                {'label': 'CANADIAN DOLLAR', 'value': 'CANADIAN DOLLAR'},
                {'label': 'AUSTRALIAN DOLLAR', 'value': 'AUSTRALIAN DOLLAR'},
                {'label': 'SOUTH AFR. RAND', 'value': 'SOUTH AFR. RAND'},
                {'label': 'EUR', 'value': 'EUR'},
                {'label': 'JORDANIAN DINAR', 'value': 'JORDANIAN DINAR'},
                {'label': 'LEBANESE POUND', 'value': 'LEBANESE POUND(10)'},
                {'label': 'EGYPTIAN POUND', 'value': 'EGYPTIAN POUND'}
            ],
            value='',
            placeholder='choose a currency'
        ),

        html.Br(),

        dcc.DatePickerSingle(
            id='date-picker-single',
            date=now,
            max_date_allowed=now
        ),

        html.Br(),
        html.Br(),

        html.Button(id="single-day-submit-button", n_clicks=0, children="submit"),

        html.Br(),
        html.Br(),

        html.H1(id='single-day-value-display')

    ], style={'display': 'none'}, id='single-day-div')
])


@app.callback([Output(component_id="graph-div", component_property="style"),
               Output(component_id="single-day-div", component_property="style")],
              [Input(component_id="viewer", component_property="value")]
              )
def display_chosen_div(choice):
    if choice == 'Graph View':
        return {'display': 'block'}, {'display': 'none'}
    elif choice == 'Single Day View':
        return {'display': 'none'}, {'display': 'block'}


@app.callback([Output(component_id="graph-container", component_property="style"),
               Output(component_id="intermediate-value", component_property="children"),
               Output(component_id="load-data-button", component_property="style"),
               Output(component_id="error-loading-message", component_property="children")],
              [Input(component_id="load-data-button", component_property="n_clicks")]
              )
def load_data(n_clicks):
    if n_clicks:
        try:
            excel_resp = requests.get(EXCHANGE_RATE_EXCEL_URL)
            excel_resp.raise_for_status()
            with io.BytesIO(excel_resp.content) as fh:
                df = pd.io.excel.read_excel(fh)
            if df.empty:
                raise CsvEmptyError
            dataset = {'df': df.to_json(date_format='iso', orient='split')}
        except requests.exceptions.HTTPError:
            return {'display': 'none'}, [], {'display': 'block'}, "error: problem with url or file not found"
        except xlrd.XLRDError:
            return {'display': 'none'}, [], {'display': 'block'}, "error: file downloaded not csv or excel"
        except CsvEmptyError:
            return {'display': 'none'}, [], {'display': 'block'}, "error: csv or excel file empty"
        else:
            return {'display': 'block'}, json.dumps(dataset), {'display': 'none'}, ''
    else:
        return {'display': 'none'}, [], {'display': 'block'}, ''


@app.callback([Output(component_id="currency_rate_graph", component_property="figure"),
               Output(component_id="date-picker-range", component_property="min_date_allowed"),
               Output(component_id="currency-choice-error", component_property="children")],
              [Input(component_id="submit-button", component_property="n_clicks"),
               Input(component_id="intermediate-value", component_property="children")],
              [State(component_id="date-picker-range", component_property="start_date"),
               State(component_id="date-picker-range", component_property="end_date"),
               State(component_id="currency", component_property="value")]
              )
def update_fig(n_clicks, jsonified_data, start_date, end_date, currency):
    if n_clicks:
        dataset = json.loads(jsonified_data)
        df = pd.read_json(dataset['df'], orient='split')
        df_customized = df.loc[(df['DATE'] >= start_date) & (df['DATE'] <= end_date)]
        if currency not in df_customized:
            return {}, '', 'you must choose a valid currency to submit'
        else:
            data = []
            scat = go.Scatter(x=list(df_customized['DATE']),
                              y=list(df_customized[currency]),
                              name="change_rate",
                              line=dict(color="#f44242"))
            data.append(scat)

            layout = {"title": currency, "height": 500}

            figure_dat = {
                "data": data,
                "layout": layout
            }

            min_date = min(df['DATE'])

            return figure_dat, min_date, ''
    else:
        return {"data": [], "layout": {"title": currency, "height": 500}}, '', ''


@app.callback([Output(component_id="single-day-value-display", component_property="children")],
              [Input(component_id="single-day-submit-button", component_property="n_clicks")],
              [State(component_id="single-day-currency", component_property="value"),
               State(component_id="date-picker-single", component_property="date")]
              )
def display_single_day_rate(n_clicks, currency, date):

    if currency != '' and date != '' and n_clicks:
        try:
            curr_num = CURRENCY_NUMS[currency]
        except Exception:
            return ['error: the currency chosen is unavailable or not valid']
        date_stringified = stringify_date(date)
        try:
            rate = get_exchange_rate(curr_num, date_stringified)
        except DateChoiceError:
            return ['error: the date chosen is invalid']
        except CurrencyChoiceError:
            return ['error: the currency chosen is unavailable or not valid']
        except Exception:
            return ['error: an error occured trying to call the api']
        return [f'1 Shekel = {rate} {currency}(S)']

    return ['']


def stringify_date(date):
    try:
        date_converted = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f')
    except Exception:
        date_converted = datetime.strptime(date, '%Y-%m-%d')
    date_stringified = date_converted.strftime('%Y') + date_converted.strftime('%m') + date_converted.strftime('%d')
    return date_stringified


def get_exchange_rate(curr_num, stringified_date):
    url = EXCHANGE_RATE_SINGLE_DAY_URL + 'rdate=' + stringified_date + '&curr=' + curr_num
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
    else:
        if re.search('<ERROR', response.text):
            if re.search('<REQUESTED_DATE>', response.text):
                raise DateChoiceError
            else:
                raise CurrencyChoiceError
        else:
            rate = re.findall('<RATE>(.*)</RATE>', response.text)[0]
        return rate


if __name__ == '__main__':
    app.run_server(debug=True)
