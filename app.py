from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/favorites_status', methods=['POST'])
def favorites_status():
    data = request.json
    tickers = data.get('tickers', [])
    result = {}
    for t in tickers:
        try:
            df = yf.Ticker(t).history(period="1mo")
            result[t] = not df.empty 
        except:
            result[t] = False
    return jsonify(result)

@app.route('/api/<path:ticker>')
def get_data(ticker):
    try:
        ticker_obj = yf.Ticker(ticker) 
        df = ticker_obj.history(period="1y") 
        
        if df.empty:
            return jsonify({'error': '데이터를 가져오지 못했습니다. 티커를 확인해주세요.'})
        
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        df = df.dropna()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        signal = "관망 (Hold)"
        emphasis = ""
        
        if prev['MA20'] <= prev['MA60'] and latest['MA20'] > latest['MA60']:
            signal = "🔴 단기 매수 (Golden Cross)"
        elif prev['MA20'] >= prev['MA60'] and latest['MA20'] < latest['MA60']:
            signal = "🔵 단기 매도 (Death Cross)"
        elif latest['MA20'] > latest['MA60']:
            signal = "상승 추세 유지 중"
        else:
            signal = "하락 추세 유지 중"
            
        if prev['Close'] <= prev['MA120'] and latest['Close'] > latest['MA120']:
            emphasis = "🚀 강력돌파!"
            
        df_chart = df.tail(100).copy()
        buy_signals, sell_signals, breakout_signals, has_signal = [], [], [], []
        
        for i in range(len(df_chart)):
            if i == 0:
                buy_signals.append(None); sell_signals.append(None); breakout_signals.append(None); has_signal.append(False)
                continue
                
            p = df_chart.iloc[i-1]
            c = df_chart.iloc[i]
            
            is_buy = p['MA20'] <= p['MA60'] and c['MA20'] > c['MA60']
            is_sell = p['MA20'] >= p['MA60'] and c['MA20'] < c['MA60']
            is_breakout = p['Close'] <= p['MA120'] and c['Close'] > p['MA120'] 
            
            # JSON 직렬화 에러를 막기 위해 float과 bool로 형변환
            buy_signals.append(float(c['MA20']) if is_buy else None)
            sell_signals.append(float(c['MA20']) if is_sell else None)
            breakout_signals.append(float(c['Close']) if is_breakout else None)
            has_signal.append(bool(is_buy or is_sell or is_breakout))

        data = {
            'dates': df_chart.index.strftime('%Y-%m-%d').tolist(),
            'close': df_chart['Close'].tolist(),
            'ma20': df_chart['MA20'].tolist(),
            'ma60': df_chart['MA60'].tolist(),
            'ma120': df_chart['MA120'].tolist(),
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'breakout_signals': breakout_signals,
            'has_signal': has_signal,
            'signal': signal,
            'emphasis': emphasis
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5001)