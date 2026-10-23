"""Long one call, financed premium, short-delta hedge. No actual option quotes."""
import math,random
from pricing import greeks

def path(seed,regime='diffusion',steps=63):
    if regime not in ['diffusion','jump']:raise ValueError('regime')
    rng=random.Random(seed);s=100.;out=[s]
    for i in range(steps):
        sigma=.25 if regime=='diffusion' else (.15 if i<steps//2 else .35)
        jump=rng.gauss(-.04,.08) if regime=='jump' and rng.random()<.025 else 0
        s*=math.exp((.02-.5*sigma*sigma)/252+sigma/math.sqrt(252)*rng.gauss(0,1)+jump);out.append(s)
    return out

def hedge(prices,policy='daily',band=.05,fee_bps=5.,vol=.25,rate=.02,dt=1/252):
    if policy not in ['none','daily','band'] or len(prices)<2 or any(not math.isfinite(p) or p<=0 for p in prices) or fee_bps<0 or band<0 or dt<=0:raise ValueError('invalid hedge input')
    steps=len(prices)-1;k=prices[0];initial=greeks(prices[0],k,steps*dt,rate,vol)
    units=0. if policy=='none' else -initial['delta'];fees=abs(units)*prices[0]*fee_bps/1e4
    cash=-initial['price']-units*prices[0]-fees;turnover=abs(units)*prices[0];cost=fees;rows=[];financing=0.;stock_pnl=0.
    rows.append(dict(step=0,spot=prices[0],option=initial['price'],delta=initial['delta'],units=units,cash=cash,equity=-fees,fee=fees,interest=0.,stock_pnl=0.,option_change=0.,delta_component=0.,gamma_component=0.,theta_component=0.,approximation_residual=0.))
    previous=initial
    for i,s in enumerate(prices[1:],1):
        interest=cash*math.expm1(rate*dt);cash+=interest;financing+=interest
        ds=s-prices[i-1];pnl=units*ds;stock_pnl+=pnl
        g=greeks(s,k,(steps-i)*dt,rate,vol);dv=g['price']-previous['price']
        dc=previous['delta']*ds;gc=.5*previous['gamma']*ds*ds;tc=previous['theta']*dt
        target=0. if i==steps or policy=='none' else -g['delta']
        change=target-units if i==steps or policy=='daily' or (policy=='band' and abs(target-units)>=band) else 0.
        fee=abs(change)*s*fee_bps/1e4;cash-=change*s+fee;units+=change;cost+=fee;turnover+=abs(change)*s
        equity=g['price']+units*s+cash
        rows.append(dict(step=i,spot=s,option=g['price'],delta=g['delta'],units=units,cash=cash,equity=equity,fee=fee,interest=interest,stock_pnl=pnl,option_change=dv,delta_component=dc,gamma_component=gc,theta_component=tc,approximation_residual=dv-dc-gc-tc))
        previous=g
    terminal=rows[-1]['equity'];bridge=rows[-1]['option']-initial['price']+stock_pnl+financing-cost
    if abs(terminal-bridge)>1e-8:raise ArithmeticError('self-financing bridge failed')
    return dict(terminal_pnl=terminal,fees=cost,turnover=turnover,bridge_residual=terminal-bridge,ledger=rows)

