from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import argparse
p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1])
p.add_argument('--tables',type=Path,required=True,help='Campaign aggregate table directory')
a=p.parse_args()
out=a.out; out.mkdir(parents=True,exist_ok=True)
ROOT=out
fig,ax=plt.subplots(figsize=(11,6.2)); ax.set(xlim=(0,11),ylim=(0,6.2)); ax.axis('off')
boxes={
'a':(.15,4.65,2.3,1.0,'(a) Parameters','Hidden coupling, noise,\nexploration, outcome\nmechanism'),
'b':(3.0,4.65,3.0,1.0,'(b) World simulator','Keyed random streams, full settlement\nOne million loans per population'),
'c':(6.65,4.65,3.9,1.0,'(c) Logged population','Actions, outcomes, exploration flags\n12-month panel, initial-decision cohort'),
'f':(.15,2.25,2.9,1.35,'(f) Privileged information','Hidden factors and probabilities\nIndependent annotation population\nSpecified corruption'),
'g':(.15,.15,2.9,1.35,'(g) Policy references','Three independent populations\nCandidates paired within each\nShared regional shocks'),
'd':(6.65,2.65,3.9,1.0,'(d) Estimator views','36 tabular contexts or 15 observables\n45 action cells, estimated propensities'),
'e':(6.65,.35,3.9,1.35,'(e) Estimator panel','DM, IS, SNIPS, DR\nTabular and boosted nuisances\nAnnotation and randomized-pilot methods'),
'h':(3.55,.35,2.55,1.35,'(h) Grading','Error and RMSE\nReference containment\nSelection and score regret')}
for k,(x,y,w,h,title,body) in boxes.items():
    priv=k in ('f','g')
    face='#fff3e0' if priv else '#eaf2f8'
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.05',facecolor=face,edgecolor='#a76a21' if priv else '#355c79',linewidth=1.2))
    ax.text(x+w/2,y+h-.2,title,ha='center',va='top',fontsize=10,fontweight='bold')
    ax.text(x+w/2,y+h-.48,body,ha='center',va='top',fontsize=8.5,linespacing=1.4)
def arrow(p,q,dashed=False):
    ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=12,linewidth=1.15,linestyle='--' if dashed else '-',color='#6d5a45' if dashed else '#355c79'))
arrow((2.5,5.15),(2.95,5.15)); arrow((6.05,5.15),(6.6,5.15))
arrow((8.6,4.6),(8.6,3.7)); arrow((8.6,2.6),(8.6,1.75)); arrow((6.6,1.0),(6.15,1.0))
arrow((3.6,4.6),(2.1,3.65),True); arrow((3.1,2.9),(6.6,1.25),True)
arrow((3.1,.8),(3.5,.8),True)
ax.plot([5.8,5.8,1.65],[4.6,2.0,2.0],linestyle='--',linewidth=1.15,color='#6d5a45')
arrow((1.65,2.0),(1.65,1.55),True)
fig.savefig(out/'fig_pipeline.pdf',bbox_inches='tight',pad_inches=.08)
fig.savefig(out/'fig_pipeline.svg',bbox_inches='tight',pad_inches=.08)
fig.savefig(out/'fig_pipeline.png',dpi=150,bbox_inches='tight',pad_inches=.08)
fig.savefig(ROOT/'pipeline-preview.png',dpi=130,bbox_inches='tight',pad_inches=.08)
plt.close(fig)

with (a.tables/'error_summary.csv').open() as f: rows=list(csv.DictReader(f))
index={(r['cond'],r['regime'],r['estimator'],r['target']):r for r in rows}
fig,axes=plt.subplots(1,3,figsize=(10.4,3.4),sharey=True)
conds=['A_off','A_on','B_off','B_on']
models=[('tabular','dr','Tabular DR','#386cb0',-.18),('nontabular','dr','Boosted DR','#2c8c62',0),('tabular','pilot_is','Pilot-IS','#c56e23',.18)]
for ax,p,title in zip(axes,['pi_far','pi_near','pi_stage'],[r'$\pi_{\mathrm{visit}}$',r'$\pi_{\mathrm{sms}}$',r'$\pi_{\mathrm{stage}}$']):
    ax.axhline(0,color='0.5',linewidth=.7)
    for reg,m,label,color,delta in models:
        rs=[index[c,reg,m,p] for c in conds]
        ax.errorbar([i+delta for i in range(4)],[float(r['mean_error']) for r in rs],yerr=[float(r['se_mean_error']) for r in rs],fmt='o',ms=4,capsize=3,label=label,color=color)
    ax.set(xticks=range(4),xticklabels=['A off','A on','B off','B on'],title=title)
    ax.tick_params(axis='x',labelsize=8); ax.grid(axis='y',alpha=.18)
axes[0].set_ylabel('Mean score error ± one SE (US$/decision)')
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.52,-.01))
fig.tight_layout(rect=(0,.08,1,1))
fig.savefig(out/'fig_campaign_errors.pdf',bbox_inches='tight')
fig.savefig(ROOT/'errors-preview.png',dpi=130,bbox_inches='tight')
plt.close(fig)
print('Generated vector pipeline and campaign error figure')
