import sys, json
import numpy as np
R='<repo>/'
sys.path.insert(0, R+'src')
from collection_simulator.config import load_config
from collection_simulator import generator as gen
H=9
def run(cfg, replicate=2, batch=50000):
    total=int(cfg['population']['borrowers']); regional=gen.regional_shocks(cfg)
    parts=[]; loan_next=1
    for bi,start,n in gen._batches(total,batch):
        b,hd,lo=gen._generate_population(cfg,replicate,bi,n,start,loan_next,regional); loan_next+=len(lo)
        s0=lo['initial_status'].to_numpy(dtype=object); l0=lo['days_in_credito_em_liquidacao'].to_numpy(np.int64)
        inc=np.isin(s0,['delinquent','credito_em_liquidacao']) & ~((s0=='credito_em_liquidacao')&(l0>180))
        rec=gen._simulate_batch(cfg,b,hd,lo,replicate,bi,None,n_months=H,loan_mask=inc)
        sel=np.flatnonzero(inc)
        parts.append(dict(B0=lo['outstanding_balance'].to_numpy(np.float64)[sel], first=rec['first_recovery_month'][sel],
            d0=rec['discount0'][sel].astype(float), disc=rec['discount'][sel], ch=rec['channel'][sel], expl=rec['is_exploration'][sel],
            alive=rec['alive'][sel], cash=rec['recovered_amount'][sel].sum(1), recov=rec['recovered'][sel], status=rec['status'][sel]))
    return {k:np.concatenate([p[k] for p in parts]) for k in parts[0]}
for world in ('world_a_on','world_b_on'):
    out={}
    for arm,eps in (('e',None),('0',0.0)):
        cfg=load_config(R+f'configs/tmlr/{world}.yaml'); cfg['seed']=7001; cfg['population']['borrowers']=200000
        if eps is not None: cfg['actions']['exploration']['epsilon']=eps
        out[arm]=run(cfg)
    e,z=out['e'],out['0']; n=len(e['B0'])
    x0=e['expl'][:,0]
    for a,nm in ((z,'eps0'),(e,'eps')):
        paid=(a['first']>=0)&(a['first']<H); idx=np.where(paid,a['first'],0); dfirst=a['disc'][np.arange(n),idx]
        late=paid&(a['first']>0); m0=paid&(a['first']==0)
        print(world,nm,'rate %.4f%%'%(100*paid.mean()),'share m0 %.3f'%(m0.sum()/paid.sum()),'mean d_first all %.3f, first>0 %.3f, first==0 %.3f'%(dfirst[paid].mean(),dfirst[late].mean(),dfirst[m0].mean()),
              'mean d0 among paid %.3f'%a['d0'][paid].mean(), 'n paid', paid.sum(), 'multi-recov share among paid %.3f'%((a['recov'].sum(1)>1)[paid].mean()))
        a['paid']=paid; a['dfirst']=dfirst
    # month-0 contact share on explored loans
    none_idx=list(gen.CHANNELS).index('none')
    print(' month0 on explored loans: incumbent no-contact share %.3f; incumbent mean d0 contacted %.3f; explored mean %.3f'%((z['ch'][x0,0]==none_idx).mean(), z['d0'][x0][z['ch'][x0,0]!=none_idx].mean(), e['d0'][x0].mean()))
    print(' channel shares incumbent month0 (explored loans):', {c: round(float((z['ch'][x0,0]==i).mean()),3) for i,c in enumerate(gen.CHANNELS)})
    later=e['expl'][:,1:]&z['alive'][:,1:]
    print(' later explored slots: incumbent no-contact share %.3f'%((z['ch'][:,1:][later]==none_idx).mean()), 'incumbent field share %.3f'%((z['ch'][:,1:][later]==gen.CHANNELS.index('field_visit')).mean()))
    # recovery-rate decomposition
    dp=e['paid'].astype(float)-z['paid'].astype(float)
    print(' recovery increase pp total %.4f; on month0-explored loans %.4f; on other loans %.4f'%(100*dp.mean(),100*(dp*x0).sum()/n,100*(dp*~x0).sum()/n))
    m0e=(e['first']==0)&e['paid']; m0z=(z['first']==0)&z['paid']
    print(' first-recovery-at-month0 increase pp %.4f; later %.4f'%(100*(m0e.mean()-m0z.mean()), 100*((e['paid']&~m0e).mean()-(z['paid']&~m0z).mean())))
    # recovery-month accounting decomposition
    v=lambda a: np.where(a['paid'],a['B0']*(1-a['dfirst']),0.0)
    vb=lambda a: a['paid']*a['B0']*(1-a['d0'])
    d=v(z)-v(e); db=vb(z)-vb(e)
    print(' Delta recmonth %.3f (m0expl %.3f other %.3f); benchmark %.3f (m0expl %.3f other %.3f)'%(d.mean(),(d*x0).sum()/n,(d*~x0).sum()/n,db.mean(),(db*x0).sum()/n,(db*~x0).sum()/n))
    # pure discount component on loans paid in both arms (recovery-month): B0*(d_e - d_0)
    both=e['paid']&z['paid']
    comp_disc=(np.where(both,e['B0']*(e['dfirst']-z['dfirst']),0)).sum()/n
    print(' recmonth: discount-at-recovery component on loans recovering in both arms %.3f; recovery-status component %.3f'%(-(-comp_disc), d.mean()-comp_disc))
    comp_disc_b=(np.where(both,e['B0']*(e['d0']-z['d0']),0)*x0).sum()/n
    print(' benchmark month0-explored: pure discount charge on loans recovering in both arms %.3f; rest %.3f'%(comp_disc_b,(db*x0).sum()/n-comp_disc_b))
