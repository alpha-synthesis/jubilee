import sys
import numpy as np

D = "<scratch>/expl_scopeaudit/"


def se(x):
    return x.std(ddof=1) / np.sqrt(len(x))


def report(tag):
    z = dict(np.load(D + tag + ".npz"))
    n = len(z["B0"])
    B0 = z["B0"]
    R = {a: z[f"paid_{a}"] * B0 * (1 - z[f"d0_{a}"]) for a in "en"}
    Rt = {a: z[f"paid_{a}"] * B0 * (1 - z[f"dtau_{a}"]) for a in "en"}
    C = {a: z[f"cash_{a}"] for a in "en"}
    x0 = z["expl0_e"]
    assert not z["expl0_n"].any()
    print(f"== {tag}: n={n}")
    print(f"V0={R['n'].mean():.6f} Ve={R['e'].mean():.6f}")
    for name, Rw in (("R(conv,d0)", R), ("Rtau(d at rec month)", Rt), ("cash", C)):
        d = Rw["n"] - Rw["e"]
        print(f"{name:22s} V0={Rw['n'].mean():8.2f} Delta={d.mean():+.3f} (se {se(d):.3f})"
              f"  month0-explored part={(d*x0).sum()/n:+.3f}  other={(d*~x0).sum()/n:+.3f}")
    pe, pn = z["paid_e"], z["paid_n"]
    te, tn = z["tau_e"], z["tau_n"]
    print(f"recovery rate n={pn.mean():.5f} e={pe.mean():.5f}")
    print(f"share of recoveries (eps=0 arm) at month 0: {(tn==0).sum()/pn.sum():.3f}")
    # month-0 explored loans: decompose R difference
    d = R["n"] - R["e"]
    both = pe & pn & x0
    only_n = pn & ~pe & x0
    only_e = pe & ~pn & x0
    print("-- month-0 explored loans (contribution per cohort loan):")
    print(f"  recovered in both arms: share {both.mean():.5f}, contribution {(d*both).sum()/n:+.3f}")
    b_t0 = both & (tn == 0) & (te == 0)
    b_later = both & (tn > 0) & (te > 0)
    print(f"    both recover at month 0: {(d*b_t0).sum()/n:+.3f}; both recover later (tau>0): {(d*b_later).sum()/n:+.3f}"
          f"; same tau>0: {(d*(b_later&(tn==te))).sum()/n:+.3f}")
    print(f"  recovered only in eps=0 arm: share {only_n.mean():.5f}, contribution {(d*only_n).sum()/n:+.3f}")
    print(f"  recovered only in eps arm:   share {only_e.mean():.5f}, contribution {(d*only_e).sum()/n:+.3f}")
    print(f"  mean d0 on month-0 explored loans: eps arm {z['d0_e'][x0].mean():.4f} vs incumbent {z['d0_n'][x0].mean():.4f}")
    print(f"  ... among those recovering in both: eps {z['d0_e'][both].mean():.4f} vs inc {z['d0_n'][both].mean():.4f}")
    # incumbent 'none' share at month 0 among explored
    print(f"  incumbent chose 'none' at month 0 for {np.mean(z['chan0_n'][x0]=='none'):.3f} of the month-0 explored loans")
    # Rtau month-0 part decomposition
    dt = Rt["n"] - Rt["e"]
    print(f"  under Rtau: both-recover part {(dt*both).sum()/n:+.3f}, only_n {(dt*only_n).sum()/n:+.3f}, only_e {(dt*only_e).sum()/n:+.3f}")
    # other loans
    o = ~x0
    print("-- other loans:")
    for name, Rw in (("R", R), ("Rtau", Rt), ("cash", C)):
        dd = Rw["n"] - Rw["e"]
        bo = pe & pn & o
        on = pn & ~pe & o
        oe = pe & ~pn & o
        print(f"  {name:5s}: both {(dd*bo).sum()/n:+.3f}  only_n {(dd*on).sum()/n:+.3f} ({on.mean():.5f})"
              f"  only_e {(dd*oe).sum()/n:+.3f} ({oe.mean():.5f})")
    # discounts at explored later months vs incumbent at same loan-month, conditional on both alive
    ae, an = z["alive_e"], z["alive_n"]
    xe = z["expl_e"]
    m = xe & ae & an
    m[:, 0] = False
    de, dn = z["disc_e"], z["disc_n"]
    ce, cn = z["chan_e"], z["chan_n"]
    print(f"-- later explored loan-months (both alive): {m.sum()}")
    print(f"  mean discount explored {de[m].mean():.4f} vs incumbent same slot {dn[m].mean():.4f};"
          f" incumbent 'none' share {(cn[m]==0).mean():.3f}")
    inc_contact = m & (cn != 0)
    print(f"  where incumbent contacts: explored disc {de[inc_contact].mean():.4f} vs incumbent {dn[inc_contact].mean():.4f}")
    # month-0
    m0 = xe[:, 0] & ae[:, 0]
    print(f"  month 0: explored disc {de[m0,0].mean():.4f} vs incumbent {dn[m0,0].mean():.4f}; inc none {(cn[m0,0]==0).mean():.3f}")


for t in sys.argv[1:]:
    report(t)
