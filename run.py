from pathlib import Path
import argparse,csv,hashlib,json,math,statistics,random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pricing import greeks
from hedging import hedge,path
ROOT=Path(__file__).parent;OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
def stats(xs):
    n=len(xs);tail=sorted(xs)[:max(1,math.ceil(n*.05))]
    return dict(n=n,mean=statistics.mean(xs),rmse=math.sqrt(statistics.mean(x*x for x in xs)),worst_5pct_mean=statistics.mean(tail))
def writecsv(name,rows):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def run():
    ap=argparse.ArgumentParser();ap.add_argument('--historical-csv');ap.add_argument('--column',default='DLF.NS');args=ap.parse_args()
    train={str(b):stats([hedge(path(i),'band',band=b)['terminal_pnl'] for i in range(50)]) for b in [.02,.05,.1]}
    band=float(min(train,key=lambda b:train[b]['rmse']));rows=[];summary={}
    for regime in ['diffusion','jump']:
        for policy in ['none','daily','band']:
            for seed in range(1000,1150):
                result=hedge(path(seed,regime),policy,band=band)
                rows.append(dict(regime=regime,policy=policy,seed=seed,**{k:v for k,v in result.items() if k!='ledger'}))
            summary[regime+'_'+policy]=stats([x['terminal_pnl'] for x in rows if x['regime']==regime and x['policy']==policy])
    writecsv('heldout_trials.csv',rows)
    costs=[]
    for fee in [0,2,5,10,25]:
        for policy in ['daily','band']:
            xs=[hedge(path(i),policy,band=band,fee_bps=fee)['terminal_pnl'] for i in range(1000,1150)]
            costs.append({'fee_bps':fee,'policy':policy,**stats(xs)})
    writecsv('cost_sensitivity.csv',costs)
    example=hedge(path(1000,'jump'),'band',band=band)['ledger'];writecsv('example_ledger.csv',example)
    report={'dataset':'Synthetic diffusion and jump/regime scenarios; model-priced European calls','source_url':'https://github.com/Anjaney336/options-greeks-hedging-lab/blob/main/hedging.py','access_date':'2026-10-24','train_seeds':[0,49],'heldout_seeds':[1000,1149],'selected_band':band,'training_scores':train,'heldout_summary':summary,'trial_count':len(rows),'units':'currency per one option on normalized spot 100, not account return','assumptions':{'steps':63,'dt':1/252,'pricing_vol':.25,'financing_rate':.02,'hedge_fee_bps':5,'initial_ATM':True,'option_multiplier':1,'dividends':0},'limits':'Idealized same-close analytic hedging; no option bid/ask, premium transaction fee, margin, tax, stock borrow fee or actual option quotes. Short stock is assumed available. Constant pricing IV under stochastic realized volatility is a stress assumption.'}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(11,4.5))
    for ax,reg in zip(axs,['diffusion','jump']):
        ax.boxplot([[x['terminal_pnl'] for x in rows if x['regime']==reg and x['policy']==pol] for pol in ['none','daily','band']],tick_labels=['Unhedged','Daily','Band'])
        ax.set(title=reg.title()+' held-out scenarios',ylabel='Terminal P&L per option (simulated)');ax.axhline(0,color='gray',lw=.8)
    fig.suptitle('Hedging error depends on model and jump risk — 150 paths per panel');fig.tight_layout();fig.savefig(OUT/'hedging_errors.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4))
    for pol in ['daily','band']:
        z=[x for x in costs if x['policy']==pol];ax.plot([x['fee_bps'] for x in z],[x['rmse'] for x in z],marker='o',label=pol)
    ax.set(xlabel='Assumed stock trading cost (bp)',ylabel='Terminal P&L RMSE',title='Cost sensitivity — same held-out diffusion paths');ax.legend();fig.tight_layout();fig.savefig(OUT/'cost_sensitivity.svg');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    spots=list(range(65,136));
    for days in [5,21,63]:
        gs=[greeks(s,100,days/252,.02,.25) for s in spots]
        axs[0].plot(spots,[g['delta'] for g in gs],label=f'{days} days');axs[1].plot(spots,[g['gamma'] for g in gs],label=f'{days} days')
    for ax,title in zip(axs,['Delta','Gamma']):ax.set(xlabel='Spot (strike 100)',ylabel=title,title=title+' near expiry');ax.legend()
    fig.tight_layout();fig.savefig(OUT/'greeks.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4));keys=['delta_component','gamma_component','theta_component','approximation_residual']
    ax.bar(['Delta','Gamma','Theta','Residual'],[sum(x[k] for x in example) for k in keys],color=['#2c6485','#568c78','#c3814f','#965971']);ax.set(ylabel='Option value change attribution',title='Jump-path Taylor attribution — residual includes higher orders');fig.tight_layout();fig.savefig(OUT/'attribution.svg');plt.close(fig)
    if args.historical_csv:
        p=Path(args.historical_csv);records=list(csv.DictReader(p.open()));valid=[(x['Date'],float(x[args.column])) for x in records if x.get(args.column)]
        assert len(valid)>123 and all(valid[i][0]<valid[i+1][0] for i in range(len(valid)-1)), 'chronological unique dates and sufficient history required'
        assert all(math.isfinite(x[1]) and x[1]>0 for x in valid), 'positive finite prices required'
        historical=[]
        for start in range(60,len(valid)-63,63):
            prior=[math.log(valid[i][1]/valid[i-1][1]) for i in range(start-59,start+1)];vol=max(.05,min(1.5,statistics.stdev(prior)*math.sqrt(252)))
            prices=[v/valid[start][1]*100 for _,v in valid[start:start+64]]
            for policy in ['none','daily','band']:
                r=hedge(prices,policy,band=band,vol=vol)
                historical.append(dict(start=valid[start][0],end=valid[start+63][0],policy=policy,assumed_vol=vol,terminal_pnl=r['terminal_pnl'],fees=r['fees']))
        writecsv('historical_underlying_replay.csv',historical)
        report['historical_underlying_replay']={'source':'Yahoo Finance vendor-adjusted close cache from prior research','source_url':'https://finance.yahoo.com/quote/'+args.column+'/history/','access_date':'2026-10-24','input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'symbol':args.column,'blocks':len(historical)//3,'pricing':'Hypothetical ATM European calls; IV proxy from preceding 60 log returns, frozen per block','limitations':'NOT a historical option-chain backtest. Adjusted prices are a total-return proxy, and dt=1/252 ignores calendar gaps. No actual contracts, strikes, expiries, quotes or borrow verified. Raw source prices not redistributed.'}
        fig,ax=plt.subplots(figsize=(10,4))
        for pol in ['none','daily','band']:
            z=[x for x in historical if x['policy']==pol];ax.plot(range(len(z)),[x['terminal_pnl'] for x in z],label=pol)
        ax.axhline(0,color='gray',lw=.8);ax.set(xlabel='Non-overlapping 63-observation block',ylabel='Model P&L per option',title='DLF underlying replay — hypothetical options, not realised returns');ax.legend();fig.tight_layout();fig.savefig(OUT/'historical_replay.svg');plt.close(fig)
    report['hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.csv')}
    (OUT/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps({'band':band,'heldout':summary,'historical':report.get('historical_underlying_replay',{})},indent=2))
if __name__=='__main__':run()

