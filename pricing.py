"""European Black-Scholes analytics. Vega/rho per unit change; theta per year."""
import math
N=lambda x: .5*(1+math.erf(x/math.sqrt(2)))
n=lambda x: math.exp(-x*x/2)/math.sqrt(2*math.pi)
def greeks(s,k,t,r,vol,kind='call'):
    if kind not in ('call','put') or not all(math.isfinite(x) for x in [s,k,t,r,vol]) or min(s,k,vol)<=0 or t<0:raise ValueError('invalid option parameters')
    sign=1 if kind=='call' else -1
    if t==0:
        delta=sign*(1 if sign*(s-k)>0 else .5 if s==k else 0)
        return dict(price=max(sign*(s-k),0),delta=delta,gamma=0.,vega=0.,theta=0.,rho=0.)
    d1=(math.log(s/k)+(r+.5*vol*vol)*t)/(vol*math.sqrt(t));d2=d1-vol*math.sqrt(t);disc=math.exp(-r*t)
    return dict(price=sign*(s*N(sign*d1)-k*disc*N(sign*d2)),delta=sign*N(sign*d1),gamma=n(d1)/(s*vol*math.sqrt(t)),vega=s*n(d1)*math.sqrt(t),theta=-s*n(d1)*vol/(2*math.sqrt(t))-sign*r*k*disc*N(sign*d2),rho=sign*k*t*disc*N(sign*d2))

def implied_vol(price,s,k,t,r,kind='call'):
    if not math.isfinite(price) or t<=0:raise ValueError('invalid IV input')
    lo,hi=1e-5,5.
    if not greeks(s,k,t,r,lo,kind)['price']<price<greeks(s,k,t,r,hi,kind)['price']:raise ValueError('price outside finite volatility bracket')
    for _ in range(90):
        mid=(lo+hi)/2
        if greeks(s,k,t,r,mid,kind)['price']<price:lo=mid
        else:hi=mid
    return (lo+hi)/2

